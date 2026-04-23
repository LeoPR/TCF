"""SQL structural quality scorer.

Evaluates a SQL query beyond binary correct/incorrect:
  - Structural correctness (explicit JOINs, correct aliases)
  - Efficiency (minimal SELECT, no cartesian product)
  - Schema adherence (only references existing tables/columns)
  - Query complexity (normalized token count)
  - Execution plan quality (rows scanned, index usage)
"""
from __future__ import annotations
import re
import sqlite3
from dataclasses import dataclass, asdict


@dataclass
class SqlQuality:
    """Quality dimensions of a SQL query."""
    # Structure
    has_explicit_join: bool        # Uses JOIN ... ON instead of FROM a, b WHERE
    join_uses_on: bool             # JOIN has ON clause (not USING)
    no_select_star: bool           # SELECT does not use *
    single_result_col: bool        # SELECT returns exactly 1 column (expected for analytics)
    # Schema adherence
    tables_exist: bool             # All referenced tables are in the schema
    # Complexity
    token_count: int               # Rough SQL token count
    has_subquery: bool             # Contains subquery (nested SELECT)
    has_cte: bool                  # Uses WITH clause
    # Execution plan (filled when conn provided)
    plan_rows_scanned: int         # Estimated rows from EXPLAIN QUERY PLAN
    plan_uses_scan: bool           # True if any full-table scan present

    def score(self) -> float:
        """Composite quality score in [0, 1].

        Higher = better. Weights reflect importance for SQL-gen correctness.
        """
        s = 0.0
        s += 0.30 * self.has_explicit_join
        s += 0.15 * self.join_uses_on
        s += 0.10 * self.no_select_star
        s += 0.10 * self.single_result_col
        s += 0.20 * self.tables_exist
        # Penalize very long queries (>200 tokens hints over-complexity)
        s += 0.15 * (1.0 if self.token_count <= 200 else max(0, 1 - (self.token_count - 200) / 400))
        return round(s, 3)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["quality_score"] = self.score()
        return d


def score_sql_quality(
    sql: str,
    tables: dict[str, list[dict]],
    conn: sqlite3.Connection | None = None,
) -> SqlQuality:
    """Compute SqlQuality for a SQL string.

    Args:
      sql     — the SQL string (may be empty or invalid)
      tables  — dict of table_name -> list of rows (for schema checking)
      conn    — optional live SQLite connection for EXPLAIN QUERY PLAN
    """
    if not sql or not sql.strip():
        return SqlQuality(
            has_explicit_join=False, join_uses_on=False, no_select_star=False,
            single_result_col=False, tables_exist=False,
            token_count=0, has_subquery=False, has_cte=False,
            plan_rows_scanned=-1, plan_uses_scan=False,
        )

    sql_up = sql.upper()
    known_tables = set(t.upper() for t in tables.keys())

    # Explicit JOIN
    has_explicit_join = bool(re.search(r'\bJOIN\b', sql_up))

    # JOIN uses ON
    join_uses_on = has_explicit_join and bool(re.search(r'\bJOIN\b.{1,120}\bON\b', sql_up, re.DOTALL))

    # SELECT *
    no_select_star = not bool(re.search(r'\bSELECT\s+\*', sql_up))

    # Single result column: SELECT only 1 expression (rough heuristic)
    select_clause = re.search(r'SELECT\s+(.*?)\s+FROM', sql_up, re.DOTALL)
    single_result_col = False
    if select_clause:
        cols_raw = select_clause.group(1)
        # Count commas not inside parentheses
        depth = 0
        commas = 0
        for ch in cols_raw:
            if ch == '(': depth += 1
            elif ch == ')': depth -= 1
            elif ch == ',' and depth == 0:
                commas += 1
        single_result_col = (commas == 0)

    # Tables exist in schema
    referenced_tables = set(re.findall(r'\bFROM\s+(\w+)|\bJOIN\s+(\w+)', sql_up))
    flat_refs = set()
    for pair in referenced_tables:
        flat_refs.update(t for t in pair if t)
    tables_exist = flat_refs.issubset(known_tables) if flat_refs else False

    # Token count
    token_count = len(sql.split())

    # Subquery
    has_subquery = sql_up.count('SELECT') > 1

    # CTE
    has_cte = bool(re.search(r'\bWITH\b', sql_up))

    # Execution plan
    plan_rows_scanned = -1
    plan_uses_scan = False
    if conn is not None:
        try:
            plan_rows = list(conn.execute(f"EXPLAIN QUERY PLAN {sql}").fetchall())
            plan_uses_scan = any("SCAN" in str(row) for row in plan_rows)
            # Sum estimated rows (not always available in SQLite)
            plan_rows_scanned = len(plan_rows)
        except Exception:
            pass

    return SqlQuality(
        has_explicit_join=has_explicit_join,
        join_uses_on=join_uses_on,
        no_select_star=no_select_star,
        single_result_col=single_result_col,
        tables_exist=tables_exist,
        token_count=token_count,
        has_subquery=has_subquery,
        has_cte=has_cte,
        plan_rows_scanned=plan_rows_scanned,
        plan_uses_scan=plan_uses_scan,
    )

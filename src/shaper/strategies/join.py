"""Join strategy — normalized (separate tables) vs flat (single supertable).

- normalized: passthrough, tables stay separate with FK references
- flat: JOIN all selected tables into one supertable via SQL,
  resolving FKs to readable names, dropping ID columns

Uses metadata.json FK declarations to build JOIN SQL automatically.
"""

from __future__ import annotations

from typing import Any

from ..pipeline import register_strategy


def _build_flat_sql(reader, table_names: list[str], tables: dict) -> str | None:
    """Build a JOIN SQL from FK metadata. Returns None if no joins possible."""
    if len(table_names) <= 1:
        return None

    meta = reader.metadata
    tables_meta = meta.get("tables", {})

    # Find the fact table: the one with FKs pointing to OTHER selected tables.
    # Tiebreaker: most rows (the largest table is typically the fact table).
    def _score(name):
        fks = tables_meta.get(name, {}).get("fk", {})
        # Count FKs that point to tables IN our selection
        joinable = sum(1 for ref in fks.values()
                       if ref.split(".")[0] in set(table_names))
        n_rows = len(tables.get(name, []))
        return (joinable, n_rows)

    ordered = sorted(table_names, key=_score, reverse=True)
    fact = ordered[0]

    fact_fk_count = len(tables_meta.get(fact, {}).get("fk", {}))
    if fact_fk_count == 0:
        return None  # no FKs to join on

    # Build JOIN chain
    joined = {fact}
    joins = []
    select_cols = []

    # Add all columns from fact table (excluding FK ID columns)
    fact_fks = set(tables_meta.get(fact, {}).get("fk", {}).keys())
    fact_cols = list(tables_meta.get(fact, {}).get("columns", {}).keys())
    pk_cols = tables_meta.get(fact, {}).get("pk", [])

    for col in fact_cols:
        if col not in fact_fks and col not in pk_cols:
            select_cols.append(f'"{fact}"."{col}"')

    # Walk FK relationships
    for fk_col, ref in tables_meta.get(fact, {}).get("fk", {}).items():
        ref_table, ref_col = ref.split(".")
        if ref_table not in set(table_names):
            continue  # referenced table not in selection

        # Find a "label" column in the referenced table (first non-PK text column)
        ref_meta = tables_meta.get(ref_table, {})
        ref_pk = ref_meta.get("pk", [])
        ref_columns = ref_meta.get("columns", {})
        label_col = None
        for rc, rc_meta in ref_columns.items():
            if rc not in ref_pk and rc_meta.get("type") in ("string", "date"):
                label_col = rc
                break
        if label_col is None:
            # No good label, skip this join
            continue

        # Use FK column name without prefix as alias
        alias = fk_col.replace("_key", "").lstrip("lops_")
        if not alias:
            alias = ref_table

        joins.append(
            f'LEFT JOIN "{ref_table}" ON "{fact}"."{fk_col}" = "{ref_table}"."{ref_col}"'
        )
        select_cols.append(f'"{ref_table}"."{label_col}" AS "{alias}_{label_col}"')
        joined.add(ref_table)

    if not joins:
        return None

    sql = f'SELECT {", ".join(select_cols)} FROM "{fact}" ' + " ".join(joins)
    return sql


def _apply(reader, tables, request, trace):
    if request.join_level == "normalized":
        trace.append("join: normalized (tables stay separate)")
        return tables

    if request.join_level != "flat":
        trace.append(f"join: unknown level '{request.join_level}', using normalized")
        return tables

    # Flat mode
    table_names = list(tables.keys())

    if len(table_names) <= 1:
        trace.append("join: flat requested but only 1 table, no join needed")
        return tables

    sql = _build_flat_sql(reader, table_names, tables)
    if sql is None:
        trace.append("join: flat requested but no joinable FKs found, keeping separate")
        return tables

    try:
        raw_rows = reader.query(sql)
        # Get column names from cursor description
        cursor = reader.con.execute(sql)
        col_names = [desc[0] for desc in cursor.description]

        flat_rows = [dict(zip(col_names, row)) for row in raw_rows]

        # Use fact table name + "_flat" as the result table name
        fact_name = table_names[0]  # first is typically the one with most FKs
        # Actually find the fact table (most rows)
        fact_name = max(tables.keys(), key=lambda t: len(tables[t]))
        flat_name = f"{fact_name}_flat"

        trace.append(
            f"join: flat -> {flat_name} ({len(flat_rows):,} rows, "
            f"{len(col_names)} cols from {len(table_names)} tables)"
        )
        trace.append(f"join: SQL = {sql[:200]}...")

        return {flat_name: flat_rows}

    except Exception as e:
        trace.append(f"join: ERROR building flat table: {e}")
        return tables


register_strategy("join_resolver", _apply)

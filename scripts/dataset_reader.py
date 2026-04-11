"""Dataset reader — loads data from our SQLite hub into generic Python structures.

**This is a SUPPORT CLIENT, not part of the TCF core library.**

The TCF core (`src/tcf/`) operates on generic Python structures:
    - list[dict]                          (row-oriented)
    - dict[str, list]                     (column-oriented)
    - list[tuple] + list[str] (columns)   (positional)

Anyone installing TCF can write their OWN reader for their OWN sources
(Postgres, Parquet, pandas, Arrow, HTTP API, whatever) — as long as they
produce these structures. They don't need this module.

We provide this reader purely so that OUR scripts (quality reports,
derivations, ground truth computation, etc.) have a single, well-tested
place to read from the SQLite hub we build in `Z:/tcf-data/interim/`.

Usage:
    from dataset_reader import DatasetReader

    reader = DatasetReader("tpch-sf001")  # opens the SQLite file

    # List available tables
    for t in reader.tables:
        print(t)

    # Get metadata (from JSON in git, not SQLite)
    meta = reader.metadata
    schema = reader.schema("lineitem")  # {"l_orderkey": {"type":"int",...}, ...}

    # Read rows
    rows = reader.rows("lineitem", limit=100)       # list[dict]
    cols = reader.columns("lineitem", limit=100)    # dict[str, list]

    # Stream for large tables
    for row in reader.iter_rows("lineitem", limit=None):
        ...

    # Execute arbitrary SQL (for ground truth computation)
    result = reader.query("SELECT COUNT(*) FROM lineitem")

    # Stats (for quality reports)
    info = reader.column_stats("lineitem", "l_extendedprice")
    # → {"type":"numeric", "count":60175, "min":904, "max":..., "mean":..., ...}

    reader.close()

    # Or use as a context manager
    with DatasetReader("adult-census") as r:
        rows = r.rows("adult", limit=1000)
"""

from __future__ import annotations

import json
import sqlite3
import statistics
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _paths import interim_db, PROJECT_ROOT  # noqa: E402


# ---------------------------------------------------------------------------
# Type classification helpers
# ---------------------------------------------------------------------------

_NUMERIC_TYPES = {"int", "float", "bool"}
_TEXT_TYPES = {"string", "date", "datetime"}


def is_numeric(col_meta: dict) -> bool:
    return col_meta.get("type") in _NUMERIC_TYPES


def is_text(col_meta: dict) -> bool:
    return col_meta.get("type") in _TEXT_TYPES


# ---------------------------------------------------------------------------
# DatasetReader
# ---------------------------------------------------------------------------

class DatasetReader:
    """Lightweight SQLite reader that knows how to interpret our metadata.json."""

    def __init__(self, dataset_name: str):
        self.name = dataset_name
        self._db_path = interim_db(dataset_name)
        if not self._db_path.exists():
            raise FileNotFoundError(
                f"SQLite DB not found: {self._db_path}\n"
                f"Run: python scripts/csv_to_sqlite.py {dataset_name}"
            )

        self._meta_path = (
            PROJECT_ROOT / "datasets" / "canonical" / dataset_name / "metadata.json"
        )
        if not self._meta_path.exists():
            raise FileNotFoundError(f"metadata.json not found: {self._meta_path}")

        self.metadata: dict = json.loads(self._meta_path.read_text(encoding="utf-8"))
        self._con: sqlite3.Connection | None = None

    # -- connection lifecycle ----------------------------------------------

    @property
    def con(self) -> sqlite3.Connection:
        if self._con is None:
            self._con = sqlite3.connect(self._db_path)
            self._con.row_factory = sqlite3.Row
        return self._con

    def close(self) -> None:
        if self._con is not None:
            self._con.close()
            self._con = None

    def __enter__(self) -> "DatasetReader":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    # -- schema introspection ----------------------------------------------

    @property
    def tables(self) -> list[str]:
        """List of table names in the metadata-defined order."""
        return self.metadata.get("table_order") or list(self.metadata["tables"].keys())

    def schema(self, table: str) -> dict[str, dict]:
        """Return {column_name: {type, nullable, ...}} for a table."""
        return self.metadata["tables"][table]["columns"]

    def column_names(self, table: str) -> list[str]:
        return list(self.schema(table).keys())

    def pk(self, table: str) -> list[str]:
        return self.metadata["tables"][table].get("pk") or []

    def fk(self, table: str) -> dict[str, str]:
        return self.metadata["tables"][table].get("fk") or {}

    def row_count(self, table: str) -> int:
        row = self.con.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()
        return int(row[0])

    # -- reading rows ------------------------------------------------------

    def rows(self, table: str, limit: int | None = None) -> list[dict[str, Any]]:
        """Return list[dict] — row-oriented."""
        sql = f'SELECT * FROM "{table}"'
        if limit is not None:
            sql += f" LIMIT {int(limit)}"
        return [dict(r) for r in self.con.execute(sql).fetchall()]

    def iter_rows(self, table: str, limit: int | None = None) -> Iterator[dict[str, Any]]:
        """Stream rows as dicts. Use for large tables to avoid loading all in memory."""
        sql = f'SELECT * FROM "{table}"'
        if limit is not None:
            sql += f" LIMIT {int(limit)}"
        for r in self.con.execute(sql):
            yield dict(r)

    def columns(self, table: str, limit: int | None = None) -> dict[str, list]:
        """Return dict[col_name, list[values]] — column-oriented.

        This is the structure TCF's encoder will likely expect.
        """
        col_names = self.column_names(table)
        result: dict[str, list] = {c: [] for c in col_names}
        for row in self.iter_rows(table, limit=limit):
            for c in col_names:
                result[c].append(row[c])
        return result

    def query(self, sql: str, params: tuple = ()) -> list[tuple]:
        """Execute arbitrary SQL. Returns list of tuples.

        Use for ground-truth computation where you want raw numeric answers.
        """
        return [tuple(r) for r in self.con.execute(sql, params).fetchall()]

    # -- statistics for quality reports ------------------------------------

    def column_stats(self, table: str, column: str) -> dict[str, Any]:
        """Compute statistics on a single column.

        Returns a dict with keys depending on the column type:
        - numeric: count, null_count, min, max, mean, median, stdev, zeros, negatives
        - text:    count, null_count, distinct, top_values (top 5), entropy_bits
        """
        col_meta = self.schema(table).get(column)
        if col_meta is None:
            raise KeyError(f"{table}.{column} not in metadata")

        total = self.row_count(table)
        null_count = self.con.execute(
            f'SELECT COUNT(*) FROM "{table}" WHERE "{column}" IS NULL'
        ).fetchone()[0]

        base = {
            "name": column,
            "type": col_meta["type"],
            "nullable": col_meta.get("nullable", True),
            "count": total,
            "null_count": null_count,
            "non_null": total - null_count,
        }

        if is_numeric(col_meta):
            return {**base, **self._numeric_stats(table, column)}
        return {**base, **self._text_stats(table, column)}

    def _numeric_stats(self, table: str, column: str) -> dict:
        row = self.con.execute(
            f'SELECT MIN("{column}"), MAX("{column}"), AVG("{column}"), '
            f'       SUM(CASE WHEN "{column}" = 0 THEN 1 ELSE 0 END), '
            f'       SUM(CASE WHEN "{column}" < 0 THEN 1 ELSE 0 END) '
            f'FROM "{table}" WHERE "{column}" IS NOT NULL'
        ).fetchone()
        if row is None or row[0] is None:
            return {
                "min": None, "max": None, "mean": None,
                "median": None, "stdev": None,
                "zeros": 0, "negatives": 0,
            }
        mn, mx, avg, zeros, negs = row

        # median and stdev: need sample. For small columns fetch all; for big
        # columns sample to avoid loading millions of values.
        total_non_null = self.con.execute(
            f'SELECT COUNT(*) FROM "{table}" WHERE "{column}" IS NOT NULL'
        ).fetchone()[0]

        sample_size = min(total_non_null, 10_000)
        if sample_size > 0:
            vals = [
                v[0] for v in self.con.execute(
                    f'SELECT "{column}" FROM "{table}" '
                    f'WHERE "{column}" IS NOT NULL LIMIT {sample_size}'
                )
            ]
            median = statistics.median(vals)
            stdev = statistics.stdev(vals) if len(vals) > 1 else 0.0
        else:
            median, stdev = None, None

        return {
            "min": mn,
            "max": mx,
            "mean": round(avg, 4) if avg is not None else None,
            "median": round(median, 4) if median is not None else None,
            "stdev": round(stdev, 4) if stdev is not None else None,
            "zeros": int(zeros or 0),
            "negatives": int(negs or 0),
            "sampled_for_median": sample_size < total_non_null,
        }

    def _text_stats(self, table: str, column: str, top_k: int = 5) -> dict:
        distinct_row = self.con.execute(
            f'SELECT COUNT(DISTINCT "{column}") FROM "{table}"'
        ).fetchone()
        distinct = int(distinct_row[0]) if distinct_row else 0

        top_rows = self.con.execute(
            f'SELECT "{column}" AS val, COUNT(*) AS n '
            f'FROM "{table}" WHERE "{column}" IS NOT NULL '
            f'GROUP BY "{column}" ORDER BY n DESC LIMIT {top_k}'
        ).fetchall()
        top_values = [(r["val"], int(r["n"])) for r in top_rows]

        # Shannon entropy (in bits) based on all groups, not just top-K
        entropy = 0.0
        total = self.con.execute(
            f'SELECT COUNT(*) FROM "{table}" WHERE "{column}" IS NOT NULL'
        ).fetchone()[0]
        if total > 0 and distinct > 0:
            import math
            for row in self.con.execute(
                f'SELECT COUNT(*) FROM "{table}" '
                f'WHERE "{column}" IS NOT NULL '
                f'GROUP BY "{column}"'
            ):
                p = row[0] / total
                if p > 0:
                    entropy -= p * math.log2(p)

        return {
            "distinct": distinct,
            "top_values": top_values,
            "entropy_bits": round(entropy, 4),
        }


# ---------------------------------------------------------------------------
# Convenience context manager
# ---------------------------------------------------------------------------

@contextmanager
def open_dataset(name: str):
    """with open_dataset('tpch-sf001') as r: ..."""
    r = DatasetReader(name)
    try:
        yield r
    finally:
        r.close()


# ---------------------------------------------------------------------------
# Self-test / demo
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Test DatasetReader")
    parser.add_argument("dataset", nargs="?", default="tpch-sf001")
    args = parser.parse_args()

    with open_dataset(args.dataset) as r:
        print(f"Dataset: {r.name}")
        print(f"Tables:  {r.tables}")
        for t in r.tables:
            n = r.row_count(t)
            cols = r.column_names(t)
            print(f"  {t:12s}: {n:>8,d} rows, {len(cols)} cols, pk={r.pk(t)}, fk={list(r.fk(t).keys())}")

        # Sample a small table
        first = r.tables[0]
        print(f"\nSample rows from {first}:")
        for row in r.rows(first, limit=3):
            print(f"  {row}")

        # Column stats demo — first numeric column of last table
        last = r.tables[-1]
        schema = r.schema(last)
        for col_name, col_meta in schema.items():
            if is_numeric(col_meta):
                print(f"\nColumn stats: {last}.{col_name}")
                stats = r.column_stats(last, col_name)
                for k, v in stats.items():
                    print(f"  {k}: {v}")
                break

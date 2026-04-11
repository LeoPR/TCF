"""Convert canonical CSV datasets to SQLite databases with proper types,
primary keys, and foreign keys.

Reads metadata.json from datasets/canonical/{name}/ to get the schema,
reads CSVs from data_root/external/{name}/, writes SQLite to
data_root/interim/{name}.db.

Usage:
    python scripts/csv_to_sqlite.py              # all datasets
    python scripts/csv_to_sqlite.py tpch-sf001   # single dataset
    python scripts/csv_to_sqlite.py --verify     # check FKs after build
"""

from __future__ import annotations

import argparse
import csv
import json
import sqlite3
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _paths import external_dir, interim_db, ensure_dirs, PROJECT_ROOT  # noqa: E402


# Map metadata type names to SQLite column affinity
TYPE_MAP = {
    "int": "INTEGER",
    "float": "REAL",
    "string": "TEXT",
    "date": "TEXT",      # ISO date stored as TEXT (SQLite convention)
    "datetime": "TEXT",  # ISO datetime as TEXT
    "bool": "INTEGER",   # 0/1
}

# Special markers to convert to NULL during import
NULL_MARKERS = {"", "?", "NA", "NaN", "null", "None"}


def load_metadata(dataset_name: str) -> dict:
    meta_path = PROJECT_ROOT / "datasets" / "canonical" / dataset_name / "metadata.json"
    if not meta_path.exists():
        sys.exit(f"metadata.json not found: {meta_path}")
    return json.loads(meta_path.read_text(encoding="utf-8"))


def build_create_sql(table_name: str, table_meta: dict) -> str:
    """Build CREATE TABLE statement from metadata."""
    cols_sql = []
    for col_name, col_meta in table_meta["columns"].items():
        sql_type = TYPE_MAP.get(col_meta["type"], "TEXT")
        # Target columns are part of schema but usually not NOT NULL in raw data
        parts = [f'"{col_name}"', sql_type]
        if not col_meta.get("nullable", True):
            parts.append("NOT NULL")
        cols_sql.append(" ".join(parts))

    # PRIMARY KEY
    pk = table_meta.get("pk")
    if pk:
        pk_cols = ", ".join(f'"{c}"' for c in pk)
        cols_sql.append(f"PRIMARY KEY ({pk_cols})")

    # FOREIGN KEY
    for fk_col, ref in table_meta.get("fk", {}).items():
        ref_table, ref_col = ref.split(".")
        cols_sql.append(
            f'FOREIGN KEY ("{fk_col}") REFERENCES "{ref_table}"("{ref_col}")'
        )

    return f'CREATE TABLE "{table_name}" (\n  ' + ",\n  ".join(cols_sql) + "\n)"


def convert_value(val: str, type_name: str) -> object:
    """Convert a CSV string to the appropriate Python type for SQLite."""
    if val in NULL_MARKERS:
        return None
    if type_name == "int":
        try:
            return int(val)
        except ValueError:
            # Some "int" fields in Adult are actually floats in the CSV
            try:
                return int(float(val))
            except ValueError:
                return None
    if type_name == "float":
        try:
            return float(val)
        except ValueError:
            return None
    if type_name == "bool":
        v = val.strip().lower()
        if v in ("1", "true", "yes", "t", "y"):
            return 1
        if v in ("0", "false", "no", "f", "n"):
            return 0
        return None
    # string, date, datetime stored as TEXT
    return val


def load_csv_to_table(
    con: sqlite3.Connection,
    csv_path: Path,
    table_name: str,
    col_metas: dict[str, dict],
) -> int:
    """Load a CSV file into an existing table, applying type conversion."""
    with csv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        header = next(reader)

        # Validate header matches schema
        expected = list(col_metas.keys())
        if header != expected:
            print(f"  WARN: header mismatch in {table_name}")
            print(f"    CSV:    {header}")
            print(f"    schema: {expected}")

        # Build insert stmt
        placeholders = ", ".join("?" * len(header))
        col_list = ", ".join(f'"{c}"' for c in header)
        insert_sql = f'INSERT INTO "{table_name}" ({col_list}) VALUES ({placeholders})'

        # Type info ordered as in CSV
        types = [col_metas[c]["type"] for c in header]

        # Stream rows in batches for performance
        rows = []
        batch_size = 5000
        count = 0
        for row in reader:
            converted = [convert_value(v, t) for v, t in zip(row, types)]
            rows.append(converted)
            if len(rows) >= batch_size:
                con.executemany(insert_sql, rows)
                count += len(rows)
                rows = []
        if rows:
            con.executemany(insert_sql, rows)
            count += len(rows)

    return count


def convert_dataset(dataset_name: str, verify: bool = True) -> None:
    print(f"\n[sqlite] Converting dataset: {dataset_name}")
    meta = load_metadata(dataset_name)

    src_dir = external_dir(dataset_name)
    if not src_dir.exists():
        sys.exit(f"  raw data not found: {src_dir}\n  Did you run the download script?")

    db_path = interim_db(dataset_name)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    if db_path.exists():
        print(f"  removing existing: {db_path}")
        db_path.unlink()

    con = sqlite3.connect(db_path)
    con.execute("PRAGMA foreign_keys = OFF")  # disable while loading
    con.execute("PRAGMA journal_mode = OFF")
    con.execute("PRAGMA synchronous = OFF")

    # Use metadata table_order if present (TPC-H), else dict order
    tables_order = meta.get("table_order") or list(meta["tables"].keys())

    total_time = 0.0
    total_rows = 0
    for table_name in tables_order:
        table_meta = meta["tables"][table_name]
        csv_path = src_dir / f"{table_name}.csv"
        if not csv_path.exists():
            print(f"  SKIP: {table_name} (CSV not found at {csv_path})")
            continue

        create_sql = build_create_sql(table_name, table_meta)
        con.execute(create_sql)

        t0 = time.perf_counter()
        n = load_csv_to_table(con, csv_path, table_name, table_meta["columns"])
        elapsed = time.perf_counter() - t0
        total_time += elapsed
        total_rows += n
        print(f"  {table_name:12s}: {n:>8,d} rows in {elapsed:>6.2f}s")

    con.commit()

    # Enable FK checks for verification
    if verify:
        con.execute("PRAGMA foreign_keys = ON")
        violations = list(con.execute("PRAGMA foreign_key_check"))
        if violations:
            print(f"  FK VIOLATIONS: {len(violations)}")
            for v in violations[:5]:
                print(f"    {v}")
        else:
            print("  FK check: OK (no violations)")

    # Summary of table info
    print(f"  DB file: {db_path} ({db_path.stat().st_size / 1024:.1f} KB)")
    print(f"  Total: {total_rows:,} rows in {total_time:.2f}s")
    con.close()


def list_datasets() -> list[str]:
    root = PROJECT_ROOT / "datasets" / "canonical"
    return sorted([p.name for p in root.iterdir()
                   if p.is_dir() and (p / "metadata.json").exists()])


def main():
    parser = argparse.ArgumentParser(description="Convert CSVs to SQLite with typed schema")
    parser.add_argument("dataset", nargs="?", help="dataset name (default: all)")
    parser.add_argument("--no-verify", action="store_true", help="skip FK verification")
    args = parser.parse_args()

    ensure_dirs()

    if args.dataset:
        targets = [args.dataset]
    else:
        targets = list_datasets()
        print(f"[sqlite] Found {len(targets)} dataset(s): {targets}")

    for name in targets:
        convert_dataset(name, verify=not args.no_verify)

    print("\n[sqlite] Done.")


if __name__ == "__main__":
    main()

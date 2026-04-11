"""Generate baseline format derivations from the SQLite hub.

For each dataset and each table, writes:
    data_root/processed/{dataset}/csv/{table}.csv
    data_root/processed/{dataset}/jsonl/{table}.jsonl
    data_root/processed/{dataset}/markdown/{table}.md

Architecture:
    DatasetReader (scripts/dataset_reader.py)
        ↓ generic Python structures
    Writers (scripts/writers/*)
        ↓ files on disk

The TCF core library is NOT involved here — these are baseline
formats used as comparison points in benchmarks.

Usage:
    python scripts/derive_formats.py                # all datasets, all formats
    python scripts/derive_formats.py tpch-sf001     # single dataset
    python scripts/derive_formats.py --formats csv  # only CSV
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _paths import processed_dir, PROJECT_ROOT, ensure_dirs  # noqa: E402
from dataset_reader import DatasetReader  # noqa: E402
from writers import write_csv, write_jsonl, write_markdown  # noqa: E402


ALL_FORMATS = ("csv", "jsonl", "markdown")


def derive_dataset(dataset_name: str, formats: tuple[str, ...]) -> None:
    print(f"\n[derive] dataset: {dataset_name}")
    with DatasetReader(dataset_name) as reader:
        for table in reader.tables:
            columns = reader.column_names(table)
            n_rows = reader.row_count(table)
            print(f"  {table:12s} ({n_rows:>6,d} rows, {len(columns)} cols)")

            for fmt in formats:
                out_dir = processed_dir(dataset_name, fmt)
                out_dir.mkdir(parents=True, exist_ok=True)

                if fmt == "csv":
                    out_path = out_dir / f"{table}.csv"
                    t0 = time.perf_counter()
                    # Use iter_rows to avoid loading giant tables in memory
                    written = write_csv(out_path, columns, reader.iter_rows(table))
                    elapsed = time.perf_counter() - t0
                    size_kb = out_path.stat().st_size / 1024
                    print(f"    csv      {written:>6,d} rows  {size_kb:>8,.1f} KB  ({elapsed:.2f}s)")

                elif fmt == "jsonl":
                    out_path = out_dir / f"{table}.jsonl"
                    t0 = time.perf_counter()
                    written = write_jsonl(out_path, columns, reader.iter_rows(table))
                    elapsed = time.perf_counter() - t0
                    size_kb = out_path.stat().st_size / 1024
                    print(f"    jsonl    {written:>6,d} rows  {size_kb:>8,.1f} KB  ({elapsed:.2f}s)")

                elif fmt == "markdown":
                    out_path = out_dir / f"{table}.md"
                    t0 = time.perf_counter()
                    # Markdown: load all rows, but truncate large tables
                    all_rows = reader.rows(table)
                    written = write_markdown(out_path, columns, all_rows, max_rows=500)
                    elapsed = time.perf_counter() - t0
                    size_kb = out_path.stat().st_size / 1024
                    note = "" if written == n_rows else f" (truncated from {n_rows:,})"
                    print(f"    markdown {written:>6,d} rows{note}  {size_kb:>8,.1f} KB  ({elapsed:.2f}s)")


def list_datasets() -> list[str]:
    root = PROJECT_ROOT / "datasets" / "canonical"
    return sorted([p.name for p in root.iterdir()
                   if p.is_dir() and (p / "metadata.json").exists()])


def main():
    parser = argparse.ArgumentParser(description="Derive baseline formats from SQLite")
    parser.add_argument("dataset", nargs="?", help="dataset name (default: all)")
    parser.add_argument("--formats", nargs="+", default=list(ALL_FORMATS),
                        choices=ALL_FORMATS, help=f"formats to generate (default: all)")
    args = parser.parse_args()

    ensure_dirs()

    targets = [args.dataset] if args.dataset else list_datasets()
    formats = tuple(args.formats)

    for name in targets:
        derive_dataset(name, formats)

    print("\n[derive] Done.")


if __name__ == "__main__":
    main()

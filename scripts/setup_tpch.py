"""Download TPC-H dataset at Scale Factor 0.01 via DuckDB.

Writes CSV files to the configured data_root (see config/storage.json).
Also generates small samples in datasets/samples/tpch-sf001/ for git.

Usage:
    pip install -e ".[datasets]"
    python scripts/setup_tpch.py

    # or with a different scale factor
    python scripts/setup_tpch.py --sf 0.1
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

# Make scripts importable
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _paths import external_dir, ensure_dirs, PROJECT_ROOT  # noqa: E402


# TPC-H schema — PK, FK, column types and nullability.
# Sourced from TPC-H specification v3.0.1.
TPCH_SCHEMA = {
    "region": {
        "pk": ["r_regionkey"],
        "fk": {},
        "columns": {
            "r_regionkey": {"type": "int", "nullable": False},
            "r_name":      {"type": "string", "nullable": False},
            "r_comment":   {"type": "string", "nullable": True},
        },
    },
    "nation": {
        "pk": ["n_nationkey"],
        "fk": {"n_regionkey": "region.r_regionkey"},
        "columns": {
            "n_nationkey": {"type": "int", "nullable": False},
            "n_name":      {"type": "string", "nullable": False},
            "n_regionkey": {"type": "int", "nullable": False},
            "n_comment":   {"type": "string", "nullable": True},
        },
    },
    "supplier": {
        "pk": ["s_suppkey"],
        "fk": {"s_nationkey": "nation.n_nationkey"},
        "columns": {
            "s_suppkey":   {"type": "int", "nullable": False},
            "s_name":      {"type": "string", "nullable": False},
            "s_address":   {"type": "string", "nullable": False},
            "s_nationkey": {"type": "int", "nullable": False},
            "s_phone":     {"type": "string", "nullable": False},
            "s_acctbal":   {"type": "float", "nullable": False},
            "s_comment":   {"type": "string", "nullable": False},
        },
    },
    "customer": {
        "pk": ["c_custkey"],
        "fk": {"c_nationkey": "nation.n_nationkey"},
        "columns": {
            "c_custkey":    {"type": "int", "nullable": False},
            "c_name":       {"type": "string", "nullable": False},
            "c_address":    {"type": "string", "nullable": False},
            "c_nationkey":  {"type": "int", "nullable": False},
            "c_phone":      {"type": "string", "nullable": False},
            "c_acctbal":    {"type": "float", "nullable": False},
            "c_mktsegment": {"type": "string", "nullable": False},
            "c_comment":    {"type": "string", "nullable": False},
        },
    },
    "part": {
        "pk": ["p_partkey"],
        "fk": {},
        "columns": {
            "p_partkey":     {"type": "int", "nullable": False},
            "p_name":        {"type": "string", "nullable": False},
            "p_mfgr":        {"type": "string", "nullable": False},
            "p_brand":       {"type": "string", "nullable": False},
            "p_type":        {"type": "string", "nullable": False},
            "p_size":        {"type": "int", "nullable": False},
            "p_container":   {"type": "string", "nullable": False},
            "p_retailprice": {"type": "float", "nullable": False},
            "p_comment":     {"type": "string", "nullable": False},
        },
    },
    "partsupp": {
        "pk": ["ps_partkey", "ps_suppkey"],
        "fk": {
            "ps_partkey": "part.p_partkey",
            "ps_suppkey": "supplier.s_suppkey",
        },
        "columns": {
            "ps_partkey":    {"type": "int", "nullable": False},
            "ps_suppkey":    {"type": "int", "nullable": False},
            "ps_availqty":   {"type": "int", "nullable": False},
            "ps_supplycost": {"type": "float", "nullable": False},
            "ps_comment":    {"type": "string", "nullable": False},
        },
    },
    "orders": {
        "pk": ["o_orderkey"],
        "fk": {"o_custkey": "customer.c_custkey"},
        "columns": {
            "o_orderkey":      {"type": "int", "nullable": False},
            "o_custkey":       {"type": "int", "nullable": False},
            "o_orderstatus":   {"type": "string", "nullable": False},
            "o_totalprice":    {"type": "float", "nullable": False},
            "o_orderdate":     {"type": "date", "nullable": False},
            "o_orderpriority": {"type": "string", "nullable": False},
            "o_clerk":         {"type": "string", "nullable": False},
            "o_shippriority":  {"type": "int", "nullable": False},
            "o_comment":       {"type": "string", "nullable": False},
        },
    },
    "lineitem": {
        "pk": ["l_orderkey", "l_linenumber"],
        "fk": {
            "l_orderkey": "orders.o_orderkey",
            "l_partkey":  "part.p_partkey",
            "l_suppkey":  "supplier.s_suppkey",
        },
        "columns": {
            "l_orderkey":      {"type": "int", "nullable": False},
            "l_partkey":       {"type": "int", "nullable": False},
            "l_suppkey":       {"type": "int", "nullable": False},
            "l_linenumber":    {"type": "int", "nullable": False},
            "l_quantity":      {"type": "float", "nullable": False},
            "l_extendedprice": {"type": "float", "nullable": False},
            "l_discount":      {"type": "float", "nullable": False},
            "l_tax":           {"type": "float", "nullable": False},
            "l_returnflag":    {"type": "string", "nullable": False},
            "l_linestatus":    {"type": "string", "nullable": False},
            "l_shipdate":      {"type": "date", "nullable": False},
            "l_commitdate":    {"type": "date", "nullable": False},
            "l_receiptdate":   {"type": "date", "nullable": False},
            "l_shipinstruct":  {"type": "string", "nullable": False},
            "l_shipmode":      {"type": "string", "nullable": False},
            "l_comment":       {"type": "string", "nullable": False},
        },
    },
}

TABLE_ORDER = [
    "region", "nation", "supplier", "customer",
    "part", "partsupp", "orders", "lineitem",
]


def download_tpch(sf: float, verbose: bool = True) -> Path:
    """Download TPC-H CSVs to data_root/external/tpch-sfNNN/.

    Returns the output directory.
    """
    try:
        import duckdb
    except ImportError:
        sys.exit(
            "duckdb not installed. Run:\n"
            "    pip install -e \".[datasets]\""
        )

    sf_tag = f"sf{str(sf).replace('.', '').rstrip('0') or '0'}"
    dataset_name = f"tpch-{sf_tag}"
    ensure_dirs()
    output = external_dir(dataset_name)
    output.mkdir(parents=True, exist_ok=True)

    if verbose:
        print(f"[tpch] SF={sf} -> {output}")

    con = duckdb.connect(":memory:")
    con.execute("INSTALL tpch")
    con.execute("LOAD tpch")

    t0 = time.perf_counter()
    con.execute(f"CALL dbgen(sf={sf})")
    gen_time = time.perf_counter() - t0
    if verbose:
        print(f"[tpch] dbgen completed in {gen_time:.1f}s")

    table_stats: dict[str, int] = {}
    for table in TABLE_ORDER:
        path = output / f"{table}.csv"
        con.execute(
            f"COPY (SELECT * FROM {table}) TO '{path.as_posix()}' "
            "(HEADER, DELIMITER ',')"
        )
        count = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        table_stats[table] = count
        size_kb = path.stat().st_size / 1024
        if verbose:
            print(f"[tpch]   {table:10s}: {count:>8,d} rows  ({size_kb:>8,.1f} KB)")

    con.close()
    return output, table_stats, dataset_name


def write_metadata(dataset_name: str, sf: float, table_stats: dict[str, int]) -> None:
    """Write the metadata.json for this dataset."""
    meta_dir = PROJECT_ROOT / "datasets" / "canonical" / dataset_name
    meta_dir.mkdir(parents=True, exist_ok=True)

    meta = {
        "name": dataset_name,
        "scale_factor": sf,
        "source": "TPC-H Benchmark (via DuckDB tpch extension)",
        "origin": "https://www.tpc.org/tpch/",
        "license": "TPC Fair Use Agreement",
        "license_note": "Academic use permitted. See https://www.tpc.org/information/about/documentation.asp",
        "citation": "Transaction Processing Performance Council (TPC). TPC Benchmark H (TPC-H) Specification.",
        "downloaded_via": "duckdb tpch extension",
        "row_counts": table_stats,
        "table_order": TABLE_ORDER,
        "tables": TPCH_SCHEMA,
    }

    meta_path = meta_dir / "metadata.json"
    meta_path.write_text(
        json.dumps(meta, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"[tpch] metadata: {meta_path}")


def generate_samples(dataset_name: str, external_path: Path) -> None:
    """Copy small samples to datasets/samples/ for git.

    - region.csv and nation.csv: small enough to include whole
    - other tables: 100-row sample
    """
    samples_dir = PROJECT_ROOT / "datasets" / "samples" / dataset_name
    samples_dir.mkdir(parents=True, exist_ok=True)

    # Whole small tables
    for small in ("region", "nation"):
        src = external_path / f"{small}.csv"
        if src.exists():
            dst = samples_dir / f"{small}.csv"
            dst.write_bytes(src.read_bytes())
            size_b = dst.stat().st_size
            print(f"[tpch]   sample: {small}.csv ({size_b} bytes)")

    # 100-row sample of lineitem (the biggest table)
    lineitem_src = external_path / "lineitem.csv"
    if lineitem_src.exists():
        dst = samples_dir / "lineitem-sample.csv"
        with lineitem_src.open("r", encoding="utf-8") as f:
            lines = []
            for i, line in enumerate(f):
                if i > 100:  # header + 100 rows
                    break
                lines.append(line)
        dst.write_text("".join(lines), encoding="utf-8")
        size_kb = dst.stat().st_size / 1024
        print(f"[tpch]   sample: lineitem-sample.csv ({size_kb:.1f} KB, 100 rows)")

    # 20-row samples of other medium tables
    for mid in ("supplier", "customer", "orders"):
        src = external_path / f"{mid}.csv"
        if src.exists():
            dst = samples_dir / f"{mid}-sample.csv"
            with src.open("r", encoding="utf-8") as f:
                lines = []
                for i, line in enumerate(f):
                    if i > 20:
                        break
                    lines.append(line)
            dst.write_text("".join(lines), encoding="utf-8")
            size_kb = dst.stat().st_size / 1024
            print(f"[tpch]   sample: {mid}-sample.csv ({size_kb:.1f} KB)")


def main():
    parser = argparse.ArgumentParser(description="Download TPC-H dataset via DuckDB")
    parser.add_argument(
        "--sf", type=float, default=0.01,
        help="Scale factor (default: 0.01 → ~10MB total)",
    )
    parser.add_argument(
        "--no-samples", action="store_true",
        help="Skip generating samples in datasets/samples/",
    )
    args = parser.parse_args()

    external_path, table_stats, dataset_name = download_tpch(sf=args.sf)
    write_metadata(dataset_name, sf=args.sf, table_stats=table_stats)

    if not args.no_samples:
        generate_samples(dataset_name, external_path)

    total_rows = sum(table_stats.values())
    print(f"\n[tpch] Done. {total_rows:,} total rows across {len(table_stats)} tables.")
    print(f"[tpch] Raw data: {external_path}")
    print(f"[tpch] Metadata + samples: in git under datasets/canonical/{dataset_name}/ and datasets/samples/{dataset_name}/")


if __name__ == "__main__":
    main()

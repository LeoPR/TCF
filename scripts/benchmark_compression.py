"""Compression benchmark — TCF L0-L3 vs CSV vs JSONL on canonical datasets.

Measures raw text size, gzip/brotli compressed size, and encode timing
for each format at multiple data scales.

Uses:
  - DatasetReader (scripts/) to get data from SQLite
  - encode_columns (src/tcf/) for TCF encoding
  - writers/ (scripts/) for CSV/JSONL baselines
  - Timings (src/tcf/) for honest phase measurement

Outputs a markdown report and JSON results to stdout/file.

Usage:
    python scripts/benchmark_compression.py
    python scripts/benchmark_compression.py --dataset tpch-sf001 --table lineitem
    python scripts/benchmark_compression.py --scales 100 500 1000 5000
"""

from __future__ import annotations

import argparse
import csv as csv_mod
import gzip
import io
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _paths import PROJECT_ROOT, data_root  # noqa: E402
from dataset_reader import DatasetReader  # noqa: E402
from writers.toon_writer import encode_toon  # noqa: E402

sys.path.insert(0, str(PROJECT_ROOT / "src"))
from tcf import encode_columns, EncodeConfig  # noqa: E402
from tcf.timing import Timings  # noqa: E402


# Columns to exclude from encoding (freeform text breaks decoder — ticket 29)
EXCLUDE_COLUMNS = {"c_comment", "l_comment", "s_comment", "ps_comment",
                   "o_comment", "p_comment", "r_comment", "n_comment"}


def _rows_to_columns(rows: list[dict], exclude: set[str] | None = None) -> dict[str, list[str]]:
    if not rows:
        return {}
    exclude = exclude or set()
    cols = [c for c in rows[0].keys() if c not in exclude]
    return {c: [str(r[c]) if r[c] is not None else "" for r in rows] for c in cols}


def _rows_to_csv(rows: list[dict], exclude: set[str] | None = None) -> str:
    if not rows:
        return ""
    exclude = exclude or set()
    cols = [c for c in rows[0].keys() if c not in exclude]
    buf = io.StringIO()
    w = csv_mod.DictWriter(buf, fieldnames=cols, extrasaction="ignore")
    w.writeheader()
    for row in rows:
        w.writerow({c: ("" if row.get(c) is None else row[c]) for c in cols})
    return buf.getvalue()


def _rows_to_jsonl(rows: list[dict], exclude: set[str] | None = None) -> str:
    if not rows:
        return ""
    exclude = exclude or set()
    cols = [c for c in rows[0].keys() if c not in exclude]
    lines = []
    for row in rows:
        obj = {c: row.get(c) for c in cols}
        lines.append(json.dumps(obj, ensure_ascii=False))
    return "\n".join(lines) + "\n"


def _try_brotli(data: bytes) -> int | None:
    try:
        import brotli
        return len(brotli.compress(data))
    except ImportError:
        return None


def benchmark_table(
    reader: DatasetReader,
    table: str,
    scales: list[int],
) -> list[dict]:
    """Run compression benchmark for a single table at multiple scales."""
    results = []

    total_rows = reader.row_count(table)
    all_rows = reader.rows(table)

    for scale in scales:
        if scale > total_rows:
            continue

        rows = all_rows[:scale]
        n = len(rows)
        columns = _rows_to_columns(rows, EXCLUDE_COLUMNS)
        col_names = list(columns.keys())

        # --- CSV baseline ---
        t = Timings()
        with t.measure("csv_encode"):
            csv_text = _rows_to_csv(rows, EXCLUDE_COLUMNS)
        csv_bytes = csv_text.encode("utf-8")
        csv_gz = len(gzip.compress(csv_bytes))
        csv_br = _try_brotli(csv_bytes)

        results.append({
            "table": table, "scale": n, "format": "csv",
            "chars": len(csv_text), "bytes": len(csv_bytes),
            "gzip": csv_gz, "brotli": csv_br,
            "encode_ms": t.to_dict()["csv_encode"],
            "cols": len(col_names),
        })

        # --- JSONL baseline ---
        t = Timings()
        with t.measure("jsonl_encode"):
            jsonl_text = _rows_to_jsonl(rows, EXCLUDE_COLUMNS)
        jsonl_bytes = jsonl_text.encode("utf-8")
        jsonl_gz = len(gzip.compress(jsonl_bytes))
        jsonl_br = _try_brotli(jsonl_bytes)

        results.append({
            "table": table, "scale": n, "format": "jsonl",
            "chars": len(jsonl_text), "bytes": len(jsonl_bytes),
            "gzip": jsonl_gz, "brotli": jsonl_br,
            "encode_ms": t.to_dict()["jsonl_encode"],
            "cols": len(col_names),
        })

        # --- TOON ---
        t = Timings()
        # TOON needs rows without excluded columns
        safe_rows = [
            {c: row[c] for c in col_names}
            for row in rows
        ]
        with t.measure("toon_encode"):
            toon_text = encode_toon(table, col_names, safe_rows)
        toon_bytes = toon_text.encode("utf-8")
        toon_gz = len(gzip.compress(toon_bytes))
        toon_br = _try_brotli(toon_bytes)

        results.append({
            "table": table, "scale": n, "format": "toon",
            "chars": len(toon_text), "bytes": len(toon_bytes),
            "gzip": toon_gz, "brotli": toon_br,
            "encode_ms": t.to_dict()["toon_encode"],
            "cols": len(col_names),
        })

        # --- TCF L0-L3 ---
        for level in [0, 1, 2, 3]:
            config = EncodeConfig(level=level, include_stats=True)
            t = Timings()
            with t.measure("tcf_encode"):
                tcf_text = encode_columns(table, columns, config=config)
            tcf_bytes = tcf_text.encode("utf-8")
            tcf_gz = len(gzip.compress(tcf_bytes))
            tcf_br = _try_brotli(tcf_bytes)

            results.append({
                "table": table, "scale": n, "format": f"tcf_L{level}",
                "chars": len(tcf_text), "bytes": len(tcf_bytes),
                "gzip": tcf_gz, "brotli": tcf_br,
                "encode_ms": t.to_dict()["tcf_encode"],
                "cols": len(col_names),
            })

    return results


def print_report(results: list[dict], dataset: str) -> str:
    """Generate markdown report from benchmark results."""
    lines = [
        f"# Compression Benchmark — {dataset}",
        f"",
        f"Formats: CSV, JSONL, TCF L0, L1, L2, L3",
        f"Compression: gzip" + (", brotli" if any(r.get("brotli") for r in results) else ""),
        f"",
    ]

    # Group by table
    tables = sorted(set(r["table"] for r in results))
    for table in tables:
        t_results = [r for r in results if r["table"] == table]
        scales = sorted(set(r["scale"] for r in t_results))

        lines.append(f"## {table}")
        lines.append("")

        # Raw size table
        lines.append("### Raw size (chars)")
        lines.append("")
        header = f"| {'Scale':>7} |"
        formats = sorted(set(r["format"] for r in t_results),
                        key=lambda f: ("0csv" if f == "csv" else "1jsonl" if f == "jsonl" else f))
        for fmt in formats:
            header += f" {fmt:>10} |"
        lines.append(header)
        lines.append("|" + "|".join("---" for _ in range(len(formats) + 1)) + "|")

        for scale in scales:
            row = f"| {scale:>7,} |"
            for fmt in formats:
                match = [r for r in t_results if r["scale"] == scale and r["format"] == fmt]
                if match:
                    row += f" {match[0]['chars']:>10,} |"
                else:
                    row += f" {'—':>10} |"
            lines.append(row)

        lines.append("")

        # Gzip size table
        lines.append("### After gzip (bytes)")
        lines.append("")
        lines.append(header)  # same header
        lines.append("|" + "|".join("---" for _ in range(len(formats) + 1)) + "|")

        for scale in scales:
            row = f"| {scale:>7,} |"
            for fmt in formats:
                match = [r for r in t_results if r["scale"] == scale and r["format"] == fmt]
                if match:
                    row += f" {match[0]['gzip']:>10,} |"
                else:
                    row += f" {'—':>10} |"
            lines.append(row)

        lines.append("")

        # Ratio vs CSV
        lines.append("### Ratio vs CSV (raw chars)")
        lines.append("")
        for scale in scales:
            csv_match = [r for r in t_results if r["scale"] == scale and r["format"] == "csv"]
            if not csv_match:
                continue
            csv_chars = csv_match[0]["chars"]
            ratios = []
            for fmt in formats:
                match = [r for r in t_results if r["scale"] == scale and r["format"] == fmt]
                if match:
                    ratio = match[0]["chars"] / csv_chars
                    ratios.append(f"{fmt}={ratio:.2f}x")
            lines.append(f"- **{scale:,} rows:** " + ", ".join(ratios))

        lines.append("")

        # Encode time
        lines.append("### Encode time (ms)")
        lines.append("")
        for scale in scales:
            times = []
            for fmt in formats:
                match = [r for r in t_results if r["scale"] == scale and r["format"] == fmt]
                if match:
                    times.append(f"{fmt}={match[0]['encode_ms']:.1f}")
            lines.append(f"- **{scale:,} rows:** " + ", ".join(times))

        lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Compression benchmark")
    parser.add_argument("--dataset", default="tpch-sf001")
    parser.add_argument("--table", default=None, help="specific table (default: largest)")
    parser.add_argument("--scales", nargs="+", type=int,
                        default=[100, 500, 1000, 5000, 10000, 50000])
    parser.add_argument("--json", action="store_true", help="output JSON instead of markdown")
    args = parser.parse_args()

    reader = DatasetReader(args.dataset)

    if args.table:
        tables = [args.table]
    else:
        # Pick the 2 largest tables
        all_tables = [(t, reader.row_count(t)) for t in reader.tables]
        all_tables.sort(key=lambda x: x[1], reverse=True)
        tables = [t for t, _ in all_tables[:2]]

    print(f"[benchmark] dataset={args.dataset}, tables={tables}, scales={args.scales}",
          file=sys.stderr)

    all_results = []
    for table in tables:
        results = benchmark_table(reader, table, args.scales)
        all_results.extend(results)
        n_combos = len(results)
        print(f"[benchmark] {table}: {n_combos} measurements", file=sys.stderr)

    reader.close()

    if args.json:
        print(json.dumps(all_results, indent=2))
    else:
        report = print_report(all_results, args.dataset)
        print(report)


if __name__ == "__main__":
    main()

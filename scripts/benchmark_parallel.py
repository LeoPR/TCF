"""Benchmark T-CODE-ENCODER-MANAGER Fase 1 — speedup paralelo per-coluna.

Compara `encode(table, parallel=False)` vs `encode(table, parallel=N)`
em real-world (TPC-H tables) e reporta:
- Tempo serial vs paralelo
- Speedup observado
- RT preservado (byte-identical)
- Bytes identico vs serial

Uso:
    python scripts/benchmark_parallel.py [--table TABLE] [--workers N]

Defaults: customer (1500x8) e orders (15000x9) — rapido. Lineitem
(60175x16) opcional via --table lineitem (--workers max 16).
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from dataset_reader import DatasetReader  # noqa: E402
from tcf import encode  # noqa: E402


def stringify_table(cols: dict) -> dict[str, list[str]]:
    return {
        c: ["" if v is None else str(v) for v in vals]
        for c, vals in cols.items()
    }


def bench_table(dataset: str, table: str, n_workers: int) -> dict:
    with DatasetReader(dataset) as r:
        cols_raw = r.columns(table, limit=None)
    cols = stringify_table(cols_raw)
    n_rows = len(next(iter(cols.values())))
    n_cols = len(cols)

    # Serial baseline
    t0 = time.perf_counter()
    text_serial = encode(cols)
    t_serial = time.perf_counter() - t0
    bytes_serial = len(text_serial.encode("utf-8"))

    # Parallel
    t0 = time.perf_counter()
    text_parallel = encode(cols, parallel=n_workers)
    t_parallel = time.perf_counter() - t0
    bytes_parallel = len(text_parallel.encode("utf-8"))

    return {
        "dataset": dataset,
        "table": table,
        "n_rows": n_rows,
        "n_cols": n_cols,
        "n_workers": n_workers,
        "t_serial_s": round(t_serial, 2),
        "t_parallel_s": round(t_parallel, 2),
        "speedup": round(t_serial / t_parallel, 2) if t_parallel > 0 else float("inf"),
        "bytes_serial": bytes_serial,
        "bytes_parallel": bytes_parallel,
        "byte_identical": text_serial == text_parallel,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--table", default=None,
                    help="Tabela especifica (customer/orders/lineitem). "
                         "Default: customer + orders")
    ap.add_argument("--workers", type=int, default=4,
                    help="N workers (default: 4)")
    args = ap.parse_args()

    if args.table:
        tasks = [("tpch-sf001", args.table)]
    else:
        tasks = [
            ("tpch-sf001", "customer"),
            ("tpch-sf001", "orders"),
        ]

    print(f"=== Benchmark parallel encoder (workers={args.workers}) ===\n")
    print(f"{'dataset/table':25s} {'rows':>6} {'cols':>4} "
          f"{'serial(s)':>10} {'parallel(s)':>12} {'speedup':>8} "
          f"{'bytes':>8} {'identical':>10}")
    print("-" * 100)

    results = []
    for dataset, table in tasks:
        try:
            res = bench_table(dataset, table, args.workers)
            results.append(res)
            print(f"{dataset+'/'+table:25s} "
                  f"{res['n_rows']:>6} {res['n_cols']:>4} "
                  f"{res['t_serial_s']:>10.2f} {res['t_parallel_s']:>12.2f} "
                  f"{res['speedup']:>7.2f}x "
                  f"{res['bytes_serial']:>8} "
                  f"{'YES' if res['byte_identical'] else 'NO':>10}")
        except Exception as e:
            print(f"{dataset+'/'+table:25s} ERROR: {e}")

    print("-" * 100)
    if results:
        avg_speedup = sum(r["speedup"] for r in results) / len(results)
        all_identical = all(r["byte_identical"] for r in results)
        print(f"Average speedup: {avg_speedup:.2f}x | All byte-identical: "
              f"{'YES' if all_identical else 'NO'}")


if __name__ == "__main__":
    main()

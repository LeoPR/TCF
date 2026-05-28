"""Benchmark extension — UCI datasets (T-DATA-1, Sprint 2 Passo 1).

Estende run.py com 3 datasets UCI/OpenML baixados em 2026-05-27:
- wine-quality (6.497 rows, decimais quimicos)
- beijing-pm25 (43.824 rows, sensores + timestamps)
- online-retail (50k subset pra brotli ser viavel; full 541k em run.py
  manifest separado se quiser)

Output: manifest_uci.jsonl + tabela print.
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

THIS = Path(__file__).parent
ROOT = THIS.parents[3]
sys.path.insert(0, str(THIS))  # pra reusar run.py

from run import bench_one, load_csv_as_dict  # noqa: E402


def main():
    print("=== Benchmark UCI extension (Sprint 2 Passo 1) ===\n")

    base = Path("Z:/tcf-data/external")

    tasks = [
        ("wine-quality",
         load_csv_as_dict(base / "wine-quality" / "wine.csv"),
         None),
        ("beijing-pm25",
         load_csv_as_dict(base / "beijing-pm25" / "beijing_pm25.csv"),
         None),
        ("online-retail-50k",
         load_csv_as_dict(base / "online-retail" / "online_retail.csv",
                           limit=50000),
         None),
    ]

    all_results = []
    for name, table, nature in tasks:
        n_rows = len(next(iter(table.values())))
        n_cols = len(table)
        print(f"\nRunning {name} ({n_rows} rows x {n_cols} cols)...")
        results = bench_one(name, table, nature_per_col=nature, save_files=True)
        all_results.extend(results)

    # Print
    print("\n" + "=" * 105)
    print(f"{'dataset':24s} {'format':12s} {'transport':10s} "
          f"{'bytes':>9} {'%vs raw_csv':>12} {'b/cell':>8} {'time':>7}")
    print("-" * 105)
    for r in all_results:
        if "error" in r:
            continue
        print(f"{r['dataset']:24s} {r['format']:12s} {r['transport']:10s} "
              f"{r['bytes']:>9} {r['ratio_vs_raw_csv']:>11.2f}% "
              f"{r['bytes_per_cell']:>8.4f} {r['time_s']:>6.2f}s")

    manifest = THIS / "manifest_uci.jsonl"
    manifest.write_text(
        "\n".join(json.dumps(r) for r in all_results) + "\n",
        encoding="utf-8",
    )

    print("\n=== Vencedor por dataset ===\n")
    by_ds = {}
    for r in all_results:
        if "error" in r:
            continue
        by_ds.setdefault(r['dataset'], []).append(r)
    for ds, results in by_ds.items():
        winner = min(results, key=lambda x: x['bytes'])
        raw_csv = next(r for r in results if r['format'] == 'csv' and r['transport'] == 'raw')
        print(f"  {ds:24s}: {winner['format']:8s} + {winner['transport']:8s} = "
              f"{winner['bytes']:>9}B "
              f"({winner['ratio_vs_raw_csv']:.2f}% vs csv raw {raw_csv['bytes']}B)")

    print(f"\nManifest: {manifest}")
    print(f"Outputs:  {THIS / 'out_files'}/")


if __name__ == "__main__":
    main()

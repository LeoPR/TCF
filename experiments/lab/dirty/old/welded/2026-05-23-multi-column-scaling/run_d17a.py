"""Fase 1 — validar D17a com canonical M10.

Baseline EXP-011 (delta_aware EXP-010, pre-M10): 322 bytes.
Esperado canonical M10: <= 322B + RT OK.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

THIS = Path(__file__).parent
ROOT = THIS.parents[3]
sys.path.insert(0, str(THIS))

from multi_col_canonical import encode_table, decode_table  # noqa: E402


def load_csv(path: Path) -> dict[str, list[str]]:
    with path.open(encoding="utf-8") as f:
        r = csv.reader(f)
        header = next(r)
        cols = {h: [] for h in header}
        for row in r:
            for h, v in zip(header, row):
                cols[h].append(v)
    return cols


def main():
    ds_path = ROOT / "datasets" / "synthetic" / "D17a-multi-column-mixed.csv"
    table = load_csv(ds_path)
    raw_bytes = ds_path.read_bytes()
    n_rows = len(next(iter(table.values())))
    n_cols = len(table)

    print("=== Fase 1: D17a canonical M10 vs EXP-011 baseline ===\n")
    print(f"Dataset: D17a ({n_rows} rows x {n_cols} cols)")
    print(f"Raw CSV: {len(raw_bytes)} bytes")
    print(f"EXP-011 baseline (M9 pre-M10): 322 bytes\n")

    text, info = encode_table(table)
    rt = decode_table(text)

    rt_ok = (rt == table)
    total = info["total_bytes"]
    header = info["header_bytes"]
    body = info["body_bytes"]

    print(f"Canonical M10 total: {total} bytes (header={header}, body={body})")
    print(f"  vs EXP-011 322B: {total - 322:+d} bytes ({(total - 322)/322*100:+.2f}%)")
    print(f"  vs raw {len(raw_bytes)}B: {total - len(raw_bytes):+d} bytes "
          f"({(total - len(raw_bytes))/len(raw_bytes)*100:+.2f}%)")
    print(f"  RT: {'OK' if rt_ok else 'FAIL'}")
    print()
    print("Per-column:")
    for col, info_col in info["per_col"].items():
        print(f"  {col:15s}: {info_col['body_bytes']:5d} bytes "
              f"({info_col['n_values']} vals)")

    out_path = THIS / "outputs" / "d17a-canonical.tcf"
    out_path.write_bytes(text.encode("utf-8"))
    print(f"\nOutput: {out_path}")

    return {
        "total_bytes": total,
        "header_bytes": header,
        "body_bytes": body,
        "rt": rt_ok,
        "exp011_baseline": 322,
        "raw_bytes": len(raw_bytes),
    }


if __name__ == "__main__":
    main()

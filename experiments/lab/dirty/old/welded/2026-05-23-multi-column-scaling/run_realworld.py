"""Fase 2-3 — multi-column canonical M10 em real-world.

Datasets:
- Adult Census: adult (48842 x 15)
- TPC-H Tier 1 (rapido, <50k rows): region, nation, supplier, customer,
  part, partsupp, orders
- TPC-H Tier 2 (opcional, --full): lineitem (60175 x 16, ~20-30min)

Metricas por tabela:
- raw_bytes: serializacao CSV-like (proxy de tamanho original)
- multi_bytes: encode_table() canonical M10
- single_bytes: concat linhas em 1 coluna gigante + encode() (controle)
- header_overhead%: header / multi_bytes
- RT: decode_table == table

Decisao via flag --full: incluir lineitem.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

THIS = Path(__file__).parent
ROOT = THIS.parents[3]
SCRIPTS = ROOT / "scripts"
SRC = ROOT / "src"
sys.path.insert(0, str(THIS))
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(SRC))

from dataset_reader import DatasetReader  # noqa: E402
from tcf import encode  # noqa: E402
from multi_col_canonical import encode_table, decode_table  # noqa: E402


def stringify_table(cols: dict) -> dict[str, list[str]]:
    """Converte qualquer tipo SQL pra str (None -> '')."""
    return {
        c: ["" if v is None else str(v) for v in vals]
        for c, vals in cols.items()
    }


def raw_csv_bytes(cols: dict[str, list[str]]) -> int:
    """Proxy de tamanho 'raw' = CSV-like (header + linhas csv-joined com vfg)."""
    n_rows = len(next(iter(cols.values())))
    header = ",".join(cols.keys())
    raw = [header]
    for i in range(n_rows):
        row = ",".join(cols[c][i] for c in cols)
        raw.append(row)
    return len("\n".join(raw).encode("utf-8")) + 1  # +1 LF final


def single_encode_concat(cols: dict[str, list[str]]) -> tuple[int, bool]:
    """Concat linhas (vfg col-separator) + tcf.encode() single-col controle.

    Returns (n_bytes, rt_ok).
    """
    n_rows = len(next(iter(cols.values())))
    rows = []
    for i in range(n_rows):
        row = ",".join(cols[c][i] for c in cols)
        rows.append(row)
    text = encode(rows)
    # RT controle
    from tcf import decode
    rt = decode(text)
    rt_ok = (rt == rows)
    return len(text.encode("utf-8")), rt_ok


def measure_table(reader: DatasetReader, table: str,
                   limit: int | None = None) -> dict:
    """Mede multi-col vs single-col vs raw pra uma tabela."""
    cols_raw = reader.columns(table, limit=limit)
    cols = stringify_table(cols_raw)
    n_rows = len(next(iter(cols.values())))
    n_cols = len(cols)
    raw_bytes = raw_csv_bytes(cols)

    # Multi-col
    t0 = time.time()
    multi_text, info = encode_table(cols)
    t_multi = time.time() - t0
    multi_bytes = info["total_bytes"]
    header_bytes = info["header_bytes"]

    # Single-col concat
    t0 = time.time()
    single_bytes, single_rt = single_encode_concat(cols)
    t_single = time.time() - t0

    # RT multi
    rt_multi_table = decode_table(multi_text)
    rt_multi_ok = (rt_multi_table == cols)

    return {
        "table": table,
        "n_rows": n_rows,
        "n_cols": n_cols,
        "raw_bytes": raw_bytes,
        "multi_bytes": multi_bytes,
        "header_bytes": header_bytes,
        "single_bytes": single_bytes,
        "header_overhead_pct": header_bytes / multi_bytes * 100,
        "multi_vs_raw_pct": (multi_bytes - raw_bytes) / raw_bytes * 100,
        "multi_vs_single_pct": (multi_bytes - single_bytes) / single_bytes * 100,
        "rt_multi_ok": rt_multi_ok,
        "rt_single_ok": single_rt,
        "t_multi_sec": round(t_multi, 2),
        "t_single_sec": round(t_single, 2),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--full", action="store_true",
                    help="Inclui lineitem (60k x 16, ~20-30 min)")
    args = ap.parse_args()

    tasks = [
        ("adult-census", "adult", None),
        ("tpch-sf001", "region", None),
        ("tpch-sf001", "nation", None),
        ("tpch-sf001", "supplier", None),
        ("tpch-sf001", "customer", None),
        ("tpch-sf001", "part", None),
        ("tpch-sf001", "partsupp", None),
        ("tpch-sf001", "orders", None),
    ]
    if args.full:
        tasks.append(("tpch-sf001", "lineitem", None))

    print("=== Fase 2-3: multi-column canonical M10 em real-world ===\n")
    print(f"{'dataset/table':30s} {'rows':>6} {'cols':>4} "
          f"{'raw':>9} {'multi':>9} {'single':>9} "
          f"{'hdr%':>6} {'vs_raw%':>8} {'vs_single%':>10} "
          f"{'RTm':>3} {'RTs':>3} {'t(s)':>5}")
    print("-" * 120)

    results = []
    for dataset, table, limit in tasks:
        try:
            with DatasetReader(dataset) as r:
                res = measure_table(r, table, limit=limit)
                results.append(res)
                print(f"{dataset+'/'+table:30s} "
                      f"{res['n_rows']:>6} {res['n_cols']:>4} "
                      f"{res['raw_bytes']:>9} {res['multi_bytes']:>9} "
                      f"{res['single_bytes']:>9} "
                      f"{res['header_overhead_pct']:>5.2f}% "
                      f"{res['multi_vs_raw_pct']:>+7.2f}% "
                      f"{res['multi_vs_single_pct']:>+9.2f}% "
                      f"{'OK' if res['rt_multi_ok'] else 'FAIL':>3} "
                      f"{'OK' if res['rt_single_ok'] else 'FAIL':>3} "
                      f"{res['t_multi_sec']:>5.1f}")
        except Exception as e:
            print(f"{dataset+'/'+table:30s} ERROR: {e}")
            results.append({"dataset": dataset, "table": table, "error": str(e)})

    # Manifest
    out = THIS / "outputs"
    out.mkdir(exist_ok=True)
    (out / "realworld_manifest.jsonl").write_text(
        "\n".join(json.dumps(r) for r in results) + "\n",
        encoding="utf-8",
    )

    # Stats agregadas
    valid = [r for r in results if "error" not in r]
    total_raw = sum(r["raw_bytes"] for r in valid)
    total_multi = sum(r["multi_bytes"] for r in valid)
    total_single = sum(r["single_bytes"] for r in valid)
    n_rt_ok = sum(1 for r in valid if r["rt_multi_ok"])

    print("-" * 120)
    print(f"{'WEIGHTED TOTAL':30s} "
          f"{'':>6} {'':>4} "
          f"{total_raw:>9} {total_multi:>9} {total_single:>9} "
          f"{'':>6} "
          f"{(total_multi-total_raw)/total_raw*100:>+7.2f}% "
          f"{(total_multi-total_single)/total_single*100:>+9.2f}% "
          f"{n_rt_ok}/{len(valid):>2}")

    print(f"\nManifest: {out / 'realworld_manifest.jsonl'}")


if __name__ == "__main__":
    main()

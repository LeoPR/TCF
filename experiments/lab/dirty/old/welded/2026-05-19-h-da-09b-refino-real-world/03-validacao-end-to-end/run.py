"""Sub-exp 03 — validacao end-to-end EXP-012 / EXP-013 com heuristica v2.

Roda mesmas tabelas usadas em EXP-012 e EXP-013 mas com auto_pre_v2
no lugar de auto_pre canonical. Compara bytes + RT.
"""

from __future__ import annotations

import csv
import io
import sys
from pathlib import Path

THIS = Path(__file__).parent
ROOT = THIS.parents[4]
SCRIPTS = ROOT / "scripts"
SRC = ROOT / "src"
EXP_010 = ROOT / "experiments" / "lab" / "clean" / "EXP-010-tcf-delta-aware-prototype"
EXP_011 = ROOT / "experiments" / "lab" / "clean" / "EXP-011-multi-column-basic"
SUB_02 = ROOT / "experiments" / "lab" / "dirty" / "2026-05-19-h-da-09b-refino-real-world" / "02-heuristica-refinada"

sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(SRC))
sys.path.insert(0, str(EXP_010))
sys.path.insert(0, str(EXP_011))
sys.path.insert(0, str(SUB_02))

from dataset_reader import DatasetReader  # noqa: E402
from shaper import Shaper, ShapeRequest  # noqa: E402

# Monkey-patch delta_aware com v2 heuristic
import delta_aware  # noqa: E402
from auto_pre_v2 import detect_cadence_v2  # noqa: E402

# Salvar original pra comparativo
ORIG_DETECT = delta_aware.detect_cadence


def use_v2():
    delta_aware.detect_cadence = detect_cadence_v2


def use_v1():
    delta_aware.detect_cadence = ORIG_DETECT


from multi_col import encode_table, decode_table  # noqa: E402


def table_to_csv_bytes(cols):
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    col_names = list(cols.keys())
    w.writerow(col_names)
    n = len(next(iter(cols.values())))
    for i in range(n):
        w.writerow([cols[c][i] for c in col_names])
    return buf.getvalue().encode("utf-8")


def rows_to_cols(rows):
    if not rows:
        return {}
    return {c: [str(r[c]) if r[c] is not None else "" for r in rows]
            for c in rows[0].keys()}


def test(label: str, cols: dict) -> dict:
    """Encode com v1 e v2; compara."""
    raw = len(table_to_csv_bytes(cols))

    use_v1()
    tcf_v1, info_v1 = encode_table(cols)
    bytes_v1 = len(tcf_v1.encode("utf-8"))
    dec_v1 = decode_table(tcf_v1)
    rt_v1 = (dec_v1 == cols)
    cad_v1 = sum(1 for ci in info_v1["col_info"].values() if ci["cadence_detected"])

    use_v2()
    tcf_v2, info_v2 = encode_table(cols)
    bytes_v2 = len(tcf_v2.encode("utf-8"))
    dec_v2 = decode_table(tcf_v2)
    rt_v2 = (dec_v2 == cols)
    cad_v2 = sum(1 for ci in info_v2["col_info"].values() if ci["cadence_detected"])

    print(f"  {label:30} raw={raw:>7}  v1={bytes_v1:>6} (cad={cad_v1})  "
          f"v2={bytes_v2:>6} (cad={cad_v2})  delta={bytes_v2-bytes_v1:+d}  "
          f"RT v1={'OK' if rt_v1 else 'FAIL'} v2={'OK' if rt_v2 else 'FAIL'}")
    return {
        "label": label, "raw": raw, "bytes_v1": bytes_v1, "bytes_v2": bytes_v2,
        "cad_v1": cad_v1, "cad_v2": cad_v2, "n_cols": len(cols),
        "rt_v1": "OK" if rt_v1 else "FAIL",
        "rt_v2": "OK" if rt_v2 else "FAIL",
    }


def main():
    print("=== Sub-exp 03 — Validacao end-to-end com heuristica v2 ===\n")

    results = []

    # Adult Census (4 volumes — same as EXP-012)
    print("\n--- Adult Census (EXP-012) ---")
    for vol in [100, 500, 1000, 5000]:
        req = ShapeRequest(dataset="adult-census", volume=vol, seed=42)
        result = Shaper().apply(req)
        cols = rows_to_cols(result.tables["adult"])
        results.append(test(f"adult vol={vol}", cols))

    # TPC-H (EXP-013 cap 5000)
    print("\n--- TPC-H (EXP-013) ---")
    reader = DatasetReader("tpch-sf001")
    for table in reader.tables:
        cnt = reader.query(f"SELECT COUNT(*) FROM {table}")[0][0]
        limit = min(5000, cnt)
        rows = reader.rows(table, limit=limit)
        cols = rows_to_cols(rows)
        results.append(test(f"tpch.{table} n={limit}", cols))
    reader.close()

    total_v1 = sum(r["bytes_v1"] for r in results)
    total_v2 = sum(r["bytes_v2"] for r in results)
    total_raw = sum(r["raw"] for r in results)
    rt_v2_pass = sum(1 for r in results if r["rt_v2"] == "OK")

    print(f"\n=== TOTAIS ===")
    print(f"raw:  {total_raw:,}")
    print(f"v1:   {total_v1:,}  ({total_v1-total_raw:+,d}, {total_v1/total_raw*100:.1f}%)")
    print(f"v2:   {total_v2:,}  ({total_v2-total_raw:+,d}, {total_v2/total_raw*100:.1f}%)")
    print(f"v2 vs v1: {total_v2-total_v1:+,d}")
    print(f"RT v2: {rt_v2_pass}/{len(results)}")

    # Report
    out = ["# Sub-exp 03 — Validacao end-to-end (heuristica v2)", ""]
    out.append("## Resumo")
    out.append("")
    out.append("| Label | raw | v1 (current) | v2 (refinada) | Δ v2 vs v1 | RT v2 |")
    out.append("|---|---:|---:|---:|---:|---|")
    for r in results:
        out.append(
            f"| `{r['label']}` | {r['raw']:,} "
            f"| {r['bytes_v1']:,} (cad={r['cad_v1']}/{r['n_cols']}) "
            f"| {r['bytes_v2']:,} (cad={r['cad_v2']}/{r['n_cols']}) "
            f"| {r['bytes_v2']-r['bytes_v1']:+,d} | {r['rt_v2']} |"
        )
    out.append("")
    out.append("## Totais")
    out.append("")
    out.append(f"- raw:  {total_raw:,} B")
    out.append(f"- v1:   {total_v1:,} B  ({total_v1/total_raw*100:.1f}%)")
    out.append(f"- **v2**:  **{total_v2:,} B  ({total_v2/total_raw*100:.1f}%)**")
    out.append(f"- **v2 melhor que v1 por**: **{total_v1-total_v2:+,d} B**")
    out.append("")
    out.append(f"RT v2: {rt_v2_pass}/{len(results)}")
    (THIS / "result.md").write_bytes("\n".join(out).encode("utf-8"))
    print(f"\nresult.md: {THIS / 'result.md'}")


if __name__ == "__main__":
    main()

"""Sub-exp 02 — testa heuristica refinada em todas 76 cols do audit.

Mede: acertos vs heuristica original (v1) e oracle (audit force_hint).
"""

from __future__ import annotations

import sys
from collections import OrderedDict
from pathlib import Path

THIS = Path(__file__).parent
ROOT = THIS.parents[4]
SCRIPTS = ROOT / "scripts"
SRC = ROOT / "src"
EXP_010 = ROOT / "experiments" / "lab" / "clean" / "EXP-010-tcf-delta-aware-prototype"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(SRC))
sys.path.insert(0, str(EXP_010))
sys.path.insert(0, str(THIS))

from dataset_reader import DatasetReader  # noqa: E402
from shaper import Shaper, ShapeRequest  # noqa: E402
from delta_aware import encode_column  # noqa: E402
from auto_pre import detect_cadence as detect_cadence_v1  # noqa: E402
from auto_pre_v2 import detect_cadence_v2  # noqa: E402


def dedup(values):
    seen = OrderedDict()
    for v in values:
        seen[v] = True
    return list(seen.keys())


def measure(values):
    """Mede bytes off vs on (oracle)."""
    try:
        body_off, _ = encode_column(values, header="x", force_hint=False)
        body_on, _ = encode_column(values, header="x", force_hint=True)
        return len(body_off.encode("utf-8")), len(body_on.encode("utf-8"))
    except Exception:
        return None, None


def outcome(bytes_off, bytes_on):
    if bytes_off is None:
        return "ERROR"
    delta = bytes_on - bytes_off
    if delta < -5:
        return "HELP"
    elif delta > 5:
        return "HURT"
    return "NO-OP"


def gather_cols():
    """Carrega mesmas cols que sub-exp 01."""
    all_cols = []
    # Adult
    req = ShapeRequest(dataset="adult-census", volume=500, seed=42)
    result = Shaper().apply(req)
    rows = result.tables["adult"]
    for c in rows[0].keys():
        vals = [str(r[c]) if r[c] is not None else "" for r in rows]
        all_cols.append(("adult-census", "adult", c, vals))
    # TPC-H
    reader = DatasetReader("tpch-sf001")
    for table in reader.tables:
        rows = reader.rows(table, limit=200)
        for c in rows[0].keys():
            vals = [str(r[c]) if r[c] is not None else "" for r in rows]
            all_cols.append(("tpch-sf001", table, c, vals))
    reader.close()
    return all_cols


def main():
    print("=== Sub-exp 02 — heuristica refinada v2 ===\n")

    cols = gather_cols()
    print(f"Total colunas: {len(cols)}")

    # Confusion matrices
    metrics = {
        "v1": {"TP": 0, "TN": 0, "FP": 0, "FN": 0},
        "v2": {"TP": 0, "TN": 0, "FP": 0, "FN": 0},
    }
    bytes_v1, bytes_v2, bytes_oracle, bytes_off_total = 0, 0, 0, 0
    rows = []

    for dataset, table, col, vals in cols:
        bytes_off, bytes_on = measure(vals)
        if bytes_off is None:
            continue
        out = outcome(bytes_off, bytes_on)

        det_v1, _ = detect_cadence_v1(vals)
        det_v2, info_v2 = detect_cadence_v2(vals)

        # Categorize correctness:
        # - HELP outcome: detect=True is correct (TP), False is FN
        # - HURT outcome: detect=True is FP, False is TN
        # - NO-OP outcome: doesn't matter much; we want False (TN equivalent)
        for v, det in [("v1", det_v1), ("v2", det_v2)]:
            if out == "HELP":
                metrics[v]["TP" if det else "FN"] += 1
            elif out == "HURT":
                metrics[v]["FP" if det else "TN"] += 1
            else:  # NO-OP
                metrics[v]["FP" if det else "TN"] += 1

        # Bytes accounting
        bytes_off_total += bytes_off
        bytes_v1 += bytes_on if det_v1 else bytes_off
        bytes_v2 += bytes_on if det_v2 else bytes_off
        bytes_oracle += min(bytes_off, bytes_on)

        rows.append({
            "dataset": dataset, "table": table, "col": col,
            "outcome": out, "v1": det_v1, "v2": det_v2,
            "rule_v2": info_v2.get("rule_hit"),
            "delta_actual": bytes_on - bytes_off,
        })

    # Print
    print(f"\n{'metric':>8} {'v1':>6} {'v2':>6}")
    for k in ["TP", "TN", "FP", "FN"]:
        print(f"{k:>8} {metrics['v1'][k]:>6} {metrics['v2'][k]:>6}")

    print(f"\nBytes total (lower = better):")
    print(f"  Always-off: {bytes_off_total}")
    print(f"  v1:         {bytes_v1}  (delta vs off: {bytes_v1-bytes_off_total:+d})")
    print(f"  v2:         {bytes_v2}  (delta vs off: {bytes_v2-bytes_off_total:+d})")
    print(f"  Oracle:     {bytes_oracle}  (best possible: {bytes_oracle-bytes_off_total:+d})")

    # Report
    out_md = ["# Sub-exp 02 — heuristica refinada v2", ""]
    out_md.append(f"Total colunas: {len(rows)}")
    out_md.append("")
    out_md.append("## Matriz de confusao")
    out_md.append("")
    out_md.append("(TP = enable em HELP; TN = skip em HURT/NO-OP; FP = enable em HURT/NO-OP; FN = skip em HELP)")
    out_md.append("")
    out_md.append("| metric | v1 (existente) | **v2 (refinada)** |")
    out_md.append("|---|---:|---:|")
    for k in ["TP", "TN", "FP", "FN"]:
        out_md.append(f"| {k} | {metrics['v1'][k]} | {metrics['v2'][k]} |")
    out_md.append("")
    out_md.append("## Bytes")
    out_md.append("")
    out_md.append("| heuristica | bytes total | delta vs off |")
    out_md.append("|---|---:|---:|")
    out_md.append(f"| Always-off | {bytes_off_total} | 0 |")
    out_md.append(f"| **v1** (existente) | {bytes_v1} | {bytes_v1-bytes_off_total:+d} |")
    out_md.append(f"| **v2** (refinada) | {bytes_v2} | {bytes_v2-bytes_off_total:+d} |")
    out_md.append(f"| Oracle (best-of) | {bytes_oracle} | {bytes_oracle-bytes_off_total:+d} |")
    out_md.append("")
    out_md.append("## Detalhes per coluna (so' divergencias entre v1 e v2)")
    out_md.append("")
    out_md.append("| dataset.table.col | outcome | v1 | v2 | rule v2 | actual delta |")
    out_md.append("|---|---|---|---|---|---:|")
    for r in rows:
        if r["v1"] != r["v2"]:
            out_md.append(
                f"| `{r['dataset']}.{r['table']}.{r['col']}` "
                f"| {r['outcome']} | {r['v1']!s} | {r['v2']!s} "
                f"| {r['rule_v2']} | {r['delta_actual']:+d} |"
            )
    out_md.append("")
    (THIS / "result.md").write_bytes("\n".join(out_md).encode("utf-8"))
    print(f"\nresult.md: {THIS / 'result.md'}")


if __name__ == "__main__":
    main()

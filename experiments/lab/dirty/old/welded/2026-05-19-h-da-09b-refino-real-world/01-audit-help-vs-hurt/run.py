"""Sub-exp 01 — audit per coluna em Adult Census + TPC-H."""

from __future__ import annotations

import csv
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

from dataset_reader import DatasetReader  # noqa: E402
from shaper import Shaper, ShapeRequest  # noqa: E402
from delta_aware import encode_column, decode_column  # noqa: E402
from tcf.core.online import lcp_len, lcs_len  # noqa: E402


def dedup(values):
    seen = OrderedDict()
    for v in values:
        seen[v] = True
    return list(seen.keys())


def column_features(values: list[str]) -> dict:
    """Coleta features descritivas de uma coluna."""
    n = len(values)
    if n == 0:
        return {"n": 0}
    unicas = dedup(values)
    lengths = [len(v) for v in values]
    n_unicas = len(unicas)
    cardinality = n_unicas / n
    avg_len = sum(lengths) / n
    min_len = min(lengths)
    max_len = max(lengths)
    len_range = max_len - min_len
    uniform = (len_range == 0)

    # LCP+LCS ratio em pares consecutivos (subset)
    sample = unicas[:min(10, len(unicas))]
    ratios = []
    if len(sample) >= 2:
        for i in range(1, len(sample)):
            a, b = sample[i - 1], sample[i]
            L = min(len(a), len(b))
            if L == 0:
                continue
            lcp = lcp_len(a, b)
            lcs = lcs_len(a, b)
            ratios.append((lcp + lcs) / L)
    avg_ratio = sum(ratios) / len(ratios) if ratios else 0.0

    # Numerica?
    is_numeric = all(v.lstrip('-').isdigit() for v in values if v)
    # Empty fraction
    n_empty = sum(1 for v in values if v == "")
    pct_empty = n_empty / n if n > 0 else 0

    return {
        "n": n,
        "n_unicas": n_unicas,
        "cardinality": round(cardinality, 3),
        "avg_len": round(avg_len, 1),
        "len_range": len_range,
        "uniform_length": uniform,
        "avg_lcp_lcs_ratio": round(avg_ratio, 3),
        "is_numeric": is_numeric,
        "pct_empty": round(pct_empty, 3),
    }


def measure_help_hurt(values: list[str]) -> dict:
    """Mede bytes com hint OFF vs ON."""
    try:
        body_off, info_off = encode_column(values, header="x", force_hint=False)
        decoded_off = decode_column(body_off)
        rt_off = (decoded_off == values)
        bytes_off = len(body_off.encode("utf-8"))
    except Exception as e:
        return {"error_off": str(e)}

    try:
        body_on, info_on = encode_column(values, header="x", force_hint=True)
        decoded_on = decode_column(body_on)
        rt_on = (decoded_on == values)
        bytes_on = len(body_on.encode("utf-8"))
    except Exception as e:
        return {"error_on": str(e), "bytes_off": bytes_off, "rt_off": rt_off}

    delta = bytes_on - bytes_off
    if delta < -5:
        outcome = "HELP"
    elif delta > 5:
        outcome = "HURT"
    else:
        outcome = "NO-OP"

    return {
        "bytes_off": bytes_off,
        "bytes_on": bytes_on,
        "delta": delta,
        "outcome": outcome,
        "rt_off": rt_off,
        "rt_on": rt_on,
    }


def audit_dataset(name: str, table_name: str, rows: list[dict]) -> list[dict]:
    """Aplica em todas colunas, retorna lista de dicts."""
    if not rows:
        return []
    cols = list(rows[0].keys())
    results = []
    for c in cols:
        values = [str(r[c]) if r[c] is not None else "" for r in rows]
        feats = column_features(values)
        meas = measure_help_hurt(values)
        results.append({
            "dataset": name,
            "table": table_name,
            "col": c,
            **feats,
            **meas,
        })
    return results


def main():
    print("=== Sub-exp 01 — Audit help-vs-hurt ===\n")

    all_results = []

    # Adult Census
    print("Adult Census (shaper volume=500)...")
    req = ShapeRequest(dataset="adult-census", volume=500, seed=42)
    result = Shaper().apply(req)
    rows = result.tables["adult"]
    all_results.extend(audit_dataset("adult-census", "adult", rows))

    # TPC-H — todas tabelas, 200 rows
    print("TPC-H (rows=200 por tabela)...")
    reader = DatasetReader("tpch-sf001")
    for table in reader.tables:
        rows = reader.rows(table, limit=200)
        all_results.extend(audit_dataset("tpch-sf001", table, rows))
    reader.close()

    # Summary
    by_outcome = {"HELP": [], "HURT": [], "NO-OP": [], "ERROR": []}
    for r in all_results:
        if "error_off" in r or "error_on" in r:
            by_outcome["ERROR"].append(r)
        else:
            by_outcome[r["outcome"]].append(r)

    # Print stats
    print(f"\nTotal colunas: {len(all_results)}")
    for k, v in by_outcome.items():
        print(f"  {k}: {len(v)}")

    # Output
    out = ["# Sub-exp 01 — Audit help-vs-hurt", ""]
    out.append(f"Total colunas analisadas: {len(all_results)}")
    out.append("")
    out.append("## Resumo por outcome")
    out.append("")
    out.append("| Outcome | Count |")
    out.append("|---|---:|")
    for k, v in by_outcome.items():
        out.append(f"| {k} | {len(v)} |")
    out.append("")

    # Detail by outcome
    for outcome in ["HELP", "HURT", "ERROR", "NO-OP"]:
        if not by_outcome[outcome]:
            continue
        out.append(f"## {outcome} ({len(by_outcome[outcome])})")
        out.append("")
        out.append("| dataset.table.col | n | uniq | card | avg_len | len_rng | uniform | LCP+LCS | num? | bytes_off | bytes_on | delta |")
        out.append("|---|---:|---:|---:|---:|---:|---|---:|---|---:|---:|---:|")
        for r in by_outcome[outcome]:
            if "bytes_off" not in r:
                out.append(f"| `{r['dataset']}.{r['table']}.{r['col']}` | — | — | — | — | — | — | — | — | ERROR | — | — |")
                continue
            out.append(
                f"| `{r['dataset']}.{r['table']}.{r['col']}` "
                f"| {r['n']} | {r['n_unicas']} | {r['cardinality']:.3f} "
                f"| {r['avg_len']:.1f} | {r['len_range']} | {r['uniform_length']!s} "
                f"| {r['avg_lcp_lcs_ratio']:.2f} | {r['is_numeric']!s} "
                f"| {r['bytes_off']} | {r['bytes_on']} | {r['delta']:+d} |"
            )
        out.append("")

    # Patterns
    out.append("## Patterns observados")
    out.append("")
    helps = by_outcome["HELP"]
    hurts = by_outcome["HURT"]
    if helps:
        avg_card_help = sum(r["cardinality"] for r in helps) / len(helps)
        avg_ratio_help = sum(r["avg_lcp_lcs_ratio"] for r in helps) / len(helps)
        uniform_help = sum(1 for r in helps if r["uniform_length"]) / len(helps)
        out.append(f"- HELP avg cardinality: {avg_card_help:.3f}")
        out.append(f"- HELP avg LCP+LCS ratio: {avg_ratio_help:.3f}")
        out.append(f"- HELP uniform_length frac: {uniform_help:.2f}")
        out.append(f"- HELP numeric frac: {sum(1 for r in helps if r['is_numeric']) / len(helps):.2f}")
    if hurts:
        avg_card_hurt = sum(r["cardinality"] for r in hurts) / len(hurts)
        avg_ratio_hurt = sum(r["avg_lcp_lcs_ratio"] for r in hurts) / len(hurts)
        uniform_hurt = sum(1 for r in hurts if r["uniform_length"]) / len(hurts)
        out.append(f"- HURT avg cardinality: {avg_card_hurt:.3f}")
        out.append(f"- HURT avg LCP+LCS ratio: {avg_ratio_hurt:.3f}")
        out.append(f"- HURT uniform_length frac: {uniform_hurt:.2f}")
        out.append(f"- HURT numeric frac: {sum(1 for r in hurts if r['is_numeric']) / len(hurts):.2f}")
    out.append("")
    out.append("(analise visual + pattern detection: ver result.md)")

    (THIS / "audit.md").write_bytes("\n".join(out).encode("utf-8"))
    print(f"\naudit.md: {THIS / 'audit.md'}")


if __name__ == "__main__":
    main()

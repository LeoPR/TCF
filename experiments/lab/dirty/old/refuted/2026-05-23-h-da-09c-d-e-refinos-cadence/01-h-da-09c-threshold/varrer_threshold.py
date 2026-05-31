"""Sub-exp 01 — H-DA-09c: varrer threshold detect_cadence em {0.5, 0.6, 0.7, 0.8}.

Pra cada coluna real-world (Adult+TPC-H 57 cols) + D1-D9 controle:
- Encode pipeline canonical com threshold ajustado
- Comparar bytes per col + agregado weighted

Identificar:
- Melhor threshold global (se houver)
- Distribuicao melhor threshold per col
- Ganho potencial weighted real-world

Criterio go: ganho weighted >= 2% sem regressao em D1-D9.
"""

from __future__ import annotations

import csv
import sys
from collections import OrderedDict, Counter
from pathlib import Path

THIS = Path(__file__).parent
ROOT = THIS.parents[4]
SCRIPTS = ROOT / "scripts"
SRC = ROOT / "src"

sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(SRC))

from dataset_reader import DatasetReader  # noqa: E402
from tcf.auto_cadence import detect_cadence_from_features  # noqa: E402
from tcf.auto_min_len import detect_min_len_from_features  # noqa: E402
from tcf.column_features import analyze_column  # noqa: E402
from tcf.composicional.hcc_seqrle import HCCSeqRLE  # noqa: E402
from tcf.core.online import processar  # noqa: E402
from tcf.obat_shape import processar_with_hint  # noqa: E402


THRESHOLDS = [0.5, 0.6, 0.7, 0.8]
DEFAULT_THR = 0.7

D1_D9 = [
    "D1-emails-simples", "D2-emails-quote-id", "D3-stress-substring",
    "D4-caos-mix", "D5-padroes-multiplos", "D6-poucos-em-ruido",
    "D7-aninhamento", "D8-cabeca-cauda", "D9-frequencia-alta",
]


def dedup_preserve_order(values):
    seen = OrderedDict()
    for v in values:
        seen[v] = True
    return list(seen.keys())


def ler_csv_single_col(path):
    with path.open(encoding="utf-8") as f:
        r = csv.reader(f)
        next(r)
        return [row[0] for row in r if row]


def rows_to_cols(rows):
    if not rows:
        return {}
    return {c: [str(r[c]) if r[c] is not None else "" for r in rows]
            for c in rows[0].keys()}


def encode_with_threshold(values, threshold, header="val"):
    """Pipeline canonical com threshold customizado em detect_cadence."""
    unicas = dedup_preserve_order(values)
    features = analyze_column(values)
    cadence, _ = detect_cadence_from_features(features, unicas,
                                                threshold=threshold)
    min_len = detect_min_len_from_features(features)
    if cadence:
        tokens, _ = processar_with_hint(unicas, min_len=min_len,
                                           prefer_shape_consistency=True)
    else:
        tokens, _ = processar(unicas, min_len=min_len)
    return HCCSeqRLE().encode(values, unicas, tokens, header)


def main():
    print(f"=== Sub-exp 01 — H-DA-09c varrer threshold {THRESHOLDS} ===\n")

    all_results = []  # {(source, col): {thr: bytes}}

    # D1-D9
    print(">> D1-D9 (controle)")
    datasets_dir = ROOT / "datasets" / "synthetic"
    for ds in D1_D9:
        values = ler_csv_single_col(datasets_dir / f"{ds}.csv")
        bytes_by_thr = {}
        for thr in THRESHOLDS:
            body = encode_with_threshold(values, thr)
            bytes_by_thr[thr] = len(body.encode("utf-8"))
        all_results.append({
            'source': 'sintetico', 'col': ds,
            'n_rows': len(values), 'bytes_by_thr': bytes_by_thr,
        })

    # Adult Census
    print(">> Adult Census")
    reader = DatasetReader("adult-census")
    for vol in [1000, 5000]:
        rows = reader.rows("adult", limit=vol)
        cols = rows_to_cols(rows)
        for cname, vals in cols.items():
            bytes_by_thr = {}
            for thr in THRESHOLDS:
                body = encode_with_threshold(vals, thr)
                bytes_by_thr[thr] = len(body.encode("utf-8"))
            all_results.append({
                'source': f"adult-{vol}", 'col': cname,
                'n_rows': len(vals), 'bytes_by_thr': bytes_by_thr,
            })
    reader.close()

    # TPC-H
    print(">> TPC-H")
    reader = DatasetReader("tpch-sf001")
    for table in ["region", "customer", "lineitem"]:
        rows = reader.rows(table, limit=5000)
        cols = rows_to_cols(rows)
        for cname, vals in cols.items():
            bytes_by_thr = {}
            for thr in THRESHOLDS:
                body = encode_with_threshold(vals, thr)
                bytes_by_thr[thr] = len(body.encode("utf-8"))
            all_results.append({
                'source': f"tpch.{table}-5k", 'col': cname,
                'n_rows': len(vals), 'bytes_by_thr': bytes_by_thr,
            })
    reader.close()

    # Agregar por threshold
    print("\n=== Agregados ===\n")
    total_by_thr = {thr: 0 for thr in THRESHOLDS}
    for r in all_results:
        for thr in THRESHOLDS:
            total_by_thr[thr] += r['bytes_by_thr'][thr]

    base_total = total_by_thr[DEFAULT_THR]
    print(f"{'thr':<6} {'total bytes':>12} {'delta vs 0.7':>14} {'pct':>7}")
    for thr in THRESHOLDS:
        delta = total_by_thr[thr] - base_total
        pct = -delta / base_total * 100 if base_total else 0
        marker = "  <- default" if thr == DEFAULT_THR else ""
        print(f"{thr:<6} {total_by_thr[thr]:>12,} {delta:>+14,} {pct:>+6.2f}%{marker}")

    # Real-world split
    rw = [r for r in all_results if r['source'] != 'sintetico']
    rw_total_by_thr = {thr: sum(r['bytes_by_thr'][thr] for r in rw)
                       for thr in THRESHOLDS}
    sint_total_by_thr = {thr: sum(r['bytes_by_thr'][thr] for r in all_results
                                    if r['source'] == 'sintetico')
                         for thr in THRESHOLDS}

    print(f"\nReal-world only ({len(rw)} cols):")
    rw_base = rw_total_by_thr[DEFAULT_THR]
    for thr in THRESHOLDS:
        delta = rw_total_by_thr[thr] - rw_base
        pct = -delta / rw_base * 100 if rw_base else 0
        print(f"  thr={thr}: {rw_total_by_thr[thr]:>10,}B  "
              f"delta={delta:+,}  ({pct:+.2f}%)")

    print(f"\nSintetico D1-D9 only:")
    sint_base = sint_total_by_thr[DEFAULT_THR]
    for thr in THRESHOLDS:
        delta = sint_total_by_thr[thr] - sint_base
        pct = -delta / sint_base * 100 if sint_base else 0
        print(f"  thr={thr}: {sint_total_by_thr[thr]:>10}B  "
              f"delta={delta:+,}  ({pct:+.2f}%)")

    # Distribuicao melhor threshold per col
    print(f"\n=== Distribuicao melhor threshold per col ===\n")
    best_by_col = {}
    for r in all_results:
        best_thr = min(r['bytes_by_thr'], key=lambda t: r['bytes_by_thr'][t])
        best_by_col[(r['source'], r['col'])] = best_thr
    ctr = Counter(best_by_col.values())
    for thr in THRESHOLDS:
        n = ctr.get(thr, 0)
        marker = "  <- default" if thr == DEFAULT_THR else ""
        print(f"  thr={thr}: {n:>3}/{len(all_results)} cols preferem{marker}")

    # Cols onde threshold != 0.7 ajuda >= 5B
    print(f"\n=== Cols onde threshold != 0.7 da ganho >= 5B ===\n")
    interesting = []
    for r in all_results:
        base = r['bytes_by_thr'][DEFAULT_THR]
        for thr in THRESHOLDS:
            if thr == DEFAULT_THR:
                continue
            delta = r['bytes_by_thr'][thr] - base
            if delta <= -5:
                interesting.append((r['source'], r['col'], thr,
                                    base, r['bytes_by_thr'][thr], delta))
    interesting.sort(key=lambda x: x[5])
    for src, col, thr, b_07, b_thr, delta in interesting[:15]:
        pct = -delta / b_07 * 100
        print(f"  {src:<18} {col:<22} thr={thr}: "
              f"{b_07:>6,} -> {b_thr:>6,} ({delta:+d}, {pct:+.2f}%)")

    # Veredito
    print(f"\n=== Veredito H-DA-09c ===\n")
    best_global_thr = min(rw_total_by_thr, key=lambda t: rw_total_by_thr[t])
    best_global_gain = (rw_base - rw_total_by_thr[best_global_thr]) / rw_base * 100

    print(f"Melhor threshold global (real-world): {best_global_thr}")
    print(f"Ganho weighted real-world: {best_global_gain:.2f}%")
    print(f"D1-D9 com melhor threshold: {sint_total_by_thr[best_global_thr]}B "
          f"({sint_total_by_thr[best_global_thr] - sint_base:+d} vs default)")

    if best_global_gain >= 2 and sint_total_by_thr[best_global_thr] <= sint_base:
        veredito = (f"GO: threshold={best_global_thr} da {best_global_gain:.2f}% "
                    f"weighted SEM regressao D1-D9. Vale considerar weld.")
        status = "go-tune-threshold"
    elif best_global_gain >= 1:
        veredito = (f"MARGINAL: ganho {best_global_gain:.2f}% weighted; "
                    f"H-DA-09d/e (multivariada/adaptativo) podem ajudar")
        status = "marginal-pode-tentar-09d"
    else:
        veredito = (f"NO-GO: threshold 0.7 atual ja' otimo "
                    f"(ganho {best_global_gain:.2f}% << 2%)")
        status = "no-go-threshold-07-otimo"

    print(f"\n{veredito}")
    print(f"Status: {status}")

    # Report
    report = [
        "# Sub-exp 01 — H-DA-09c varrer threshold detect_cadence",
        "",
        "## Setup",
        "",
        f"- Thresholds testados: {THRESHOLDS}",
        f"- Default atual: {DEFAULT_THR}",
        f"- Total colunas: {len(all_results)}",
        "",
        "## Agregado por threshold",
        "",
        "| Cohort | thr=0.5 | thr=0.6 | thr=0.7 (default) | thr=0.8 |",
        "|---|---:|---:|---:|---:|",
        f"| Total | {total_by_thr[0.5]:,} | {total_by_thr[0.6]:,} | "
        f"{total_by_thr[0.7]:,} | {total_by_thr[0.8]:,} |",
        f"| Real-world ({len(rw)}) | {rw_total_by_thr[0.5]:,} | "
        f"{rw_total_by_thr[0.6]:,} | {rw_total_by_thr[0.7]:,} | "
        f"{rw_total_by_thr[0.8]:,} |",
        f"| Sintetico (9) | {sint_total_by_thr[0.5]} | "
        f"{sint_total_by_thr[0.6]} | {sint_total_by_thr[0.7]} | "
        f"{sint_total_by_thr[0.8]} |",
        "",
        "## Distribuicao melhor threshold per col",
        "",
        "| Threshold | n_cols preferem |",
        "|---|---:|",
    ]
    for thr in THRESHOLDS:
        n = ctr.get(thr, 0)
        report.append(f"| {thr} | {n}/{len(all_results)} |")

    if interesting:
        report.append("")
        report.append("## Cols onde threshold != 0.7 da ganho >= 5B")
        report.append("")
        report.append("| Source | Col | thr | bytes 0.7 | bytes thr | delta | pct |")
        report.append("|---|---|---:|---:|---:|---:|---:|")
        for src, col, thr, b_07, b_thr, delta in interesting[:20]:
            pct = -delta / b_07 * 100
            report.append(f"| {src} | {col} | {thr} | {b_07:,} | "
                          f"{b_thr:,} | {delta:+d} | {pct:+.2f}% |")

    report.extend([
        "",
        "## Veredito",
        "",
        f"**{veredito}**",
        "",
        f"**Status**: `{status}`",
        "",
    ])

    out = THIS / "result.md"
    out.write_bytes(("\n".join(report) + "\n").encode("utf-8"))
    print(f"\nresult.md: {out}")


if __name__ == "__main__":
    main()

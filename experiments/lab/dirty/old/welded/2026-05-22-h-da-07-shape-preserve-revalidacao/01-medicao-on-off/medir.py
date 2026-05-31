"""Sub-exp 01 — medir shape-preserve on/off em real-world.

Compara 2 variantes em D1-D9 + Adult+TPC-H:
- V1 (off): pipeline manual sem shape-preserve — processar canonical sempre
- V2 (on): pipeline canonical M10 (tcf.encode com cadence + shape-preserve)

Por coluna: bytes V1, bytes V2, delta.
Agregado: weighted gain/loss + count de regressoes.

Criterio:
- Confirmada: V2 <= V1 em >= 95% das colunas; ganho weighted >= 0%
- Refutada-parcial: regressoes em > 5% das colunas
- Refutada: regressao weighted > 1%
"""

from __future__ import annotations

import csv
import sys
from collections import OrderedDict
from pathlib import Path

THIS = Path(__file__).parent
ROOT = THIS.parents[4]
SCRIPTS = ROOT / "scripts"
SRC = ROOT / "src"

sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(SRC))

from dataset_reader import DatasetReader  # noqa: E402
from tcf import encode as tcf_encode  # noqa: E402
from tcf.auto_min_len import detect_min_len_from_features  # noqa: E402
from tcf.column_features import analyze_column  # noqa: E402
from tcf.composicional.hcc_seqrle import HCCSeqRLE  # noqa: E402
from tcf.core.online import processar  # noqa: E402


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


def encode_shape_off(values, header="val"):
    """V1: pipeline canonical M10 mas SEM shape-preserve hint.

    Usa mesmo detect_min_len + HCCSeqRLE, mas processar canonical
    sempre (nunca processar_with_hint, prefer_shape_consistency=False).
    """
    unicas = dedup_preserve_order(values)
    features = analyze_column(values)
    min_len = detect_min_len_from_features(features)
    tokens, _ = processar(unicas, min_len=min_len)
    return HCCSeqRLE().encode(values, unicas, tokens, header)


def measure_col(values):
    body_off = encode_shape_off(values)
    body_on = tcf_encode(values)
    bytes_off = len(body_off.encode("utf-8"))
    bytes_on = len(body_on.encode("utf-8"))
    return bytes_off, bytes_on


def main():
    print("=== Sub-exp 01 — H-DA-07 shape-preserve on/off ===\n")
    datasets_dir = ROOT / "datasets" / "synthetic"

    all_results = []

    # D1-D9
    print(">> D1-D9 (sintetico)")
    for ds in D1_D9:
        path = datasets_dir / f"{ds}.csv"
        values = ler_csv_single_col(path)
        b_off, b_on = measure_col(values)
        delta = b_on - b_off
        marker = "OK" if delta == 0 else f"{delta:+d}"
        print(f"  {ds:<25} off={b_off:>4}  on={b_on:>4}  {marker}")
        all_results.append({
            'source': 'sintetico', 'dataset': ds, 'col': 'val',
            'off': b_off, 'on': b_on, 'delta': delta,
        })

    # Adult + TPC-H
    print("\n>> Adult Census")
    reader = DatasetReader("adult-census")
    for vol in [1000, 5000]:
        rows = reader.rows("adult", limit=vol)
        cols = rows_to_cols(rows)
        for cname, vals in cols.items():
            b_off, b_on = measure_col(vals)
            all_results.append({
                'source': f"adult-{vol}", 'dataset': cname, 'col': cname,
                'off': b_off, 'on': b_on, 'delta': b_on - b_off,
            })
    reader.close()

    print(">> TPC-H")
    reader = DatasetReader("tpch-sf001")
    for table in ["region", "customer", "lineitem"]:
        rows = reader.rows(table, limit=5000)
        cols = rows_to_cols(rows)
        for cname, vals in cols.items():
            b_off, b_on = measure_col(vals)
            all_results.append({
                'source': f"tpch.{table}-5k", 'dataset': cname, 'col': cname,
                'off': b_off, 'on': b_on, 'delta': b_on - b_off,
            })
    reader.close()

    # Aggregate
    total_off = sum(r['off'] for r in all_results)
    total_on = sum(r['on'] for r in all_results)
    total_delta = total_on - total_off
    pct = total_delta / total_off * 100 if total_off else 0

    print(f"\nTotal off={total_off:,}  on={total_on:,}  "
          f"delta={total_delta:+,}  ({pct:+.2f}%)")

    # Identifica colunas com diferenca (shape-preserve ativo)
    diffs = [r for r in all_results if r['delta'] != 0]
    wins = [r for r in diffs if r['delta'] < 0]
    losses = [r for r in diffs if r['delta'] > 0]

    print(f"\nColunas com diferenca: {len(diffs)}/{len(all_results)}")
    print(f"  Wins (on < off): {len(wins)}")
    print(f"  Losses (on > off): {len(losses)}")

    if wins:
        print(f"\n  Top wins (shape-preserve ajuda):")
        for r in sorted(wins, key=lambda x: x['delta'])[:10]:
            pct_r = r['delta'] / r['off'] * 100
            print(f"    {r['source']}/{r['col']:<25} off={r['off']:>6}  "
                  f"on={r['on']:>6}  ({r['delta']:+d}, {pct_r:+.2f}%)")

    if losses:
        print(f"\n  Losses (shape-preserve regride):")
        for r in sorted(losses, key=lambda x: -x['delta'])[:10]:
            pct_r = r['delta'] / r['off'] * 100
            print(f"    {r['source']}/{r['col']:<25} off={r['off']:>6}  "
                  f"on={r['on']:>6}  ({r['delta']:+d}, {pct_r:+.2f}%)")

    # Real-world split
    rw = [r for r in all_results if r['source'] != 'sintetico']
    rw_off = sum(r['off'] for r in rw)
    rw_on = sum(r['on'] for r in rw)
    rw_delta = rw_on - rw_off
    rw_pct = rw_delta / rw_off * 100 if rw_off else 0
    rw_losses = [r for r in rw if r['delta'] > 0]

    print(f"\n=== Veredito H-DA-07 ===\n")
    print(f"D1-D9: off={sum(r['off'] for r in all_results if r['source'] == 'sintetico'):,}  "
          f"on={sum(r['on'] for r in all_results if r['source'] == 'sintetico'):,}  "
          f"delta={sum(r['delta'] for r in all_results if r['source'] == 'sintetico'):+d}")
    print(f"Real-world: off={rw_off:,}  on={rw_on:,}  delta={rw_delta:+,}  ({rw_pct:+.2f}%)")
    print(f"Real-world losses: {len(rw_losses)}/{len(rw)} colunas")

    if rw_pct <= 0 and len(rw_losses) / len(rw) <= 0.05:
        veredito = "CONFIRMADA real-world: zero regressao significativa"
        status = "confirmada-empirica real-world"
    elif len(rw_losses) / len(rw) > 0.05:
        veredito = f"REFUTADA-PARCIAL: {len(rw_losses)}/{len(rw)} regressoes (>5%)"
        status = "refutada-parcial real-world"
    elif rw_pct > 1:
        veredito = f"REFUTADA: regressao weighted {rw_pct:.2f}%"
        status = "refutada-real-world"
    else:
        veredito = (f"MARGINAL: {len(rw_losses)} regressoes pequenas; "
                    f"ganho {-rw_pct:.2f}%")
        status = "confirmada-empirica marginal real-world"

    print(f"\n{veredito}")
    print(f"Status sugerido H-DA-07: {status}")

    # Report
    report = [
        "# Sub-exp 01 — H-DA-07 shape-preserve on/off",
        "",
        "## Estrategia",
        "",
        "- **V1 (off)**: pipeline canonical M10 SEM `processar_with_hint`",
        "  (so' `processar` canonical, mesmo detect_min_len + HCCSeqRLE)",
        "- **V2 (on)**: pipeline canonical M10 default (com cadence +",
        "  shape-preserve quando dispara)",
        "",
        "Mede impacto isolado do gating `detect_cadence` + `processar_with_hint`",
        "no real-world (Adult + TPC-H) e D1-D9 (controle).",
        "",
        "## Tabela completa (apenas colunas com diferenca)",
        "",
        "| Source | Col | off (B) | on (B) | delta | pct |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for r in sorted(diffs, key=lambda x: x['delta']):
        pct_r = r['delta'] / r['off'] * 100
        report.append(f"| {r['source']} | {r['col']} | {r['off']:,} | "
                      f"{r['on']:,} | {r['delta']:+d} | {pct_r:+.2f}% |")
    if not diffs:
        report.append("| (nenhuma) | | | | | |")

    report.extend([
        "",
        "## Agregado",
        "",
        f"| Camada | off (B) | on (B) | delta | pct |",
        f"|---|---:|---:|---:|---:|",
    ])
    s_off = sum(r['off'] for r in all_results if r['source'] == 'sintetico')
    s_on = sum(r['on'] for r in all_results if r['source'] == 'sintetico')
    report.append(f"| Sintetico D1-D9 | {s_off:,} | {s_on:,} | "
                  f"{s_on - s_off:+d} | {(s_on - s_off) / s_off * 100:+.2f}% |")
    report.append(f"| Real-world (Adult+TPC-H) | {rw_off:,} | {rw_on:,} | "
                  f"{rw_delta:+,} | {rw_pct:+.2f}% |")
    report.append(f"| **Total** | **{total_off:,}** | **{total_on:,}** | "
                  f"**{total_delta:+,}** | **{pct:+.2f}%** |")

    report.extend([
        "",
        "## Distribuicao",
        "",
        f"- Colunas com diferenca: {len(diffs)}/{len(all_results)}",
        f"- Wins (shape-preserve ajuda): {len(wins)}",
        f"- Losses (shape-preserve regride): {len(losses)}",
        f"  - Real-world losses: {len(rw_losses)}/{len(rw)} cols",
        "",
        "## Veredito",
        "",
        f"**{veredito}**",
        "",
        f"**Status sugerido H-DA-07**: `{status}`",
        "",
    ])

    out = THIS / "result.md"
    out.write_bytes(("\n".join(report) + "\n").encode("utf-8"))
    print(f"\nresult.md: {out}")


if __name__ == "__main__":
    main()

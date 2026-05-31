"""Sub-exp 01 — caracterizar low-card cols + estimar ganho enumerated.

Pra cada coluna em Adult+TPC-H + D1-D9 (controle):
1. Bytes atual TCF M10 (`tcf.encode`)
2. Lower bound teorico enumerated:
   - dict overhead: sum(len(v) for v in unicas) + (N-1) separadores
   - body: n_rows * ceil(log10(N+1)) chars + (n_rows-1) separadores

Comparar bytes_m10 vs lower_bound. Ganho potencial = bytes_m10 -
lower_bound (positivo = ganho).

Filtro: so' colunas com cardinality < 0.05 (low-card).

Veredito:
- Ganho weighted real-world >= 5%: GO prototype
- Caso contrario: NO-GO, M10 ja' captura bem
"""

from __future__ import annotations

import csv
import math
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


D1_D9 = [
    "D1-emails-simples", "D2-emails-quote-id", "D3-stress-substring",
    "D4-caos-mix", "D5-padroes-multiplos", "D6-poucos-em-ruido",
    "D7-aninhamento", "D8-cabeca-cauda", "D9-frequencia-alta",
]

CARD_THRESHOLD = 0.05  # low-card if card < threshold


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


def estimate_enumerated_bytes(values):
    """Lower bound teorico encoder enumerated explicito.

    Assumindo:
    - dict inline: cada atom como string + 1 separador entre atoms
    - body: indice por linha (1..N) como digits + 1 separador
    - sem overhead extra de marker/header

    Realistic: encoder real teria overhead (marker prefix, etc.) — esse
    e' apenas LOWER BOUND.
    """
    unicas = dedup_preserve_order(values)
    n_unicas = len(unicas)
    n_rows = len(values)
    if n_unicas == 0:
        return 0

    # Dict inline: sum(atom_len) + (N-1) seps
    dict_bytes = sum(len(u) for u in unicas) + max(0, n_unicas - 1)

    # Body: n_rows * digits_per_index + (n_rows - 1) seps
    if n_unicas == 1:
        digits_per_idx = 1
    else:
        digits_per_idx = len(str(n_unicas))
    body_bytes = n_rows * digits_per_idx + max(0, n_rows - 1)

    return dict_bytes + body_bytes


def analyze_col(source, name, values):
    if not values:
        return None
    unicas = dedup_preserve_order(values)
    n_rows = len(values)
    n_unicas = len(unicas)
    card = n_unicas / n_rows if n_rows else 0

    # Bytes atual TCF M10
    body_m10 = tcf_encode(values)
    bytes_m10 = len(body_m10.encode("utf-8"))

    # Lower bound enumerated
    bytes_enum_lb = estimate_enumerated_bytes(values)

    return {
        'source': source,
        'col': name,
        'n_rows': n_rows,
        'n_unicas': n_unicas,
        'cardinality': card,
        'bytes_m10': bytes_m10,
        'bytes_enum_lb': bytes_enum_lb,
        'delta': bytes_enum_lb - bytes_m10,
        'gain_pct': ((bytes_m10 - bytes_enum_lb) / bytes_m10 * 100
                     if bytes_m10 else 0),
    }


def main():
    print("=== Sub-exp 01 — caracterizar low-card cols ===\n")
    datasets_dir = ROOT / "datasets" / "synthetic"

    all_results = []

    # D1-D9 controle
    print(">> D1-D9 (controle)")
    for ds in D1_D9:
        values = ler_csv_single_col(datasets_dir / f"{ds}.csv")
        r = analyze_col('sintetico', ds, values)
        if r:
            all_results.append(r)

    # Adult Census
    print(">> Adult Census")
    reader = DatasetReader("adult-census")
    for vol in [1000, 5000]:
        rows = reader.rows("adult", limit=vol)
        cols = rows_to_cols(rows)
        for cname, vals in cols.items():
            r = analyze_col(f"adult-{vol}", cname, vals)
            if r:
                all_results.append(r)
    reader.close()

    # TPC-H
    print(">> TPC-H")
    reader = DatasetReader("tpch-sf001")
    for table in ["region", "customer", "lineitem"]:
        rows = reader.rows(table, limit=5000)
        cols = rows_to_cols(rows)
        for cname, vals in cols.items():
            r = analyze_col(f"tpch.{table}-5k", cname, vals)
            if r:
                all_results.append(r)
    reader.close()

    # Filtra low-card
    low_card = [r for r in all_results if r['cardinality'] < CARD_THRESHOLD]
    print(f"\nTotal colunas: {len(all_results)}")
    print(f"Low-card cols (card < {CARD_THRESHOLD}): {len(low_card)}")

    # Tabela low-card
    print(f"\n=== Low-card cols (potenciais para enumerated) ===\n")
    print(f"{'source':<18} {'col':<22} {'n_rows':>6} {'n_uniq':>6} "
          f"{'card':>5} {'m10':>7} {'enum_lb':>8} {'delta':>7} {'gain':>7}")
    print("-" * 90)
    for r in sorted(low_card, key=lambda x: x['delta']):
        print(f"{r['source']:<18} {r['col']:<22} {r['n_rows']:>6} "
              f"{r['n_unicas']:>6} {r['cardinality']:>5.3f} "
              f"{r['bytes_m10']:>7,} {r['bytes_enum_lb']:>8,} "
              f"{r['delta']:>+7} {r['gain_pct']:>+6.2f}%")

    # Agregado low-card
    total_m10 = sum(r['bytes_m10'] for r in low_card)
    total_enum_lb = sum(r['bytes_enum_lb'] for r in low_card)
    total_delta = total_enum_lb - total_m10
    total_gain = -total_delta / total_m10 * 100 if total_m10 else 0

    rw_low_card = [r for r in low_card if r['source'] != 'sintetico']
    rw_m10 = sum(r['bytes_m10'] for r in rw_low_card)
    rw_enum_lb = sum(r['bytes_enum_lb'] for r in rw_low_card)
    rw_delta = rw_enum_lb - rw_m10
    rw_gain = -rw_delta / rw_m10 * 100 if rw_m10 else 0

    # Tambem agregar TODOS os bytes real-world pra weighted geral
    rw_all = [r for r in all_results if r['source'] != 'sintetico']
    rw_total_m10 = sum(r['bytes_m10'] for r in rw_all)
    weighted_pct_over_all = -rw_delta / rw_total_m10 * 100 if rw_total_m10 else 0

    print(f"\nAgregado low-card:")
    print(f"  Total bytes M10: {total_m10:,}")
    print(f"  Total bytes enum LB: {total_enum_lb:,}")
    print(f"  Delta: {total_delta:+,}  ({total_gain:+.2f}% sobre low-card)")
    print()
    print(f"Agregado low-card REAL-WORLD apenas:")
    print(f"  Total bytes M10 (low-card RW): {rw_m10:,}")
    print(f"  Delta: {rw_delta:+,}  ({rw_gain:+.2f}% sobre low-card RW)")
    print()
    print(f"  Real-world TOTAL (todas cols): {rw_total_m10:,}")
    print(f"  Weighted over all RW: {weighted_pct_over_all:+.2f}%")

    # Veredito
    print(f"\n=== Veredito ===\n")
    if rw_gain >= 5:
        veredito = (f"GO: ganho {rw_gain:.2f}% sobre low-card RW; "
                    f"{weighted_pct_over_all:.2f}% weighted total RW. "
                    f"Vale prototype encoder enumerated.")
        status = "go-prototype"
    elif weighted_pct_over_all >= 2:
        veredito = (f"MARGINAL: low-card cols representam pequena fracao "
                    f"do total RW ({weighted_pct_over_all:.2f}%). Prototype "
                    f"opcional — ganho seletivo em algumas colunas.")
        status = "marginal-condicional"
    else:
        veredito = (f"NO-GO: ganho weighted total {weighted_pct_over_all:.2f}% "
                    f"< 2%. M10 ja' captura bem. Encoder enumerated nao vale.")
        status = "no-go-m10-suficiente"

    print(veredito)
    print(f"Status: {status}")

    # Report
    report = [
        "# Sub-exp 01 — caracterizar low-card cols",
        "",
        "## Setup",
        "",
        f"- Threshold low-card: cardinality < {CARD_THRESHOLD}",
        f"- Total colunas testadas: {len(all_results)}",
        f"- Low-card cols: {len(low_card)}",
        "",
        "## Estimativa enumerated (lower bound)",
        "",
        "```",
        "dict_bytes = sum(len(atom) for atom in unicas) + (N-1) seps",
        "body_bytes = n_rows * digits_per_idx + (n_rows-1) seps",
        "total = dict_bytes + body_bytes",
        "```",
        "",
        "Real encoder teria overhead extra (marker prefix etc.) —",
        "isso e' LOWER BOUND teorico.",
        "",
        "## Tabela low-card cols",
        "",
        "| Source | Col | n_rows | n_uniq | card | M10 (B) | enum LB (B) | delta | gain |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for r in sorted(low_card, key=lambda x: x['delta']):
        report.append(
            f"| {r['source']} | {r['col']} | {r['n_rows']} | {r['n_unicas']} | "
            f"{r['cardinality']:.3f} | {r['bytes_m10']:,} | "
            f"{r['bytes_enum_lb']:,} | {r['delta']:+d} | "
            f"{r['gain_pct']:+.2f}% |"
        )

    report.extend([
        "",
        "## Agregados",
        "",
        f"| Cohort | bytes M10 | bytes enum LB | delta | gain |",
        f"|---|---:|---:|---:|---:|",
        f"| Low-card total | {total_m10:,} | {total_enum_lb:,} | "
        f"{total_delta:+,} | {total_gain:+.2f}% |",
        f"| Low-card real-world apenas | {rw_m10:,} | {rw_enum_lb:,} | "
        f"{rw_delta:+,} | {rw_gain:+.2f}% |",
        "",
        f"**Weighted over all RW cols (incl. high-card)**: "
        f"{weighted_pct_over_all:+.2f}%",
        f"(real-world total: {rw_total_m10:,}B em todas as cols)",
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

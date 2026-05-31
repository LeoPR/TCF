"""Sub-exp 04 — validacao pos-welding em EXP-010 prototype.

Welding canonical em src/tcf adiado (aguarda aprovacao explicita).
Welding intermediario em EXP-010 prototype (auto_min_len.py +
delta_aware.encode_column min_len auto-detect default).

Mede:
1. D1-D9 single-col bytes (M9 baseline 1615B INVARIANT)
2. RT (round-trip) em D1-D9 + Adult+TPC-H
3. Adult+TPC-H ganho weighted (target ~9.87%)

Compara:
- baseline: encode_column(rows, min_len=3) — explicit
- novo: encode_column(rows) — min_len auto-detect via detect_min_len
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
EXP_010 = ROOT / "experiments" / "lab" / "clean" / "EXP-010-tcf-delta-aware-prototype"

sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(SRC))
sys.path.insert(0, str(EXP_010))

from dataset_reader import DatasetReader  # noqa: E402
from delta_aware import encode_column, decode_column  # noqa: E402


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


def measure_col(values):
    """Encode com min_len=3 forçado vs min_len=None (auto-detect).

    Mede so' o body (sem shebang) pra comparacao fair.
    """
    body_base, info_base = encode_column(values, min_len=3, include_shebang=False)
    body_new, info_new = encode_column(values, min_len=None, include_shebang=False)

    bytes_base = len(body_base.encode("utf-8"))
    bytes_new = len(body_new.encode("utf-8"))

    # RT: decode usando shebang
    text_with_shebang, _ = encode_column(values, min_len=None, include_shebang=True)
    decoded = decode_column(text_with_shebang)
    rt = "OK" if decoded == values else "FAIL"

    return {
        'bytes_base': bytes_base,
        'bytes_new': bytes_new,
        'ml_new': info_new['min_len'],
        'rt': rt,
    }


def main():
    print("=== Sub-exp 04 — validacao prototipo EXP-010 ===\n")

    # D1-D9 baseline
    print(">> D1-D9 (M9 baseline INVARIANT)")
    datasets_dir = ROOT / "datasets" / "synthetic"
    total_base = total_new = 0
    rt_pass = 0
    d1d9 = []
    for ds in D1_D9:
        path = datasets_dir / f"{ds}.csv"
        values = ler_csv_single_col(path)
        r = measure_col(values)
        r['dataset'] = ds
        d1d9.append(r)
        total_base += r['bytes_base']
        total_new += r['bytes_new']
        if r['rt'] == 'OK':
            rt_pass += 1
        delta = r['bytes_new'] - r['bytes_base']
        marker = "OK" if delta == 0 else f"{delta:+d}"
        print(f"  {ds:<25} base={r['bytes_base']:>4}  new={r['bytes_new']:>4}  "
              f"{marker:<6} ml={r['ml_new']} RT={r['rt']}")
    print(f"  {'TOTAL':<25} base={total_base:>4}  new={total_new:>4}  "
          f"delta={total_new - total_base:+d}  RT={rt_pass}/{len(d1d9)}")

    d1d9_preserved = (total_new == total_base)
    d1d9_rt_ok = (rt_pass == len(d1d9))

    # Adult Census
    print("\n>> Adult Census")
    real_results = []
    reader = DatasetReader("adult-census")
    for vol in [1000, 5000]:
        rows = reader.rows("adult", limit=vol)
        cols = rows_to_cols(rows)
        for cname, vals in cols.items():
            r = measure_col(vals)
            r['source'] = f"adult-{vol}"
            r['col'] = cname
            real_results.append(r)
    reader.close()

    # TPC-H
    print(">> TPC-H")
    reader = DatasetReader("tpch-sf001")
    for table in ["region", "customer", "lineitem"]:
        rows = reader.rows(table, limit=5000)
        cols = rows_to_cols(rows)
        for cname, vals in cols.items():
            r = measure_col(vals)
            r['source'] = f"tpch.{table}-5k"
            r['col'] = cname
            real_results.append(r)
    reader.close()

    # Aggregate
    rw_base = sum(r['bytes_base'] for r in real_results)
    rw_new = sum(r['bytes_new'] for r in real_results)
    rw_rt_pass = sum(1 for r in real_results if r['rt'] == 'OK')
    rw_gain = (rw_base - rw_new) / rw_base * 100 if rw_base else 0
    rw_rt_ok = (rw_rt_pass == len(real_results))

    print(f"\n  Real-world TOTAL: base={rw_base:,}  new={rw_new:,}  "
          f"delta={rw_new - rw_base:+,}  gain={rw_gain:.2f}%  "
          f"RT={rw_rt_pass}/{len(real_results)}")

    real_results.sort(key=lambda r: r['bytes_new'] - r['bytes_base'])
    print("\n  Top 10 wins:")
    for r in real_results[:10]:
        d = r['bytes_new'] - r['bytes_base']
        if d >= 0:
            break
        pct = (r['bytes_base'] - r['bytes_new']) / r['bytes_base'] * 100
        print(f"    {r['source']}/{r['col']:<25} {r['bytes_base']:>6} -> "
              f"{r['bytes_new']:>6} ml={r['ml_new']} ({d:+d}, -{pct:.2f}%)")

    regr = [r for r in real_results if r['bytes_new'] > r['bytes_base']]
    if regr:
        print(f"\n  Regressoes ({len(regr)}):")
        for r in regr[:10]:
            d = r['bytes_new'] - r['bytes_base']
            print(f"    {r['source']}/{r['col']:<25} {r['bytes_base']:>6} -> "
                  f"{r['bytes_new']:>6} ml={r['ml_new']} (+{d}B)")

    # Veredito
    print("\n=== Veredito prototipo ===\n")
    print(f"D1-D9 M9 baseline preservado: {'YES' if d1d9_preserved else 'NO'} "
          f"(base={total_base}, new={total_new})")
    print(f"D1-D9 RT 100%: {'YES' if d1d9_rt_ok else 'NO'} ({rt_pass}/{len(d1d9)})")
    print(f"Real-world ganho: {rw_gain:.2f}% (target ~9.87%)")
    print(f"Real-world RT 100%: {'YES' if rw_rt_ok else 'NO'} "
          f"({rw_rt_pass}/{len(real_results)})")

    # Threshold ajustado: EXP-010 ja' tem HCC seq-RLE + auto-cadence,
    # baseline ja' mais comprimida que canonical M8A puro do sub-exp 02
    # (9.87% predito era vs M8A puro). 5%+ adicional sobre EXP-010 e' forte.
    welding_ok = (d1d9_preserved and d1d9_rt_ok and rw_rt_ok and rw_gain >= 5)
    print(f"\n** PROTOTYPE WELDING {'CONFIRMED' if welding_ok else 'PROBLEMS'} **")

    # Report
    report = [
        "# Sub-exp 04 — validacao prototipo EXP-010 (H-DA-11)",
        "",
        "## Strategy",
        "",
        "Welding canonical em src/tcf adiado (CLAUDE.md exige aprovacao",
        "explicita). Welding intermediario em EXP-010 prototype:",
        "- novo `auto_min_len.py` (heur v3 + gating)",
        "- modificado `delta_aware.encode_column` (default `min_len=None`",
        "  -> auto-detect)",
        "",
        "Esta validacao mede o ganho real do prototipo, comparativo entre:",
        "- baseline: `encode_column(rows, min_len=3)` (explicit)",
        "- novo: `encode_column(rows)` (min_len auto-detect)",
        "",
        "## D1-D9 (M9 baseline INVARIANT)",
        "",
        "| Dataset | base (B) | new (B) | delta | ml | RT |",
        "|---|---:|---:|---:|---|---|",
    ]
    for r in d1d9:
        delta = r['bytes_new'] - r['bytes_base']
        report.append(f"| {r['dataset']} | {r['bytes_base']} | {r['bytes_new']} | "
                      f"{delta:+d} | {r['ml_new']} | {r['rt']} |")
    report.append(f"| **TOTAL** | **{total_base}** | **{total_new}** | "
                  f"**{total_new - total_base:+d}** | — | {rt_pass}/{len(d1d9)} |")

    report.extend([
        "",
        f"**M9 baseline preservado**: {'**SIM**' if d1d9_preserved else '**NAO**'} "
        f"(total={total_new}B)",
        f"**RT 100%**: {'**SIM**' if d1d9_rt_ok else '**NAO**'}",
        "",
        "## Real-world Adult + TPC-H",
        "",
        f"- Total baseline (ml=3 explicit): {rw_base:,}B",
        f"- Total novo (auto-detect):       {rw_new:,}B",
        f"- **Gain**: {rw_base - rw_new:+,}B ({rw_gain:.2f}% weighted)",
        f"- RT: {rw_rt_pass}/{len(real_results)}",
        "",
        "### Top 10 wins",
        "",
        "| Col | base | new | ml | delta | pct |",
        "|---|---:|---:|---|---:|---:|",
    ])
    for r in real_results[:10]:
        d = r['bytes_new'] - r['bytes_base']
        if d >= 0:
            break
        pct = (r['bytes_base'] - r['bytes_new']) / r['bytes_base'] * 100
        report.append(f"| {r['source']}/{r['col']} | {r['bytes_base']:,} | "
                      f"{r['bytes_new']:,} | {r['ml_new']} | {d:+d} | -{pct:.2f}% |")

    if regr:
        report.append("")
        report.append("### Regressoes")
        report.append("")
        report.append("| Col | base | new | ml | delta |")
        report.append("|---|---:|---:|---|---:|")
        for r in regr:
            d = r['bytes_new'] - r['bytes_base']
            report.append(f"| {r['source']}/{r['col']} | {r['bytes_base']:,} | "
                          f"{r['bytes_new']:,} | {r['ml_new']} | +{d} |")

    report.extend([
        "",
        "## Veredito",
        "",
        f"- D1-D9 baseline preservado: {'OK' if d1d9_preserved else 'FAIL'}",
        f"- D1-D9 RT 100%: {'OK' if d1d9_rt_ok else 'FAIL'}",
        f"- Real-world gain >= 5%: {'OK' if rw_gain >= 5 else 'FAIL'} "
        f"({rw_gain:.2f}%; nota: vs EXP-010 baseline ja' otimizado, "
        f"diferente dos 9.87% predito vs M8A canonical puro)",
        f"- Real-world RT 100%: {'OK' if rw_rt_ok else 'FAIL'}",
        "",
        f"**PROTOTYPE H-DA-11: {'CONFIRMED' if welding_ok else 'PROBLEMS'}**",
        "",
        "## Proximos passos",
        "",
        "- Welding canonical em `src/tcf/encoder.py` aguarda aprovacao",
        "  explicita do owner (regra CLAUDE.md)",
        "- ADR-0010 atualizado registrando estado intermediario",
        "",
    ])

    out = THIS / "result.md"
    out.write_bytes(("\n".join(report) + "\n").encode("utf-8"))
    print(f"\nresult.md: {out}")


if __name__ == "__main__":
    main()

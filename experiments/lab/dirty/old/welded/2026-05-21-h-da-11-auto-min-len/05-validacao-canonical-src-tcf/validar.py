"""Sub-exp 05 — validacao welding canonical em src/tcf.

Diferente do sub-exp 04 (que validou EXP-010 prototype), aqui medimos
diretamente a API canonical `from tcf import encode, decode`.

Baseline: encoder canonical com min_len=3 hard-coded
  `M8AVirtualRefsSyntax().encode(values, unicas, processar(unicas, ml=3))`
Welded: `tcf.encode(values)` (chama detect_min_len por dentro)

Critérios:
1. D1-D9 single-col bytes == M9 baseline 1615B EXATO (INVARIANT)
2. RT 100% em D1-D9 (decode reproduz original)
3. Adult+TPC-H ganho weighted >= 7% (target ~9%)
4. RT 100% real-world
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
from tcf import decode as tcf_decode  # noqa: E402
from tcf.composicional.syntax import M8AVirtualRefsSyntax  # noqa: E402
from tcf.core.online import processar  # noqa: E402


D1_D9 = [
    "D1-emails-simples", "D2-emails-quote-id", "D3-stress-substring",
    "D4-caos-mix", "D5-padroes-multiplos", "D6-poucos-em-ruido",
    "D7-aninhamento", "D8-cabeca-cauda", "D9-frequencia-alta",
]

M9_BASELINE = 1615  # INVARIANT


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


def encode_baseline(values, header="val"):
    """Encode com min_len=3 explicit (baseline pre-welding)."""
    unicas = dedup_preserve_order(values)
    tokens, _ = processar(unicas, min_len=3)
    return M8AVirtualRefsSyntax().encode(values, unicas, tokens, header)


def measure_col(values):
    """Mede:
    - bytes_base: encoder canonical com min_len=3 hard-coded
    - bytes_new: tcf.encode (auto-detect via detect_min_len)
    - RT: tcf.decode(tcf.encode(values)) == values

    NOTA: tcf.encode (canonical M14) NAO emite shebang — output e' body
    direto. Comparacao fair: body baseline vs tcf.encode output direto.
    """
    body_base = encode_baseline(values)
    body_new = tcf_encode(values)  # canonical NAO tem shebang

    bytes_base = len(body_base.encode("utf-8"))
    bytes_new = len(body_new.encode("utf-8"))

    # RT canonical
    decoded = tcf_decode(body_new)
    rt = "OK" if decoded == values else "FAIL"

    return {
        'bytes_base': bytes_base,
        'bytes_new': bytes_new,
        'rt': rt,
    }


def main():
    print("=== Sub-exp 05 — validacao welding canonical src/tcf ===\n")

    # D1-D9 (M9 baseline)
    print(">> D1-D9 (M9 baseline = 1615B INVARIANT)")
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
        delta = r['bytes_new'] - r['bytes_base']
        marker = "OK" if delta == 0 else f"{delta:+d}"
        print(f"  {ds:<25} base={r['bytes_base']:>4}  new={r['bytes_new']:>4}  "
              f"{marker:<6} RT={r['rt']}")
        total_base += r['bytes_base']
        total_new += r['bytes_new']
        if r['rt'] == 'OK':
            rt_pass += 1

    print(f"  {'TOTAL':<25} base={total_base:>4}  new={total_new:>4}  "
          f"delta={total_new - total_base:+d}  RT={rt_pass}/{len(d1d9)}")

    d1d9_match_m9 = (total_base == M9_BASELINE)
    d1d9_preserved = (total_new == total_base)
    d1d9_rt_ok = (rt_pass == len(d1d9))

    if not d1d9_match_m9:
        print(f"  WARNING: baseline base={total_base} != M9 expected {M9_BASELINE}")

    # Adult Census + TPC-H
    print("\n>> Adult Census + TPC-H")
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

    rw_base = sum(r['bytes_base'] for r in real_results)
    rw_new = sum(r['bytes_new'] for r in real_results)
    rw_rt_pass = sum(1 for r in real_results if r['rt'] == 'OK')
    rw_gain = (rw_base - rw_new) / rw_base * 100 if rw_base else 0
    rw_rt_ok = (rw_rt_pass == len(real_results))

    print(f"\n  Real-world TOTAL: base={rw_base:,}  new={rw_new:,}  "
          f"delta={rw_new - rw_base:+,}  gain={rw_gain:.2f}%  "
          f"RT={rw_rt_pass}/{len(real_results)}")

    # Top 10 wins
    real_results.sort(key=lambda r: r['bytes_new'] - r['bytes_base'])
    print("\n  Top 10 wins:")
    for r in real_results[:10]:
        d = r['bytes_new'] - r['bytes_base']
        if d >= 0:
            break
        pct = (r['bytes_base'] - r['bytes_new']) / r['bytes_base'] * 100
        print(f"    {r['source']}/{r['col']:<25} {r['bytes_base']:>6} -> "
              f"{r['bytes_new']:>6} ({d:+d}, -{pct:.2f}%)")

    regr = [r for r in real_results if r['bytes_new'] > r['bytes_base']]
    if regr:
        print(f"\n  Regressoes ({len(regr)}):")
        for r in regr[:10]:
            d = r['bytes_new'] - r['bytes_base']
            print(f"    {r['source']}/{r['col']:<25} (+{d}B)")

    # Veredito
    print("\n=== Veredito canonical welding ===\n")
    print(f"D1-D9 baseline M9 (1615B) base medido: {total_base}B "
          f"({'MATCH' if d1d9_match_m9 else 'MISMATCH'})")
    print(f"D1-D9 welding preserva baseline: {'YES' if d1d9_preserved else 'NO'} "
          f"(new={total_new}B)")
    print(f"D1-D9 RT 100%: {'YES' if d1d9_rt_ok else 'NO'} "
          f"({rt_pass}/{len(d1d9)})")
    print(f"Real-world ganho weighted: {rw_gain:.2f}% (target ~9%)")
    print(f"Real-world RT 100%: {'YES' if rw_rt_ok else 'NO'} "
          f"({rw_rt_pass}/{len(real_results)})")

    welding_ok = (d1d9_preserved and d1d9_rt_ok and rw_rt_ok and rw_gain >= 7)
    print(f"\n** CANONICAL WELDING {'CONFIRMED' if welding_ok else 'PROBLEMS'} **")

    # Report
    report = [
        "# Sub-exp 05 — validacao welding canonical src/tcf (H-DA-11)",
        "",
        "## Strategy",
        "",
        "Welding canonical em src/tcf:",
        "- `src/tcf/auto_min_len.py` (novo modulo, detect_min_len + helper)",
        "- `src/tcf/encoder.py` (encode() chama detect_min_len em vez de min_len=3)",
        "",
        "Comparativo:",
        "- baseline: M8AVirtualRefsSyntax + processar(min_len=3) explicit",
        "- welded: `tcf.encode(values)` (auto-detect)",
        "",
        "## D1-D9 (M9 baseline 1615B INVARIANT)",
        "",
        "| Dataset | base (B) | new (B) | delta | RT |",
        "|---|---:|---:|---:|---|",
    ]
    for r in d1d9:
        delta = r['bytes_new'] - r['bytes_base']
        report.append(f"| {r['dataset']} | {r['bytes_base']} | {r['bytes_new']} | "
                      f"{delta:+d} | {r['rt']} |")
    report.append(f"| **TOTAL** | **{total_base}** | **{total_new}** | "
                  f"**{total_new - total_base:+d}** | {rt_pass}/{len(d1d9)} |")

    report.extend([
        "",
        f"**M9 baseline 1615B**: {'MATCH' if d1d9_match_m9 else 'MISMATCH'} "
        f"(base medido={total_base}B)",
        f"**Welding preserva baseline**: {'SIM' if d1d9_preserved else 'NAO'} "
        f"(new={total_new}B)",
        f"**RT 100%**: {'SIM' if d1d9_rt_ok else 'NAO'} "
        f"({rt_pass}/{len(d1d9)})",
        "",
        "## Real-world (Adult + TPC-H)",
        "",
        f"- Baseline total: {rw_base:,}B",
        f"- Welded total:   {rw_new:,}B",
        f"- **Delta**: {rw_new - rw_base:+,}B (**{rw_gain:.2f}%** weighted)",
        f"- RT: {rw_rt_pass}/{len(real_results)}",
        "",
        "### Top 10 wins",
        "",
        "| Col | base | new | delta | pct |",
        "|---|---:|---:|---:|---:|",
    ])
    for r in real_results[:10]:
        d = r['bytes_new'] - r['bytes_base']
        if d >= 0:
            break
        pct = (r['bytes_base'] - r['bytes_new']) / r['bytes_base'] * 100
        report.append(f"| {r['source']}/{r['col']} | {r['bytes_base']:,} | "
                      f"{r['bytes_new']:,} | {d:+d} | -{pct:.2f}% |")

    if regr:
        report.append("")
        report.append("### Regressoes")
        report.append("")
        report.append("| Col | base | new | delta |")
        report.append("|---|---:|---:|---:|")
        for r in regr:
            d = r['bytes_new'] - r['bytes_base']
            report.append(f"| {r['source']}/{r['col']} | {r['bytes_base']:,} | "
                          f"{r['bytes_new']:,} | +{d} |")

    report.extend([
        "",
        "## Veredito canonical welding",
        "",
        f"- D1-D9 baseline preservado: {'OK' if d1d9_preserved else 'FAIL'}",
        f"- D1-D9 RT 100%: {'OK' if d1d9_rt_ok else 'FAIL'}",
        f"- Real-world gain >= 7%: {'OK' if rw_gain >= 7 else 'FAIL'} "
        f"({rw_gain:.2f}%)",
        f"- Real-world RT 100%: {'OK' if rw_rt_ok else 'FAIL'}",
        "",
        f"**CANONICAL WELDING: {'CONFIRMED' if welding_ok else 'PROBLEMS'}**",
        "",
    ])

    out = THIS / "result.md"
    out.write_bytes(("\n".join(report) + "\n").encode("utf-8"))
    print(f"\nresult.md: {out}")


if __name__ == "__main__":
    main()

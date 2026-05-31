"""Sub-exp 04 — validacao pos-welding H-DA-11 em src/tcf.

Mede:
1. D1-D9 single-col bytes (M9 baseline 1615B INVARIANT)
2. RT (round-trip) decode reproduz original em D1-D9
3. Adult+TPC-H bytes (per coluna single-col + agregado)
4. Captura % do ganho oracle real-world (target ~9.87%)

Compara contra:
- baseline: encode com tcf.core.online.processar(unicas, min_len=3) hard-coded
- novo: tcf.encode() (que agora chama detect_min_len)
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
    """Encode com min_len=3 hard-coded (baseline pre-welding)."""
    unicas = dedup_preserve_order(values)
    tokens, _ = processar(unicas, min_len=3)
    return M8AVirtualRefsSyntax().encode(values, unicas, tokens, header)


def measure_col(values):
    body_base = encode_baseline(values)
    tcf_full = tcf_encode(values)  # full TCF text com shebang
    # extrai body (apos primeira linha shebang)
    raw = tcf_full.encode("utf-8")
    nl = raw.find(b"\n")
    body_new = raw[nl + 1:].decode("utf-8")

    bytes_base_body = len(body_base.encode("utf-8"))
    bytes_new_body = len(body_new.encode("utf-8"))

    # RT
    decoded = tcf_decode(tcf_full)
    rt = "OK" if decoded == values else "FAIL"

    return bytes_base_body, bytes_new_body, rt


def main():
    print("=== Sub-exp 04 — validacao pos-welding H-DA-11 ===\n")

    # D1-D9 baseline
    print(">> D1-D9 (M9 baseline INVARIANT)")
    datasets_dir = ROOT / "datasets" / "synthetic"
    total_base = total_new = 0
    rt_pass = 0
    rt_total = 0
    for ds in D1_D9:
        path = datasets_dir / f"{ds}.csv"
        values = ler_csv_single_col(path)
        bb, bn, rt = measure_col(values)
        delta = bn - bb
        marker = "OK" if bn == bb else f"{delta:+d}"
        print(f"  {ds:<25} base={bb:>4}  new={bn:>4}  {marker:<6} RT={rt}")
        total_base += bb
        total_new += bn
        if rt == "OK":
            rt_pass += 1
        rt_total += 1
    print(f"  {'TOTAL':<25} base={total_base:>4}  new={total_new:>4}  "
          f"delta={total_new - total_base:+d}  RT={rt_pass}/{rt_total}")

    d1d9_preserved = (total_new == total_base)
    d1d9_rt_ok = (rt_pass == rt_total)

    # Adult Census
    print("\n>> Adult Census (real-world)")
    real_results = []
    reader = DatasetReader("adult-census")
    for vol in [1000, 5000]:
        rows = reader.rows("adult", limit=vol)
        cols = rows_to_cols(rows)
        for cname, vals in cols.items():
            bb, bn, rt = measure_col(vals)
            real_results.append({
                'source': f"adult-{vol}", 'col': cname,
                'base': bb, 'new': bn, 'rt': rt,
            })
    reader.close()

    # TPC-H
    print(">> TPC-H (real-world)")
    reader = DatasetReader("tpch-sf001")
    for table in ["region", "customer", "lineitem"]:
        rows = reader.rows(table, limit=5000)
        cols = rows_to_cols(rows)
        for cname, vals in cols.items():
            bb, bn, rt = measure_col(vals)
            real_results.append({
                'source': f"tpch.{table}-5k", 'col': cname,
                'base': bb, 'new': bn, 'rt': rt,
            })
    reader.close()

    # Print real-world
    rw_total_base = sum(r['base'] for r in real_results)
    rw_total_new = sum(r['new'] for r in real_results)
    rw_rt_pass = sum(1 for r in real_results if r['rt'] == 'OK')

    print(f"\n  Real-world TOTAL: base={rw_total_base:,}  "
          f"new={rw_total_new:,}  "
          f"delta={rw_total_new - rw_total_base:+,}  "
          f"gain={(rw_total_base - rw_total_new) / rw_total_base * 100:.2f}%  "
          f"RT={rw_rt_pass}/{len(real_results)}")

    rw_gain = (rw_total_base - rw_total_new) / rw_total_base * 100
    rw_rt_ok = (rw_rt_pass == len(real_results))

    # Top wins/losses
    real_results.sort(key=lambda r: r['new'] - r['base'])
    print("\n  Top 10 wins (biggest byte reductions):")
    for r in real_results[:10]:
        d = r['new'] - r['base']
        if d >= 0:
            break
        pct = (r['base'] - r['new']) / r['base'] * 100 if r['base'] else 0
        print(f"    {r['source']}/{r['col']:<25} base={r['base']:>6}  "
              f"new={r['new']:>6}  ({d:+d}, -{pct:.2f}%)")

    regr = [r for r in real_results if r['new'] > r['base']]
    if regr:
        print(f"\n  Regressoes ({len(regr)}):")
        for r in regr[:5]:
            d = r['new'] - r['base']
            print(f"    {r['source']}/{r['col']:<25} (+{d}B)")

    # Veredito
    print("\n=== Veredito pos-welding ===\n")
    print(f"D1-D9 M9 baseline 1615B preservado: {'YES' if d1d9_preserved else 'NO'} "
          f"({total_new}B)")
    print(f"D1-D9 RT 100%: {'YES' if d1d9_rt_ok else 'NO'} "
          f"({rt_pass}/{rt_total})")
    print(f"Real-world ganho: {rw_gain:.2f}% (target ~9.87%)")
    print(f"Real-world RT 100%: {'YES' if rw_rt_ok else 'NO'} "
          f"({rw_rt_pass}/{len(real_results)})")

    welding_ok = (d1d9_preserved and d1d9_rt_ok and rw_rt_ok and
                  rw_gain >= 7.0)
    print(f"\n** WELDING {'OK' if welding_ok else 'PROBLEMS'} **")

    # Report
    report = [
        "# Sub-exp 04 — validacao pos-welding H-DA-11 (ADR-0010)",
        "",
        "## Cenarios",
        "",
        "Comparativo: baseline (`processar(unicas, min_len=3)` hard-coded)",
        "vs novo `tcf.encode()` (que chama `detect_min_len(values)`).",
        "",
        "## D1-D9 single-col (M9 baseline)",
        "",
        "| Dataset | base (B) | new (B) | delta | RT |",
        "|---|---:|---:|---:|---|",
    ]
    for i, ds in enumerate(D1_D9):
        path = datasets_dir / f"{ds}.csv"
        values = ler_csv_single_col(path)
        bb, bn, rt = measure_col(values)
        delta = bn - bb
        report.append(f"| {ds} | {bb} | {bn} | {delta:+d} | {rt} |")
    report.append(f"| **TOTAL** | **{total_base}** | **{total_new}** | "
                  f"**{total_new - total_base:+d}** | {rt_pass}/{rt_total} |")

    report.extend([
        "",
        f"**M9 baseline (1615B) preservado**: "
        f"{'**SIM**' if d1d9_preserved else '**NAO**'} (atual: {total_new}B)",
        f"**RT 100%**: {'**SIM**' if d1d9_rt_ok else '**NAO**'} "
        f"({rt_pass}/{rt_total})",
        "",
        "## Real-world (Adult Census + TPC-H)",
        "",
        f"- **Bytes total baseline**: {rw_total_base:,}",
        f"- **Bytes total welded**: {rw_total_new:,}",
        f"- **Delta**: {rw_total_new - rw_total_base:+,}B",
        f"- **Gain weighted**: **{rw_gain:.2f}%**",
        f"- **RT 100%**: {'**SIM**' if rw_rt_ok else '**NAO**'} "
        f"({rw_rt_pass}/{len(real_results)})",
        "",
        "### Top 10 wins",
        "",
        "| Col | base | new | delta | pct |",
        "|---|---:|---:|---:|---:|",
    ])
    for r in real_results[:10]:
        d = r['new'] - r['base']
        if d >= 0:
            break
        pct = (r['base'] - r['new']) / r['base'] * 100 if r['base'] else 0
        report.append(f"| {r['source']}/{r['col']} | {r['base']:,} | "
                      f"{r['new']:,} | {d:+d} | -{pct:.2f}% |")

    if regr:
        report.append("")
        report.append("### Regressoes")
        report.append("")
        report.append("| Col | base | new | delta |")
        report.append("|---|---:|---:|---:|")
        for r in regr:
            d = r['new'] - r['base']
            report.append(f"| {r['source']}/{r['col']} | {r['base']:,} | "
                          f"{r['new']:,} | {d:+d} |")

    report.extend([
        "",
        "## Veredito",
        "",
        f"- D1-D9 baseline preservado: {'OK' if d1d9_preserved else 'FAIL'}",
        f"- D1-D9 RT 100%: {'OK' if d1d9_rt_ok else 'FAIL'}",
        f"- Real-world gain >= 7%: {'OK' if rw_gain >= 7 else 'FAIL'} "
        f"({rw_gain:.2f}%)",
        f"- Real-world RT 100%: {'OK' if rw_rt_ok else 'FAIL'}",
        "",
        f"**WELDING H-DA-11: {'CONFIRMED' if welding_ok else 'PROBLEMS'}**",
        "",
    ])

    out = THIS / "result.md"
    out.write_bytes(("\n".join(report) + "\n").encode("utf-8"))
    print(f"\nresult.md: {out}")


if __name__ == "__main__":
    main()

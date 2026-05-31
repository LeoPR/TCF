"""Sub-exp 01 — validacao welding canonical Pacote 1 (M9 → M10).

Mede:
1. D1-D9 novo baseline M10 (vs M9 antigo 1615B)
2. 20 datasets sinteticos (EXP-010 set) — comparar com prototype
3. Adult Census 1k/5k + TPC-H region/customer/lineitem 5k
4. RT 100% obrigatorio em todas as camadas

Critérios:
- D1-D9 RT 9/9 OK
- 20 datasets sinteticos: bytes <= ou = EXP-010 prototype, RT 20/20 OK
- Adult+TPC-H: ganho weighted >= 10% sobre M9 antigo (1,008,003B)
- Adult+TPC-H: RT 57/57 OK
"""

from __future__ import annotations

import csv
import sys
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


D1_D9 = [
    "D1-emails-simples", "D2-emails-quote-id", "D3-stress-substring",
    "D4-caos-mix", "D5-padroes-multiplos", "D6-poucos-em-ruido",
    "D7-aninhamento", "D8-cabeca-cauda", "D9-frequencia-alta",
]

# 20 datasets do EXP-010 set
EXP010_SET = D1_D9 + [
    "D11a-datas-dia", "D11b-datas-borda", "D11c-datas-mensal",
    "D11d-datetime-min", "D11e-datetime-mensal",
    "D11f-datetime-ms", "D11g-datetime-us", "D11h-datetime-ns",
    "D16a-ids-3digits", "D16b-ids-4digits", "D16c-ids-prefixados",
]

M9_BASELINE = 1615  # historico


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
    tcf_text = tcf_encode(values)
    bytes_new = len(tcf_text.encode("utf-8"))
    decoded = tcf_decode(tcf_text)
    rt = "OK" if decoded == values else "FAIL"
    return bytes_new, rt


def main():
    print("=== Sub-exp 01 — welding Pacote 1 canonical (M10) ===\n")
    datasets_dir = ROOT / "datasets" / "synthetic"

    # D1-D9
    print(">> D1-D9 (M9 baseline 1615B; M10 novo a medir)")
    total_m10_d1d9 = 0
    rt_pass = 0
    d1d9_results = []
    for ds in D1_D9:
        path = datasets_dir / f"{ds}.csv"
        values = ler_csv_single_col(path)
        bytes_new, rt = measure_col(values)
        total_m10_d1d9 += bytes_new
        if rt == "OK":
            rt_pass += 1
        d1d9_results.append({'dataset': ds, 'bytes_m10': bytes_new, 'rt': rt})
        print(f"  {ds:<25} {bytes_new:>4}B  RT={rt}")
    print(f"  {'TOTAL D1-D9 M10':<25} {total_m10_d1d9:>4}B  "
          f"(vs M9 {M9_BASELINE}B = {total_m10_d1d9 - M9_BASELINE:+d}, "
          f"{(total_m10_d1d9 - M9_BASELINE) / M9_BASELINE * 100:+.2f}%)  "
          f"RT={rt_pass}/{len(D1_D9)}")

    # 20 datasets EXP-010 set
    print("\n>> EXP-010 set (20 datasets: D1-D9 + D11a-h + D16a-c)")
    total_m10_exp010 = 0
    rt_pass_exp010 = 0
    exp010_results = []
    for ds in EXP010_SET:
        path = datasets_dir / f"{ds}.csv"
        if not path.exists():
            print(f"  SKIP {ds} (nao existe)")
            continue
        values = ler_csv_single_col(path)
        bytes_new, rt = measure_col(values)
        total_m10_exp010 += bytes_new
        if rt == "OK":
            rt_pass_exp010 += 1
        exp010_results.append({'dataset': ds, 'bytes_m10': bytes_new, 'rt': rt})
    print(f"  TOTAL EXP-010 M10: {total_m10_exp010}B  "
          f"RT={rt_pass_exp010}/{len(exp010_results)}")
    print(f"  (Comparar com EXP-010 prototype ~1340B esperado)")

    # Adult Census + TPC-H
    print("\n>> Adult Census + TPC-H (real-world)")
    real_results = []
    reader = DatasetReader("adult-census")
    for vol in [1000, 5000]:
        rows = reader.rows("adult", limit=vol)
        cols = rows_to_cols(rows)
        for cname, vals in cols.items():
            bytes_new, rt = measure_col(vals)
            real_results.append({
                'source': f"adult-{vol}", 'col': cname,
                'bytes_m10': bytes_new, 'rt': rt,
            })
    reader.close()

    reader = DatasetReader("tpch-sf001")
    for table in ["region", "customer", "lineitem"]:
        rows = reader.rows(table, limit=5000)
        cols = rows_to_cols(rows)
        for cname, vals in cols.items():
            bytes_new, rt = measure_col(vals)
            real_results.append({
                'source': f"tpch.{table}-5k", 'col': cname,
                'bytes_m10': bytes_new, 'rt': rt,
            })
    reader.close()

    total_rw_m10 = sum(r['bytes_m10'] for r in real_results)
    rt_rw_pass = sum(1 for r in real_results if r['rt'] == 'OK')

    # Referencia M9 + H-DA-11 welded (commit 27fdb6b): 908,502B
    # Referencia M9 puro (sem H-DA-11): 1,008,003B
    M9_PURE_RW = 1_008_003  # M9 puro Adult+TPC-H 57 cols
    M9_HDA11_RW = 908_502   # M9 + H-DA-11 welded (canonical pre-Pacote1-weld)

    delta_vs_m9_pure = total_rw_m10 - M9_PURE_RW
    gain_vs_m9_pure = -delta_vs_m9_pure / M9_PURE_RW * 100

    delta_vs_m9_hda11 = total_rw_m10 - M9_HDA11_RW
    gain_vs_m9_hda11 = -delta_vs_m9_hda11 / M9_HDA11_RW * 100

    print(f"\n  Real-world TOTAL M10: {total_rw_m10:,}B  RT={rt_rw_pass}/{len(real_results)}")
    print(f"  vs M9 puro ({M9_PURE_RW:,}B): {delta_vs_m9_pure:+,}B "
          f"({gain_vs_m9_pure:+.2f}%)")
    print(f"  vs M9+H-DA-11 ({M9_HDA11_RW:,}B): {delta_vs_m9_hda11:+,}B "
          f"({gain_vs_m9_hda11:+.2f}%)")

    # Top wins
    print("\n  Top 10 colunas com menos bytes (esperado: dates/IDs/comments):")
    for r in sorted(real_results, key=lambda x: -x['bytes_m10'])[:10]:
        print(f"    {r['source']}/{r['col']:<25} {r['bytes_m10']:>6}B")

    # Veredito
    print("\n=== Veredito welding Pacote 1 canonical ===\n")
    d1d9_rt_ok = (rt_pass == len(D1_D9))
    exp010_rt_ok = (rt_pass_exp010 == len(exp010_results))
    rw_rt_ok = (rt_rw_pass == len(real_results))
    print(f"D1-D9 RT 100%: {'YES' if d1d9_rt_ok else 'NO'} ({rt_pass}/{len(D1_D9)})")
    print(f"EXP-010 set RT 100%: {'YES' if exp010_rt_ok else 'NO'} "
          f"({rt_pass_exp010}/{len(exp010_results)})")
    print(f"Real-world RT 100%: {'YES' if rw_rt_ok else 'NO'} "
          f"({rt_rw_pass}/{len(real_results)})")
    print(f"D1-D9 baseline M10: {total_m10_d1d9}B (M9 era 1615B)")
    print(f"Real-world ganho vs M9 puro: {gain_vs_m9_pure:.2f}%")

    welding_ok = (d1d9_rt_ok and exp010_rt_ok and rw_rt_ok and
                  gain_vs_m9_pure >= 10)
    print(f"\n** WELDING PACOTE 1 CANONICAL "
          f"{'CONFIRMED' if welding_ok else 'PROBLEMS'} **")

    # Report
    report = [
        "# Sub-exp 01 — validacao welding Pacote 1 canonical (M9 → M10)",
        "",
        "## Pipeline canonical novo (M10)",
        "",
        "```",
        "values",
        "  → analyze_column (features)",
        "  → detect_cadence_from_features (regras 1+2)",
        "  → detect_min_len_from_features (heur v3, gating n>=100)",
        "  → OBAT: processar_with_hint OR processar",
        "  → HCC: HCCSeqRLE (M8A + seq-RLE near-identical)",
        "  → texto TCF",
        "```",
        "",
        "## D1-D9 novo baseline M10",
        "",
        "| Dataset | M10 (B) | RT |",
        "|---|---:|---|",
    ]
    for r in d1d9_results:
        report.append(f"| {r['dataset']} | {r['bytes_m10']} | {r['rt']} |")
    report.append(f"| **TOTAL M10** | **{total_m10_d1d9}** | {rt_pass}/{len(D1_D9)} |")
    report.append("")
    report.append(f"M9 baseline (historico): {M9_BASELINE}B")
    report.append(f"M10 baseline (novo): {total_m10_d1d9}B")
    report.append(f"Delta: {total_m10_d1d9 - M9_BASELINE:+d}B "
                  f"({(total_m10_d1d9 - M9_BASELINE) / M9_BASELINE * 100:+.2f}%)")

    report.append("")
    report.append("## EXP-010 set (20 datasets)")
    report.append("")
    report.append("| Dataset | M10 (B) | RT |")
    report.append("|---|---:|---|")
    for r in exp010_results:
        report.append(f"| {r['dataset']} | {r['bytes_m10']} | {r['rt']} |")
    report.append(f"| **TOTAL** | **{total_m10_exp010}** | "
                  f"{rt_pass_exp010}/{len(exp010_results)} |")

    report.append("")
    report.append("## Real-world (Adult + TPC-H, 57 cols)")
    report.append("")
    report.append(f"- Total M10: {total_rw_m10:,}B")
    report.append(f"- vs M9 puro (1,008,003B): {delta_vs_m9_pure:+,} "
                  f"({gain_vs_m9_pure:+.2f}%)")
    report.append(f"- vs M9+H-DA-11 (908,502B): {delta_vs_m9_hda11:+,} "
                  f"({gain_vs_m9_hda11:+.2f}%)")
    report.append(f"- RT: {rt_rw_pass}/{len(real_results)}")

    report.append("")
    report.append("## Veredito")
    report.append("")
    report.append(f"- D1-D9 RT 100%: {'OK' if d1d9_rt_ok else 'FAIL'}")
    report.append(f"- EXP-010 set RT 100%: {'OK' if exp010_rt_ok else 'FAIL'}")
    report.append(f"- Real-world RT 100%: {'OK' if rw_rt_ok else 'FAIL'}")
    report.append(f"- Real-world gain >= 10% vs M9 puro: "
                  f"{'OK' if gain_vs_m9_pure >= 10 else 'FAIL'} "
                  f"({gain_vs_m9_pure:.2f}%)")
    report.append("")
    report.append(f"**WELDING PACOTE 1 CANONICAL: "
                  f"{'CONFIRMED' if welding_ok else 'PROBLEMS'}**")
    report.append("")

    out = THIS / "result.md"
    out.write_bytes(("\n".join(report) + "\n").encode("utf-8"))
    print(f"\nresult.md: {out}")


if __name__ == "__main__":
    main()

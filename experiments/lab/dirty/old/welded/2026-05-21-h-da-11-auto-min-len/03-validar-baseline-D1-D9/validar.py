"""Sub-exp 03 — validar heur v3 vs baseline M9 em D1-D9.

INVARIANT: M9 single-col baseline = 1615B (D1-D9 cumulativo).
Qualquer welding deve preservar esse baseline (zero regressao).

Sub-exp 02 mostrou regressao em D9 (oracle=4 mas v3=6 → +16B).
Esta validacao mede CUMULATIVO em D1-D9 single-col:
- Default ml=3 (M9 baseline)
- Heur v3 (welding candidato)
- Diferenca

Se v3 regride > 0 em D1-D9: precisamos gating ou refinement antes
de welding.

Estrategias de gating consideradas:
- (A) n_rows >= 100: D1-D9 sao pequenos (5-50 rows), gating filtra
- (B) heur_v4 mais conservativa (cardinality threshold maior)
- (C) so' aplicar em multi-col (D1-D9 sao single-col por construcao)
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

from tcf.composicional.syntax import M8AVirtualRefsSyntax  # noqa: E402
from tcf.core.online import processar  # noqa: E402
from auto_pre import _is_numeric_string  # noqa: E402


D1_D9 = [
    "D1-emails-simples", "D2-emails-quote-id", "D3-stress-substring",
    "D4-caos-mix", "D5-padroes-multiplos", "D6-poucos-em-ruido",
    "D7-aninhamento", "D8-cabeca-cauda", "D9-frequencia-alta",
]


def heur_v3(avg_len, card, is_num):
    if card < 0.2:
        return 3
    if avg_len >= 25:
        return 6
    if avg_len >= 8 and card >= 0.4:
        return 6
    if avg_len >= 5 and is_num and card >= 0.8:
        return 6
    if avg_len >= 12 and card >= 0.7:
        return 5
    if avg_len >= 3 and card >= 0.2:
        return 4
    return 3


def heur_v3_gated(avg_len, card, is_num, n_rows, n_threshold=100):
    """v3 com gating: nao aplicar pra colunas pequenas (n < threshold)."""
    if n_rows < n_threshold:
        return 3  # default seguro pra datasets pequenos
    return heur_v3(avg_len, card, is_num)


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


def features_of(values):
    sample = values[:min(20, len(values))]
    is_num = all(_is_numeric_string(v) for v in sample) if sample else False
    n_unicas = len(set(values))
    avg = sum(len(v) for v in values) / len(values)
    return {
        'n_rows': len(values),
        'avg_len': avg,
        'cardinality': n_unicas / len(values),
        'is_numeric': is_num,
    }


def encode_ml(values, unicas, ml):
    tokens, _ = processar(unicas, min_len=ml)
    body = M8AVirtualRefsSyntax().encode(values, unicas, tokens, "val")
    return len(body.encode("utf-8"))


def main():
    print("=== Sub-exp 03 — validar heur v3 vs M9 baseline D1-D9 ===\n")
    datasets_dir = ROOT / "datasets" / "synthetic"

    results = []
    for ds in D1_D9:
        path = datasets_dir / f"{ds}.csv"
        values = ler_csv_single_col(path)
        unicas = dedup_preserve_order(values)
        feat = features_of(values)

        bytes_default = encode_ml(values, unicas, 3)
        v3_ml = heur_v3(feat['avg_len'], feat['cardinality'], feat['is_numeric'])
        bytes_v3 = encode_ml(values, unicas, v3_ml)
        v3g_ml = heur_v3_gated(feat['avg_len'], feat['cardinality'],
                               feat['is_numeric'], feat['n_rows'])
        bytes_v3g = encode_ml(values, unicas, v3g_ml)

        results.append({
            'dataset': ds,
            **feat,
            'bytes_default': bytes_default,
            'v3_ml': v3_ml,
            'bytes_v3': bytes_v3,
            'v3g_ml': v3g_ml,
            'bytes_v3g': bytes_v3g,
        })

    # Print
    print(f"{'dataset':<25} {'n':>3} {'avg':>5} {'card':>5} {'num':>3} "
          f"{'def':>4} {'v3':>4} {'d(v3)':>5} {'v3g':>4} {'d(v3g)':>6}")
    print("-" * 78)
    total_default = total_v3 = total_v3g = 0
    for r in results:
        num = "Y" if r['is_numeric'] else "n"
        d_v3 = r['bytes_v3'] - r['bytes_default']
        d_v3g = r['bytes_v3g'] - r['bytes_default']
        total_default += r['bytes_default']
        total_v3 += r['bytes_v3']
        total_v3g += r['bytes_v3g']
        print(f"{r['dataset']:<25} {r['n_rows']:>3} {r['avg_len']:>5.1f} "
              f"{r['cardinality']:>5.2f} {num:>3} "
              f"{r['bytes_default']:>4} ml{r['v3_ml']}={r['bytes_v3']:>3} {d_v3:>+4} "
              f"ml{r['v3g_ml']}={r['bytes_v3g']:>3} {d_v3g:>+5}")
    print("-" * 78)
    print(f"{'TOTAL':<25} {'':>3} {'':>5} {'':>5} {'':>3} "
          f"{total_default:>4} {'':>4} {total_v3 - total_default:>+5} "
          f"{'':>4} {total_v3g - total_default:>+6}")

    print(f"\nM9 baseline D1-D9: {total_default}B")
    print(f"Heur v3 (no gating): {total_v3}B ({total_v3 - total_default:+d}B)")
    print(f"Heur v3+gating (n>=100): {total_v3g}B "
          f"({total_v3g - total_default:+d}B)")

    if total_v3 == total_default:
        veredito = "v3 preserva M9 baseline (zero regressao) — pode wedldar SEM gating"
    elif total_v3 < total_default:
        veredito = f"v3 MELHORA M9 ({total_default - total_v3}B) — pode wedldar SEM gating"
    else:
        if total_v3g <= total_default:
            veredito = (f"v3 regride M9 +{total_v3 - total_default}B; "
                        f"gating n>=100 RESOLVE (preserva baseline). Welding com gating.")
        else:
            veredito = (f"v3 regride +{total_v3 - total_default}B e gating "
                        f"+{total_v3g - total_default}B — precisa refinar heur ou gating mais agressivo.")

    print(f"\n=== Veredito ===\n{veredito}")

    # Report
    report = [
        "# Sub-exp 03 — validar heur v3 vs M9 baseline D1-D9",
        "",
        "## INVARIANT",
        "",
        "M9 single-col baseline = soma bytes D1-D9 com default ml=3.",
        "Qualquer welding em src/tcf NAO pode regredir esse total.",
        "",
        "## Tabela",
        "",
        "| dataset | n | avg | card | num | default | v3 | d(v3) | v3+gating | d(gated) |",
        "|---|---:|---:|---:|---|---:|---:|---:|---:|---:|",
    ]
    for r in results:
        num = "Y" if r['is_numeric'] else "n"
        d_v3 = r['bytes_v3'] - r['bytes_default']
        d_v3g = r['bytes_v3g'] - r['bytes_default']
        report.append(
            f"| {r['dataset']} | {r['n_rows']} | {r['avg_len']:.1f} | "
            f"{r['cardinality']:.2f} | {num} | {r['bytes_default']} | "
            f"ml{r['v3_ml']}={r['bytes_v3']} | {d_v3:+d} | "
            f"ml{r['v3g_ml']}={r['bytes_v3g']} | {d_v3g:+d} |"
        )

    report.extend([
        "",
        "## Total",
        "",
        f"- **M9 baseline**: {total_default}B",
        f"- Heur v3 (no gating): {total_v3}B ({total_v3 - total_default:+d}B)",
        f"- Heur v3+gating (n>=100): {total_v3g}B ({total_v3g - total_default:+d}B)",
        "",
        "## Veredito",
        "",
        veredito,
        "",
        "## Implicacao welding",
        "",
    ])
    if total_v3g <= total_default:
        report.extend([
            "Welding deve usar **gating por n_rows >= 100**:",
            "",
            "```python",
            "def detect_min_len(values):",
            "    if len(values) < 100:",
            "        return 3  # baseline seguro para datasets pequenos",
            "    return heur_v3(features_of(values))",
            "```",
            "",
            "D1-D9 (5-50 rows) cai no fallback. Adult+TPC-H (1000+ rows) "
            "recebe heur v3.",
        ])

    out = THIS / "result.md"
    out.write_bytes(("\n".join(report) + "\n").encode("utf-8"))
    print(f"\nresult.md: {out}")


if __name__ == "__main__":
    main()

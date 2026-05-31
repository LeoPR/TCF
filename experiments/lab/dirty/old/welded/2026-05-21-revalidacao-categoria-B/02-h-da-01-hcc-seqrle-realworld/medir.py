"""Sub-exp 02 — H-DA-01 medicao isolada em real-world.

Pergunta: HCC seq-RLE near-identical (`*N+delta|template`) sozinho
da' quanto de ganho em Adult Census + TPC-H? E' similar aos -22.2%
em D11a-h sinteticos?

Metodo:
- Baseline: M8AVirtualRefsSyntax canonical (com `*N|linha` RLE puro)
- Tratamento: HCCSeqRLE (canonical + `*N+delta|template` near-identical)
- Medir delta em cada coluna de:
  - D11a-h sintetico (controle — reproduz -22.2% original)
  - Adult Census 1k/5k (real-world)
  - TPC-H region/customer/lineitem-5k (real-world)

Reportar:
- ganho por coluna
- ganho weighted real-world
- comparacao sintetico vs real
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
from tcf.composicional.syntax import M8AVirtualRefsSyntax  # noqa: E402
from tcf.core.online import processar  # noqa: E402
from hcc_seqrle import HCCSeqRLE  # noqa: E402


D11_SINTETICOS = [
    "D11a-datas-dia", "D11b-datas-borda", "D11c-datas-mensal",
    "D11d-datetime-min", "D11e-datetime-mensal",
    "D11f-datetime-ms", "D11g-datetime-us", "D11h-datetime-ns",
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


def measure_col(name, values):
    """Mede baseline (M8A canonical) vs tratamento (HCCSeqRLE)."""
    unicas = dedup_preserve_order(values)
    tokens, _ = processar(unicas, min_len=3)

    body_baseline = M8AVirtualRefsSyntax().encode(values, unicas, tokens, "val")
    body_seqrle = HCCSeqRLE().encode(values, unicas, tokens, "val")

    bytes_base = len(body_baseline.encode("utf-8"))
    bytes_treat = len(body_seqrle.encode("utf-8"))
    delta = bytes_treat - bytes_base
    pct = (delta / bytes_base * 100) if bytes_base else 0

    # RT check
    decoded = HCCSeqRLE().decode(body_seqrle)
    rt_ok = (decoded == values)

    return {
        'col': name,
        'n_rows': len(values),
        'n_unicas': len(unicas),
        'bytes_base': bytes_base,
        'bytes_treat': bytes_treat,
        'delta': delta,
        'pct': pct,
        'rt': 'OK' if rt_ok else 'FAIL',
    }


def main():
    print("=== Sub-exp 02 — H-DA-01 HCC seq-RLE real-world ===\n")
    all_results = []

    # D11 sintetico (controle)
    print(">> D11a-h sintetico (controle)")
    datasets_dir = ROOT / "datasets" / "synthetic"
    for ds in D11_SINTETICOS:
        path = datasets_dir / f"{ds}.csv"
        if not path.exists():
            print(f"  SKIP {ds}")
            continue
        values = ler_csv_single_col(path)
        r = measure_col(f"{ds}/val", values)
        r['source'] = 'sintetico'
        r['dataset'] = ds
        all_results.append(r)
        print(f"  {r['col']:<35} base={r['bytes_base']:5} treat={r['bytes_treat']:5} "
              f"delta={r['delta']:+5} pct={r['pct']:+6.2f}% RT={r['rt']}")

    # Adult Census real-world
    print("\n>> Adult Census")
    reader = DatasetReader("adult-census")
    for vol in [1000, 5000]:
        rows = reader.rows("adult", limit=vol)
        cols = rows_to_cols(rows)
        for cname, values in cols.items():
            r = measure_col(f"adult-{vol}/{cname}", values)
            r['source'] = 'realworld'
            r['dataset'] = f"adult-{vol}"
            all_results.append(r)
    reader.close()
    for r in [x for x in all_results if x['dataset'].startswith('adult')]:
        print(f"  {r['col']:<35} base={r['bytes_base']:6} treat={r['bytes_treat']:6} "
              f"delta={r['delta']:+5} pct={r['pct']:+6.2f}% RT={r['rt']}")

    # TPC-H real-world
    print("\n>> TPC-H")
    reader = DatasetReader("tpch-sf001")
    for table in ["region", "customer", "lineitem"]:
        rows = reader.rows(table, limit=5000)
        cols = rows_to_cols(rows)
        for cname, values in cols.items():
            r = measure_col(f"tpch.{table}-5k/{cname}", values)
            r['source'] = 'realworld'
            r['dataset'] = f"tpch.{table}-5k"
            all_results.append(r)
    reader.close()
    for r in [x for x in all_results if x['dataset'].startswith('tpch')]:
        print(f"  {r['col']:<35} base={r['bytes_base']:6} treat={r['bytes_treat']:6} "
              f"delta={r['delta']:+5} pct={r['pct']:+6.2f}% RT={r['rt']}")

    # Agregado
    print("\n=== Agregado ===\n")
    sintetico = [r for r in all_results if r['source'] == 'sintetico']
    realworld = [r for r in all_results if r['source'] == 'realworld']

    s_base = sum(r['bytes_base'] for r in sintetico)
    s_treat = sum(r['bytes_treat'] for r in sintetico)
    s_pct = (s_treat - s_base) / s_base * 100 if s_base else 0

    r_base = sum(r['bytes_base'] for r in realworld)
    r_treat = sum(r['bytes_treat'] for r in realworld)
    r_pct = (r_treat - r_base) / r_base * 100 if r_base else 0

    print(f"Sintetico (D11a-h): base={s_base:>7,}  treat={s_treat:>7,}  "
          f"delta={s_treat - s_base:+5}  pct={s_pct:+6.2f}%")
    print(f"Real-world:         base={r_base:>7,}  treat={r_treat:>7,}  "
          f"delta={r_treat - r_base:+5}  pct={r_pct:+6.2f}%")

    if s_pct < 0:
        print(f"\nGanho sintetico: {-s_pct:.2f}% (referencia original "
              f"reportou -22.2% em D11a-h)")
    if r_pct < 0:
        print(f"Ganho real-world: {-r_pct:.2f}%")
    else:
        print(f"Real-world ganho: 0% (neutro ou regressao {r_pct:.2f}%)")

    # Reducao sintetico → real
    if s_pct < 0 and r_pct < 0:
        ratio = abs(s_pct) / abs(r_pct) if r_pct != 0 else float('inf')
        print(f"Reducao sintetico -> real-world: {ratio:.1f}x")
    elif s_pct < 0 and r_pct >= 0:
        print(f"Real-world ZERA (ou inverte) ganho sintetico")

    # Veredito
    print("\n=== Veredito H-DA-01 ===\n")
    if r_pct <= -5:
        veredito = "CONFIRMADA real-world: ganho >=5%"
        status_novo = "confirmada-empirica real-world"
    elif r_pct <= -1:
        veredito = "MARGINAL real-world: ganho 1-5%"
        status_novo = "A-revalidar (marginal real-world)"
    else:
        veredito = "REFUTADA real-world: ganho <1% (mesmo padrao Pacote 2)"
        status_novo = "refutada-real-world"

    print(f"{veredito}")
    print(f"Status sugerido: {status_novo}")

    # Report
    report = [
        "# Sub-exp 02 — H-DA-01 HCC seq-RLE real-world",
        "",
        "## Pergunta",
        "",
        "HCC seq-RLE near-identical (`*N+delta|template`) isolado da' quanto",
        "em Adult Census + TPC-H comparado aos -22.2% em D11a-h sinteticos?",
        "",
        "## Tabela por coluna",
        "",
        "| Source | Col | n_rows | base (B) | treat (B) | delta | pct | RT |",
        "|---|---|---:|---:|---:|---:|---:|---|",
    ]
    for r in all_results:
        report.append(
            f"| {r['source']} | {r['col']} | {r['n_rows']} | "
            f"{r['bytes_base']:,} | {r['bytes_treat']:,} | "
            f"{r['delta']:+d} | {r['pct']:+.2f}% | {r['rt']} |"
        )

    report.extend([
        "",
        "## Agregado",
        "",
        f"| Cohort | base (B) | treat (B) | delta | pct |",
        f"|---|---:|---:|---:|---:|",
        f"| Sintetico D11a-h | {s_base:,} | {s_treat:,} | {s_treat - s_base:+d} | {s_pct:+.2f}% |",
        f"| Real-world | {r_base:,} | {r_treat:,} | {r_treat - r_base:+d} | {r_pct:+.2f}% |",
        "",
        "## Comparacao sintetico vs real",
        "",
    ])
    if s_pct < 0 and r_pct < 0:
        ratio = abs(s_pct) / abs(r_pct) if r_pct != 0 else float('inf')
        report.append(f"- Sintetico: {-s_pct:.2f}% ganho")
        report.append(f"- Real-world: {-r_pct:.2f}% ganho")
        report.append(f"- **Reducao**: {ratio:.1f}x menor em real-world")
    elif r_pct >= 0 and s_pct < 0:
        report.append(f"- Sintetico: {-s_pct:.2f}% ganho")
        report.append(f"- **Real-world: 0% ganho (ou regressao {r_pct:.2f}%)**")
        report.append("- Real-world ZERA o ganho sintetico — mesmo padrao Pacote 2")

    report.extend([
        "",
        "## Veredito",
        "",
        f"**{veredito}**",
        "",
        f"**Status sugerido roadmap H-DA-01**: `{status_novo}`",
        "",
        "## Notas metodologicas",
        "",
        "- Baseline e' M8AVirtualRefsSyntax canonical (com `*N|linha` RLE puro",
        "  para linhas IDENTICAS adjacentes — feature standard).",
        "- Tratamento e' HCCSeqRLE (extends M8A com `*N+delta|template` para",
        "  linhas NEAR-IDENTICAL via escape-digit shifts).",
        "- A diferenca isola EXATAMENTE o ganho do near-identical detector.",
        "",
    ])

    out = THIS / "result.md"
    out.write_bytes(("\n".join(report) + "\n").encode("utf-8"))
    print(f"\nresult.md: {out}")


if __name__ == "__main__":
    main()

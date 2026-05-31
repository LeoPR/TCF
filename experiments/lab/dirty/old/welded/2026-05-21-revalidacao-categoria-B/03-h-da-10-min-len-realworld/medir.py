"""Sub-exp 03 — H-DA-10 min_len trade-off em real-world.

Pergunta: Em Adult Census + TPC-H, algum min_len != 3 (default)
da' ganho >= 2% em pelo menos 3 colunas?

Metodo:
- Varia min_len em {2, 3, 4, 5, 6} pra cada coluna de:
  - D9-frequencia-alta (controle — onde H-DA-10 original viu ganho)
  - Adult Census 1k/5k
  - TPC-H region/customer/lineitem-5k
- Encoder: pipeline canonical (M8AVirtualRefsSyntax + OBAT.processar)
- Mede bytes; identifica melhor min_len por coluna

Reportar:
- Tabela por (coluna, min_len)
- Melhor min_len por coluna
- Quantas colunas preferem != 3 com ganho >= 2%
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
from tcf.composicional.syntax import M8AVirtualRefsSyntax  # noqa: E402
from tcf.core.online import processar  # noqa: E402


MIN_LENS = [2, 3, 4, 5, 6]
DEFAULT_ML = 3
THRESHOLD_PCT = 2.0  # ganho minimo pra considerar relevante


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
    unicas = dedup_preserve_order(values)
    results = {}
    for ml in MIN_LENS:
        try:
            tokens, _ = processar(unicas, min_len=ml)
            body = M8AVirtualRefsSyntax().encode(values, unicas, tokens, "val")
            results[ml] = len(body.encode("utf-8"))
        except Exception as e:
            results[ml] = -1  # erro
    return {'col': name, 'bytes_by_ml': results}


def main():
    print("=== Sub-exp 03 — H-DA-10 min_len real-world ===\n")
    all_results = []

    # D9 controle
    print(">> D9 controle (origem H-DA-10)")
    datasets_dir = ROOT / "datasets" / "synthetic"
    values = ler_csv_single_col(datasets_dir / "D9-frequencia-alta.csv")
    r = measure_col("D9-frequencia-alta/val", values)
    r['source'] = 'sintetico'
    all_results.append(r)
    bs = r['bytes_by_ml']
    print(f"  {r['col']:<35} " +
          "  ".join(f"ml{ml}={bs[ml]:>5}" for ml in MIN_LENS))

    # Adult Census real-world
    print("\n>> Adult Census")
    reader = DatasetReader("adult-census")
    for vol in [1000, 5000]:
        rows = reader.rows("adult", limit=vol)
        cols = rows_to_cols(rows)
        for cname, values in cols.items():
            r = measure_col(f"adult-{vol}/{cname}", values)
            r['source'] = 'realworld'
            all_results.append(r)
            bs = r['bytes_by_ml']
            print(f"  {r['col']:<35} " +
                  "  ".join(f"ml{ml}={bs[ml]:>6}" for ml in MIN_LENS))
    reader.close()

    # TPC-H real-world
    print("\n>> TPC-H")
    reader = DatasetReader("tpch-sf001")
    for table in ["region", "customer", "lineitem"]:
        rows = reader.rows(table, limit=5000)
        cols = rows_to_cols(rows)
        for cname, values in cols.items():
            r = measure_col(f"tpch.{table}-5k/{cname}", values)
            r['source'] = 'realworld'
            all_results.append(r)
            bs = r['bytes_by_ml']
            print(f"  {r['col']:<35} " +
                  "  ".join(f"ml{ml}={bs[ml]:>6}" for ml in MIN_LENS))
    reader.close()

    # Analise: melhor min_len por coluna
    print("\n=== Analise melhor min_len ===\n")
    cols_prefer_non_default = []
    total_gain = 0
    total_baseline = 0
    for r in all_results:
        bs = r['bytes_by_ml']
        default_bytes = bs.get(DEFAULT_ML, -1)
        valid = {ml: b for ml, b in bs.items() if b > 0}
        if not valid:
            continue
        best_ml = min(valid, key=lambda k: valid[k])
        best_bytes = valid[best_ml]
        if default_bytes > 0:
            gain_pct = (default_bytes - best_bytes) / default_bytes * 100
            total_gain += default_bytes - best_bytes
            total_baseline += default_bytes
            if best_ml != DEFAULT_ML and gain_pct >= THRESHOLD_PCT:
                cols_prefer_non_default.append({
                    'col': r['col'],
                    'source': r['source'],
                    'best_ml': best_ml,
                    'default_bytes': default_bytes,
                    'best_bytes': best_bytes,
                    'gain_pct': gain_pct,
                })

    weighted_gain = (total_gain / total_baseline * 100
                     if total_baseline else 0)

    print(f"Total colunas: {len(all_results)}")
    print(f"Colunas que preferem min_len != 3 com ganho >= {THRESHOLD_PCT}%: "
          f"{len(cols_prefer_non_default)}")
    print(f"Total bytes economizados (best vs default): "
          f"{total_gain:,} / {total_baseline:,} = {weighted_gain:.2f}%")

    if cols_prefer_non_default:
        print(f"\n  Colunas com ganho real (>= {THRESHOLD_PCT}%):")
        for c in cols_prefer_non_default:
            print(f"    {c['col']:<40} ml={c['best_ml']} "
                  f"gain={c['gain_pct']:.2f}% "
                  f"({c['default_bytes']} -> {c['best_bytes']})")

    # Veredito
    print("\n=== Veredito H-DA-10 ===\n")
    n_with_gain = len(cols_prefer_non_default)
    if n_with_gain >= 3:
        veredito = (f"CONFIRMADA real-world: {n_with_gain} colunas com ganho "
                    f">= {THRESHOLD_PCT}% (mas marginais)")
        status_novo = "confirmada-empirica real-world marginal"
    elif n_with_gain >= 1:
        veredito = (f"MARGINAL: apenas {n_with_gain} colunas com ganho "
                    f">= {THRESHOLD_PCT}% — ruido provavel")
        status_novo = "A-revalidar (poucos casos)"
    else:
        veredito = (f"REFUTADA real-world: 0 colunas com ganho "
                    f">= {THRESHOLD_PCT}% (default min_len=3 e' otimo)")
        status_novo = "refutada-real-world"

    print(f"{veredito}")
    print(f"Status sugerido: {status_novo}")

    # Report
    report = [
        "# Sub-exp 03 — H-DA-10 min_len trade-off real-world",
        "",
        "## Pergunta",
        "",
        f"Em Adult Census + TPC-H, algum min_len != {DEFAULT_ML} (default)",
        f"da' ganho >= {THRESHOLD_PCT}% em pelo menos 3 colunas?",
        "",
        "## Tabela completa (bytes por min_len)",
        "",
        "| Source | Col | " + " | ".join(f"ml={ml}" for ml in MIN_LENS) + " | best |",
        "|---|---|" + "---:|" * (len(MIN_LENS) + 1),
    ]
    for r in all_results:
        bs = r['bytes_by_ml']
        cells = " | ".join(f"{bs.get(ml, '-'):,}" for ml in MIN_LENS)
        valid = {ml: b for ml, b in bs.items() if b > 0}
        best_ml = min(valid, key=lambda k: valid[k]) if valid else '-'
        report.append(f"| {r['source']} | {r['col']} | {cells} | **ml={best_ml}** |")

    report.extend([
        "",
        "## Colunas que preferem min_len != 3 com ganho relevante",
        "",
        f"Threshold: ganho >= {THRESHOLD_PCT}% vs default min_len={DEFAULT_ML}",
        "",
    ])
    if cols_prefer_non_default:
        report.append("| Col | best_ml | default (B) | best (B) | gain |")
        report.append("|---|---:|---:|---:|---:|")
        for c in cols_prefer_non_default:
            report.append(f"| {c['col']} | {c['best_ml']} | "
                          f"{c['default_bytes']:,} | {c['best_bytes']:,} | "
                          f"{c['gain_pct']:.2f}% |")
    else:
        report.append("(nenhuma — default min_len=3 e' otimo em todas)")

    report.extend([
        "",
        "## Agregado",
        "",
        f"- Total colunas testadas: **{len(all_results)}**",
        f"- Colunas com ganho relevante (!= 3, >= {THRESHOLD_PCT}%): "
        f"**{n_with_gain}**",
        f"- Bytes economizados (best vs default, weighted): "
        f"**{total_gain:,} / {total_baseline:,} = {weighted_gain:.2f}%**",
        "",
        "## Veredito",
        "",
        f"**{veredito}**",
        "",
        f"**Status sugerido roadmap H-DA-10**: `{status_novo}`",
        "",
        "## Notas metodologicas",
        "",
        "- min_len controla tamanho minimo de prefix/suffix em OBAT",
        "- Default = 3 (decisao M0 fase exploratoria)",
        "- H-DA-10 original: D9 sintetico mostrou min_len=5 da -33B "
        "(N=3 datasets, N=4 valores)",
        "- Real-world: testa generalizacao do trade-off",
        "",
    ])

    out = THIS / "result.md"
    out.write_bytes(("\n".join(report) + "\n").encode("utf-8"))
    print(f"\nresult.md: {out}")


if __name__ == "__main__":
    main()

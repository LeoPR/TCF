"""Sub-exp 01 — H-DA-06 inspecao: subsumida em H-DA-09b-v2?

Pergunta: H-DA-09b-v2 (numeric+high-cardinality, welded ADR-0008)
ja' captura colunas-alvo de H-DA-06 (numeric IDs sequenciais)
em real-world?

Metodo:
- Rodar detect_cadence em todas colunas de:
  - D16a/b/c (sintetico — onde H-DA-06 foi validado original)
  - Adult Census 1k/5k (real-world)
  - TPC-H region/customer/lineitem-5k (real-world)
- Reportar quais colunas disparam:
  - regra 1 (wrapper+counter)
  - regra 2 (numeric high-cardinality) ← H-DA-09b-v2
  - nenhuma
- Identificar colunas numeric ID que NAO disparam regra 2
  → essas seriam casos onde H-DA-06 ainda agrega valor

Cobertura ALTA → H-DA-06 subsumida.
Cobertura BAIXA → H-DA-06 ortogonal, manter aberta.
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
from auto_pre import detect_cadence, _is_numeric_string  # noqa: E402


D16 = ["D16a-ids-3digits", "D16b-ids-4digits", "D16c-ids-prefixados"]


def ler_csv_single_col(path):
    with path.open(encoding="utf-8") as f:
        r = csv.reader(f)
        next(r)
        return [row[0] for row in r if row]


def dedup_preserve_order(values):
    seen = OrderedDict()
    for v in values:
        seen[v] = True
    return list(seen.keys())


def is_numeric_col(strings, sample_size=20):
    sample = strings[:min(sample_size, len(strings))]
    return all(_is_numeric_string(v) for v in sample) if sample else False


def cardinality(strings):
    if not strings:
        return 0.0
    return len(set(strings)) / len(strings)


def avg_len(strings):
    if not strings:
        return 0
    return sum(len(s) for s in strings) / len(strings)


def inspect_col(name, values):
    hit, info = detect_cadence(values)
    is_num = is_numeric_col(values)
    card = cardinality(values)
    return {
        'col': name,
        'n_rows': len(values),
        'avg_len': round(avg_len(values), 1),
        'is_numeric': is_num,
        'cardinality': round(card, 3),
        'hit': hit,
        'rule': info.get('rule_hit'),
        'reason': info.get('reason', ''),
    }


def rows_to_cols(rows):
    if not rows:
        return {}
    return {c: [str(r[c]) if r[c] is not None else "" for r in rows]
            for c in rows[0].keys()}


def main():
    print("=== Sub-exp 01 — H-DA-06 inspecao subsumida ===\n")
    all_results = []

    # D16 sintetico (referencia original H-DA-06)
    print(">> D16 sintetico (referencia H-DA-06 original)")
    datasets_dir = ROOT / "datasets" / "synthetic"
    for ds_name in D16:
        path = datasets_dir / f"{ds_name}.csv"
        if not path.exists():
            print(f"  SKIP {ds_name}: nao existe")
            continue
        values = ler_csv_single_col(path)
        r = inspect_col(f"{ds_name}/val", values)
        r['source'] = ds_name
        all_results.append(r)
        rule_mark = "Y" if r['hit'] else "."
        print(f"  {r['col']:<35} {rule_mark} rule={r['rule']} "
              f"is_num={r['is_numeric']} card={r['cardinality']}")

    # Adult Census real-world
    print("\n>> Adult Census (real-world)")
    reader = DatasetReader("adult-census")
    for vol in [1000, 5000]:
        rows = reader.rows("adult", limit=vol)
        cols = rows_to_cols(rows)
        for cname, values in cols.items():
            r = inspect_col(f"adult-{vol}/{cname}", values)
            r['source'] = f"adult-{vol}"
            all_results.append(r)
    reader.close()
    for r in [x for x in all_results if 'adult' in x['source']]:
        rule_mark = "Y" if r['hit'] else "."
        print(f"  {r['col']:<35} {rule_mark} rule={r['rule']} "
              f"is_num={r['is_numeric']} card={r['cardinality']}")

    # TPC-H real-world
    print("\n>> TPC-H (real-world)")
    reader = DatasetReader("tpch-sf001")
    for table in ["region", "customer", "lineitem"]:
        rows = reader.rows(table, limit=5000)
        cols = rows_to_cols(rows)
        for cname, values in cols.items():
            r = inspect_col(f"tpch.{table}-5k/{cname}", values)
            r['source'] = f"tpch.{table}-5k"
            all_results.append(r)
    reader.close()
    for r in [x for x in all_results if x['source'].startswith('tpch.')]:
        rule_mark = "Y" if r['hit'] else "."
        print(f"  {r['col']:<35} {rule_mark} rule={r['rule']} "
              f"is_num={r['is_numeric']} card={r['cardinality']}")

    # Analise: numericas que disparam regra 2 vs total numericas
    print("\n=== Analise cobertura H-DA-06 ===\n")
    numeric_cols = [r for r in all_results if r['is_numeric']]
    numeric_hit_rule2 = [r for r in numeric_cols
                         if r['hit'] and r['rule'] == '2-numeric-high-cardinality']
    numeric_hit_any = [r for r in numeric_cols if r['hit']]

    print(f"Total colunas numericas: {len(numeric_cols)}")
    print(f"  Disparam regra 2 (H-DA-09b-v2 numeric-high-card): {len(numeric_hit_rule2)}")
    print(f"  Disparam alguma regra:                            {len(numeric_hit_any)}")

    # Colunas numericas que NAO disparam = casos onde H-DA-06 poderia agregar
    not_hit = [r for r in numeric_cols if not r['hit']]
    print(f"\n  Numericas NAO disparam (casos H-DA-06 potencial):")
    for r in not_hit:
        print(f"    {r['col']:<35} card={r['cardinality']} "
              f"reason={r['reason']}")

    # Subsumed if regra 2 cobre >= 80% das numericas com alta cardinalidade
    high_card_numeric = [r for r in numeric_cols if r['cardinality'] > 0.5]
    high_card_hit = [r for r in high_card_numeric
                     if r['hit'] and r['rule'] == '2-numeric-high-cardinality']
    cov = (len(high_card_hit) / len(high_card_numeric) * 100
           if high_card_numeric else 0)
    print(f"\n  Cobertura regra 2 sobre numeric+high-card: "
          f"{len(high_card_hit)}/{len(high_card_numeric)} ({cov:.1f}%)")

    # Veredito
    print("\n=== Veredito ===\n")
    if cov >= 80:
        veredito = "SUBSUMIDA — H-DA-09b-v2 ja' captura caso de H-DA-06 em real-world"
        status_novo = "subsumida em H-DA-09b-v2 (welded ADR-0008)"
    elif cov >= 50:
        veredito = "PARCIALMENTE SUBSUMIDA — alguns casos ainda ortogonais"
        status_novo = "subsumida-parcial em H-DA-09b-v2; ressalva real-world"
    else:
        veredito = "ORTOGONAL — H-DA-09b-v2 NAO cobre, H-DA-06 segue relevante"
        status_novo = "confirmada-empirica (mantida); A-revalidar com novos sub-exps"

    print(f"Cobertura: {cov:.1f}%")
    print(f"{veredito}")
    print(f"\nStatus sugerido roadmap: {status_novo}")

    # Report
    report = [
        "# Sub-exp 01 — H-DA-06 inspecao subsumida em H-DA-09b-v2",
        "",
        "## Pergunta",
        "",
        "H-DA-09b-v2 (numeric+high-cardinality, welded ADR-0008) ja' captura",
        "colunas-alvo de H-DA-06 (numeric IDs sequenciais) em real-world?",
        "",
        "## Tabela completa",
        "",
        "| Source | Col | n_rows | avg_len | num? | card | hit | rule |",
        "|---|---|---:|---:|---|---:|---|---|",
    ]
    for r in all_results:
        num = "Y" if r['is_numeric'] else "n"
        hit = "✓" if r['hit'] else "·"
        rule = r['rule'] or '-'
        report.append(
            f"| {r['source']} | {r['col'].split('/')[-1]} | {r['n_rows']} | "
            f"{r['avg_len']} | {num} | {r['cardinality']} | {hit} | {rule} |"
        )

    report.extend([
        "",
        "## Analise",
        "",
        f"- Total colunas numericas: **{len(numeric_cols)}**",
        f"- Disparam regra 2 (H-DA-09b-v2): **{len(numeric_hit_rule2)}**",
        f"- Disparam alguma regra: **{len(numeric_hit_any)}**",
        f"- Cobertura sobre numeric+high-card (>0.5): "
        f"**{len(high_card_hit)}/{len(high_card_numeric)} ({cov:.1f}%)**",
        "",
        "### Numericas que NAO disparam (casos H-DA-06 potenciais)",
        "",
    ])
    if not_hit:
        report.append("| Col | card | reason |")
        report.append("|---|---:|---|")
        for r in not_hit:
            report.append(f"| {r['col']} | {r['cardinality']} | {r['reason']} |")
    else:
        report.append("(nenhuma — todas numericas disparam regra 2)")

    report.extend([
        "",
        "## Veredito",
        "",
        f"**Cobertura**: {cov:.1f}%",
        "",
        f"**{veredito}**",
        "",
        f"**Status sugerido roadmap H-DA-06**: `{status_novo}`",
        "",
    ])

    out = THIS / "result.md"
    out.write_bytes(("\n".join(report) + "\n").encode("utf-8"))
    print(f"\nresult.md: {out}")


if __name__ == "__main__":
    main()

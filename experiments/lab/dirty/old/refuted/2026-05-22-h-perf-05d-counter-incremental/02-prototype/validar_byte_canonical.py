"""Sub-exp 02 — validar IncrementalSyntax byte-canonical.

Compara bytes em D1-D9 + lineitem 1k/5k:
- canonical (M8AVirtualRefsSyntax)
- incremental (IncrementalSyntax)

Criterio: bytes IDENTICOS em TODOS os datasets/cols.
Se qualquer diferenca, fix bug no prototype.
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
sys.path.insert(0, str(THIS))

from dataset_reader import DatasetReader  # noqa: E402
from tcf.composicional.syntax import M8AVirtualRefsSyntax  # noqa: E402
from tcf.column_features import analyze_column  # noqa: E402
from tcf.auto_min_len import detect_min_len_from_features  # noqa: E402
from tcf.core.online import processar  # noqa: E402
from incremental_syntax import IncrementalSyntax  # noqa: E402


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


def encode_with(syntax_cls, values, header="val"):
    unicas = dedup_preserve_order(values)
    features = analyze_column(values)
    min_len = detect_min_len_from_features(features)
    tokens, _ = processar(unicas, min_len=min_len)
    return syntax_cls().encode(values, unicas, tokens, header)


def main():
    print("=== Sub-exp 02 — validar IncrementalSyntax byte-canonical ===\n")

    results = []
    datasets_dir = ROOT / "datasets" / "synthetic"

    # D1-D9
    print(">> D1-D9")
    for ds in D1_D9:
        values = ler_csv_single_col(datasets_dir / f"{ds}.csv")
        b_can = encode_with(M8AVirtualRefsSyntax, values)
        b_inc = encode_with(IncrementalSyntax, values)
        match = b_can == b_inc
        results.append({
            'source': 'sintetico', 'col': ds, 'n_rows': len(values),
            'bytes_can': len(b_can.encode("utf-8")),
            'bytes_inc': len(b_inc.encode("utf-8")),
            'match': match,
        })
        marker = "OK" if match else "DIFF"
        print(f"  {ds:<25} can={len(b_can.encode('utf-8')):>4}  "
              f"inc={len(b_inc.encode('utf-8')):>4}  {marker}")

    # Lineitem 1k
    print("\n>> lineitem 1k")
    reader = DatasetReader("tpch-sf001")
    rows = reader.rows("lineitem", limit=1000)
    cols = rows_to_cols(rows)
    for cname, vals in cols.items():
        b_can = encode_with(M8AVirtualRefsSyntax, vals)
        b_inc = encode_with(IncrementalSyntax, vals)
        match = b_can == b_inc
        results.append({
            'source': 'lineitem-1k', 'col': cname, 'n_rows': len(vals),
            'bytes_can': len(b_can.encode("utf-8")),
            'bytes_inc': len(b_inc.encode("utf-8")),
            'match': match,
        })
        marker = "OK" if match else "DIFF"
        if not match:
            print(f"  {cname:<25} can={len(b_can.encode('utf-8')):>6}  "
                  f"inc={len(b_inc.encode('utf-8')):>6}  {marker}")

    # Lineitem 5k (mais robusto)
    print(">> lineitem 5k")
    rows = reader.rows("lineitem", limit=5000)
    cols = rows_to_cols(rows)
    for cname, vals in cols.items():
        b_can = encode_with(M8AVirtualRefsSyntax, vals)
        b_inc = encode_with(IncrementalSyntax, vals)
        match = b_can == b_inc
        results.append({
            'source': 'lineitem-5k', 'col': cname, 'n_rows': len(vals),
            'bytes_can': len(b_can.encode("utf-8")),
            'bytes_inc': len(b_inc.encode("utf-8")),
            'match': match,
        })
        marker = "OK" if match else "DIFF"
        if not match:
            print(f"  {cname:<25} can={len(b_can.encode('utf-8')):>6}  "
                  f"inc={len(b_inc.encode('utf-8')):>6}  {marker}")
    reader.close()

    # Veredito
    total = len(results)
    match_count = sum(1 for r in results if r['match'])
    print(f"\n=== Veredito ===\n")
    print(f"Match: {match_count}/{total}")

    diffs = [r for r in results if not r['match']]
    if diffs:
        print(f"\nDiffs ({len(diffs)}):")
        for r in diffs:
            d = r['bytes_inc'] - r['bytes_can']
            print(f"  {r['source']}/{r['col']:<25} n={r['n_rows']:>5}  "
                  f"can={r['bytes_can']:>6}  inc={r['bytes_inc']:>6}  "
                  f"delta={d:+d}")

    if match_count == total:
        print("\n** BYTE-CANONICAL OK — prototype incremental valido **")
    else:
        print(f"\n** BUG NO PROTOTYPE — {len(diffs)} diffs encontradas **")

    # Report
    report = [
        "# Sub-exp 02 — validar IncrementalSyntax byte-canonical",
        "",
        "## Setup",
        "",
        "Compara bytes M8AVirtualRefsSyntax (canonical) vs",
        "IncrementalSyntax (counter incremental) em D1-D9 + lineitem 1k/5k.",
        "",
        "Criterio: bytes IDENTICOS (zero diferenca).",
        "",
        "## Resultados",
        "",
        f"**Match**: {match_count}/{total}",
        "",
    ]
    if diffs:
        report.append(f"### Diffs ({len(diffs)})")
        report.append("")
        report.append("| Source | Col | n_rows | canonical | incremental | delta |")
        report.append("|---|---|---:|---:|---:|---:|")
        for r in diffs:
            d = r['bytes_inc'] - r['bytes_can']
            report.append(f"| {r['source']} | {r['col']} | {r['n_rows']} | "
                          f"{r['bytes_can']} | {r['bytes_inc']} | {d:+d} |")
    else:
        report.append("Zero diffs. Prototype byte-canonical VALIDO.")

    out = THIS / "result_byte_canonical.md"
    out.write_bytes(("\n".join(report) + "\n").encode("utf-8"))
    print(f"\nresult_byte_canonical.md: {out}")


if __name__ == "__main__":
    main()

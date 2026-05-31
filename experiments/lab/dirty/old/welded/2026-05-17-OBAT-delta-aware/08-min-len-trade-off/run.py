"""Sub-exp 08 — H-DA-10: trade-off min_len.

Varia min_len em pipeline canonical OBAT + HCC fork. Mede bytes
e RT por (dataset, min_len).
"""

from __future__ import annotations

import csv
import sys
from collections import OrderedDict
from pathlib import Path

THIS = Path(__file__).parent
ROOT = THIS.parents[4]
SRC = ROOT / "src"
HCC_FORK_DIR = THIS.parent / "02-hcc-sozinho-rle-near-identical"
sys.path.insert(0, str(SRC))
sys.path.insert(0, str(HCC_FORK_DIR))

from tcf.composicional.syntax import M8AVirtualRefsSyntax  # noqa: E402
from tcf.core.online import processar  # noqa: E402
from hcc_fork import HCCForkSeqRLE  # noqa: E402


DATASETS = [
    "D16a-ids-3digits",
    "D11d-datetime-min",
    "D9-frequencia-alta",
]
MIN_LENS = [2, 3, 4, 5]


def write_lf(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content.encode("utf-8"))


def load_rows(ds):
    p = ROOT / "datasets" / "synthetic" / f"{ds}.csv"
    with p.open(encoding="utf-8") as f:
        r = csv.reader(f)
        next(r)
        return [row[0] for row in r if row]


def dedup_preserve_order(values):
    seen = OrderedDict()
    for v in values:
        seen[v] = True
    return list(seen.keys())


def process(ds, min_len):
    rows = load_rows(ds)
    unicas = dedup_preserve_order(rows)
    tokens, _ = processar(unicas, min_len=min_len)

    # Canonical body (sem fork)
    body_can = M8AVirtualRefsSyntax().encode(rows, unicas, tokens, "val")
    bytes_can = len(body_can.encode("utf-8"))

    # HCC fork body
    syn = HCCForkSeqRLE()
    body_fork = syn.encode(rows, unicas, tokens, "val")
    bytes_fork = len(body_fork.encode("utf-8"))
    decoded = syn.decode(body_fork)
    rt = "OK" if decoded == rows else "FAIL"

    out_dir = THIS / "outputs" / ds / f"min_len_{min_len}"
    write_lf(out_dir / "body-canonical.tcf", body_can)
    write_lf(out_dir / "body-hcc-fork.tcf", body_fork)
    write_lf(out_dir / "stats.txt",
             f"min_len: {min_len}\n"
             f"bytes_canonical_body: {bytes_can}\n"
             f"bytes_hcc_fork_body: {bytes_fork}\n"
             f"RT: {rt}\n")

    return {
        'dataset': ds,
        'min_len': min_len,
        'bytes_canonical': bytes_can,
        'bytes_fork': bytes_fork,
        'rt': rt,
    }


def main():
    print("=== Sub-exp 08 — min_len trade-off ===\n")
    results = []
    for ds in DATASETS:
        print(f"  Dataset: {ds}")
        for ml in MIN_LENS:
            try:
                r = process(ds, ml)
                results.append(r)
                print(f"    min_len={ml}  canon={r['bytes_canonical']:4}  "
                      f"fork={r['bytes_fork']:4}  RT={r['rt']}")
            except Exception as e:
                print(f"    min_len={ml}  ERROR: {e}")
                results.append({
                    'dataset': ds, 'min_len': ml,
                    'bytes_canonical': -1, 'bytes_fork': -1, 'rt': 'ERROR',
                })

    # Encontrar melhor min_len por dataset
    out = [
        "# Resumo — Sub-exp 08 (min_len trade-off)",
        "",
        "## Tabela por (dataset, min_len)",
        "",
        "| Dataset | min_len | canon (B) | fork (B) | RT |",
        "|---|---:|---:|---:|---|",
    ]
    for r in results:
        out.append(
            f"| {r['dataset']} | {r['min_len']} | {r['bytes_canonical']} | "
            f"{r['bytes_fork']} | {r['rt']} |"
        )
    out.append("")
    out.append("## Melhor min_len por dataset (pelo fork bytes)")
    out.append("")
    out.append("| Dataset | Melhor min_len | Bytes fork |")
    out.append("|---|---:|---:|")
    by_ds = {}
    for r in results:
        if r['rt'] != 'OK':
            continue
        by_ds.setdefault(r['dataset'], []).append(r)
    for ds, lst in by_ds.items():
        best = min(lst, key=lambda x: x['bytes_fork'])
        out.append(f"| {ds} | {best['min_len']} | {best['bytes_fork']} |")
    out.append("")
    out.append("## Observacoes")
    out.append("")
    for ds, lst in by_ds.items():
        bytes_per_ml = [(r['min_len'], r['bytes_fork']) for r in lst]
        out.append(f"- **{ds}**: " +
                   ", ".join(f"ml={ml}→{b}B" for ml, b in bytes_per_ml))
    out.append("")
    write_lf(THIS / "summary.md", "\n".join(out) + "\n")
    print()
    print(f"summary.md: {THIS / 'summary.md'}")


if __name__ == "__main__":
    main()

"""Profile bucket sizes pra diferentes index keys em lineitem 5k.

Output: tabela comparativa por coluna em result.md.
"""

from __future__ import annotations

import sys
from collections import OrderedDict, Counter
from pathlib import Path

THIS = Path(__file__).parent
ROOT = THIS.parents[4]
SCRIPTS = ROOT / "scripts"

sys.path.insert(0, str(SCRIPTS))

from dataset_reader import DatasetReader  # noqa: E402


def dedup_preserve_order(values):
    seen = OrderedDict()
    for v in values:
        seen[v] = True
    return list(seen.keys())


def write_lf(path, content):
    if isinstance(content, str):
        content = content.encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def make_keys(s):
    """Retorna dict de keys candidatas pra esta string."""
    L = len(s)
    if L < 3:
        return None
    mid_start = (L - 3) // 2
    middle = s[mid_start:mid_start + 3] if L >= 5 else None
    return {
        "prefix": s[:3],
        "suffix": s[-3:],
        "middle": middle,
        "combined_ps": s[:3] + s[-3:],
        "combined_full": s[:3] + (middle if middle else "") + s[-3:],
    }


def bucket_stats(uniques, key_name):
    """Calcula buckets pra uma key. Retorna dict com stats."""
    buckets = {}
    for s in uniques:
        keys = make_keys(s)
        if not keys or keys.get(key_name) is None:
            continue
        k = keys[key_name]
        buckets.setdefault(k, []).append(s)
    sizes = [len(b) for b in buckets.values()]
    if not sizes:
        return None
    sizes_sorted = sorted(sizes, reverse=True)
    # Strings em buckets grandes (>= 10)
    big_strings = sum(s for s in sizes if s >= 10)
    return {
        "n_buckets": len(buckets),
        "max_bucket": max(sizes),
        "avg_bucket": sum(sizes) / len(sizes),
        "median_bucket": sorted(sizes)[len(sizes)//2],
        "top5_sizes": sizes_sorted[:5],
        "n_strings_in_big_buckets": big_strings,
        "n_total_strings": sum(sizes),
    }


def main():
    print("=== Profile bucket sizes — lineitem 5000 ===")
    reader = DatasetReader("tpch-sf001")
    rows = reader.rows("lineitem", limit=5000)
    reader.close()

    cols = {c: [str(r[c]) if r[c] is not None else "" for r in rows]
            for c in rows[0].keys()}

    key_names = ["prefix", "suffix", "middle", "combined_ps", "combined_full"]
    report = ["# Sub-exp 01 — profile bucket sizes (lineitem 5k)", ""]
    report.append(f"Dataset: lineitem 5000 rows x {len(cols)} cols")
    report.append("")

    # Tabela 1: por coluna, max bucket por key
    report.append("## Max bucket size por key (menor = melhor dispersao)")
    report.append("")
    report.append(f"| coluna | n_unicas | {' | '.join(key_names)} |")
    report.append("|---|---:|" + "|".join([":---:"] * len(key_names)) + "|")

    by_col_detail = {}

    for cname, cvals in cols.items():
        unicas = dedup_preserve_order(cvals)
        if len(unicas) < 50:
            continue
        row = [cname, str(len(unicas))]
        stats_by_key = {}
        for kn in key_names:
            st = bucket_stats(unicas, kn)
            stats_by_key[kn] = st
            if st is None:
                row.append("-")
            else:
                row.append(str(st["max_bucket"]))
        report.append("| " + " | ".join(row) + " |")
        by_col_detail[cname] = (len(unicas), stats_by_key)

    report.append("")

    # Tabela 2: detalhes por coluna grande (>500 unicas)
    report.append("## Detalhe colunas grandes (>=500 unicas)")
    report.append("")
    for cname, (n_unicas, stats_by_key) in by_col_detail.items():
        if n_unicas < 500:
            continue
        report.append(f"### {cname} ({n_unicas} unicas)")
        report.append("")
        report.append("| key | n_buckets | max | avg | median | top5 | strings em buckets >=10 |")
        report.append("|---|---:|---:|---:|---:|---|---:|")
        for kn in key_names:
            st = stats_by_key[kn]
            if st is None:
                continue
            top5_str = ", ".join(str(x) for x in st["top5_sizes"])
            report.append(
                f"| {kn} | {st['n_buckets']} | {st['max_bucket']} | "
                f"{st['avg_bucket']:.1f} | {st['median_bucket']} | "
                f"{top5_str} | {st['n_strings_in_big_buckets']} ({st['n_strings_in_big_buckets']/st['n_total_strings']*100:.0f}%) |"
            )
        report.append("")

    # Analise resumo
    report.append("## Resumo")
    report.append("")
    report.append("Procurando: key onde max_bucket e' menor (especialmente em datas).")
    report.append("Quanto menor max_bucket, menos comparacoes por string nova.")
    report.append("")
    report.append("**Datas TPC-H** (l_shipdate/commitdate/receiptdate): comparar")
    report.append("max_bucket de prefix vs middle vs combined_ps.")
    report.append("")
    report.append("*(preencher analise apos rodar)*")

    write_lf(THIS / "result.md", "\n".join(report) + "\n")
    print(f"\nresult.md: {THIS / 'result.md'}")


if __name__ == "__main__":
    main()

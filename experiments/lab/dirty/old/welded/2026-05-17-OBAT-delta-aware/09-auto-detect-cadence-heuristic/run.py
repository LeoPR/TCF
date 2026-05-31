"""Sub-exp 09 — auto-detect cadence heuristic em 20 datasets.

Compara 3 pipelines:
  1. baseline   = OBAT canonical + HCC canonical
  2. always_on  = OBAT fork shape-preserve + HCC fork
  3. auto       = Pre detecta cadencia, OBAT canonical OU fork, + HCC fork
"""

from __future__ import annotations

import csv
import json
import sys
from collections import OrderedDict
from pathlib import Path

THIS = Path(__file__).parent
ROOT = THIS.parents[4]
SRC = ROOT / "src"
HCC_FORK_DIR = THIS.parent / "02-hcc-sozinho-rle-near-identical"
OBAT_FORK_DIR = THIS.parent / "04-obat-shape-consistency-hint"
sys.path.insert(0, str(SRC))
sys.path.insert(0, str(HCC_FORK_DIR))
sys.path.insert(0, str(OBAT_FORK_DIR))
sys.path.insert(0, str(THIS))

from tcf.composicional.syntax import M8AVirtualRefsSyntax  # noqa: E402
from tcf.core.online import processar  # noqa: E402
from hcc_fork import HCCForkSeqRLE  # noqa: E402
from obat_fork import processar_with_hint  # noqa: E402
from auto_pre import detect_cadence  # noqa: E402


DATASETS = [
    "D1-emails-simples",
    "D2-emails-quote-id",
    "D3-stress-substring",
    "D4-caos-mix",
    "D5-padroes-multiplos",
    "D6-poucos-em-ruido",
    "D7-aninhamento",
    "D8-cabeca-cauda",
    "D9-frequencia-alta",
    "D11a-datas-dia",
    "D11b-datas-borda",
    "D11c-datas-mensal",
    "D11d-datetime-min",
    "D11e-datetime-mensal",
    "D11f-datetime-ms",
    "D11g-datetime-us",
    "D11h-datetime-ns",
    "D16a-ids-3digits",
    "D16b-ids-4digits",
    "D16c-ids-prefixados",
]


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


def process(ds):
    rows = load_rows(ds)
    unicas = dedup_preserve_order(rows)

    # 1. Baseline
    tokens_canon, _ = processar(unicas, min_len=3)
    body_bl = M8AVirtualRefsSyntax().encode(rows, unicas, tokens_canon, "val")
    bytes_bl = len(body_bl.encode("utf-8"))

    # 2. Always-on
    tokens_alwayson, _ = processar_with_hint(unicas, 3, prefer_shape_consistency=True)
    syn_alwayson = HCCForkSeqRLE()
    body_alwayson = syn_alwayson.encode(rows, unicas, tokens_alwayson, "val")
    bytes_alwayson = len(body_alwayson.encode("utf-8"))
    rt_alwayson = "OK" if syn_alwayson.decode(body_alwayson) == rows else "FAIL"

    # 3. Auto: Pre detecta, OBAT enable/disable
    detected, info = detect_cadence(unicas)
    if detected:
        tokens_auto = tokens_alwayson
    else:
        tokens_auto = tokens_canon
    syn_auto = HCCForkSeqRLE()
    body_auto = syn_auto.encode(rows, unicas, tokens_auto, "val")
    bytes_auto = len(body_auto.encode("utf-8"))
    rt_auto = "OK" if syn_auto.decode(body_auto) == rows else "FAIL"

    out = THIS / "outputs" / ds
    write_lf(out / "detect-result.txt",
             f"detectou_cadencia: {detected}\n"
             f"info: {json.dumps(info, indent=2, default=str)}\n")
    write_lf(out / "body-baseline.tcf", body_bl)
    write_lf(out / "body-alwayson.tcf", body_alwayson)
    write_lf(out / "body-auto.tcf", body_auto)
    write_lf(out / "stats.txt",
             f"detectou_cadencia: {detected}\n"
             f"bytes_baseline:    {bytes_bl}\n"
             f"bytes_alwayson:    {bytes_alwayson}\n"
             f"bytes_auto:        {bytes_auto}\n"
             f"d_alwayson_vs_bl:  {bytes_alwayson - bytes_bl:+d}\n"
             f"d_auto_vs_bl:      {bytes_auto - bytes_bl:+d}\n"
             f"d_auto_vs_alwayson: {bytes_auto - bytes_alwayson:+d}\n"
             f"RT_alwayson:       {rt_alwayson}\n"
             f"RT_auto:           {rt_auto}\n")

    return {
        'dataset': ds,
        'detected': detected,
        'bytes_bl': bytes_bl,
        'bytes_alwayson': bytes_alwayson,
        'bytes_auto': bytes_auto,
        'rt_alwayson': rt_alwayson,
        'rt_auto': rt_auto,
    }


def main():
    print("=== Sub-exp 09 — auto-detect cadence heuristic ===\n")
    results = []
    for ds in DATASETS:
        r = process(ds)
        results.append(r)
        flag = "[on]" if r['detected'] else "[off]"
        d_ao = r['bytes_alwayson'] - r['bytes_bl']
        d_au = r['bytes_auto'] - r['bytes_bl']
        s_ao = '+' if d_ao >= 0 else ''
        s_au = '+' if d_au >= 0 else ''
        print(f"  {ds:24} {flag:5} bl={r['bytes_bl']:4} ao={r['bytes_alwayson']:4} "
              f"au={r['bytes_auto']:4}  ao-bl={s_ao}{d_ao:4} au-bl={s_au}{d_au:4}")

    # Totals
    total_bl = sum(r['bytes_bl'] for r in results)
    total_ao = sum(r['bytes_alwayson'] for r in results)
    total_au = sum(r['bytes_auto'] for r in results)
    detected_count = sum(1 for r in results if r['detected'])
    rt_pass_ao = sum(1 for r in results if r['rt_alwayson'] == 'OK')
    rt_pass_au = sum(1 for r in results if r['rt_auto'] == 'OK')

    out = [
        "# Resumo — Sub-exp 09 (auto-detect cadence)",
        "",
        "Pipelines:",
        "- **baseline** = OBAT canon + HCC canon",
        "- **always-on (ao)** = OBAT fork shape-preserve + HCC fork",
        "- **auto** = Pre heuristica decide; OBAT canon OU fork; + HCC fork",
        "",
        f"Datasets onde heuristica detectou cadencia: {detected_count}/{len(results)}",
        f"RT always-on: {rt_pass_ao}/{len(results)}",
        f"RT auto:      {rt_pass_au}/{len(results)}",
        "",
        "## Totais",
        "",
        f"- baseline:  {total_bl} B",
        f"- always-on: {total_ao} B ({total_ao-total_bl:+d}, "
        f"{(total_ao-total_bl)/total_bl*100:+.1f}%)",
        f"- auto:      {total_au} B ({total_au-total_bl:+d}, "
        f"{(total_au-total_bl)/total_bl*100:+.1f}%)",
        "",
        "## Tabela",
        "",
        "| Dataset | det? | baseline | always-on | auto | ao-bl | au-bl | au-ao |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for r in results:
        flag = "yes" if r['detected'] else "no"
        d_ao = r['bytes_alwayson'] - r['bytes_bl']
        d_au = r['bytes_auto'] - r['bytes_bl']
        d_au_ao = r['bytes_auto'] - r['bytes_alwayson']
        s_ao = '+' if d_ao >= 0 else ''
        s_au = '+' if d_au >= 0 else ''
        s_au_ao = '+' if d_au_ao >= 0 else ''
        out.append(f"| [{r['dataset']}]({r['dataset']}/stats.txt) | {flag} | "
                   f"{r['bytes_bl']} | {r['bytes_alwayson']} | {r['bytes_auto']} | "
                   f"{s_ao}{d_ao} | {s_au}{d_au} | {s_au_ao}{d_au_ao} |")
    out.append("")
    write_lf(THIS / "summary.md", "\n".join(out) + "\n")
    print()
    print(f"Totais: bl={total_bl} ao={total_ao} ({(total_ao-total_bl)/total_bl*100:+.1f}%) "
          f"au={total_au} ({(total_au-total_bl)/total_bl*100:+.1f}%)")
    print(f"Detectou: {detected_count}/{len(results)}")


if __name__ == "__main__":
    main()

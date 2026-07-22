"""Sumariza results.json do T1 em tabelas + comparacoes decisivas + checagens."""
from __future__ import annotations
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
R = json.loads((HERE / "results.json").read_text(encoding="utf-8"))


def pct(a, b):
    """a como % de b (a=tcf, b=concorrente). <100 => TCF menor (vence)."""
    return 100.0 * a / b if b else float("nan")


def line(r, key):
    return r.get(key)


print("=" * 100)
print("T1 — TCF+brotli vs NDJSON/JSON+brotli — comparacoes decisivas (brotli q11)")
print("=" * 100)
print(f"{'dataset':14s} {'favor':11s} {'n':>6s} {'c':>2s} | "
      f"{'tcf':>7s} {'ndj_typ':>7s} {'ndj_str':>7s} {'json_col':>8s} {'csv':>7s} "
      f"| {'%vNDJt':>7s} {'%vJcol':>7s} {'%vCSV':>7s} RT")
worst_vs_ndjt = (None, -1)
worst_vs_jcol = (None, -1)
loses_ndjt = []
loses_jcol = []
for r in R:
    tcf = r["tcf_br"]; ndjt = r["ndjson_typed_br"]; ndjs = r["ndjson_str_br"]
    jcol = r["json_columnar_br"]; csv = r["csv_br"]
    p_ndjt = pct(tcf, ndjt); p_jcol = pct(tcf, jcol); p_csv = pct(tcf, csv)
    rt = "ok" if r["rt_ok"] else "FAIL"
    print(f"{r['dataset']:14s} {r['favor']:11s} {r['scale']:6d} {r['cols']:2d} | "
          f"{tcf:7d} {ndjt:7d} {ndjs:7d} {jcol:8d} {csv:7d} "
          f"| {p_ndjt:6.1f}% {p_jcol:6.1f}% {p_csv:6.1f}% {rt}")
    if p_ndjt > worst_vs_ndjt[1]:
        worst_vs_ndjt = (r, p_ndjt)
    if p_jcol > worst_vs_jcol[1]:
        worst_vs_jcol = (r, p_jcol)
    if tcf >= ndjt:
        loses_ndjt.append((r['dataset'], r['scale'], tcf, ndjt))
    if tcf >= jcol:
        loses_jcol.append((r['dataset'], r['scale'], tcf, jcol))

print("\n--- pior caso do TCF (maior %, mais perto de perder) ---")
w = worst_vs_ndjt[0]
print(f"vs NDJSON-typed: {w['dataset']} n={w['scale']} -> TCF {worst_vs_ndjt[1]:.1f}% do NDJSON-typed")
w = worst_vs_jcol[0]
print(f"vs json_columnar: {w['dataset']} n={w['scale']} -> TCF {worst_vs_jcol[1]:.1f}% do json_columnar")
print(f"\nTCF PERDE/empata vs NDJSON-typed em: {loses_ndjt or 'NENHUM'}")
print(f"TCF PERDE/empata vs json_columnar em: {loses_jcol or 'NENHUM'}")

# RT
rt_fails = [(r['dataset'], r['scale']) for r in R if not r['rt_ok']]
print(f"\nRT-FAIL em: {rt_fails or 'NENHUM (todos round-trip ok)'}")

# Sensibilidade q5
print("\n--- sensibilidade brotli q5 (TCF ainda vence NDJSON-typed?) ---")
q5_loses = []
for r in R:
    if r["tcf_br5"] >= r["ndjson_typed_br5"]:
        q5_loses.append((r['dataset'], r['scale'], r['tcf_br5'], r['ndjson_typed_br5']))
print(f"q5: TCF perde/empata vs NDJSON-typed em: {q5_loses or 'NENHUM'}")

# gzip consistencia
print("\n--- consistencia gzip (TCF+gzip vence NDJSON-typed+gzip?) ---")
gz_loses = [(r['dataset'], r['scale']) for r in R if r['tcf_gz'] >= r['ndjson_typed_gz']]
print(f"gzip: TCF perde/empata em: {gz_loses or 'NENHUM'}")

# monotonicidade por dataset (byte deve crescer com scale)
print("\n--- checagem monotonicidade (tcf_br cresce com scale?) ---")
from collections import defaultdict
byds = defaultdict(list)
for r in R:
    byds[r['dataset']].append((r['scale'], r['tcf_br']))
for d, xs in byds.items():
    xs.sort()
    non_mono = [(xs[i], xs[i+1]) for i in range(len(xs)-1) if xs[i+1][1] < xs[i][1]]
    if non_mono:
        print(f"  {d}: NAO-MONOTONICO {non_mono}")

# agregado weighted (soma de bytes) no maior scale comum
print("\n--- AGREGADO weighted (soma bytes, todos datasets, por scale) ---")
byscale = defaultdict(lambda: defaultdict(int))
for r in R:
    for k in ("tcf_br", "ndjson_typed_br", "json_columnar_br", "csv_br"):
        byscale[r['scale']][k] += r[k]
for scale in sorted(byscale):
    s = byscale[scale]
    print(f"  n={scale}: tcf={s['tcf_br']} | vs NDJSON-typed {pct(s['tcf_br'],s['ndjson_typed_br']):.1f}% "
          f"| vs json_col {pct(s['tcf_br'],s['json_columnar_br']):.1f}% "
          f"| vs csv {pct(s['tcf_br'],s['csv_br']):.1f}%")

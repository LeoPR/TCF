"""Estudo exploratorio (FORK, nao toca src/tcf) — 2 perguntas do owner (2026-06-16):

C. "Aplicar MENOS TCF deixa o brotli comprimir mais?" Sweep em ETAPAS de intensidade
   de TCF, medindo cada etapa SOZINHA e +brotli/+gzip. Procura o ponto onde o
   TCF+brotli e' MENOR (pode nao ser o TCF mais agressivo, ja' que o TCF tira a
   redundancia que o brotli reaproveitaria).

E. Ordenacao x compressao no MULTI-COLUMN: qual ordenacao (sort_by por chave low-card)
   comprime mais, tanto TCF-sozinho quanto TCF+brotli. (O lab 2026-06-14-ordering-
   characterizacao mediu so' TCF-sozinho; aqui adiciona o brotli.)

Datasets reais em Z:. ROWS limitado pra rodar rapido (brotli q11).
"""
from __future__ import annotations
import csv, sys, gzip
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "src"))
from tcf import encode                       # noqa: E402
from tcf.pipeline import PipelineConfig      # noqa: E402
import brotli                                # noqa: E402

EXT = Path("Z:/tcf-data/external")
ROWS = 3000
DATASETS = [
    ("adult",         EXT / "adult-census" / "adult.csv"),
    ("online-retail", EXT / "online-retail" / "online_retail.csv"),
    ("receita",       EXT / "receita-cnpj" / "estabelecimentos.csv"),
    ("tpch-lineitem", EXT / "tpch-sf001" / "lineitem.csv"),
]

LITE = PipelineConfig(pre_pass=False, obat_shape_preserve=False, hcc_seq_rle=False)


def load(path, limit):
    for enc in ("utf-8", "latin-1"):
        try:
            with path.open(encoding=enc, newline="") as f:
                r = csv.reader(f); header = next(r)
                cols = {h: [] for h in header}
                for n, row in enumerate(r):
                    if n >= limit:
                        break
                    if len(row) != len(header):
                        continue
                    for h, v in zip(header, row):
                        cols[h].append(v)
            return cols
        except UnicodeDecodeError:
            continue
    return {}


def csv_text(table):
    keys = list(table); n = len(table[keys[0]])
    lines = [",".join(keys)] + [",".join(table[k][i] for k in keys) for i in range(n)]
    return "\n".join(lines)


def br(s):  return len(brotli.compress(s.encode("utf-8"), quality=11))
def gz(s):  return len(gzip.compress(s.encode("utf-8"), 9))
def nbytes(s): return len(s.encode("utf-8"))


def part_C(label, table):
    print(f"\n### C — TCF estagiado x brotli — {label}")
    stages = [
        ("csv (sem TCF)", csv_text(table)),
        ("tcf-lite",      encode(table, layers=LITE, fallback=False, min_header=False)),
        ("tcf-M10 (#6)",  encode(table, fallback=False, min_header=False)),
        ("tcf-0.7",       encode(table)),
    ]
    print(f"{'etapa':16s} {'alone':>8s} {'+brotli':>8s} {'+gzip':>8s}")
    rows = []
    for name, s in stages:
        rows.append((name, nbytes(s), br(s), gz(s)))
        print(f"{name:16s} {rows[-1][1]:8d} {rows[-1][2]:8d} {rows[-1][3]:8d}")
    best_alone = min(rows, key=lambda r: r[1])
    best_br = min(rows, key=lambda r: r[2])
    print(f"  -> menor ALONE: {best_alone[0]} ({best_alone[1]}B)")
    print(f"  -> menor +BROTLI: {best_br[0]} ({best_br[2]}B)")


def part_E(label, table):
    keys = list(table); n = len(table[keys[0]])
    card = sorted(((len(set(table[k])), k) for k in keys), key=lambda x: x[0])
    low = [k for c, k in card if 1 < c < n][:3]          # 3 chaves low-card
    print(f"\n### E — ordenacao x compressao — {label}  (chaves low-card: {low})")
    print(f"{'ordering':18s} {'tcf':>8s} {'tcf+brotli':>11s}")
    rows = []
    base = encode(table)
    rows.append(("none", nbytes(base), br(base)))
    print(f"{'none':18s} {rows[-1][1]:8d} {rows[-1][2]:11d}")
    for k in low:
        s = encode(table, sort_by=k)
        rows.append((f"sort:{k}"[:18], nbytes(s), br(s)))
        print(f"{('sort:'+k)[:18]:18s} {rows[-1][1]:8d} {rows[-1][2]:11d}")
    best_tcf = min(rows, key=lambda r: r[1])
    best_br = min(rows, key=lambda r: r[2])
    print(f"  -> menor TCF: {best_tcf[0]} ({best_tcf[1]}B, {100*best_tcf[1]/rows[0][1]:.1f}% do none)")
    print(f"  -> menor TCF+brotli: {best_br[0]} ({best_br[2]}B, {100*best_br[2]/rows[0][2]:.1f}% do none)")


def main():
    for label, path in DATASETS:
        if not path.exists():
            print(f"\n== {label}: SKIP (sem dataset) =="); continue
        table = load(path, ROWS)
        if not table:
            print(f"\n== {label}: SKIP (load vazio) =="); continue
        n = len(next(iter(table.values())))
        print(f"\n{'='*64}\n== {label}  ({n} linhas x {len(table)} colunas) ==")
        part_C(label, table)
        part_E(label, table)


if __name__ == "__main__":
    main()

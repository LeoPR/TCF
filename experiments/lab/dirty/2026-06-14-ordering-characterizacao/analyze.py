"""O-FMT-01..04 — caracterizacao do ganho de ORDENACAO (Segment #5).

Ordenar agrupa valores similares/identicos adjacentes -> mais RLE (marcador
`*N|`) + mais sharing de afixo (OBAT ve' strings parecidas vizinhas) -> body
menor. Mas:
- REVERSIVEL (O-FMT-01): precisa salvar a permutacao reversa (N indices) =
  caro. net = ganho_body - custo_mapa.
- NATURAL (O-FMT-02): sem mapa (ordem livre/perdida). Ganho cheio, SE a ordem
  nao importa.

Mede, em datasets reais:
A. Por-coluna (single-col): encode(col) vs encode(sorted(col)) -> ganho puro.
B. Tabela (multi-col): encode(table) vs min_k encode(table ordenada por col k)
   -> ganho realista (ordenar por 1 chave reordena tudo). + custo do mapa reverso.

FORK exploratorio — NAO toca src/tcf.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "src"))
from tcf import encode  # noqa: E402

EXT = Path("Z:/tcf-data/external")
ROWS = 2000
N_KEYS = 6  # candidatos a chave de ordenacao = N colunas de menor cardinalidade


def load(path, limit):
    for enc in ("utf-8", "latin-1"):
        try:
            with path.open(encoding=enc, newline="") as f:
                r = csv.reader(f)
                header = next(r)
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


def b(table):
    return len(encode(table).encode("utf-8"))


DATASETS = [
    ("adult",        EXT / "adult-census" / "adult.csv"),
    ("online-retail", EXT / "online-retail" / "online_retail.csv"),
    ("tpch-lineitem", EXT / "tpch-sf001" / "lineitem.csv"),
    ("br-pessoas",   EXT / "br-identidades" / "pessoas.csv"),
    ("receita",      EXT / "receita-cnpj" / "estabelecimentos.csv"),
    ("ibge",         EXT / "ibge-municipios" / "municipios.csv"),
]


def main():
    print("=== B. Tabela: ordenar por chave (natural) vs as-is ===")
    print(f"{'dataset':14s} {'N':>5s} {'cols':>4s} {'base B':>8s} "
          f"{'best%':>6s} {'bestKey':>16s} {'mapCost':>8s} {'netRev':>8s}")
    print("-" * 78)
    for label, path in DATASETS:
        if not path.exists():
            print(f"{label}: SKIP")
            continue
        cols = load(path, ROWS)
        if not cols:
            continue
        names = list(cols.keys())
        N = len(next(iter(cols.values())))
        base = b(cols)
        # candidatos a chave = menor cardinalidade
        keys = sorted(names, key=lambda c: len(set(cols[c])))[:N_KEYS]
        best_b, best_key = base, "(none)"
        for k in keys:
            order = sorted(range(N), key=lambda i: cols[k][i])
            st = {c: [cols[c][i] for i in order] for c in names}
            tb = b(st)
            if tb < best_b:
                best_b, best_key = tb, k
        gain = 100 * (base - best_b) / base if base else 0
        map_cost = N * len(str(N))          # permutacao reversa como texto
        net_rev = (base - best_b) - map_cost
        print(f"{label:14s} {N:5d} {len(names):4d} {base:8d} {gain:5.1f}% "
              f"{best_key:>16.16s} {map_cost:8d} {net_rev:8d}")

    print("\n=== A. Por-coluna: ganho puro de ordenar a coluna (single-col) ===")
    print(f"{'dataset.col':30s} {'asis B':>8s} {'sorted B':>8s} {'gain%':>6s}")
    print("-" * 60)
    for label, path in DATASETS:
        if not path.exists():
            continue
        cols = load(path, ROWS)
        for c, vals in cols.items():
            if len(set(vals)) < 3:
                continue
            asis = len(encode(vals).encode("utf-8"))
            srt = len(encode(sorted(vals)).encode("utf-8"))
            g = 100 * (asis - srt) / asis if asis else 0
            if g >= 5.0:  # so' lista colunas com ganho relevante
                print(f"{label+'.'+c:30.30s} {asis:8d} {srt:8d} {g:5.1f}% <<")


if __name__ == "__main__":
    main()

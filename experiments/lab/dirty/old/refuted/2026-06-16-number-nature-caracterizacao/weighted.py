"""Weighted no nivel da TABELA — fecha a decisao de weld da nature de numero.

Aplica pack_int SELETIVAMENTE (so' nas colunas onde ganha vs o 0.7-fallback; nature
e' opt-in por coluna) e mede a TABELA inteira: baseline 0.7 vs 0.7+nature(seletiva),
cru e +brotli. Criterio de weld: >=15% weighted em 2+ datasets reais.

FORK, nao toca src/tcf. (O marcador de nature no header — H-NAT-MARK-01 — e' tiny e
necessario p/ deploy real; aqui o foco e' o ganho de bytes.)
"""
from __future__ import annotations
import csv, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "src"))
from tcf import encode               # noqa: E402
from tcf.natures import BASE94       # noqa: E402
import brotli                        # noqa: E402

EXT = Path("Z:/tcf-data/external"); ROWS = 5000; B = len(BASE94)
TABLES = [
    ("tpch-lineitem", "tpch-sf001/lineitem.csv"),
    ("adult", "adult-census/adult.csv"),
    ("beijing", "beijing-pm25/beijing_pm25.csv"),
    ("receita", "receita-cnpj/estabelecimentos.csv"),
]


def load(path, limit):
    for enc in ("utf-8", "latin-1"):
        try:
            with (EXT / path).open(encoding=enc, newline="") as f:
                r = csv.reader(f); h = next(r); cols = {x: [] for x in h}
                for n, row in enumerate(r):
                    if n >= limit:
                        break
                    if len(row) == len(h):
                        for k, v in zip(h, row):
                            cols[k].append(v)
            return cols
        except (UnicodeDecodeError, FileNotFoundError):
            continue
    return {}


def pack_int(v):
    if v.isdigit() and str(int(v)) == v:
        n = int(v)
        if n == 0:
            return BASE94[0]
        out = []
        while n:
            out.append(BASE94[n % B]); n //= B
        return "".join(reversed(out))
    return "_" + v


def nb(s): return len(s.encode("utf-8"))
def br(s): return len(brotli.compress(s.encode("utf-8"), quality=11))


def main():
    print(f"{'tabela':16s} {'cols':>5s} {'nat':>4s} {'base':>8s} {'+nat':>8s} {'gain%':>6s} "
          f"{'base+br':>8s} {'nat+br':>8s} {'gainbr%':>7s}")
    print("-" * 88)
    for label, path in TABLES:
        t = load(path, ROWS)
        if not t:
            print(f"{label:16s} SKIP"); continue
        # elegiveis: >=90% inteiros canonicos
        elig = [c for c in t if sum(1 for v in t[c] if v.isdigit() and str(int(v)) == v) >= 0.9 * len(t[c])]
        # winners: nature ganha vs 0.7-fallback NAQUELA coluna (per-col)
        winners = []
        for c in elig:
            if nb(encode({c: [pack_int(v) for v in t[c]]})) < nb(encode({c: t[c]})):
                winners.append(c)
        natured = {c: ([pack_int(v) for v in t[c]] if c in winners else t[c]) for c in t}
        base, nat = encode(t), encode(natured)
        g = 100 * (nb(base) - nb(nat)) / nb(base)
        gbr = 100 * (br(base) - br(nat)) / br(base)
        print(f"{label:16s} {len(t):5d} {len(winners):4d} {nb(base):8d} {nb(nat):8d} {g:5.1f}% "
              f"{br(base):8d} {br(nat):8d} {gbr:6.1f}%")
    print("\nweighted = (base-natured)/base na TABELA toda. Criterio weld: >=15% em 2+ reais.")


if __name__ == "__main__":
    main()

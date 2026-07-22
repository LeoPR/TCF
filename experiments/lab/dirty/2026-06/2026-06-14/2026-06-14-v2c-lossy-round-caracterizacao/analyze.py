"""V2-C lossy-round — caracterizacao do headroom (decidir depois).

Owner: "so' caracterizar, decidir depois". Mede quanto o arredondamento (lossy)
ganha SOBRE o estado welded (split+V2-B ja' capturam o lossless), em 8 datasets,
pra ver se o nicho de alta-precisao decimal e' maior do que parece (wine 15% @ d=2).

Contrato medido: round-as-pre-transform. Arredonda colunas numericas-decimais a D
casas (1x, explicito), TCF armazena/recupera EXATO o arredondado. Erro maximo
absoluto = 0.5*10^-D (deterministico, declarado). decode == round(x, D).

So' arredonda colunas com >=90% float-parseavel E precisao tipica > D (senao
no-op lossless). Demais colunas intocadas.

FORK exploratorio — NAO toca src/tcf.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "src"))
from tcf import encode, decode  # noqa: E402

EXT = Path("Z:/tcf-data/external")
ROWS = 5000


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


def decimals_of(v):
    """numero de casas decimais do texto, ou -1 se nao for float-like."""
    try:
        float(v)
    except (ValueError, TypeError):
        return -1
    if "." not in v:
        return 0
    return len(v.rsplit(".", 1)[1])


def col_precision(vals):
    """(frac_parseavel, precisao_tipica) da coluna."""
    dec = [decimals_of(v) for v in vals]
    ok = [d for d in dec if d >= 0]
    if not ok:
        return 0.0, 0
    frac = len(ok) / len(vals)
    # precisao tipica = max casas (o que define o custo de armazenar lossless)
    typ = max(ok)
    return frac, typ


def round_col(vals, d):
    out = []
    for v in vals:
        try:
            out.append(f"{float(v):.{d}f}")
        except (ValueError, TypeError):
            out.append(v)
    return out


def round_table(t, d):
    """arredonda so' colunas numericas-decimais com precisao > d (senao intocada)."""
    out = {}
    rounded = []
    for c, vals in t.items():
        frac, typ = col_precision(vals)
        if frac >= 0.90 and typ > d:
            out[c] = round_col(vals, d)
            rounded.append(c)
        else:
            out[c] = vals
    return out, rounded


DATASETS = ["adult-census/adult.csv", "online-retail/online_retail.csv",
            "tpch-sf001/lineitem.csv", "br-identidades/pessoas.csv",
            "receita-cnpj/estabelecimentos.csv", "ibge-municipios/municipios.csv",
            "beijing-pm25/beijing_pm25.csv", "wine-quality/wine.csv"]


def main():
    print(f"ROWS={ROWS}  (gain sobre o welded lossless; round so' em prec>d)\n")
    print(f"{'dataset':14s} {'base':>9s} {'d=3':>16s} {'d=2':>16s} {'d=1':>16s} {'#hi-prec':>8s}")
    print("-" * 86)
    g_base = {0: 0}
    g = {3: 0, 2: 0, 1: 0}
    for rel in DATASETS:
        path = EXT / rel
        if not path.exists():
            continue
        label = rel.split("/")[0].split("-")[0]
        t = load(path, ROWS)
        base = len(encode(t).encode("utf-8"))
        g_base[0] += base
        cells = []
        n_hi = 0
        for d in (3, 2, 1):
            rt, rounded = round_table(t, d)
            if d == 2:
                n_hi = len(rounded)
            b = len(encode(rt).encode("utf-8"))
            g[d] += b
            pct = 100 * (base - b) / base if base else 0
            cells.append(f"{b:8d}({pct:4.1f}%)")
        print(f"{label:14s} {base:9d} {cells[0]:>16s} {cells[1]:>16s} {cells[2]:>16s} {n_hi:8d}")
    print("-" * 86)
    print(f"{'WEIGHTED':14s} {g_base[0]:9d}", end="")
    for d in (3, 2, 1):
        print(f"  d={d}:{100*(g_base[0]-g[d])/g_base[0]:4.1f}%", end="")
    print()

    print("\n=== onde vive o nicho: colunas hi-precisao (>=3 casas, >=90% float) ===")
    print(f"{'dataset.col':30s} {'prec':>4s} {'baseSC':>8s} {'d2':>7s} {'d1':>7s} {'erro@d2':>9s}")
    print("-" * 70)
    for rel in DATASETS:
        path = EXT / rel
        if not path.exists():
            continue
        label = rel.split("/")[0].split("-")[0]
        t = load(path, ROWS)
        for c, vals in t.items():
            frac, typ = col_precision(vals)
            if frac >= 0.90 and typ >= 3:
                bsc = len(encode(vals).encode("utf-8"))
                d2 = len(encode(round_col(vals, 2)).encode("utf-8"))
                d1 = len(encode(round_col(vals, 1)).encode("utf-8"))
                err = 0.5 * 10 ** -2
                print(f"{label+'.'+c:30.30s} {typ:4d} {bsc:8d} {d2:7d} {d1:7d} {err:9.4f}")


if __name__ == "__main__":
    main()

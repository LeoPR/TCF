"""Caracterizacao — nature de NUMERO (filtro basico). FORK, nao toca src/tcf.

Pergunta (roadmap FILTRO-NUMERO): o pipeline delta-aware/seq-RLE/split/dict JA cobre
numeros? Onde uma nature de numero adicionaria valor LOSSLESS? "Como trabalhamos":
classifica colunas numericas reais + mede generico vs nature (pack base-94 do inteiro)
+ brotli. So' caracteriza; weld so' com ganho >=15% em 2+ datasets reais (anti-incidente).

Candidato (o mais simples, lossless p/ o subconjunto aplicavel):
  num-pack: inteiro nao-negativo CANONICO (str(int(v))==v) -> base-94 (largura variavel,
  delimitado por '\\n'); demais valores -> literal `_`+v (fallback). Reversivel: base94->int.
  (Decimais/sinais/zeros-a-esquerda ficam no fallback; variantes registradas pra depois.)
"""
from __future__ import annotations
import csv, sys, gzip
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "src"))
from tcf import encode                       # noqa: E402
from tcf.natures import BASE94               # noqa: E402  (alfabeto TCF-safe)
import brotli                                # noqa: E402

EXT = Path("Z:/tcf-data/external")
ROWS = 5000
B = len(BASE94)

# colunas inteiras reais a caracterizar
COLS = [
    ("adult", "adult-census/adult.csv",
     ["age", "fnlwgt", "capital-gain", "capital-loss", "hours-per-week", "education-num"]),
    ("tpch-lineitem", "tpch-sf001/lineitem.csv",
     ["l_orderkey", "l_partkey", "l_suppkey", "l_linenumber", "l_quantity"]),
    ("beijing", "beijing-pm25/beijing_pm25.csv", ["PRES", "Iws", "Ir"]),
]


def load(path, limit):
    for enc in ("utf-8", "latin-1"):
        try:
            with (EXT / path).open(encoding=enc, newline="") as f:
                r = csv.reader(f); header = next(r)
                cols = {h: [] for h in header}
                for n, row in enumerate(r):
                    if n >= limit:
                        break
                    if len(row) == len(header):
                        for h, v in zip(header, row):
                            cols[h].append(v)
            return cols
        except (UnicodeDecodeError, FileNotFoundError):
            continue
    return {}


def pack_int(v: str) -> str:
    """int nao-neg canonico -> base-94; senao literal `_`+v. Reversivel."""
    if v.isdigit() and str(int(v)) == v:        # canonico (sem zero a esquerda)
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
    # COMPARACAO JUSTA: 0.7 (fallback min tcf/raw/dict/split) nos valores CRUS
    # vs 0.7 nos valores PACKED (a nature e' um pre-transform; o 0.7 faz o resto).
    print(f"{'dataset.coluna':28s} {'N':>5s} {'%int':>5s} {'card%':>6s} "
          f"{'07':>7s} {'07+nat':>7s} {'nat/07':>7s} {'07+br':>7s} {'natbr':>7s} {'natbr/br':>8s}")
    print("-" * 104)
    wins = 0; total = 0
    for label, path, cols in COLS:
        t = load(path, ROWS)
        if not t:
            print(f"{label}: SKIP"); continue
        for c in cols:
            if c not in t or not t[c]:
                continue
            vals = t[c]; n = len(vals)
            frac_int = sum(1 for v in vals if v.isdigit() and str(int(v)) == v) / n
            card = len(set(vals)) / n
            packed = [pack_int(v) for v in vals]
            b07 = encode({c: vals})                  # 0.7 real (fallback) nos crus
            bnat = encode({c: packed})               # 0.7 nos packed (= nature pre-tx)
            r = 100 * nb(bnat) / nb(b07)
            rbr = 100 * br(bnat) / br(b07)
            total += 1
            if r < 100: wins += 1
            print(f"{label+'.'+c:28s} {n:5d} {frac_int*100:4.0f}% {card*100:5.1f}% "
                  f"{nb(b07):7d} {nb(bnat):7d} {r:6.1f}% {br(b07):7d} {br(bnat):7d} {rbr:7.1f}%")
    print(f"\nnat/07 < 100% = nature ganha vs o 0.7-fallback. Ganhou em {wins}/{total} colunas (cru).")


if __name__ == "__main__":
    main()

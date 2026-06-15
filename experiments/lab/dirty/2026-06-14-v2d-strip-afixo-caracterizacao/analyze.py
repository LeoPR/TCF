"""V2-D — caracterizacao do strip de afixo comum (lossless, ADR-0018).

Coluna onde TODOS os valores compartilham um prefixo e/ou sufixo (`.0`,
zero-pad, `BR-`, etc.): stripa o afixo, guarda 1x no header, restaura no decode.

PERGUNTA CRITICA: o OBAT JA' e' bidirecional (captura prefixo via LCP + sufixo
via LCS). Entao o afixo comum ja' vira UM fragmento compartilhado. V2-D so' vale
se stripar (afixo no header, ZERO ref por linha) bater o que o OBAT ja' faz
(afixo como fragmento + 1 ref/linha). Mede isso em colunas reais.

  base = encode(values)                       # OBAT ja' compartilha o afixo
  v2d  = header(afixo) + encode(stripped)     # afixo fora, body so' o miolo
  gain = base - v2d
+ RT: lcp + stripped[i] + lcs == values[i]

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
ROWS = 5000


def load(path, cols, limit):
    for enc in ("utf-8", "latin-1"):
        try:
            with path.open(encoding=enc, newline="") as f:
                r = csv.reader(f)
                header = next(r)
                idx = {h: i for i, h in enumerate(header)}
                want = cols or header
                data = {c: [] for c in want if c in idx}
                for n, row in enumerate(r):
                    if n >= limit:
                        break
                    if len(row) != len(header):
                        continue
                    for c in data:
                        data[c].append(row[idx[c]])
            return data
        except UnicodeDecodeError:
            continue
    return {}


def common_prefix(vals):
    if not vals:
        return ""
    p = vals[0]
    for v in vals[1:]:
        n = 0
        m = min(len(p), len(v))
        while n < m and p[n] == v[n]:
            n += 1
        p = p[:n]
        if not p:
            break
    return p


def common_suffix(vals):
    rev = [v[::-1] for v in vals]
    return common_prefix(rev)[::-1]


def nbytes(s):
    return len(s.encode("utf-8"))


def strip_affix(values):
    """Acha LCP/LCS universais (sem overlap) e devolve (lcp, lcs, stripped)."""
    lcp = common_prefix(values)
    # LCS sobre o que sobra apos remover o LCP (evita overlap em valores curtos)
    rest = [v[len(lcp):] for v in values]
    lcs = common_suffix(rest)
    if lcs:
        stripped = [r[:len(r) - len(lcs)] for r in rest]
    else:
        stripped = rest
    return lcp, lcs, stripped


def v2d_candidate(values):
    """(v2d_bytes, lcp, lcs, rt_ok) ou None se nao ha' afixo comum util."""
    lcp, lcs, stripped = strip_affix(values)
    if not lcp and not lcs:
        return None
    # RT
    rt_ok = all(lcp + stripped[i] + lcs == values[i] for i in range(len(values)))
    body = encode(stripped)  # single-col body do miolo
    # header: guarda lcp e lcs 1x. framing conservador: "P<len>:<lcp>S<len>:<lcs>"
    header = nbytes(lcp) + nbytes(lcs) + 4
    return nbytes(body) + header, lcp, lcs, rt_ok


DATASETS = [
    ("adult",         EXT / "adult-census" / "adult.csv", None),
    ("online-retail", EXT / "online-retail" / "online_retail.csv", None),
    ("tpch-lineitem", EXT / "tpch-sf001" / "lineitem.csv", None),
    ("br-pessoas",    EXT / "br-identidades" / "pessoas.csv", None),
    ("receita",       EXT / "receita-cnpj" / "estabelecimentos.csv", None),
    ("ibge",          EXT / "ibge-municipios" / "municipios.csv", None),
    ("beijing",       EXT / "beijing-pm25" / "beijing_pm25.csv", None),
    ("wine",          EXT / "wine-quality" / "wine.csv", None),
]


def main():
    print(f"ROWS={ROWS}  (so' colunas COM afixo comum universal)\n")
    print(f"{'dataset.col':30s} {'base':>8s} {'v2d':>8s} {'gain':>6s} {'%':>6s} "
          f"{'lcp':>8s} {'lcs':>8s} {'RT':>3s}")
    print("-" * 82)
    tot_base = tot_v2d = tot_base_all = 0
    any_rt_fail = False
    rows = 0
    for label, path, cols in DATASETS:
        if not path.exists():
            print(f"{label}: SKIP")
            continue
        data = load(path, cols, ROWS)
        for c, vals in data.items():
            if not vals or len(set(vals)) < 2:
                continue
            base = nbytes(encode(vals))
            tot_base_all += base
            cand = v2d_candidate(vals)
            if cand is None:
                continue
            v2d, lcp, lcs, rt = cand
            if not rt:
                any_rt_fail = True
            gain = base - v2d
            pct = 100 * gain / base if base else 0
            # so' lista quando o afixo e' nao-trivial e muda algo
            if (lcp or lcs) and abs(gain) >= 1:
                tot_base += base
                tot_v2d += v2d
                rows += 1
                mark = " <<" if pct >= 1.0 else (" REG" if gain < 0 else "")
                print(f"{label+'.'+c:30.30s} {base:8d} {v2d:8d} {gain:6d} {pct:5.1f}% "
                      f"{repr(lcp)[:8]:>8s} {repr(lcs)[:8]:>8s} {'OK' if rt else 'X':>3s}{mark}")
    print("-" * 82)
    print(f"RT: {'OK' if not any_rt_fail else 'FALHOU'}")
    if tot_base:
        print(f"colunas com afixo (|gain|>=1): {rows}")
        print(f"soma base={tot_base}  v2d={tot_v2d}  gain={tot_base-tot_v2d} "
              f"({100*(tot_base-tot_v2d)/tot_base:.2f}% das afetadas)")
        print(f"weighted sobre TODAS as colunas: "
              f"{100*(tot_base-tot_v2d)/tot_base_all:.2f}% (base_all={tot_base_all})")


if __name__ == "__main__":
    main()

"""V2-B — caracterizacao do encoder dicionario/categorico (lossless, order-free).

PONTO CEGO ATACADO (ADR-0018 V2-B): coluna low-card de N linhas. Hoje o HCC
deduplica os K unicos e emite 1 whole-value ref `^idx\\n` por linha repetida
(`^` + indice decimal + `\\n` ~ 4 bytes/linha). Pra K=24, N=40k isso infla
~150KB pra ~25KB de entropia real. O fallback 0.7 (V2-A) so' troca por raw
(~3 bytes/linha) — ainda longe do piso.

V2-B: separar [TABELA de unicos: encode(unicas)] + [STREAM de indices], 1 char
por linha (alfabeto printable, K<=94 -> 1 char; senao W chars). Order-free: nao
depende da ordem. Com sort_by (O-FMT-02) o stream vira runs -> RLE casa.

Mede, por coluna low-card REAL:
  base = min(encode(col), raw)        # o que o 0.7 hoje ja' faz (fallback)
  v2b  = tabela + stream (packed)     # order-free
  v2b_rle = tabela + stream RLE       # ganha em runs (sorted ou cadencia natural)
  v2b_sorted_rle = idem, valores ordenados (combina com sort_by)
  floor = tabela + N*log2(K)/8        # piso de entropia
+ RT: reconstrucao (unicas, idxs) == col  (NUNCA reportar bytes sem RT)

FORK exploratorio — NAO toca src/tcf.
"""

from __future__ import annotations

import csv
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "src"))
from tcf import encode  # noqa: E402

EXT = Path("Z:/tcf-data/external")
ROWS = 8000
# alfabeto printable invertivel, sem '\n': 0x21..0x7E = 94 chars
ALPHA = "".join(chr(c) for c in range(0x21, 0x7F))


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


def idx_width(k):
    """chars por indice no alfabeto ALPHA (base-94)."""
    if k <= 1:
        return 1
    return max(1, math.ceil(math.log(k, len(ALPHA))))


def to_idx_chars(idx, width):
    """indice inteiro -> string de `width` chars base-94 (big-endian)."""
    if width == 1:
        return ALPHA[idx]
    out = []
    for _ in range(width):
        out.append(ALPHA[idx % len(ALPHA)])
        idx //= len(ALPHA)
    return "".join(reversed(out))


def stream_packed(idxs, width):
    return "".join(to_idx_chars(i, width) for i in idxs)


def stream_rle(idxs, width):
    """RLE sobre indices: run>=2 vira `*<count><idxchars>`, senao repete.
    Custo textual aproximado (mesmo espirito do `*N|` do HCC, framing menor)."""
    if not idxs:
        return ""
    out = []
    run_val, run_len = idxs[0], 1
    for v in idxs[1:]:
        if v == run_val:
            run_len += 1
        else:
            out.append(_emit_run(run_val, run_len, width))
            run_val, run_len = v, 1
    out.append(_emit_run(run_val, run_len, width))
    return "".join(out)


def _emit_run(val, length, width):
    chars = to_idx_chars(val, width)
    if length == 1:
        return chars
    runtok = "*" + str(length) + chars
    plain = chars * length
    return runtok if len(runtok) < len(plain) else plain


def nbytes(s):
    return len(s.encode("utf-8"))


def v2b_size(vals, sort_it=False, rle=False):
    """tamanho V2-B de uma coluna. RT-checked: devolve (bytes, rt_ok)."""
    seq = sorted(vals) if sort_it else vals
    seen = {}
    unicas = []
    for v in seq:
        if v not in seen:
            seen[v] = len(unicas)
            unicas.append(v)
    K = len(unicas)
    w = idx_width(K)
    idxs = [seen[v] for v in seq]
    # RT: reconstroi a partir de (unicas, idxs)
    rt_ok = [unicas[i] for i in idxs] == list(seq)
    table = encode(unicas)  # tabela TCF-encodada (dedup/OBAT do conjunto pequeno)
    stream = stream_rle(idxs, w) if rle else stream_packed(idxs, w)
    # framing: header "K=<n>;w=<w>\n" + sep "\n" entre tabela e stream
    header = f"D{K};{w}\n"
    total = nbytes(header) + nbytes(table) + 1 + nbytes(stream)
    return total, rt_ok, K, w


def entropy_floor(vals):
    seen = set(vals)
    K = len(seen)
    if K <= 1:
        return 0
    return math.ceil(len(vals) * math.log2(K) / 8)


DATASETS = [
    ("adult",         EXT / "adult-census" / "adult.csv"),
    ("online-retail", EXT / "online-retail" / "online_retail.csv"),
    ("tpch-lineitem", EXT / "tpch-sf001" / "lineitem.csv"),
    ("br-pessoas",    EXT / "br-identidades" / "pessoas.csv"),
    ("receita",       EXT / "receita-cnpj" / "estabelecimentos.csv"),
    ("ibge",          EXT / "ibge-municipios" / "municipios.csv"),
    ("beijing",       EXT / "beijing-pm25" / "beijing_pm25.csv"),
    ("wine",          EXT / "wine-quality" / "wine.csv"),
]

MAXCARD = 96  # so' colunas low-card (K <= 96 -> 1 char por indice)


def main():
    print(f"ROWS={ROWS}  alfabeto={len(ALPHA)} chars  (low-card: K<={MAXCARD})\n")
    print(f"{'dataset.col':28s} {'N':>5s} {'K':>4s} {'tcf':>7s} {'raw':>7s} "
          f"{'base':>7s} {'v2b':>7s} {'v2bRLE':>7s} {'v2bSrt':>7s} "
          f"{'floor':>6s} {'gain%':>6s}")
    print("-" * 104)
    rows = []
    any_rt_fail = False
    for label, path in DATASETS:
        if not path.exists():
            print(f"{label}: SKIP (no file)")
            continue
        cols = load(path, ROWS)
        for c, vals in cols.items():
            N = len(vals)
            K = len(set(vals))
            if K < 2 or K > MAXCARD or K >= N:
                continue
            tcf = nbytes(encode(vals))
            raw = nbytes("\n".join(vals))
            base = min(tcf, raw)
            v2b, ok1, _, _ = v2b_size(vals, sort_it=False, rle=False)
            v2b_rle, ok2, _, _ = v2b_size(vals, sort_it=False, rle=True)
            v2b_srt, ok3, _, _ = v2b_size(vals, sort_it=True, rle=True)
            floor = entropy_floor(vals)
            if not (ok1 and ok2 and ok3):
                any_rt_fail = True
            best_orderfree = min(v2b, v2b_rle)
            gain = 100 * (base - best_orderfree) / base if base else 0
            name = f"{label}.{c}"
            print(f"{name:28.28s} {N:5d} {K:4d} {tcf:7d} {raw:7d} {base:7d} "
                  f"{v2b:7d} {v2b_rle:7d} {v2b_srt:7d} {floor:6d} {gain:5.1f}%")
            rows.append((name, N, K, base, best_orderfree, v2b_srt, floor, gain))

    print("\n=== resumo por-coluna ===")
    print(f"RT (todas as colunas): {'OK' if not any_rt_fail else 'FALHOU!!'}")
    if rows:
        wins = [r for r in rows if r[7] > 0]
        print(f"colunas low-card avaliadas: {len(rows)}  |  v2b order-free vence base: {len(wins)}")
        tot_base = sum(r[3] for r in rows)
        tot_v2b = sum(r[4] for r in rows)
        tot_srt = sum(r[5] for r in rows)
        tot_floor = sum(r[6] for r in rows)
        print(f"soma base={tot_base}  v2b_orderfree={tot_v2b} "
              f"({100*(tot_base-tot_v2b)/tot_base:.1f}%)  "
              f"v2b_sorted={tot_srt} ({100*(tot_base-tot_srt)/tot_base:.1f}%)  "
              f"floor={tot_floor} ({100*(tot_base-tot_floor)/tot_base:.1f}%)")

    # ----- Parte B: ganho AO NIVEL DE TABELA (peso real-world) -----
    # V2-B entra como 3o candidato no fallback per-coluna: min(tcf, raw, v2b).
    # Zero regressao (sempre o menor). Savings = soma(base_col - v2b) onde v2b<base.
    print("\n=== Parte B: ganho ponderado por TABELA (V2-B como 3o candidato do fallback) ===")
    print(f"{'dataset':14s} {'cols':>4s} {'lowK':>4s} {'baseTbl':>9s} "
          f"{'savings':>8s} {'gain%':>6s}")
    print("-" * 56)
    g_base = g_sav = 0
    for label, path in DATASETS:
        if not path.exists():
            continue
        cols = load(path, ROWS)
        if not cols:
            continue
        base_tbl = nbytes(encode(cols))
        savings = 0
        lowk = 0
        for c, vals in cols.items():
            N = len(vals)
            K = len(set(vals))
            if K < 2 or K > MAXCARD or K >= N:
                continue
            lowk += 1
            base_col = min(nbytes(encode(vals)), nbytes("\n".join(vals)))
            v2b1, _, _, _ = v2b_size(vals, sort_it=False, rle=False)
            v2b2, _, _, _ = v2b_size(vals, sort_it=False, rle=True)
            best = min(v2b1, v2b2)
            if best < base_col:
                savings += base_col - best
        gain = 100 * savings / base_tbl if base_tbl else 0
        g_base += base_tbl
        g_sav += savings
        print(f"{label:14s} {len(cols):4d} {lowk:4d} {base_tbl:9d} "
              f"{savings:8d} {gain:5.1f}%")
    print("-" * 56)
    print(f"{'WEIGHTED':14s} {'':4s} {'':4s} {g_base:9d} {g_sav:8d} "
          f"{100*g_sav/g_base:5.1f}%")


if __name__ == "__main__":
    main()

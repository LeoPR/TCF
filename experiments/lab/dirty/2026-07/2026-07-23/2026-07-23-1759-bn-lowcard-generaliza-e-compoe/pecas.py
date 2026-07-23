"""Peças composíveis (lab-local) — bN generalizado: bool(w=1) e low-card(w=2/4/8).

KIT REUSÁVEL pros próximos estudos (owner 2026-07-23: "manter pros próximos pra ver se conversam").
Testa se as peças CONVERSAM: cardinalidade→largura `w` (bN) compõe com segmentação adaptativa por
regime. Reusa a IDEIA de bitpack.py (2026-07-07). NÃO toca src/tcf.

Contrato das peças (todas operam sobre `runs = [(idx,len)]` de ÍNDICES, produzido em 1 passe):
  build_and_scan(fonte) -> (domain, runs)   # 1 passe: domínio 1ª-aparição + runs de índice
  width_for(k) -> w                          # bN: k distintos -> bits/símbolo
  enc_dense/enc_rle/seg_adapt(runs, w)       # 3 modos de corpo; seg_adapt = adaptativo por regime
  dec_*(corpo, w, n) -> índices -> domain    # RT
"""
from __future__ import annotations

import base64
import math


class Fonte:
    """Fonte instrumentada — conta leituras (prova passe único)."""
    def __init__(self, seq):
        self.seq, self.reads = seq, 0

    def __len__(self):
        return len(self.seq)

    def __getitem__(self, i):
        self.reads += 1
        return self.seq[i]


def width_for(k):
    """bN: nº de símbolos distintos -> bits/símbolo. None se alta-card (bN não se aplica)."""
    if k <= 2:
        return 1
    if k <= 4:
        return 2
    if k <= 16:
        return 4
    if k <= 256:
        return 8
    return None


def b64_len(nbits):
    return math.ceil(math.ceil(nbits / 8) / 3) * 4


def build_and_scan(fonte):
    """UM passe: domínio (ordem de 1ª aparição) + runs de ÍNDICE. Cada elemento lido 1 vez."""
    domain, idx_of, runs = [], {}, []
    cur, L = None, 0
    for i in range(len(fonte)):
        v = fonte[i]
        if v not in idx_of:
            idx_of[v] = len(domain)
            domain.append(v)
        ix = idx_of[v]
        if cur is None:
            cur, L = ix, 1
        elif ix == cur:
            L += 1
        else:
            runs.append((cur, L))
            cur, L = ix, 1
    if L:
        runs.append((cur, L))
    return domain, runs


def runs_to_indices(runs):
    out = []
    for ix, L in runs:
        out.extend([ix] * L)
    return out


# ------------------------------------------------------------------ bit-packing largura-w (bN)
def pack_w(indices, w):
    bits = "".join(format(ix, f"0{w}b") for ix in indices)
    bits += "0" * ((-len(bits)) % 8)
    return bytes(int(bits[i:i + 8], 2) for i in range(0, len(bits), 8))


def unpack_w(data, w, n):
    ab = "".join(format(b, "08b") for b in data)
    return [int(ab[i * w:(i + 1) * w], 2) for i in range(n)]


# ------------------------------------------------------------------------------- 3 modos de corpo
def enc_dense(runs, w):
    return base64.b64encode(pack_w(runs_to_indices(runs), w)).decode("ascii")


def dec_dense(b64, w, n):
    return unpack_w(base64.b64decode(b64), w, n)


def enc_rle(runs):
    return ",".join(f"{ix}x{L}" for ix, L in runs)          # idx EXPLÍCITO (k>2 não alterna)


def dec_rle(s):
    out = []
    for part in s.split(","):
        ix, L = part.split("x")
        out.extend([int(ix)] * int(L))
    return out


def seg_adapt(runs, w):
    """Segmentação ADAPTATIVA por regime (greedy, 1 acumulador) — generalizada pra largura w.
    Fronteira ONDE o modo vira (não em S fixo). Cada segmento declara count -> auto-decodável."""
    segs, aberto = [], []
    for ix, L in runs:
        open_ct = sum(l for _, l in aberto)
        simbolico = 1 + len(str(L)) + 1 + len(str(ix))       # "R"+len+":"+idx
        marginal_d = b64_len((open_ct + L) * w) - b64_len(open_ct * w)
        if simbolico < marginal_d:
            if aberto:
                segs.append(_emit_D(aberto, w)); aberto = []
            segs.append(f"R{L}:{ix}")
        else:
            aberto.append((ix, L))
    if aberto:
        segs.append(_emit_D(aberto, w))
    return ";".join(segs)


def _emit_D(runs_acc, w):
    idx = runs_to_indices(runs_acc)
    return f"D{len(idx)}:{base64.b64encode(pack_w(idx, w)).decode('ascii')}"


def dec_seg_adapt(s, w):
    out = []
    for seg in s.split(";"):
        h, p = seg[0], seg[1:]
        if h == "R":
            L, ix = p.split(":")
            out.extend([int(ix)] * int(L))
        else:
            ct, b64 = p.split(":")
            out.extend(unpack_w(base64.b64decode(b64), w, int(ct)))
    return out


def domain_bytes(domain):
    """Custo de embutir o domínio (bN low-card precisa; bool tem domínio implícito)."""
    return len("\n".join(str(v) for v in domain).encode("utf-8"))

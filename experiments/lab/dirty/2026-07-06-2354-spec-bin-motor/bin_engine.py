"""bin_engine — motor da spec BINÁRIA com ESCAPE + overlay de exceções (owner 2026-07-06).

Ideia: NÃO precisa catálogo. Uma spec `spec_bin` com escape: os 2 valores mais comuns SÃO o domínio,
guardados uma vez (aproveitam o afixo do OBAT — `female`→`fe1` referenciando `male`). O resto vira
bit-stream (0=v0, 1=v1). O motor testa DUAS codificações de corpo e escolhe a menor:
 - RLE (textual, EXPLICÁVEL, mantém a quebra/grupos) — vence quando ordenado/contínuo;
 - bitstream empacotado (N/8, opaco) — vence quando aleatório.
Overlay de EXCEÇÕES: caso 99% male/female + raros null/other → domínio = os 2 dominantes; os raros vão
num canal esparso (posição, valor). Lossless. Não toca src/tcf.
"""
from __future__ import annotations
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))
from tcf import encode                                 # noqa: E402


def induce(values):
    """domínio = 2 mais comuns; frac de exceções = resto."""
    c = Counter(values)
    top = c.most_common(2)
    v0 = top[0][0]
    v1 = top[1][0] if len(top) > 1 else None
    covered = sum(n for _, n in top[:2])
    return (v0, v1), (1 - covered / len(values) if values else 0.0)


def encode_col(values):
    (v0, v1), exc_frac = induce(values)
    bits, exc = [], []
    for i, v in enumerate(values):
        if v == v0:
            bits.append("0")
        elif v == v1:
            bits.append("1")
        else:
            bits.append("0")                            # placeholder; valor real vai na overlay
            exc.append((i, v))
    return {"domain": (v0, v1), "bits": "".join(bits), "exc": exc, "exc_frac": exc_frac}


def decode_col(enc):
    v0, v1 = enc["domain"]
    out = [v1 if b == "1" else v0 for b in enc["bits"]]
    for i, v in enc["exc"]:
        out[i] = v
    return out


# ---- codificações de corpo (o motor testa e escolhe) ----
def rle_runs(bits):
    if not bits:
        return []
    runs, cur, cnt = [], bits[0], 1
    for b in bits[1:]:
        if b == cur:
            cnt += 1
        else:
            runs.append((cnt, cur)); cur, cnt = b, 1
    runs.append((cnt, cur))
    return runs


def rle_bytes(bits):
    """RLE textual '*N|s' por run — mantém a quebra/grupos visível (explicável)."""
    return sum(len(str(c)) + 3 for c, _ in rle_runs(bits))


def packed_bytes(bits):
    """bitstream empacotado (1 bit/valor) — opaco, binário."""
    return (len(bits) + 7) // 8


def textbits_bytes(bits):
    """bit-string '0/1' como corpo TCF (RLE interno pode ajudar se contíguo)."""
    return len(encode([bits]).encode()) if bits else 0


def domain_bytes(dom):
    vals = [v for v in dom if v is not None]
    return len(encode(vals).encode()) if vals else 0


def exc_bytes(exc):
    return len(encode([f"{i}:{v}" for i, v in exc]).encode()) if exc else 0


def best_body(bits):
    opts = {"rle": rle_bytes(bits), "packed": packed_bytes(bits), "textbits": textbits_bytes(bits)}
    win = min(opts, key=opts.get)
    return win, opts

"""bitpack — spec primitivo de TIPO por LARGURA DE BITS (owner 2026-07-07). Generaliza spec_bin.

k valores distintos → w bits/valor → 8/w linhas por byte:
  k<=2  → b   (1 bit,  8 linhas/byte)
  k<=4  → b2  (2 bits, 4 linhas/byte)
  k<=16 → b4  (4 bits, 2 linhas/byte)
  k<=256→ b8  (8 bits, 1 linha/byte)   ; >256 → b16 / fallback HCC.
O spec é `b<w>` + a LISTA do domínio EMBUTIDA (a lista É a referência: índice↔valor). O corpo = os
índices empacotados a w bits. O HCC-nativo (RLE de refs) é a alternativa p/ repetição/ordenado — pesa-se
os dois e escolhe o menor. Não toca src/tcf.
"""
from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))
from tcf import encode                                 # noqa: E402


def width_for(k: int) -> int:
    if k <= 1:
        return 0
    if k <= 2:
        return 1
    if k <= 4:
        return 2
    if k <= 16:
        return 4
    if k <= 256:
        return 8
    return 16


def spec_name(w: int) -> str:
    return {0: "b0", 1: "b", 2: "b2", 4: "b4", 8: "b8", 16: "b16"}.get(w, f"b{w}")


def rows_per_byte(w: int):
    return (8 // w) if w else None


def pack(indices, w: int) -> bytes:
    if w == 0:
        return b""
    bits = "".join(format(ix, f"0{w}b") for ix in indices)
    bits += "0" * ((-len(bits)) % 8)
    return bytes(int(bits[i:i + 8], 2) for i in range(0, len(bits), 8))


def unpack(data: bytes, w: int, n: int):
    if w == 0:
        return [0] * n
    allbits = "".join(format(b, "08b") for b in data)
    return [int(allbits[i * w:(i + 1) * w], 2) for i in range(n)]


def induce(values):
    dom = list(dict.fromkeys(values))                  # 1ª aparição
    return dom, width_for(len(dom))


def encode_col(values):
    dom, w = induce(values)
    idx = {v: i for i, v in enumerate(dom)}
    data = pack([idx[v] for v in values], w)
    return {"dom": dom, "w": w, "data": data, "n": len(values)}


def decode_col(enc):
    ix = unpack(enc["data"], enc["w"], enc["n"])
    return [enc["dom"][i] for i in ix]


def domain_bytes(dom) -> int:
    """domínio embutido no spec (afixo-comprimido pelo OBAT)."""
    return len(encode(dom).encode()) if dom else 0


def packed_total(enc) -> int:
    """corpo total = domínio (referência embutida) + índices empacotados."""
    return domain_bytes(enc["dom"]) + len(enc["data"])

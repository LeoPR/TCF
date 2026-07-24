"""bit-pack de w bits/símbolo -> bytes, para o modo DENSO bN do single-col tipado (weld #4b).

Empacota um stream de índices (0..2^w-1) em w bits cada, tile-de-byte. Usado pelo modo denso do
`#TCF.8<tag><modo><n>` (encoder/decoder): o corpo é base64 desse pack. Domínio implícito por tipo
(bool: false=0, true=1). Larguras 1/2/4/8 (o namespace do `<modo>`); só w=1 (bool) é exercido agora.

Implementação PURE-PYTHON e clara de propósito (o "mecanismo lógico bom") — a otimização de
velocidade (evitar a string-de-bits; bit-ops nativas / Cython / Rust) fica pro `.9`
(T-TYPED-SINGLECOL-MODE-HEURISTIC). Reusa a IDEIA de
`experiments/lab/dirty/2026-07/2026-07-07/2026-07-07-0028-spec-bitwidth-bN/bitpack.py`.
"""
from __future__ import annotations


def pack_w(indices: "list[int]", w: int) -> bytes:
    """Índices (0..2^w-1) -> bytes, w bits cada, MSB-first, padding de zeros no fim."""
    if w == 0:
        return b""
    bits = "".join(format(i, f"0{w}b") for i in indices)
    bits += "0" * ((-len(bits)) % 8)                       # padding p/ fechar o último byte
    return bytes(int(bits[i:i + 8], 2) for i in range(0, len(bits), 8))


def unpack_w(data: bytes, w: int, n: int) -> "list[int]":
    """bytes -> os primeiros `n` índices de w bits (descarta o padding). Espelho de pack_w."""
    if w == 0:
        return [0] * n
    allbits = "".join(format(b, "08b") for b in data)
    if len(allbits) < n * w:                               # payload curto p/ (n,w) -> fail-loud
        raise ValueError(f"payload denso curto: {len(data)} bytes nao cobrem {n} simbolos de {w} bits")
    return [int(allbits[i * w:(i + 1) * w], 2) for i in range(n)]

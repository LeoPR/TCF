"""V2-B dicionario/categorico (ADR-0025) — candidato de coluna low-card.

Coluna low-card -> [tabela de unicos: encode(unicas)] + [stream de indices].
Alfabeto printable 0x21..0x7E (94 chars, exclui '\\n'): K<=94 -> 1 char/linha.
Marcador '@<size>=<name>' no header #TCF.7 (ao lado de '!' raw e tcf normal).
Slot = b"<ntable>\\n" + table_bytes + stream  (ntable = bytes da tabela ->
fronteira inequivoca; width derivado de K apos decodar a tabela).

Concern isolado de `multi.core` (P1 modularizacao, 2026-06-24). Byte-identico.
"""
from __future__ import annotations

from tcf.encoder import _encode_column
from tcf.pipeline import PipelineConfig

_V2B_ALPHA = "".join(chr(c) for c in range(0x21, 0x7F))
_V2B_BASE = len(_V2B_ALPHA)
_V2B_MAX_CARD = 1024  # gating: acima disso V2-B nao compensa (evita custo)


def _v2b_width(k: int) -> int:
    """chars por indice no alfabeto base-94 (minimo w com base^w >= k)."""
    w, cap = 1, _V2B_BASE
    while k > cap:
        w += 1
        cap *= _V2B_BASE
    return w


def _v2b_idx_chars(idx: int, width: int) -> str:
    """indice inteiro -> `width` chars base-94 (big-endian)."""
    if width == 1:
        return _V2B_ALPHA[idx]
    out = []
    for _ in range(width):
        out.append(_V2B_ALPHA[idx % _V2B_BASE])
        idx //= _V2B_BASE
    return "".join(reversed(out))


def _v2b_encode(values: list[str], *, cfg: PipelineConfig,
                min_len: int | None) -> bytes | None:
    """Candidato V2-B. Retorna body bytes, ou None se nao aplicavel (high-card
    ou sem repeticao). Caller escolhe min(tcf, raw, v2b) no fallback."""
    seen: dict[str, int] = {}
    unicas: list[str] = []
    for v in values:
        if v not in seen:
            seen[v] = len(unicas)
            unicas.append(v)
            if len(unicas) > _V2B_MAX_CARD:
                return None  # high-card -> V2-B improvavel, evita o sub-encode
    K = len(unicas)
    N = len(values)
    if K < 2 or K >= N:
        return None  # sem repeticao -> nada a ganhar
    width = _v2b_width(K)
    table_bytes = _encode_column(unicas, header="val", cfg=cfg,
                                 min_len=min_len).encode("utf-8")
    stream = "".join(_v2b_idx_chars(seen[v], width) for v in values)
    return f"{len(table_bytes)}\n".encode("utf-8") + table_bytes + stream.encode("utf-8")


def _decode_v2b(body_bytes: bytes) -> list[str]:
    """Decoda slot V2-B: <ntable>\\n + table + stream -> lista de valores."""
    from tcf.decoder import _decode_column

    nl = body_bytes.find(b"\n")
    ntable = int(body_bytes[:nl])
    start = nl + 1
    unicas = _decode_column(body_bytes[start:start + ntable].decode("utf-8"))
    width = _v2b_width(len(unicas))
    stream = body_bytes[start + ntable:]  # ASCII, len == N*width
    out: list[str] = []
    for j in range(0, len(stream), width):
        idx = 0
        for ch in stream[j:j + width]:  # ch e' int (byte)
            idx = idx * _V2B_BASE + (ch - 0x21)
        out.append(unicas[idx])
    return out

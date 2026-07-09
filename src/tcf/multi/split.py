"""Split estrutural (ADR-0026, H-STRUCT-01) — candidato de coluna estruturada.

Valor estruturado (decimal, data, datetime, CPF/CNPJ) = grupos de DIGITOS
separados por NAO-digitos. Se TODOS os valores tem o MESMO template (mesmos
separadores, mesma contagem de campos), os grupos de digito viram colunas-campo
e o template e' guardado 1x. Cada campo tende a low-card -> esmagado pelo V2-B
(sinergia, o motor do ganho). Marcador `%<size>=<name>` no header #TCF.8M.
Slot = <ntmpl>\\n + template_blob + field_subtable(#TCF.8M — recursa em _encode_multi).
  template_blob = (<bytelen>:<bytes>) por parte nao-digito (nf+1 partes).

Concern isolado de `multi.core` (P1 modularizacao, 2026-06-24). Byte-identico.
O split reusa o pipeline multi-col (`_encode_multi`/`_decode_multi` de `multi.core`)
nos campos -> import LAZY (dentro das funcoes) pra quebrar o ciclo core<->split.
"""
from __future__ import annotations

import re

from tcf.pipeline import PipelineConfig

_DIGITS = re.compile(r"(\d+)")


def _struct_split_encode(values: list[str], *, cfg: PipelineConfig,
                         min_len: int | None) -> bytes | None:
    """Candidato split estrutural. Retorna body bytes, ou None se nao aplicavel
    (template nao-uniforme, <2 campos, ou campos todos constantes)."""
    from tcf.multi.core import _encode_multi  # lazy: quebra ciclo core<->split

    if len(values) < 2:
        return None
    toks0 = _DIGITS.split(values[0])
    nf = len(toks0) // 2
    if nf < 2:
        return None  # <2 campos de digito -> nada a ganhar com split
    sig = tuple(toks0[::2])  # nf+1 partes nao-digito (o template)
    all_toks = [toks0]
    for v in values[1:]:
        t = _DIGITS.split(v)
        if len(t) // 2 != nf or tuple(t[::2]) != sig:
            return None  # template NAO-uniforme -> nao splita (gate 100%)
        all_toks.append(t)
    fields = [[t[1 + 2 * fi] for t in all_toks] for fi in range(nf)]
    if all(len(set(f)) <= 1 for f in fields):
        return None  # sem variacao real -> dedup/OBAT ja' cobre
    # sub-table de campos -> reusa o pipeline multi-col (-> V2-B nos campos low-card).
    # Campos sao digitos puros -> _struct_split_encode neles retorna None (sem recursao).
    sub_bytes = _encode_multi(
        {f"c{i}": f for i, f in enumerate(fields)}, cfg=cfg, min_len=min_len
    ).encode("utf-8")
    tmpl_blob = b"".join(
        str(len(pb)).encode() + b":" + pb
        for p in sig for pb in (p.encode("utf-8"),)
    )
    return str(len(tmpl_blob)).encode() + b"\n" + tmpl_blob + sub_bytes


def _decode_struct_split(body_bytes: bytes) -> list[str]:
    """Decoda slot split estrutural: template + sub-table de campos -> valores."""
    from tcf.multi.core import _decode_multi  # lazy: quebra ciclo core<->split

    nl = body_bytes.find(b"\n")
    ntmpl = int(body_bytes[:nl])
    start = nl + 1
    tmpl_blob = body_bytes[start:start + ntmpl]
    sub = body_bytes[start + ntmpl:]
    parts: list[str] = []
    i = 0
    while i < len(tmpl_blob):
        c = tmpl_blob.find(b":", i)
        L = int(tmpl_blob[i:c])
        i = c + 1
        parts.append(tmpl_blob[i:i + L].decode("utf-8"))
        i += L
    nf = len(parts) - 1
    ftable = _decode_multi(sub.decode("utf-8"))
    fields = [ftable[f"c{k}"] for k in range(nf)]
    nrows = len(fields[0]) if fields else 0
    out = []
    for r in range(nrows):
        out.append("".join(parts[k] + fields[k][r] for k in range(nf)) + parts[nf])
    return out

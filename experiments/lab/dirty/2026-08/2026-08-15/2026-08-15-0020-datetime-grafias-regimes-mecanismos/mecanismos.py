# -*- coding: utf-8 -*-
"""Os mecanismos de compressão do TCF, medidos ISOLADOS contra datetime.

O `encode()` público devolve só o VENCEDOR. Para ver o comportamento — que é o que o owner
pediu — cada candidato é invocado à parte, e o wire de cada um é gravado.

**Nada aqui modifica `src/tcf`.** Todos os candidatos são funções já existentes, chamadas por
import; o lab só os expõe lado a lado.

| mecanismo | de onde vem | o que explora |
|---|---|---|
| `core` | `encode(list)` | OBAT (afixos) + HCC + polaridade + RLE de linha + seq-RLE |
| `bN` | `composicional.dominio_bn.candidatos` | cardinalidade ≤ 256 (bit-pack + domínio) |
| `raw` | `"\\n".join` | o piso: sem transformação nenhuma |
| `dict` | `multi.dict_v2b._v2b_encode` | dicionário de valores repetidos |
| `split` | `multi.split._struct_split_encode` | **os campos** — o alvo do datetime |
| `multi` | `encode({"c": vals})` | o `_best_of` = `min(tcf, raw, dict, split)` |

E as TRANSFORMAÇÕES que hoje não são automáticas (o dev teria de fazer à mão):

| transformação | o que faz |
|---|---|
| `epoch-s` | o instante vira **um** inteiro |
| `separado` | 2 colunas: data (com `:dt`) + hora em segundos |
| `campos-6` | 6 colunas: ano, mês, dia, hora, min, seg — o split feito à mão |
"""
from __future__ import annotations

import base64
from datetime import datetime

from tcf import decode, encode
from tcf.composicional.dominio_bn import candidatos as _bn_cands
from tcf.multi.core import DEFAULT_PIPELINE, _encode_multi
from tcf.multi.dict_v2b import _v2b_encode
from tcf.multi.split import _struct_split_encode
from tcf.natures import SPEC_DATA_ISO, encode_value


def B(t):
    return len(t.encode("utf-8")) if isinstance(t, str) else len(t)


def _enc_col(vs):
    from tcf.encoder import _encode_column
    return _encode_column(vs, header="val", cfg=DEFAULT_PIPELINE)


# ── os candidatos ISOLADOS ───────────────────────────────────────────────────
def m_core(vals):
    """O que o `encode()` público devolve para a lista — o núcleo escolhendo sozinho."""
    w = encode(vals)
    return w, decode(w) == vals, w.split("\n")[0]


def m_raw(vals):
    """O piso: as linhas sem transformação nenhuma."""
    return "\n".join(vals), True, "(raw)"


def m_bn(vals):
    """bN de domínio — só existe se a cardinalidade couber em 8 bits (k ≤ 256)."""
    c = _bn_cands(vals, _enc_col, None)
    if not c:
        return None, None, "(nao qualifica: k > 256)"
    return c[0], None, c[0].split("\n")[0]


def m_dict(vals):
    """Dicionário V2-B — valores repetidos viram índices."""
    b = _v2b_encode(vals, cfg=DEFAULT_PIPELINE, min_len=None)
    return (b.decode("utf-8", "replace") if b else None), None, "(dict)" if b else "(nao aplica)"


def m_split(vals):
    """Split estrutural `%` — os grupos de dígito viram colunas-campo. O alvo do datetime."""
    b = _struct_split_encode(vals, cfg=DEFAULT_PIPELINE, min_len=None)
    return (b.decode("utf-8", "replace") if b else None), None, \
           "(split)" if b else "(nao aplica: template nao-uniforme ou <2 campos)"


def m_multi(vals):
    """`encode({"c": vals})` — o `_best_of` = min(tcf, raw, dict, split), COM RT público."""
    w = encode({"c": vals})
    return w, decode(w) == {"c": vals}, w.split("\n")[0][:40]


# ── as TRANSFORMAÇÕES (o dev faria à mão hoje) ──────────────────────────────
_FMT = {
    "g01-sql-espaco": "%Y-%m-%d %H:%M:%S", "g02-iso-t": "%Y-%m-%dT%H:%M:%S",
    "g07-sem-segundo": "%Y-%m-%d %H:%M", "g08-compacta": "%Y%m%d%H%M%S",
    "g09-iso-basica": "%Y%m%dT%H%M%S", "g10-br": "%d/%m/%Y %H:%M:%S",
}


def _parse(vals, grafia):
    """Devolve datetimes, ou None se a grafia não tiver parser trivial aqui."""
    f = _FMT.get(grafia)
    if not f:
        return None
    try:
        return [datetime.strptime(v, f) for v in vals]
    except Exception:
        return None


def t_epoch(vals, grafia):
    """O instante vira UM inteiro (segundos desde a época)."""
    ds = _parse(vals, grafia)
    if ds is None:
        return None, None, "(sem parser)"
    segs = [str(int(d.timestamp())) for d in ds]
    w = encode(segs)
    return w, decode(w) == segs, w.split("\n")[0]


def t_separado(vals, grafia):
    """2 colunas: a data com o spec `:dt` + a hora em segundos desde meia-noite."""
    ds = _parse(vals, grafia)
    if ds is None:
        return None, None, "(sem parser)"
    datas = [d.strftime("%Y-%m-%d") for d in ds]
    horas = [str(d.hour * 3600 + d.minute * 60 + d.second) for d in ds]
    w_d = encode(datas, nature=SPEC_DATA_ISO)
    w_h = encode(horas)
    junto = w_d + "\n" + w_h
    ok = decode(w_d, nature=SPEC_DATA_ISO) == datas and decode(w_h) == horas
    return junto, ok, w_d.split("\n")[0]


def t_campos6(vals, grafia):
    """6 colunas de campo (ano, mês, dia, hora, min, seg) — o split feito à mão."""
    ds = _parse(vals, grafia)
    if ds is None:
        return None, None, "(sem parser)"
    cols = {
        "a": [f"{d.year}" for d in ds], "m": [f"{d.month:02d}" for d in ds],
        "d": [f"{d.day:02d}" for d in ds], "H": [f"{d.hour:02d}" for d in ds],
        "M": [f"{d.minute:02d}" for d in ds], "S": [f"{d.second:02d}" for d in ds],
    }
    w = _encode_multi(cols, cfg=DEFAULT_PIPELINE)
    return w, decode(w) == cols, w.split("\n")[0][:44]


CANDIDATOS = [("core", m_core), ("raw", m_raw), ("bN", m_bn),
              ("dict", m_dict), ("split", m_split), ("multi(_best_of)", m_multi)]
TRANSFORMACOES = [("epoch-s", t_epoch), ("separado", t_separado), ("campos-6", t_campos6)]

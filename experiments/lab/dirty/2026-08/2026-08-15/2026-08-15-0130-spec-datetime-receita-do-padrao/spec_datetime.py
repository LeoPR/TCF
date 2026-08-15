# -*- coding: utf-8 -*-
"""Protótipo do spec de DATETIME — a receita do `data_iso`, aplicada.

**Engenhoca de dirty lab: para jogar fora.** Sobrevive a IDEIA, nunca o código.
**Nada aqui toca `src/tcf`.**

## A decisão do owner que fixou o desenho (2026-08-15)

> *"o datetime pode entrar no mesmo esquema do date e do time, ou seja, eles são
> **pré-formatados ou padronizados** para entrar no tcf; aí formatos variantes podem ser
> tratados como **string**. Como sabemos que não tem um tipo nativo de relógio (tirando
> timestamp, que é praticamente um inteiro), então é justo pensar que o dataset interno de uma
> linguagem ao entrar no tcf seja um **string com semântica forte**, principalmente se foi
> **confiado** isso. Só seguir a receita de padrão."*

Isso elimina o problema das 13 grafias que o lab `…-0020` mediu: **uma canônica, o resto é
string**. É literalmente o que o `data_iso.py` já declara:

> *"Nenhum adivinhador de formato. Este spec lê UMA grafia — a que o mundo já emite por
> default. Outras grafias, se vierem, são specs nomeados irmãos."*

## A RESTRIÇÃO que decide tudo

O contrato de nature é `encode_value(v) -> (payload, status)`: **um valor, um payload**. Um
spec **não pode** partir a coluna em campos — isso é o `split`, que é multi-col. Então a única
pergunta de desenho é: **qual string o payload deve ser?**

Três candidatos, medidos no `run.py`:

| payload | forma | tamanho | por quê |
|---|---|---|---|
| `ordinal` | `dia_ordinal · 86400 + seg_do_dia` | ~11 díg. | a extensão direta do `data_iso` |
| `epoch` | segundos desde 1970, **calculado dos campos** | ~10 díg. | 1 dígito a menos |
| `par` | `dia_ordinal:seg_do_dia` | ~12 chars | **2 grupos** — deixa as duas aritméticas visíveis |

## Por que NÃO usar `datetime.timestamp()`

Ele depende do **fuso local** e do horário de verão — o mesmo texto daria inteiros diferentes
em máquinas diferentes, e o round-trip quebraria fora da máquina que gravou. Os três payloads
acima são calculados **dos campos do calendário**, como o `data_iso` faz com `toordinal()`.
"""
from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass

from tcf.natures import MARKER_LITERAL

_EPOCH_ORD = _dt.date(1970, 1, 1).toordinal()        # 719163
PAYLOADS = ("ordinal", "epoch", "par")


@dataclass(frozen=True)
class DatetimeIsoSpec:
    """Uma grafia, um payload. Sem adivinhação, sem parâmetro que precise viajar.

    `sep` e `payload` são variantes **do laboratório**, para medir a escolha. O spec real
    congelaria uma de cada, como o `data_iso` congelou `YYYY-MM-DD`.
    """

    sep: str = " "                       # " " (SQL) ou "T" (ISO/JSON)
    payload: str = "ordinal"
    name: str = "datetime-iso"
    wire_id: str = "dtm"                 # reservado no ADR-0041, sem dono

    def __post_init__(self):
        if self.sep not in (" ", "T"):
            raise ValueError(f"sep deve ser ' ' ou 'T'; got {self.sep!r}")
        if self.payload not in PAYLOADS:
            raise ValueError(f"payload deve ser um de {PAYLOADS}; got {self.payload!r}")

    # ── classificação — a MESMA ordem de gates do `data_iso` ─────────────────
    def classify_value(self, v: str) -> str:
        if not v:
            return "empty_value"
        if len(v) != 19:
            # Gate barato ANTES do parse, como `data_iso.py:82`. Pega de graça:
            # `20260302082600` (14), `2026-03-02T08:26:00Z` (20), `.ffffff` (26),
            # `2026-3-2 8:26:00` (16), `02/03/2026 08:26:00` (19 — passa aqui e morre
            # no parse), epoch (10).
            return "length_wrong"
        try:
            d = _dt.datetime.fromisoformat(v)
        except (ValueError, TypeError):
            return "format_mismatch"
        # CANONICIDADE POR RE-EMISSÃO — a lei do projeto (5 aplicações soldadas).
        # `fromisoformat` aceita MAIS do que `isoformat` emite; sem isto, duas grafias
        # colapsariam no mesmo inteiro e só uma voltaria.
        if d.isoformat(sep=self.sep) != v:
            return "format_noncanonical"
        return "compressible"

    # ── transformação ───────────────────────────────────────────────────────
    def encode_value(self, v: str) -> "tuple[str, str]":
        status = self.classify_value(v)
        if status != "compressible":
            return MARKER_LITERAL + v, status
        d = _dt.datetime.fromisoformat(v)
        ordinal = d.date().toordinal()
        segs = d.hour * 3600 + d.minute * 60 + d.second
        if self.payload == "ordinal":
            return str(ordinal * 86400 + segs), status
        if self.payload == "epoch":
            return str((ordinal - _EPOCH_ORD) * 86400 + segs), status
        return f"{ordinal}:{segs}", status            # "par"

    def decode_value(self, payload: str) -> str:
        if payload.startswith(MARKER_LITERAL):
            return payload[1:]
        if self.payload == "par":
            o_s, s_s = payload.split(":")
            ordinal, segs = int(o_s), int(s_s)
        else:
            n = int(payload)
            ordinal, segs = divmod(n, 86400)
            if self.payload == "epoch":
                ordinal += _EPOCH_ORD
        d = _dt.datetime.combine(
            _dt.date.fromordinal(ordinal),
            _dt.time(segs // 3600, (segs % 3600) // 60, segs % 60))
        return d.isoformat(sep=self.sep)


# as 6 variantes que o lab compara (2 separadores × 3 payloads)
VARIANTES = [
    (f"{'espaco' if sep == ' ' else 'T'}-{pl}", DatetimeIsoSpec(sep=sep, payload=pl))
    for sep in (" ", "T") for pl in PAYLOADS
]

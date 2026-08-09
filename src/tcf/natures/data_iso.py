"""DataIsoSpec — data `YYYY-MM-DD` -> ordinal decimal. Categoria TCU-Delta.

Weld T-DATA-LAZY-ISO (2026-08-08). Implementa o mesmo Protocol das outras natures
(`classify_value` / `encode_value` / `decode_value`), entao o encoder segue polimorfico.

## Por que ordinal DECIMAL, e nao denso como o CPF

O CPF transforma pra BASE94 denso porque CPF nao vem em sequencia — o que paga la' e'
densidade. Data e' o oposto: a forma que rende e' a que deixa a **aritmetica visivel**, pra o
`*N+M|` do seq-RLE (ADR-0016) enxergar a progressao. Medido (lab 2026-08-07-2311):

    600 datas diarias, ISO       ->  414 B
    600 datas diarias, ordinal   ->   22 B    `#TCF.8\\n*600+1|\\739617`
    600 datas mensais, ISO       -> 6338 B
    600 datas mensais, ordinal   ->   23 B

O passo nem importa: pro seq-RLE, +1, +7 e +30 dao o mesmo trabalho. Pra grafia ISO, nao —
`2026-01-31` -> `2026-02-01` nao e' "+1" em campo nenhum isolado, e o ganho despenca com a
irregularidade do passo.

## Por que `fromisoformat`, e nao `strptime`

Medido com o lookup hoistado, guard incluido, coluna de 1000, contra o custo do encode que
esta funcao acompanha:

    fromisoformat + guard    ~3,2% do encode
    strptime      + guard   ~52,8% do encode      (16x mais caro)

`date.fromisoformat` e' implementado em C e custa o mesmo que olhar 3 caracteres.

## A ressalva que obriga o guard de re-emissao

Desde a 3.11 o `fromisoformat` **aceita mais do que emite**: `20191204` e `2021-W01-1`
entram e voltam como `2019-12-04` e `2021-01-04`. Aceitar isso quebraria o RT byte-exato —
duas grafias colapsariam no mesmo ordinal e so' uma voltaria. O guard e' a mesma tecnica de
canonicidade por re-emissao ja' usada no cabecalho do bN e na grafia numerica do `#TCF.8n`:
**re-emite e compara; se diferiu, e' literal.**

## O que NAO esta aqui, de proposito

Nenhum adivinhador de formato. Este spec le' UMA grafia — a que o mundo ja' emite por default
(RFC 3339 `full-date`; ver `docs/how-to/normalizar-data-antes-do-tcf.md`). Outras grafias, se
vierem, sao specs nomeados irmaos — precedente CPF/CNPJ, um objeto por grafia.
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass

from tcf.natures.templated_checked import MARKER_LITERAL

#: Hoistado de proposito: e' chamado uma vez por VALOR, e a busca de atributo no laco
#: aparece na medicao.
_FROM_ISO = _dt.date.fromisoformat
_FROM_ORD = _dt.date.fromordinal

#: `YYYY-MM-DD` = 10 chars. Descarte barato antes de pagar o parse.
_LARGURA_ISO = 10


@dataclass(frozen=True)
class DataIsoSpec:
    """Data em `YYYY-MM-DD` -> ordinal proleptico gregoriano, em decimal."""

    name: str = "data-iso"

    # ── classificacao ────────────────────────────────────────────────────────
    def classify_value(self, v: str) -> str:
        """`'compressible'` ou o motivo de nao ser. Mesmo vocabulario das outras natures."""
        if not v:
            return "empty_value"
        if len(v) != _LARGURA_ISO:
            # Pega de graca: `20260131`, `2026-1-1`, `+10000-12-31`, `2026-01-31Z`,
            # `2026-01-31+02:00`, `31-JAN-26`. Descarta antes de pagar o parse.
            return "length_wrong"
        try:
            d = _FROM_ISO(v)
        except (ValueError, TypeError):
            return "format_mismatch"
        # CANONICIDADE POR RE-EMISSAO — o guard que o `fromisoformat` obriga (ver docstring
        # do modulo). Sem ele, duas grafias colapsariam no mesmo ordinal e o RT quebraria.
        if d.isoformat() != v:
            return "format_noncanonical"
        return "compressible"

    # ── transformacao ────────────────────────────────────────────────────────
    def encode_value(self, v: str) -> "tuple[str, str]":
        status = self.classify_value(v)
        if status != "compressible":
            return MARKER_LITERAL + v, status
        return str(_FROM_ISO(v).toordinal()), status

    def decode_value(self, payload: str) -> str:
        if payload.startswith(MARKER_LITERAL):
            return payload[1:]
        try:
            return _FROM_ORD(int(payload)).isoformat()
        except (ValueError, OverflowError) as e:
            # Fail-loud: o encoder canonico so' emite ordinal valido ou literal marcado.
            # Payload fora disso e' wire que este spec nunca produziu.
            raise ValueError(
                f"#TCF.8 :{self.name}: payload {payload[:16]!r} nao e' ordinal de data "
                f"valido nem literal marcado — corpo nao-canonico"
            ) from e


SPEC_DATA_ISO = DataIsoSpec()

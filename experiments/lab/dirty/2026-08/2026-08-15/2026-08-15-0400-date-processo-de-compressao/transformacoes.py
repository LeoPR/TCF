# -*- coding: utf-8 -*-
"""As transformações de coluna para DATE — todas no mesmo lugar, para competirem juntas.

**Engenhoca de dirty lab: para jogar fora.** `src/tcf` intocado.

## O enquadramento (owner, 2026-08-15)

> *"o core do tcf vai tratar a data de outra forma, **com permissão de transformação se isso
> significa obter compressões melhores**, e isso **não se mistura com a entrada e saída**…
> a gente vê o formato mais comum e se sustenta nele pra ver o processo de compressão primeiro."*

Então: **grafia de entrada FIXA** (`YYYY-MM-DD`, já welded) e o core livre para transformar.
Cada transformação abaixo é uma leitura diferente da MESMA coluna.

## Por que transformação de COLUNA, e não de valor

O `data_iso` é per-valor (`encode_value(v)`), e por isso o ordinal é a única coisa que ele
consegue emitir. Uma transformação de **coluna** vê os vizinhos — e é aí que mora delta,
delta-of-delta e período. É o que o `T-DATA-ALVO-DELTA` chama de *"protocolo da nature:
transform de coluna"*, ainda **aguardando decisão de design**.

## O contrato de cada uma

`(datas: list[str]) -> list[str] | None` — a lista transformada (que vai ao `encode`), ou
`None` se não se aplica. E a inversa, para o RT.
"""
from __future__ import annotations

import datetime as _dt

_ORD = _dt.date.fromisoformat
_DE_ORD = _dt.date.fromordinal


def _ords(datas):
    """Ordinais, ou None se alguma não for a grafia canônica (o gate do `data_iso`)."""
    fora = []
    for v in datas:
        if v is None or len(v) != 10:
            return None
        try:
            d = _ORD(v)
        except ValueError:
            return None
        if d.isoformat() != v:                 # canonicidade por re-emissão — a lei
            return None
        fora.append(d.toordinal())
    return fora


# ── T0 · núcleo puro (a linha de base) ──────────────────────────────────────
def t_nucleo(datas):
    return list(datas)


def i_nucleo(vals):
    return list(vals)


# ── T1 · ordinal (o que o `data_iso` emite hoje — WELDED) ───────────────────
def t_ordinal(datas):
    o = _ords(datas)
    return None if o is None else [str(x) for x in o]


def i_ordinal(vals):
    return [_DE_ORD(int(v)).isoformat() for v in vals]


# ── T2 · delta de coluna (medido em 2026-08-09, NÃO soldado) ────────────────
def t_delta(datas):
    """`[1º ordinal, d1, d2, …]` — o 1º verbatim, o resto são diferenças."""
    o = _ords(datas)
    if o is None or len(o) < 2:
        return None
    return [str(o[0])] + [str(o[i] - o[i - 1]) for i in range(1, len(o))]


def i_delta(vals):
    cur = int(vals[0])
    fora = [_DE_ORD(cur).isoformat()]
    for v in vals[1:]:
        cur += int(v)
        fora.append(_DE_ORD(cur).isoformat())
    return fora


# ── T3 · delta-of-delta (o BURACO: nunca medido neste projeto) ──────────────
def t_delta2(datas):
    """`[1º ordinal, 1º delta, dd1, dd2, …]` — a 2ª diferença.

    É o candidato clássico de série temporal (Gorilla/Facebook usa a mesma ideia sobre
    timestamps). O registry do projeto mede delta de coluna e delta cíclico, mas **nunca a
    segunda diferença** — este é o primeiro.
    """
    o = _ords(datas)
    if o is None or len(o) < 3:
        return None
    d = [o[i] - o[i - 1] for i in range(1, len(o))]
    return [str(o[0]), str(d[0])] + [str(d[i] - d[i - 1]) for i in range(1, len(d))]


def i_delta2(vals):
    o0, d0 = int(vals[0]), int(vals[1])
    deltas = [d0]
    for v in vals[2:]:
        deltas.append(deltas[-1] + int(v))
    cur = o0
    fora = [_DE_ORD(cur).isoformat()]
    for dd in deltas:
        cur += dd
        fora.append(_DE_ORD(cur).isoformat())
    return fora


# ── T4 · componentes (o split feito à mão, como 3 colunas concatenadas) ─────
def t_componentes(datas):
    """Ano, mês e dia como três blocos — o que o `split` faz, mas visível no single-col.

    Não é o split do formato (que é multi-col embutido): é a MESMA ideia numa lista só,
    para medir se a separação por campo ajuda a compressão nesta rota.
    """
    o = _ords(datas)
    if o is None:
        return None
    ds = [_DE_ORD(x) for x in o]
    return ([f"{d.year}" for d in ds] + [f"{d.month:02d}" for d in ds]
            + [f"{d.day:02d}" for d in ds])


def i_componentes(vals):
    n = len(vals) // 3
    a, m, d = vals[:n], vals[n:2 * n], vals[2 * n:]
    return [f"{int(x):04d}-{y}-{z}" for x, y, z in zip(a, m, d)]


# ── T5 · ordinal RELATIVO ao primeiro (a base sai do número) ────────────────
def t_ordinal_rel(datas):
    """`[1º ordinal, o1-o0, o2-o0, …]` — todos relativos ao primeiro, não ao anterior.

    Diferente do delta: aqui os números CRESCEM, mas ficam pequenos. Testa a hipótese do
    `T-OBAT-COME-O-SEQRLE`: menos dígitos invariantes = mais chance de o seq-RLE agir.
    """
    o = _ords(datas)
    if o is None or len(o) < 2:
        return None
    return [str(o[0])] + [str(x - o[0]) for x in o[1:]]


def i_ordinal_rel(vals):
    base = int(vals[0])
    return [_DE_ORD(base).isoformat()] + [_DE_ORD(base + int(v)).isoformat()
                                          for v in vals[1:]]


TRANSFORMACOES = [
    ("nucleo", t_nucleo, i_nucleo, "a grafia crua — a linha de base"),
    ("ordinal", t_ordinal, i_ordinal, "dias desde 0001-01-01 — **o que o `data_iso` emite** (welded)"),
    ("ordinal-rel", t_ordinal_rel, i_ordinal_rel, "relativo ao 1º — menos dígitos invariantes"),
    ("delta", t_delta, i_delta, "1ª diferença — medido 2026-08-09, não soldado"),
    ("delta2", t_delta2, i_delta2, "**2ª diferença — NUNCA medida neste projeto**"),
    ("componentes", t_componentes, i_componentes, "ano|mês|dia — a ideia do split, no single-col"),
]

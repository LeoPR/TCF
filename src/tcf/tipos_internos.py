"""Tipos internos — FONTE UNICA das tabelas congeladas de slots (mapa de tipos interno).

Hoje a única família congelada é a bool (ADR-0037 denso b2 · ADR-0038 índice default no
core). Este módulo declara essas tabelas **como DADOS** — tabelas nomeadas, não literais
espalhados pelo encoder/decoder — pra que a externalização futura do mapa (decisão do
owner, T-TIPOS-CONFORTO-MAP) troque a FONTE sem tocar nos consumidores.

## A tabela congelada bool

    0 = null     pré-alocado em TODO o formato (slot 0, ADR-0036)
    1 = false
    2 = true
    3 = RESERVADO (padding natural do b2 a 2 bits; fail-loud no decode)
    4..13 = livres
    14/15 = EARMARK documentado do owner ("tipos de conforto de formulário", ex.
            masculino/feminino) — INATIVO, aguardando o design do mapa
            (T-TIPOS-CONFORTO-MAP)

## Wire-sketch do owner (2026-08-01, verbatim — REGISTRO de direção, NÃO implementado)

    com true/false/null e afins
    #TCF.8b264
    FVRVUVVFVSqoqqKqiqoqqKqiqoqqKqiqog==

    mas se for Masculino/Feminino onde 14 e 15 são tipos de conforto interno:
    #TCF.8b264
    \14
    \15
    FVRVUVVFVSqoqqKqiqoqqKqiqoqqKqiqog==

## Fronteiras

- O `.8H` tem **definition mask própria** (`hierarchical.py`) — não consome estas tabelas.
- O slot 0 do `dominio_bn` (rota flat, ADR-0036) é convenção SEPARADA — mesmo valor (`0`),
  origem distinta; este módulo cobre a rota TIPADA.

## Aviso

**NÃO adicionar tipos aqui sem a decisão do mapa (T-TIPOS-CONFORTO-MAP).** Tipo interno é
CONTRATO DE FORMATO: uma vez emitido, vira grafia canônica congelada.
"""
from __future__ import annotations

SLOT_NULL = 0                                          # pré-alocado em todo o formato (ADR-0036)
SLOT_FALSE = 1
SLOT_TRUE = 2
# 3 = RESERVADO (fail-loud) · 4..13 livres · 14/15 = EARMARK do owner, INATIVO (ver docstring)

# Densos (índice -> valor): w=1 bool puro, w=2 ternário (ADR-0037)
TABELA_B1 = (False, True)
TABELA_B2 = (None, False, True)

# Core tipado (ADR-0038): valor -> literal emitido (grafica canônica, ÚNICA emitida)
RENDER_B = {False: "1", True: "2"}

# Cast no decode: slots (canônico) + nomes (decodável-NÃO-emitido; wires legados e futuro
# opt-in legível T-TIPADO-LEGIVEL-PARAM — mesmo contrato do modo `C`, ADR-0036)
CAST_B = {"1": False, "2": True, "false": False, "true": True}

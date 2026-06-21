# 0026 — Split estrutural welded (#TCF.7, marcador `%`)

**Status**: accepted
**Date**: 2026-06-14
**Deciders**: project owner
**Tags**: v2.0, format, structural-split, decimal, datetime, multi-column, #TCF.7

## Context and Problem Statement

Investigando por que colunas DATETIME ganhavam no V2-D (refutado), descobriu-se
um efeito muito maior e geral: **valor estruturado** (decimal, data, datetime,
CPF/CNPJ) e' uma sequencia de grupos de DIGITOS separados por NAO-digitos. Se
TODOS os valores compartilham o MESMO template, os grupos de digito viram
colunas-campo independentes, e cada campo tende a low-card (fracao `.00`-`.99`,
mes 1-12, ano quase-constante) -> **esmagado pelo V2-B** ([ADR-0025](0025-v2b-dictionary-categorical-weld.md)).
A sinergia split->V2-B e' o motor.

Caracterizado no lab [`2026-06-14-datetime-nature-caracterizacao`](../../experiments/lab/dirty/old/welded/2026-06-14-datetime-nature-caracterizacao/result.md):
8 datasets reais, RT OK. **19.39% weighted** (50.4% nas colunas afetadas) — o
maior lever do ciclo 0.7, maior que o V2-B isolado (13.9%). Refinamento
([refine_result.md](../../experiments/lab/dirty/old/welded/2026-06-14-datetime-nature-caracterizacao/refine_result.md))
respondeu as perguntas de desenho: gate uniforme basta (1 near-miss em 80
colunas -> sem mecanismo de excecao); complementa as natures CPF/CNPJ (nenhum
subsume); bordas seguras (mistura cai pro fallback).

## Decision Outcome

**Weld como 4o candidato do fallback per-coluna**: `min(tcf, raw, dict, split)`.
Multi-col, emite `#TCF.7 M`. Gated pelo mesmo flag `fallback` (default True).

- **Auto-detect gated** (escopo escolhido pelo owner): detecta template, splita,
  escolhe min. **Zero-regressao por construcao** (sempre o menor). Mesma filosofia
  do V2-A/V2-B (mais um candidato no min()).
- **Gate**: template **100% uniforme** (todos os valores com os mesmos
  separadores e mesma contagem de campos), **>=2 campos**, e variacao real (algum
  campo nao-constante). Mistura (sinais variados, vazios, estrutura irregular) cai
  abaixo do gate -> nao splita -> fallback. Sem mecanismo de excecao (decisao do
  refinamento: 1 near-miss em 80 colunas reais).
- **Sub-table de campos**: reusa `_encode_multi` -> cada campo passa pelo fallback
  (tcf/raw/**dict V2-B**). Campos sao digitos puros -> sem recursao de split.
- **Complementa natures** (CPF/CNPJ, ADR-0015): nenhum subsume (cpf nature 34038
  vence split 58148; cnpj split 32668 vence nature 53827). Quando ambos aplicam,
  `min()`.
- **`fallback=False`**: desliga raw/dict/split -> `#TCF.6 M` legado byte-limpo.

## Format (#TCF.7, slot da coluna split)

    %<size>=<name>            (no meta; size = bytes do slot)

    slot = <ntmpl>\n<template_blob><field_subtable>

- `<ntmpl>` = bytes do template_blob (fronteira).
- `<template_blob>` = `(<bytelen>:<bytes>)` por parte nao-digito (nf+1 partes,
  big-endian). Length-framing por bytes -> partes multibyte/UTF-8 OK.
- `<field_subtable>` = `_encode_multi({c0:..., c1:..., ...})` (um `#TCF.7 M`
  aninhado; cada campo low-card vira dict via V2-B). nf derivado de len(partes)-1.

Decoder: parseia template_blob, decoda o sub-table (recursivo), reintercala
`parte[0] + campo0[r] + parte[1] + campo1[r] + ... + parte[nf]`.

## Name guard (correcao incidental)

Nomes de coluna nao podem comecar com `!@%` (marcadores de modo) — colidiria com
o parse da ultima-coluna-bare (min_header). Fecha tambem o risco latente de `!`
(V2-A) e `@` (V2-B). Tightening pré-1.0, seguro.

## Pros and Cons

**Pros**:
- Maior lever do ciclo 0.7: 19.39% weighted real-world; pega decimais, datas,
  datetimes, ids — alem do que OBAT/V2-A/V2-B cobrem.
- Zero-regressao (min()); compoe com V2-B (motor) e natures.
- Gate uniforme = bordas seguras sem mecanismo de excecao.

**Cons / limites**:
- Single-col fora de escopo (como V2-A/V2-B).
- Gate 100% uniforme deixa de fora colunas near-miss (1 em 80 reais — aceitavel).
- Overlap parcial com natures CPF/CNPJ (resolvido por min()).
- Sub-table aninhado: header amortizado em N alto; em tabela pequena o min()
  mantem a coluna inteira (ex: D17a 13 linhas -> timestamp NAO splita).

## Relation to other ADRs

- **ADR-0018** (roadmap v2.0): novo lever (nao estava no roadmap original; emergiu
  do V2-D refutado -> H-DT-01 -> generalizado H-STRUCT-01).
- **ADR-0025** (V2-B): split reusa V2-B nos campos (a sinergia e' o motor); 4o
  candidato do mesmo mecanismo min().
- **ADR-0015** (natures): complementa CPF/CNPJ, nao subsume.
- **ADR-0024** (versioning): baselines re-pinaveis. D17a=303 e D1-D9=1523
  INTOCADOS (split nao dispara neles).

## Verification

- `tests/test_multi_col_rt.py::TestStructSplit` (13 casos: marcador `%`, RT,
  decimal+data split, non-uniform/mixed-signs nao splita, off com fallback=False,
  nunca maior, RT bordas negativos/utf8/id, name guard, helper direto).
- Suite completa: **398 passed, 1 xfailed**. GATE real-world verde. Baselines
  INTOCADOS (D17a=303, D1-D9=1523 — split nao dispara em tabela pequena/single-col).
- Welded confirmado via `encode()`: wine 8 cols, lineitem 5, br-pessoas (cpf,
  data_cadastro), retail (InvoiceDate, UnitPrice) — RT OK.

## Links

- [Lab caracterizacao](../../experiments/lab/dirty/old/welded/2026-06-14-datetime-nature-caracterizacao/result.md)
- [Lab refinamento](../../experiments/lab/dirty/old/welded/2026-06-14-datetime-nature-caracterizacao/refine_result.md)
- [ADR-0025 V2-B](0025-v2b-dictionary-categorical-weld.md)
- [ADR-0015 natures](0015-natures-templated-checked-weld.md)

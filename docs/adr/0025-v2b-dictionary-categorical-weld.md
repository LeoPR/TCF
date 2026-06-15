# 0025 — V2-B dicionario/categorico welded (#TCF.7, marcador `@`)

**Status**: accepted
**Date**: 2026-06-14
**Deciders**: project owner
**Tags**: v2.0, format, dictionary, categorical, multi-column, low-cardinality, #TCF.7

## Context and Problem Statement

[ADR-0018](0018-v2-format-roadmap.md) registrou V2-B (encoder dicionario/
categorico) como prioridade #2 do roadmap v2.0, com o maior teto: "resolve a
RAIZ do ponto cego de baixa-cardinalidade". Coluna low-card de N linhas, K
unicos: hoje o HCC deduplica os K e emite 1 whole-value ref `^idx\n` por linha
repetida (`^` + indice decimal + `\n` ~ 4 bytes/linha). Pra K=24, N=8000 isso e'
~28KB contra ~4.6KB de entropia. O fallback V2-A ([ADR-0022](0022-v2a-fallback-identity-weld.md))
so' troca por raw (~3 bytes/linha) — melhor, mas ainda 4.5x acima do piso.

V2-B foi caracterizado no lab [`2026-06-14-v2b-dicionario-caracterizacao`](../../experiments/lab/dirty/2026-06-14-v2b-dicionario-caracterizacao/result.md):
8 datasets reais, RT 42/42 OK. Por-coluna: **63.7%** menor que o fallback
(vence 37/42). Por-tabela, V2-B como 3o candidato do fallback: **13.9% weighted**
(367KB / 2.64MB) — cumpre o checklist confirmada-empirica (real-world, N=8,
weighted >= 5%).

## Decision Outcome

**Weld V2-B como 3o candidato do fallback per-coluna**: `min(tcf, raw, v2b)`.
Multi-col, emite `#TCF.7 M`. Gated pelo mesmo flag `fallback` (default True, 0.7
e' o default por [ADR-0024](0024-pre-1.0-versioning-git-as-compat.md)).

- **Zero-regressao por construcao**: V2-B so' e' escolhido quando ESTRITAMENTE
  menor que tcf e raw. Onde nao vence (ibge pre-ordenado ja' RLE-otimo, high-card),
  o fallback mantem o atual. ibge = 0.0% (nenhuma coluna trocada).
- **Gating barato**: so' tenta V2-B quando `2 <= K < N` e `K <= 1024` (acima
  disso o stream de indices nao compensa; evita o sub-encode). `K = n_unicas`
  ja' esta' em column_features.
- **Marcador**: par meta `@<size>=<name>` (`@` ANTES do size). Ao lado de `!`
  (raw, V2-A) e `<size>=<name>` (tcf). Nao colide com nome (size e' digito; `@`
  so' aparece em `#TCF.7`).
- **Decoder**: `@` por par roteia pro `_decode_v2b` (self-describing, sem flag).
- **`fallback=False`**: desliga raw E dict -> `#TCF.6 M` byte-identico ao legado
  (caminho de comparacao/regressao preservado).

## Format (#TCF.7, slot da coluna dict)

    @<size>=<name>            (no meta; size = bytes do slot)

    slot = <ntable>\n<table_bytes><stream>

- `<ntable>` = bytes da TABELA (linha 1 do slot, decimal) -> fronteira inequivoca.
- `<table_bytes>` = `encode(unicas)` (tabela de unicos TCF-encodada; dedup/OBAT
  do conjunto pequeno).
- `<stream>` = 1 indice por linha, `width` chars no alfabeto printable
  `0x21..0x7E` (94 chars, exclui `\n`). `width` = minimo com `94^width >= K`
  (K<=94 -> 1 char). big-endian. Derivado de K apos decodar a tabela (nao
  precisa estar no header).

Stream so' tem bytes ASCII (`<0x80`, sem `\n`): `len(stream) == N*width` exato.
Tabela fatiada por BYTE (ntable), nao por linha -> valores multibyte/UTF-8 OK.

## Pros and Cons

**Pros**:
- Maior teto do roadmap: 13.9% weighted real-world, 63.7% por-coluna low-card.
- Zero-regressao: entra no mecanismo min() do V2-A; nunca pior que tcf/raw.
- Order-free: captura a redundancia low-card sem reordenar linhas (complementa
  o `sort_by`/O-FMT-02, que leva V2-B sorted a 98.7%).
- Mesma seguranca do caminho tcf (tabela assume 'dados felizes', como o resto).

**Cons / limites**:
- Single-col fora de escopo (sem header pra marcar modo) — como V2-A.
- Stream nao e' human-meaningful (chars de indice), mas e' ASCII inspecionavel
  (nivel "avancado" da filosofia: textual, dentro do ASCII).
- Sem RLE no stream nesta versao (packed puro). RLE no stream (ganha em
  adjacencia natural/sorted) fica como follow-up se os numeros justificarem.

## Relation to other ADRs

- **ADR-0018** (roadmap v2.0): V2-B **welded**. Restam V2-C (lossy), V2-D (strip
  sufixo) no roadmap.
- **ADR-0022** (V2-A fallback): V2-B reaproveita o mecanismo de selecao per-coluna
  e o magic `#TCF.7`. Agora sao 3 candidatos (tcf/raw/dict).
- **ADR-0024** (pré-1.0 versioning): baselines re-pinados (D17a 307->303, V2-B na
  coluna `categoria`). Re-pin intencional, nao contrato eterno. D1-D9 (single-col)
  inalterado.

## Verification

- `tests/test_multi_col_rt.py::TestV2BDict` (8 casos: marcador `@`, RT, low-card
  -> dict, all-unique -> nao dict, off com fallback=False, nunca maior, RT bordas
  vazios/UTF-8, helper `_decode_v2b` direto).
- 2 testes V2-A atualizados (low-card agora vai pra `@`, nao `!`; coluna
  all-unique incompressivel cobre o `!`).
- Suite completa: **385 passed, 1 xfailed**. GATE real-world verde (7 passed,
  colunas single-col high-card inalteradas). Baselines re-pinados (D17a=303,
  ADR-0024/0025; D1-D9=1523 intocado).
- Welded confirmado em tabelas reais via `encode()`: RT OK; vs #TCF.6 legado
  adult 46.1%, beijing 44.2%, lineitem 19.0%.

## Links

- [Lab 2026-06-14-v2b-dicionario-caracterizacao](../../experiments/lab/dirty/2026-06-14-v2b-dicionario-caracterizacao/result.md)
- [ADR-0018 roadmap v2.0](0018-v2-format-roadmap.md)
- [ADR-0022 V2-A fallback](0022-v2a-fallback-identity-weld.md)
- [ADR-0024 pré-1.0 versioning](0024-pre-1.0-versioning-git-as-compat.md)

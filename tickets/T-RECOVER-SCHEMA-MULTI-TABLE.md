---
title: T-RECOVER-SCHEMA-MULTI-TABLE — Expandir schema builder pra relacionamentos multi-tabela
status: de-prontidao
priority: P2
created: 2026-05-27
blocked-by: []
related:
  - src/tcf/schema.py
  - docs/theory/strategies/05-dispatch-formato.md
  - tickets/T-CODE-SCHEMA-BUILDER.md
---

# T-RECOVER-SCHEMA-MULTI-TABLE

## Contexto

Owner mencionou (2026-05-27) que o schema builder atual (welded Fases 1+2,
`build_schema → TableSchema/ColumnSchema`) e' subaproveitado. Proposta:
**expandir pra avaliar relacionamentos entre tabelas separadas** — quando
duas tabelas tem boa correlacao (FK, joins implicitos, colunas
compartilhadas), o schema pode informar **ordem mais eficiente** de
encode (multi-tabela aware), nao apenas por-coluna.

## Hipotese / Objetivo

Schema multi-tabela detecta:
- FK candidates (col_A.values ⊂ col_B.values com cardinalidade alta)
- Colunas compartilhadas entre tabelas (mesmo nome+tipo+amostra)
- Ordem otima de encode (tabelas "maes" antes de "filhas" pra max dedup
  cross-table — pra quando V2-G "cross-column atom sharing" abrir)

Resultado: schema **estruturado**, nao apenas analitico, que orienta o
encoder pra ordem/agrupamento melhor mesmo em tabelas separadas.

## Estado atual

- Welded: `build_schema(data) → TableSchema` (Fases 1+2, ADR vinculado)
- Fase 3 (auto-detect nature via NatureApplyStats) adiada (depende Pacote 7)
- **NAO existe**: analise cross-table (FK, joins, ordem)

## Plano (futuro, pos-H-PERF-06-v2 + estudo owner)

### Fase 1 — Detector de FK candidate
- `detect_fk_candidates(tableA, tableB) → list[FKCandidate]`
- Criterio: cardinalidade A.col ⊂ B.col, % match, distinct counts
- Output enriquece TableSchema com .related_tables / .fk_candidates

### Fase 2 — Detector de colunas compartilhadas
- `detect_shared_columns(tables: dict[str, TableSchema]) → SharedSchema`
- Cross-table feature matching (nome, dtype, sample overlap)

### Fase 3 — Plano de encode multi-tabela
- `plan_encode_order(tables: dict, related: SharedSchema) → list[str]`
- Topological order pra max dedup quando cross-table compartilha refs

## Conexao

- Schema builder atual (welded Fases 1+2)
- T-CODE-SCHEMA-BUILDER.md (ticket pai, registra Fase 3 nature auto-detect)
- V2-G cross-column atom sharing (ADR-0018) — pre-requisito do plano de
  ordem fazer sentido
- Filosofia: textual + explicavel; schema enriquecido permite TCF "ver"
  o que esta comprimindo

## Status

**De prontidao** (registrado 2026-05-27). Atacar apos H-PERF-06-v2 Fase A
+ owner estudar mapa de estrategias segmentado.

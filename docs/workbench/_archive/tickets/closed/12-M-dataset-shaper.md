---
title: META — Fase 1.5: Dataset Shaper (sampler multidimensional)
type: meta
status: IN_PROGRESS
priority: 11
created: 2026-04-12
---

# META: Fase 1.5 — Dataset Shaper

## Contexto

Apos a Fase 1 (datasets canonicos), antes de tocar no TCF,
precisamos de um **shaper** que extrai subsets controlados
dos datasets segundo varias dimensoes: volume, schema complexity,
join level, ordering, stratification, compressibility.

Sem isso nao conseguimos testar sistematicamente.

## Decisoes (2026-04-12)

Ver [docs/research-notes/2026-04-12-dataset-shaper.md](../../docs/research-notes/2026-04-12-dataset-shaper.md)

- Minimo viavel com modularidade para escalar
- Cache sob demanda para compressibility
- Join level: so normalized vs flat por enquanto
- Schema: niveis nomeados
- Arranque: Adult primeiro, TPC-H depois

## Sub-tickets (Fase 1.5a — minimo viavel)

| # | Ticket | Escopo |
|---|--------|--------|
| 13 | T-shaper-request | ShapeRequest dataclass + validacao |
| 14 | T-shaper-pipeline | Executor com trace + strategy protocol |
| 15 | T-shaper-volume | Volume (N absoluto + fraction) |
| 16 | T-shaper-schema | Niveis nomeados (minimal, core, full, custom) |
| 17 | T-shaper-ordering | natural, random(seed), sorted, reverse |
| 18 | T-shaper-e2e | End-to-end test com Adult + TPC-H |

## Sub-tickets (Fase 1.5b — extensoes)

| # | Ticket | Escopo |
|---|--------|--------|
| 19 | T-shaper-stratify | Amostragem estratificada |
| 20 | T-shaper-compressibility | Score de raridade + bucketing + cache |
| 21 | T-shaper-join | normalized vs flat (via SQL) |
| 22 | T-shaper-combined | Testes combinatoriais (pairwise) |

## Criterio de conclusao

Fase 1.5a: tickets 13-18 DONE + Adult funciona end-to-end.
Fase 1.5b: tickets 19-22 DONE + TPC-H funciona com joins.

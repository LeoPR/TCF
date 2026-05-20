---
title: EXP-014 — TPC-H lineitem performance scale test
type: clean-experiment
status: active
tags: [tcf, real-world, performance, scale, tpch, lineitem, profiling]
created: 2026-05-19
updated: 2026-05-19
predecessor: EXP-013-real-world-tpch
related:
  - experiments/lab/dirty/notas/roadmap-hipoteses.md
  - docs/adr/0008-detect-cadence-numeric-rule.md
---

# EXP-014 — TPC-H lineitem performance scale test

**Predecessor**: EXP-013 (cap 5000 rows, encode ~103s)
**Goal**: caracterizar escala do encode pipeline em lineitem
(60175 rows × 16 cols).

## Pergunta cientifica

Como pipeline EXP-011 + ADR-0008 escala em volume crescente?
- Tempo de encode (suspeita: O(N²) do OBAT)
- Tempo de decode (linear esperado)
- Ratio compressao (estavel ou degrade?)
- RT byte-canonical em todas escalas

## Plano

Volumes progressivos: **1000, 5000, 10000, 20000**.
Cap em 20k se encode ficar proibitivo (>10 min). 60175 full vai ser
extrapolacao baseada em curva, se nao terminar.

Para cada volume:
- Encode time, decode time
- Bytes raw, bytes TCF, ratio
- RT byte-canonical
- Per-coluna stats (cadence detected, runs)

## Datasets

`Z:/tcf-data/interim/tpch-sf001.db` table `lineitem`.

## Aceite

- Curva de encode time documentada (1k → 5k → 10k → 20k)
- Ratio estavel (~85-90% conforme EXP-013)
- RT 100% em todas escalas

## Hipoteses derivadas

- **H-RW-05** (re-aberta): encode time cresce como O(N²) — confirmar
  ou refutar via curve fit
- **H-RW-07** (nova): ratio degrade levemente com escala
  (mais entropy variability)

## See also

- [EXP-013 TPC-H](../EXP-013-real-world-tpch/) — predecessor
- [EXP-012 Adult](../EXP-012-real-world-adult-census/) — Adult tambem mostrou O(N²)
- [ADR-0008](../../../docs/adr/0008-detect-cadence-numeric-rule.md) — heuristica v2 ativa

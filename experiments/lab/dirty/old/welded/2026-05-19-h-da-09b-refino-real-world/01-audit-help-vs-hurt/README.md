---
title: Sub-exp 01 — Audit help-vs-hurt per-coluna real-world
type: sub-experiment
status: active
tags: [tcf, audit, help-vs-hurt, real-world]
created: 2026-05-19
updated: 2026-05-19
parent: 2026-05-19-h-da-09b-refino-real-world
---

# Sub-exp 01 — Audit help-vs-hurt

## Objetivo

Per-coluna em Adult Census + TPC-H, medir o impacto de habilitar
H-DA-07 hint (force_hint=True) vs disabled (force_hint=False).

Categorizar cada coluna:
- **HELP**: bytes_on < bytes_off (delta > 5 bytes pra reduzir
  noise)
- **HURT**: bytes_on > bytes_off (delta > 5 bytes)
- **NO-OP**: |delta| <= 5

Coletar features da coluna pra correlacionar com outcome:
- lengths uniformes? (max-min length)
- LCP+LCS avg em pares consecutivos
- n_unicas
- cardinalidade (n_unicas / n_rows)
- numerica? (todos parseaveis como int?)
- avg length

## Datasets

Sub-amostra de cada:
- Adult Census: shaper volume=500 (15 cols)
- TPC-H: dataset_reader rows direto, 200 rows por tabela (todas 8)

## Output

`audit.md` com:
- Tabela por coluna (dataset, col, features, outcome)
- Sumario por categoria (HELP/HURT/NO-OP)
- Patterns visuais: que features predizem HELP vs HURT?

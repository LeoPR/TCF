---
title: H-DA-09b refino — heuristica de auto-detect para real-world
type: dirty-lab
status: active
tags: [tcf, auto-detect, heuristic, real-world, refinement, h-da-09b]
created: 2026-05-19
updated: 2026-05-19
hypothesis: H-DA-09b refino (criterio para real-world)
related:
  - experiments/lab/dirty/2026-05-17-OBAT-delta-aware/09-auto-detect-cadence-heuristic/
  - experiments/lab/clean/EXP-012-real-world-adult-census/
  - experiments/lab/clean/EXP-013-real-world-tpch/
  - docs/adr/0003-tripartite-pre-obat-hcc.md
---

# 2026-05-19 — Refino do auto-detect cadence (H-DA-09b)

## Contexto

H-DA-09b (sub-exp 09 do pacote 1) introduziu `detect_cadence` com
heuristica:
- lengths uniformes nas primeiras 5 strings
- LCP+LCS / length >= 0.7 em pares consecutivos

Resultados em real-world (EXP-012 Adult, EXP-013 TPC-H):
- **0/15 colunas** Adult Census detectaram cadence
- **0/n_cols** TPC-H detectaram cadence

Heuristica calibrada para D11d/D16 sinteticos (cadencia aritmetica
forte). Em real-world numerico (age, fnlwgt) ou categorico
(workclass), critica nao dispara.

## Pergunta

Em real-world, **quais features de coluna predizem se enabling
H-DA-07 hint HELP, HURT, ou NO-OP**?

Sub-exp 06 do pacote 1 (D1-D9 always-on) mostrou:
- HELP grande: D9 wrapper pattern (-58%)
- HURT grande: D5 mixed patterns (+72%)
- No-op: D4, D8

Em real-world esperamos comportamento similar — mas precisamos
DADOS.

## Estagios (seguindo `docs/how-to/fluxo-hipotese-producao.md`)

### 1. Sub-exp 01 — Audit help-vs-hurt (este lab)

Per-coluna em Adult Census + TPC-H, medir:
- bytes com hint OFF (baseline)
- bytes com hint ON (always-on H-DA-07)
- Categoria: HELP / HURT / NO-OP
- Features da coluna: lengths uniformes? LCP+LCS ratio? n_unicas?
  cardinalidade (unicas/total)? numerico vs string?

Output: dataset rotulado de features × outcome.

### 2. Sub-exp 02 — Design + teste de heuristica refinada

Com base no audit, propor 2-3 heuristicas alternativas:
- Threshold tunado
- Multivariada (length + cardinalidade + numerica)
- Detect categorica e disabilita hint

Testar em mesmo dataset.

### 3. Sub-exp 03 — Validacao end-to-end

Aplicar heuristica refinada em EXP-012/013 cenarios. Comparar
contra always-on e always-off.

### 4. ADR + welding (se confirmar)

Atualizar `auto_pre.py` (EXP-010) e potencialmente src/tcf se houver
mudancas que possam beneficiar canonical.

## Restricoes herdadas

- src/tcf intocado (so' EXP-010's auto_pre.py em prototype)
- Validacao multi-camada antes de welding
- Vertice triplice (single-pass, low-mem)

## Sub-experimentos

```
2026-05-19-h-da-09b-refino-real-world/
├── README.md
├── 01-audit-help-vs-hurt/    ← ATIVO
├── 02-heuristica-refinada/   ← planejado
└── 03-validacao-end-to-end/  ← planejado
```

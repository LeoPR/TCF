---
title: Escalabilidade progressiva — accuracy x rows (20 a 1000)
type: experiment
status: DONE (2026-04-09)
priority: HIGH
origin: Revisao de H10 (v0.1, parcial em Etapa 1)
---

# Escalabilidade Progressiva

## Setup

Modelo fixo: gemma3:12b (melhor em Etapa 2, 88% TCF L0)
Formatos: CSV, TCF L0, TCF L2
Escalas: 20, 50, 100, 200, 500, 1000 orders
Questoes: q1_sum, q3_max, q5_count, q6_top_product (4 representativas)
TCF inclui STATS lines.

Total: 3 formatos x 6 escalas x 4 questoes = 72 combos

## Resultados

| Scale | Rows | CSV | TCF L0 | TCF L2 | csv chars | L0 chars | L2 chars |
|-------|------|-----|--------|--------|-----------|----------|----------|
| 20 | ~52 | 75% | 75% | 50% | 2K | 2K | 2K |
| 50 | ~130 | 25% | 75% | 75% | 5K | 5K | 3.5K |
| 100 | ~252 | 25% | **100%** | **100%** | 11K | 11K | 7K |
| 200 | ~509 | 50% | **100%** | 75% | 21K | 22K | 19K |
| 500 | ~1241 | 50% | 50% | 0% | 50K | 51K | 45K |
| 1000 | ~2508 | 25% | 0% | 0% | 104K | 104K | 93K |

## Findings

### F85: TCF L0 pico em 100-200 rows (100%)
Sweet spot: 100-200 orders (~252-509 vendas). Accuracy perfeita.
Abaixo de 50: pouco dado, STATS menos informativos.
Acima de 500: contexto grande demais, modelo perde os STATS.

### F86: CSV estavel mas mediano (~25-50%)
Nunca atinge 100%. Nao colapsa tao dramaticamente quanto TCF.
Provavelmente porque CSV nao tem STATS — accuracy vem de calculo real
(que o modelo faz mal, conforme F80).

### F87: TCF L2 colapsa antes de L0
L2 = 0% a 500 rows, L0 = 50% a 500.
RLE comprime texto mas nao reduz o contexto o suficiente.
A reordenacao pode confundir o modelo.

### F88: Crossover TCF > CSV em 50-200 rows
Faixa onde TCF supera CSV claramente.
Abaixo de 50: empate. Acima de 500: ambos ruins.

### F89: A 1000 rows, tudo colapsa
CSV 25%, TCF L0 0%, TCF L2 0%.
Prompt com 104K chars excede a capacidade efetiva do modelo.

## Caveat critico: STATS como shortcut

Os resultados de TCF sao inflados pelos STATS hints (F81).
gemma3:12b nao calcula — le STATS. O pico de 100% em 100-200 rows
pode refletir que o modelo encontra os STATS no contexto, nao que
processa os dados.

Experimento necessario: repetir sem STATS (include_stats=False).

## Tarefas

- [x] Adaptar runner para mais escalas
- [x] Rodar com gemma3:12b
- [x] Gerar resultados
- [ ] Repetir SEM STATS (ablacao critica)
- [ ] Rodar com qwen3:8b (modelo que genuinamente calcula)
- [ ] Gerar grafico accuracy vs rows
- [ ] Documentar em article/07

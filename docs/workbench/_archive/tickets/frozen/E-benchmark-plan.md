---
title: Plano combinatorio de benchmark — cobertura completa para o paper
type: experiment
status: OPEN
priority: CRITICAL
created: 2026-04-09
---

# Plano Combinatorio de Benchmark

## Principio: cada experimento elimina combinacoes futuras

Nao testar tudo com tudo. Usar ablacao progressiva:
1. Etapa 2 expandida — baseline com todos os modelos
2. Stats ablation — separar accuracy real de hints
3. Scale progression — so com top 2-3 modelos
4. Prompt presentation — so com 1 modelo, 1 formato

## Modelos selecionados (12 finais para o paper)

Excluir obsoletos (phi3, qwen2.5, deepseek-r1:7b — superados por versoes novas).
Incluir novos (5 instalados hoje).

| # | Modelo | Params | Familia | Thinking | Status E2 |
|---|--------|--------|---------|----------|-----------|
| 1 | qwen3:0.6b | 0.75B | qwen3 | sim | NOVO |
| 2 | gemma3:1b | 1B | gemma3 | nao | NOVO |
| 3 | qwen3:1.7b | 2B | qwen3 | sim | NOVO |
| 4 | llama3.2:latest | 3.2B | llama | nao | 33% avg |
| 5 | gemma3:4b | 4.3B | gemma3 | nao | NOVO |
| 6 | qwen3:8b | 8.2B | qwen3 | sim | 38% avg |
| 7 | gemma2:9b | 9.2B | gemma2 | nao | 12% avg |
| 8 | gemma3:12b | 12.2B | gemma3 | nao | 62% avg |
| 9 | phi4:latest | 14.7B | phi | nao | 50% avg |
| 10 | deepseek-r1:14b | 14.8B | deepseek | sim | 33% avg |
| 11 | qwen3:14b | 14.8B | qwen3 | sim | NOVO |
| 12 | gpt-oss:latest | 20.9B | gptoss | sim | 50% avg |

## Experimentos em ordem de execucao

### E1. Etapa 2 Expandida (PROXIMO)

**Objetivo:** baseline de todos os 12 modelos com 3 formatos.
**Formatos:** CSV, TCF L0, TCF L2
**Questoes:** 8 (q1-q8)
**Total:** 12 modelos × 3 formatos × 8 questoes = **288 combos**

Reutiliza resultados de Etapa 2 original para modelos que nao mudaram
(gemma3:12b, phi4, gpt-oss, llama3.1, gemma2, llama3.2, qwen3:8b, deepseek-r1:14b).
So precisa rodar os 5 novos + mistral (manter como baseline europeu):
**5 novos × 3 × 8 = 120 combos** (~2-4h dependendo dos modelos)

### E2. Stats Ablation Expandida

**Objetivo:** separar accuracy real de STATS hints para TODOS os modelos.
**Formatos:** TCF L0-stats, L0+stats, L2-stats, L2+stats
**Modelos:** Top 6 (gemma3:12b, qwen3:8b, phi4, gpt-oss, qwen3:14b, deepseek-r1:14b)
**Questoes:** 8

Ja rodando com 4 modelos (128 combos). Expandir com qwen3:14b e gpt-oss depois:
**2 extras × 4 × 8 = 64 combos** adicional

### E3. Scaling Curve (accuracy x params)

**Objetivo:** curva de accuracy por tamanho de modelo dentro da mesma familia.
**Familias:**
- gemma3: 1b → 4b → 12b (3 pontos)
- qwen3: 0.6b → 1.7b → 4b → 8b → 14b (5 pontos — NAO temos qwen3:4b!)

Espera: dados da Etapa 2 Expandida ja cobrem isso. So gerar o grafico.
**0 combos adicionais** — reusa E1.

### E4. Prompt Presentation Ablation

**Objetivo:** idioma, decoracao, wording, CoT, few-shot.
**Modelo fixo:** gemma3:12b (melhor, permite comparar com baseline)
**Formato fixo:** TCF L2 (onde ha mais espaco para melhorar)
**Total:** 8 variantes × 3 questoes + 4 wording = **28 combos** (~30min)

### E5. Scale Progression Expandida (opcional)

**Objetivo:** curva accuracy x rows para top 2 modelos.
**Modelos:** gemma3:12b (STATS reader) + qwen3:8b (genuine calculator)
**Escalas:** 20, 50, 100, 200, 500, 1000
gemma3 ja feito (72 combos). Rodar qwen3:
**1 modelo × 6 escalas × 3 formatos × 4 questoes = 72 combos**

### E6. Formatos concorrentes (opcional)

**Objetivo:** TOON + Markdown Table no mesmo benchmark.
**Modelos:** top 3 (gemma3, qwen3, phi4)
**Total:** 3 × 2 formatos × 8 questoes = **48 combos**

## Resumo de combos

| Experimento | Combos | Tempo est. | Prioridade | Depende de |
|-------------|--------|------------|------------|------------|
| E1 Etapa 2 Expandida | 120 (novos) | 2-4h | CRITICO | - |
| E2 Stats Ablation ext | 64 | 1-2h | CRITICO | E-stats (em andamento) |
| E3 Scaling Curve | 0 (reusa E1) | 0 | HIGH | E1 |
| E4 Prompt Presentation | 28 | 30min | MEDIUM | - |
| E5 Scale + qwen3 | 72 | 2-3h | MEDIUM | - |
| E6 Formatos concorrentes | 48 | 1h | LOW | - |
| **TOTAL** | **332** | **~8-10h** | | |

## Ordem de execucao

```
[AGORA]     E-stats ablation (128 combos, rodando)
[PROXIMO]   E1: Etapa 2 expandida — 5 novos modelos (120 combos)
[DEPOIS]    E2: Stats ablation + qwen3:14b + gpt-oss (64 combos)
[DEPOIS]    E4: Prompt presentation (28 combos, rapido)
[DEPOIS]    E5: Scale com qwen3 (72 combos)
[OPCIONAL]  E6: TOON + Markdown (48 combos)
[ANALISE]   E3: Gerar scaling curve dos dados de E1
[FIGURAS]   T-figures-analysis: gerar todas as figuras
```

## Heuristica de eliminacao

Apos cada etapa, avaliar se a proxima e necessaria:
- Se E1 mostra que modelos <2B sao 0% em tudo → nao precisa de E5 com eles
- Se E2 mostra que STATS nao afeta nenhum modelo → narrativa muda
- Se E4 mostra variancia de wording <5pp → robusto, nao precisa de repeticoes
- Se E6 mostra TOON = JSONL → so uma linha no paper, nao precisa de mais

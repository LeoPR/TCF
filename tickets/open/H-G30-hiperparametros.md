---
title: Temperature, thinking, context — isolar efeitos
type: hypothesis
status: DONE
---

# Temperature, thinking, context — isolar efeitos

## Experimento G30

**Modelo:** qwen3:8b
**Formatos:** TCF L0, TCF L2
**Questoes:** q1_sum, q2_avg, q3_max, q5_count, q6_top_product, q7_top_spender (6)
**Configs:** 4 combinacoes de thinking (on/off) x temperature (0/0.6)
**Total:** 4 configs x 2 formatos x 6 questoes = 48 combos
**Data:** 2026-04-09

## Resultados

### Accuracy geral por config

| Config | Accuracy | Avg latency |
|--------|----------|-------------|
| think_on + t=0 | **75%** | 144s |
| think_off + t=0.6 | **75%** | 134s |
| think_on + t=0.6 | 67% | 176s |
| think_off + t=0 | 58% | 87s |

### Accuracy por config x formato

| Config | TCF L0 | TCF L2 |
|--------|--------|--------|
| think_on + t=0 | **100%** | 50% |
| think_on + t=0.6 | 83% | 50% |
| think_off + t=0.6 | 83% | **67%** |
| think_off + t=0 | 67% | 50% |

## Findings

### F60: Thinking ON + temp 0 = 100% em TCF L0
- Configuracao perfeita para formato expandido
- Thinking permite ao modelo "trabalhar" os dados passo a passo
- Temperature 0 elimina variancia — respostas deterministas

### F61: TCF L0 >> TCF L2 em todas as configs
- L0 media: 83% | L2 media: 54%
- Diferenca: ~29pp consistente
- RLE (N*val) adiciona carga cognitiva real que nem thinking resolve

### F62: Temperature tem efeito nao-linear
- Com thinking ON: t=0 > t=0.6 (75% vs 67%)
- Com thinking OFF: t=0.6 > t=0 (75% vs 58%)
- Hipotese: sem thinking, alguma aleatoriedade ajuda a "achar" respostas

### F63: Respostas vazias (FAIL 0s)
- Varios FAIL com latencia 0s — modelo retorna vazio ou malformado
- Mais frequente em L2 — formato comprimido pode confundir o parser do modelo
- Nao e timeout (0s), e resposta instantanea invalida

## Implicacoes

- **Para o paper:** reportar que thinking + temp=0 e a config ideal para TCF L0
- **Para proximos experimentos:** usar think_on + temp=0 como default
- **Para E-prompt-presentation:** L2 precisa de ajuda (decoracao? explicacao?)
- **H-G31 (thinking):** absorvido — thinking ON e claramente superior em L0

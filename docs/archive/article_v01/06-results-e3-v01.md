# 6. Resultados: Phase 1 — Compreensao de Formato (E3, G02)

**Phase 1 concluida:** 6 modelos x 35 questoes = 210 combinacoes (100%).
**Data:** 2026-04-06.

## 6.1 Modelos Avaliados

| Model | Params | Quant | Family | Size Category |
|-------|--------|-------|--------|---------------|
| phi3:latest | 3.8B | Q4_0 | phi3 | tiny |
| qwen2.5:latest | 7.6B | Q4_K_M | qwen2 | small |
| qwen3:8b | 8.2B | Q4_K_M | qwen3 | medium |
| llama3.1:8b | 8B | Q4_K_M | llama | medium |
| gemma2:9b | 9.2B | Q4_0 | gemma2 | medium |
| gpt-oss:latest | 20.9B | MXFP4 | gptoss | large |

## 6.2 Resultados por Modelo x Camada

| Model | math_ctrl | decode | compute |
|-------|-----------|--------|---------|
| gpt-oss:latest | 100% | 100% | **97%** |
| qwen3:8b | 100% | 100% | **90%** |
| qwen2.5:latest | 0% | 33% | 47% |
| llama3.1:8b | 0% | 100% | 30% |
| gemma2:9b | 0% | 100% | 27% |
| phi3:latest | 0% | 0% | 20% |

## 6.3 Resultados por Formato (compute layer)

| Format | Accuracy | N |
|--------|----------|---|
| JSONL | **63%** | 60 |
| CSV | 48% | 60 |
| TCF | 43% | 60 |

## 6.4 Modelo x Formato (compute)

| Model | CSV | JSONL | TCF | Delta TCF-JSONL |
|-------|-----|-------|-----|-----------------|
| gpt-oss:latest | 100% | 100% | 90% | -10% |
| qwen3:8b | 90% | 100% | 80% | -20% |
| qwen2.5:latest | 30% | 60% | 50% | -10% |
| llama3.1:8b | 20% | 50% | 20% | -30% |
| gemma2:9b | 20% | 40% | 20% | -20% |
| phi3:latest | 30% | 30% | 0% | -30% |

## 6.5 Accuracy por Questao

| Questao | Tipo | Accuracy | Dificuldade |
|---------|------|----------|-------------|
| q8_top_product | lookup nome | 89% | Facil |
| q3_max_vl | max | 83% | Facil |
| q4_min_vl | min | 72% | Facil |
| q9_distinct_pessoa | count distinct | 61% | Media |
| q6_count_ana | FK count | 50% | Media |
| q10_top_spender | FK+argmax | 44% | Media |
| q1_sum_vl | sum | 33% | Dificil |
| q2_avg_vl | avg | 33% | Dificil |
| q7_sum_ana | FK+sum | 28% | Dificil |
| q5_count_rows | count | 22% | Dificil* |

*q5 surpreendentemente dificil no TCF multi-tabela (gpt-oss respondeu 83=30+12+41)

## 6.6 Distribuicao de Erros

| Error Type | Count | % |
|-----------|-------|---|
| arithmetic_error | 54 | 62% |
| wrong_count | 14 | 16% |
| parse_failure | 13 | 15% |
| list_instead_of_agg | 6 | 7% |

## 6.7 Latencia

### Por modelo (compute, media)

| Model | Avg | Min | Max |
|-------|-----|-----|-----|
| gemma2:9b | 1.4s | 1.2s | 4.1s |
| qwen2.5:latest | 3.5s | 1.0s | 46.7s |
| phi3:latest | 3.8s | 0.8s | 20.4s |
| llama3.1:8b | 12.2s | 1.3s | 66.5s |
| gpt-oss:latest | 72.6s | 8.8s | 307.5s |
| qwen3:8b | 118.3s | 16.3s | 193.3s |

### gpt-oss por formato (compute)

| Format | Avg | Total |
|--------|-----|-------|
| TCF | **61.2s** | 612s |
| CSV | 73.3s | 733s |
| JSONL | 83.4s | 834s |

## 6.8 Findings

**F1:** JSONL > CSV > TCF em accuracy bruta. Gap de ~20pp entre JSONL e TCF.

**F2:** TCF perde principalmente em modelos pequenos (phi3: 0% TCF vs 30% CSV).
Modelos fortes (gpt-oss, qwen3) performam bem em TCF (80-90%).

**F3:** O principal erro e arithmetic_error (62%). Modelos entendem o formato
mas erram a conta. Nao e problema de parse — e de raciocinio matematico.

**F4:** q5_count_rows e surpreendentemente dificil no TCF multi-tabela.
gpt-oss somou todas as tabelas (83). Motivacao direta para supertable mode (G03b).

**F5:** TCF gera respostas mais rapidas no gpt-oss (61s vs 83s JSONL).
Hipotese: dados colunares reduzem o raciocinio necessario para localizar valores.

**F6:** math_control separa modelos em 2 classes — os que sabem aritmetica
(gpt-oss, qwen3: 100%) e os que nao sabem (0% em todos os outros).
Accuracy < 50% nos outros modelos nao e culpa do formato.

**F7 (vies metodologico):** CSV/JSONL recebem dados desnormalizados (JOIN pronto),
TCF recebe dados normalizados (3 tabelas + FK). Phase 2 inline corrige.

Separando FK-dependent vs pure numeric:
- **Pure numeric:** TCF 40% vs JSONL 60% (gap 20pp — problema real)
- **FK-dependent:** TCF 47% vs JSONL 67% (gap 20pp — amplificado pelo vies)

Separando modelos fortes vs fracos:
- **Fortes (gpt-oss+qwen3):** CSV 95% / JSONL 100% / TCF 85% (gap 15pp)
- **Fracos (4 modelos):** CSV 25% / JSONL 45% / TCF 22% (gap 23pp)

## 6.9 Survivors para Phase 2

4 modelos com compute accuracy >= 30%:
- gpt-oss:latest (97%)
- qwen3:8b (90%)
- qwen2.5:latest (47%)
- llama3.1:8b (30%)

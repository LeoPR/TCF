---
title: Gerar figuras e analise estatistica para o paper
type: task
status: OPEN
priority: HIGH (bloqueante para paper)
origin: Revisao de P07 (v0.1, nunca feito)
---

# Figuras e Analise Estatistica

## Figuras planejadas

| Fig | Titulo | Dados de | Status |
|-----|--------|----------|--------|
| 1 | Compression ratio: TCF levels vs CSV vs JSONL por escala | G20b benchmark | PENDENTE |
| 2 | Accuracy heatmap: modelo x formato (Etapa 2) | Etapa 2 manifest | PENDENTE |
| 3 | Accuracy x escala: CSV vs TCF L0 vs L2 (curva) | E-scale manifest | **DADOS PRONTOS** |
| 4 | Pareto scatter: accuracy x prompt_chars | Etapa 2 manifest | PENDENTE |
| 5 | Error distribution: stacked bar por tipo de erro | Etapa 2 manifest | **DADOS PRONTOS** |
| 6 | Thinking ablation: on vs off x formato | G30 manifest | **DADOS PRONTOS** |
| 7 | Model family comparison: bar chart | Etapa 2 | PENDENTE |
| 8 | **3-layer diagnostic: bar chart por camada x modelo** | diagnostic manifest | **DADOS PRONTOS** |
| 9 | **Transport compression: TCF+gzip vs CSV+gzip vs JSONL+gzip** | transport results | **DADOS PRONTOS** |
| 10 | **Accuracy x log(params): curva por familia** | Etapa 2 expandida | PENDENTE (apos re-run) |

## Dados de erro (Etapa 2) — para Fig 5

```
Total: 288, Correct: 100 (35%), Errors: 188
  arithmetic_error: 70 (37%)
  exception:        45 (24%)
  wrong_count:      44 (23%)
  wrong_name:       26 (14%)
  parse_failure:     3 (2%)
```

## Figuras novas motivadas por findings desta sessao

### Fig 8 — 3-Layer Diagnostic (F80-F84)
Bar chart com 3 barras por modelo (L0_math, L1_decode, L2_compute).
Mostra claramente que gemma3 so acerta L2 (STATS shortcut).
qwen3 e o unico com L0>0. Central para o paper.

### Fig 9 — Transport Compression (F70-F73)
Line chart: eixo X = escala, eixo Y = tamanho apos gzip.
Linhas: CSV+gzip, JSONL+gzip, TCF L0+gzip, L2+gzip, L3+gzip.
Mostra que TCF+gzip < CSV+gzip em todas as escalas.

### Fig 10 — Accuracy x Model Size (H-scaling)
Scatter: eixo X = log(params), eixo Y = accuracy.
Cor por familia (gemma, qwen, etc). Precisa de Etapa 2 expandida.

## Analise estatistica

- Bootstrap CI 95% para cada accuracy (Efron & Tibshirani 1993)
- McNemar's test para pares de formatos (pareado por questao)
- Cohen's h para effect sizes
- Bonferroni correction para multiplas comparacoes

## Manifests disponiveis

| Manifest | Local | Entries |
|----------|-------|---------|
| Etapa 1 | experiments/results/etapa1/manifest.jsonl | ~320 |
| Etapa 2 | experiments/results/etapa2/manifest.jsonl | 288 |
| G30 | experiments/results/g30_hyperparams/manifest.jsonl | 48 |
| Diagnostic | experiments/results/diagnostic_3layer/manifest.jsonl | 48 |
| Scale | experiments/results/scale_progression/manifest.jsonl | 72 |
| Transport | experiments/results/transport_compression/results.json | 25 |

## Tarefas

- [ ] Script para gerar todas as figuras de manifests JSONL
- [ ] Calcular CI 95% para Etapa 2
- [ ] Gerar figuras 1-10
- [ ] Incluir em article/ como imagens ou texto descritivo

# P07 — Análise Estatística e Geração de Figuras

**Status:** ABERTO  
**Tipo:** Análise / Paper  
**Deps:** H02–H10 (precisa dos resultados)  
**Arquivo:** `experiments/analysis/` (criar)

## O que Produzir

### Tabelas para o Paper

**Tabela 1 — Accuracy × Formato × Categoria de Modelo**
```
              | tiny  | small | medium | large
csv_expanded  |  ?    |  ?    |   ?    |   ?
jsonl_expanded|  ?    |  ?    |   ?    |   ?
tcf_raw       |  ?    |  ?    |   ?    |   ?
tcf_sorted    |  ?    |  ?    |   ?    |   ?
tcf_sorted_dict|  ?   |  ?    |   ?    |   ?
```

**Tabela 2 — Token Count × Formato**
```
formato         | chars | tokens | ratio vs JSONL
csv_expanded    | 600   | 180    | 0.26×
tcf_sorted_dict | 900   | 270    | 0.39×
jsonl_expanded  | 2336  | 700    | 1.00× (baseline)
```

### Figuras para o Paper

| Figura | Hipótese | Tipo |
|--------|----------|------|
| Fig 1 | H02 | Heatmap accuracy × formato × modelo |
| Fig 2 | H03 | Barras agrupadas por camada diagnóstica |
| Fig 3 | H05 | Gráfico de interação 2×2 (sort × query_type) |
| Fig 4 | H09 | Scatter Pareto (accuracy × tokens) |
| Fig 5 | H10 | Curvas de degradação por chunk size |

### Testes Estatísticos

| Hipótese | Teste | Pacote |
|----------|-------|--------|
| H02 | Friedman + Nemenyi post-hoc | `scipy.stats`, `scikit_posthocs` |
| H03 | ANOVA 2×3 fatorial | `pingouin` |
| H05 | ANOVA 2×2 interação | `pingouin` |
| H07, H08 | ANOVA mista | `pingouin` |
| H10 | Regressão logística por formato | `scipy.optimize` |

## Estrutura

```
experiments/analysis/
├── load_results.py    # carrega todos os JSONL em um DataFrame pandas
├── h02_analysis.py    # ANOVA + heatmap
├── h03_analysis.py    # camadas diagnósticas
├── h05_analysis.py    # 2×2 sort × query_type
├── h09_pareto.py      # fronteira Pareto
├── h10_scaling.py     # curvas de degradação
└── figures/           # saída PNG/SVG para o paper
```

## Dependências Python

```
pandas, scipy, pingouin, scikit_posthocs, matplotlib, seaborn
```

Adicionar em `pyproject.toml` como `[project.optional-dependencies] analysis = [...]`.

## Critério de Aceitação

`python experiments/analysis/h02_analysis.py` produz `figures/fig1_heatmap.png` e imprime p-values do teste de Friedman.

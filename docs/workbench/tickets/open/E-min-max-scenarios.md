---
title: E-min-max-scenarios — descobrir limites superiores e inferiores do TCF
type: experiment
status: OPEN
priority: MEDIUM
created: 2026-04-27
origin: Decisao "o tcf funciona bem em que cenarios minimos e maximos?"
see_also:
  - docs/workbench/tickets/open/E-format-comparison-bench.md
  - docs/workbench/tickets/open/T-test-harness-mvp.md
---

# E-min-max-scenarios — onde TCF brilha e onde apaga

Construir matriz de cenarios cobrindo o espaco onde TCF pode ser
testado, identificando:

- **Cenarios MIN** — TCF tem ganho minimo ou perde para alternativas
- **Cenarios MAX** — TCF tem ganho maximo, justificando seu uso
- **Cenarios LIMITE** — onde TCF vira inviavel (ex: dados nested)

## Eixos de variacao

### 1. Tamanho

| Range | Categoria |
|-------|-----------|
| 1-10 rows | nano |
| 10-100 | small |
| 100-1000 | medium |
| 1k-10k | large |
| 10k+ | xlarge |

### 2. Largura

| Range | Categoria |
|-------|-----------|
| 1-3 cols | narrow |
| 4-15 | normal |
| 16-50 | wide |
| 50+ | very_wide |

### 3. Cardinalidade

| Range | Categoria |
|-------|-----------|
| <5 unique values | very_low |
| 5-20 | low |
| 20-100 | medium |
| 100+ | high |
| 1 unique per row | maximum |

### 4. Tipos

| Mix | Categoria |
|-----|-----------|
| 100% numerico | numeric_only |
| 100% string | string_only |
| 50/50 mix | balanced |
| categorical heavy | categorical_dominant |

### 5. Sortedness

| Estado | Categoria |
|--------|-----------|
| ja sorted por col chave | pre_sorted |
| pode ser sortado | sortable |
| ordem semantica | natural_order |
| aleatorio | random |

### 6. Estrutura

| Tipo | Categoria |
|------|-----------|
| single table | flat |
| multi-table com FKs | relational |
| nested objects | nested (TCF nao suporta nativo) |
| time series | temporal |

## Combinacoes notaveis

### Cenarios MAX (TCF deveria brilhar)

| ID | Combinacao | Razao |
|----|-----------|-------|
| MAX1 | medium + normal + low_card + categorical + sortable | RLE+DICT+sort tudo aciona |
| MAX2 | large + wide + low_card | overhead amortizado, RLE explora |
| MAX3 | medium + temporal + numeric | delta encoding (futuro) |
| MAX4 | medium + flat + low_card_categorical | LLM input ideal (Adult-like) |

### Cenarios MIN (TCF tem pouco ganho)

| ID | Combinacao | Razao |
|----|-----------|-------|
| MIN1 | nano + narrow + qualquer | overhead supera ganho |
| MIN2 | medium + numeric_only + maximum_cardinality | sem repeticao |
| MIN3 | wide + random | sem padrao para explorar |

### Cenarios LIMITE (TCF nao se aplica)

| ID | Combinacao | Razao |
|----|-----------|-------|
| LIM1 | nested objects | TCF nao suporta nesting |
| LIM2 | binary fields (image bytes) | TCF e text-only |
| LIM3 | streaming infinito | TCF e batch |

## Datasets para gerar cada combinacao

Use **synthetic generators** controlados:

```python
def gen_dataset(size, width, cardinality, types, sortedness, structure):
    # gera dataset sintetico determinstico com essas caracteristicas
    ...
```

E datasets **reais** quando possivel:
- Adult Census → categorical_dominant + medium + flat + sortable
- TPC-H partsupp → relational + numeric_dominant + medium
- IoT sensor logs → temporal + low_card + large

## Output cientifico

Tabela: **TCF best vs CSV best vs JSON best** em cada cenario:

| Categoria | TCF v0.4 | CSV+gzip | JSON+gzip | Vencedor | Margem |
|-----------|----------|----------|-----------|----------|--------|
| MAX1 (medium+norm+lowcard+cat+sort) | 1500 | 3500 | 4200 | **TCF** | -57% |
| MAX2 (large+wide+lowcard) | 12000 | 28000 | 35000 | **TCF** | -57% |
| MIN1 (nano+narrow) | 180 | 95 | 145 | **CSV** | TCF +90% |
| MIN2 (medium+num+maxcard) | 5800 | 5200 | 7800 | **CSV** | TCF +12% |
| LIM1 (nested) | n/a | 9500 | 12000 | **CSV** | TCF unsupported |

Plus **plot 2D**: eixo X = tamanho, eixo Y = % gain vs CSV+gzip,
linhas por categoria de cardinalidade. Mostra "regiao Pareto" do TCF.

## Achados a documentar

Para o paper:
1. **TCF brilha em datasets** com (medium-large) + (low cardinality
   categorical) + (sortable)
2. **TCF perde overhead em** datasets nano + narrow (recomendar
   CSV/JSON nesses casos)
3. **TCF nao se aplica a** nested + binary + streaming
4. **Magnitude de ganho** em cenarios bons: 30-60% menor que CSV+gzip

## Criterio de aceite

- [ ] 3+ datasets reais + 5+ sinteticos cobrindo as combinacoes
- [ ] Resultados em CSV + plots
- [ ] Documento `min_max_findings.md` com regras claras de quando
  usar TCF vs alternativas
- [ ] Inputs para Cap 8 (Discussao) sobre limitacoes

## Dependencias

- T-test-harness-mvp + E-format-comparison-bench
- Synthetic data generators (a criar em `experiments/harness/scenarios/`)

## Impacto estimado

2 semanas, em paralelo a E-format-comparison-bench.

## Notas para revisar

Quando reabrir:
- Resultados em `experiments/results/harness/min-max/`
- Plot output em `docs/article/figuras/min-max-pareto.png`
- Conclusoes entram em Cap 7 + Cap 8

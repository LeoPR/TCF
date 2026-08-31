# Pesquisa 2026-04-14: Enriquecimento de Perguntas + Stats Ablation Design

## 1. Framework de tipos de perguntas analiticas

Da literatura de BI e analytics, 4 niveis progressivos:

| Nivel | Pergunta | Exemplo (Adult dataset) | Precisa de calculo? |
|-------|----------|------------------------|---------------------|
| **Descriptive** | "O que aconteceu?" | "Qual a media de idade?" | Agregacao |
| **Diagnostic** | "Por que aconteceu?" | "Por que pessoas >50K tem idade maior?" | Comparacao + raciocinio |
| **Predictive** | "O que vai acontecer?" | "Alguem de 25 anos com Bachelors provavelmente ganha >50K?" | Inferencia |
| **Prescriptive** | "O que fazer?" | "Para aumentar renda, qual educacao investir?" | Raciocinio complexo |

Para nosso benchmark, focamos em **Descriptive** (calculavel) e **Diagnostic** (comparativo).
Predictive e Prescriptive sao futuro (requerem raciocinio multi-step).

Fonte: [Analytics8](https://www.analytics8.com/blog/what-are-the-four-types-of-analytics-and-how-do-you-use-them/),
[Harvard Business School](https://online.hbs.edu/blog/post/types-of-data-analysis)

## 2. Perguntas de BI no mundo real

Padroes de dashboards corporativos (Klipfolio, Domo, ThoughtSpot):

### KPIs mais comuns em analytics
- Revenue total e por segmento
- Customer count e churn
- Average order value
- Top N products/customers
- Period-over-period comparison (MoM, YoY)
- Distribution breakdown (% por categoria)
- Threshold alerts (acima/abaixo de meta)

### Mapeamento para nossos datasets

**Adult Census:**
- Revenue → income class distribution
- Segmento → education, workclass, sex
- Top N → top occupations, top countries
- Threshold → "people working >40h/week"
- Comparison → "males vs females in hours worked"

**TPC-H Orders:**
- Revenue → o_totalprice
- Segmento → o_orderpriority, o_orderstatus
- Top N → top customers by total spent
- Threshold → "orders above $100K"
- Period → "orders by year" (o_orderdate)

## 3. Taxonomia de perguntas para TCF benchmark

### 3.1 Perguntas que STATS responde diretamente

| ID | Tipo | Pergunta | STATS field |
|----|------|----------|------------|
| D1 | sum | "Total de X?" | sum=Y |
| D2 | avg | "Media de X?" | avg=Y |
| D3 | count | "Quantas linhas?" | n=Y |
| D4 | max | "Maior valor de X?" | max=Y |
| D5 | min | "Menor valor de X?" | min=Y |

**Medem:** capacidade de ler STATS (nao raciocinio).

### 3.2 Perguntas que STATS NAO responde (raciocinio real)

| ID | Tipo | Pergunta | Por que STATS nao ajuda |
|----|------|----------|------------------------|
| R1 | filter+count | "Quantas pessoas tem age > 50?" | STATS nao tem conditional |
| R2 | filter+avg | "Media de age onde education=Bachelors?" | STATS so tem global |
| R3 | group+count | "Quantas pessoas por sex?" | STATS nao agrupa |
| R4 | argmax | "Qual education tem maior avg age?" | STATS nao tem per-group |
| R5 | comparison | "Males trabalham mais horas que females?" | STATS nao compara grupos |
| R6 | proportion | "Que % ganha >50K?" | STATS nao tem proporção |
| R7 | top-K | "Top 3 occupations mais comuns?" | STATS nao tem ranking |
| R8 | threshold | "Quantos pedidos acima de $100K?" | STATS nao tem threshold |

**Medem:** raciocinio real sobre os dados.

### 3.3 Perguntas heuristicas/qualitativas

| ID | Tipo | Pergunta | Resposta esperada |
|----|------|----------|-------------------|
| H1 | trend | "Horas trabalhadas variam muito?" | Sim/Nao (olhar stdev) |
| H2 | dominance | "Private domina workclass?" | Sim (69%) |
| H3 | balance | "Distribuicao de income e equilibrada?" | Nao (76% <=50K) |
| H4 | relative | "Pessoas mais velhas ganham mais?" | Sim (44 vs 37 avg age) |
| H5 | anomaly | "Ha capital-gain com valores extremos?" | Sim (99999 outlier) |

**Medem:** compreensao de padrao (nao calculo exato).

## 4. Stats Ablation Design para perguntas segmentadas

### O que testar

Para CADA pergunta, rodar com 4 variantes de STATS:

| Variante | STATS incluido? | O que testa |
|----------|----------------|-------------|
| **S0: sem STATS** | Nao | Raciocinio puro |
| **S1: STATS global** (atual) | Sim (n, sum, min, max, avg) | Shortcut para D1-D5 |
| **S2: STATS + distinct** | Sim + distinct count por col cat | Ajuda em R3, R6 |
| **S3: STATS + mode** | Sim + distinct + valor mais frequente | Ajuda em R7, H2 |

### Escalas para ablation

| Escala | N rows | Proposito |
|--------|--------|-----------|
| Micro | 10 | "Funciona com pouquissimo?" |
| Small | 50 | "Amostra representativa minima" |
| Medium | 200 | "Dashboard tipico" |
| Large | 500 | "Limite de contexto" |

### Matriz experimental

```
Perguntas: 5 (D1, R1, R2, R5, H2)
Stats: 2 (S0 sem, S1 com)
Escalas: 3 (10, 100, 500)
Formatos: 2 (CSV, TCF L0)
Modelos: 3 (gemma3:4b, gemma3:12b, gpt-oss)

Total: 5 × 2 × 3 × 2 × 3 = 180 combos
```

Cada combo grava: correct, tier, rel_error, prompt_tokens, latency.

### Metrica principal

**Stats dependency gap:**
```
Gap = Acc@T2(with_stats) - Acc@T2(without_stats)
```

Por tipo de pergunta:
- D1-D5 (stats-answerable): gap esperado ALTO (30-60pp)
- R1-R8 (reasoning): gap esperado BAIXO (<10pp)
- H1-H5 (heuristic): gap esperado VARIAVEL

Se gap em R1-R8 for ALTO → STATS ajudam em raciocinio, nao so shortcut.
Se gap em R1-R8 for BAIXO → STATS so servem para leitura direta.

## 5. STATS como checksum no encoder/decoder

### Encode

Apos encode_columns(), verificar:
```python
# Compute expected STATS from column data
expected_sum = sum(float(v) for v in columns["age"] if v)
# Verify STATS line matches
assert "sum=..." in tcf_text  # matches expected_sum
```

### Decode

Apos decode(), verificar:
```python
# Re-compute from decoded data
decoded_sum = sum(float(row["age"]) for row in decoded_rows if row["age"])
# Compare with STATS from header
assert abs(decoded_sum - stats_sum) < 0.01  # integrity check
```

Se nao bate → dados corrompidos durante transmissao/processamento.

### Nivel de verificacao

| Check | O que verifica | Custo |
|-------|---------------|-------|
| n check | count de rows bate | O(1) |
| sum check | soma numerica bate | O(N) |
| min/max check | extremos batem | O(N) |
| full roundtrip | encode→decode→re-encode = identico | O(N) heavy |

## 6. O que modificar / criar

### Enriquecer banco de perguntas (datasets/questions/)

Adicionar perguntas R1-R8 e H1-H5 aos JSONs existentes, com campo
`stats_answerable: true/false` e `question_category: descriptive/diagnostic/heuristic`.

### Stats ablation script

Novo runner que roda mesmas perguntas COM e SEM STATS, mesmos dados,
e compara accuracy.

### STATS como checksum no encoder

Adicionar verificacao opcional no `encode_columns()` e `decode()`.
Flag: `verify_stats=True`.

---

## 7. Referencias

- [Analytics8 — Four Types of Analytics](https://www.analytics8.com/blog/what-are-the-four-types-of-analytics-and-how-do-you-use-them/)
- [Harvard Business School — Types of Data Analysis](https://online.hbs.edu/blog/post/types-of-data-analysis)
- [Klipfolio — KPIs and BI Dashboards](https://www.klipfolio.com/resources/articles/kpis-business-intelligence-dashboards)
- [TPC-H Business Questions](https://www.tpc.org/tpch/)
- [TQA-Bench (2024)](https://arxiv.org/abs/2411.19504)
- [Domo — Data Analytics Types](https://www.domo.com/learn/article/data-analytics-types)

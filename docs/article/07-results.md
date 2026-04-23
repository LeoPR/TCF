# 7. Resultados: Experimentos LLM (v0.2)

Este capitulo apresenta os experimentos de compreensao por LLMs com
o encoder v0.2, dataset `retail_sales` sintetico realistas (Zipf s=1.0,
ratio 1:10 cliente:pedido), em multiplos modelos e formatos.

Experimentos anteriores com v0.1 (dataset 41 vendas, encoder pre-niveis)
estao em [archive/article_v01/](../../archive/article_v01/) como registro historico.

---

## 7.1 Etapa 1 — Formato × Escala (qwen3:8b fixo)

**Objetivo:** Isolar o efeito do formato variando escala, com modelo fixo.
**Modelos:** qwen3:8b
**Formatos:** CSV, JSONL, TCF L0, L2, L3
**Escalas:** retail_sales(50) e retail_sales(200)
**Questoes:** 8 (q1-q8)
**Total:** 80 combinacoes

### Accuracy por formato (overall)

| Formato | Accuracy | Prompt 200 rows |
|---------|----------|-----------------|
| **tcf_L0** | **75%** | 22K chars |
| **tcf_L2** | **75%** | 19K chars |
| tcf_L3 | 62% | 13K chars |
| csv | 38% | 21K chars |
| jsonl | 19% | 57K chars |

### Efeito de escala (50 vs 200 orders)

| Formato | 50 orders | 200 orders | Delta |
|---------|-----------|------------|-------|
| csv | 62% | **12%** | **-50pp** |
| jsonl | 25% | 12% | -13pp |
| tcf_L0 | 75% | 75% | **0pp** |
| tcf_L2 | 88% | 62% | -26pp |
| tcf_L3 | 75% | 50% | -25pp |

### Findings (F30-F34)

**F30:** TCF escala, CSV/JSONL colapsam. Com 200 orders (~509 vendas),
CSV cai de 62% para 12%, JSONL de 25% para 12%. TCF L0 mantem 75%.

**F31:** SUM/AVG/MAX: TCF = 100% em todos os levels. CSV/JSONL = 0-50%.

**F32:** JSONL com 200 orders gera 57K chars — estrangula contexto.
TCF L3 gera apenas 13K chars (4.4x menor).

**F33:** L0 e L2 empatam em 75%. L3 perde para 62% (indices confundem).

**F34:** q6 (top_product) e q7 (top_spender) sao pontos fracos do TCF.

---

## 7.2 Etapa 2 — Multiplos Modelos × Dados Fixos

**Objetivo:** Comparar 12 modelos no mesmo benchmark.
**Dados fixos:** retail_sales(200) → 509 vendas
**Formatos:** CSV, TCF L0, TCF L2
**Questoes:** 8 (q1-q8)
**Total:** 288 combinacoes

### Ranking completo (Etapa 2 original)

| Modelo | Params | CSV | TCF L0 | TCF L2 | avg |
|--------|--------|-----|--------|--------|-----|
| **gemma3:12b** | 12.2B | 25% | **88%** | 75% | **62%** |
| llama3.1:8b | 8B | 38% | 75% | 50% | 54% |
| gpt-oss:latest | 20.9B | 12% | 75% | 62% | 50% |
| phi4:latest | 14B | 12% | 75% | 62% | 50% |
| qwen3:8b | 8.2B | 0% | 50% | 62% | 38% |
| deepseek-r1:14b | 14.8B | 25% | 50% | 25% | 33% |
| llama3.2:latest | 3.2B | 25% | 50% | 25% | 33% |
| qwen2.5:latest | 7.6B | 25% | 50% | 25% | 33% |
| mistral:latest | 7.2B | 12% | 50% | 25% | 29% |
| phi3:latest | 3.8B | 12% | 25% | 25% | 21% |
| gemma2:9b | 9.2B | 38% | 0% | 0% | 12% |
| deepseek-r1:7b | 7.6B | 0% | 0% | 0% | 0% |

**Overall por formato:** CSV 19% | TCF L0 **49%** | TCF L2 36%

### Findings Etapa 2 (F50-F55)

**F50:** TCF L0 (49%) e 2.5x melhor que CSV (19%) em dados realistas com 12 modelos.

**F51:** gemma3:12b e o melhor modelo (88% em TCF L0).

**F52:** gpt-oss (20.9B) perde para gemma3 (12B). Tamanho nao e tudo —
familia e arquitetura importam mais.

**F53:** gemma2 (0% TCF) vs gemma3 (88% TCF). Diferenca de geracao.

**F54:** deepseek-r1:7b falha totalmente (0%). A versao 14b funciona (33%).

**F55:** CSV colapsa em escala — nenhum modelo >38% em CSV com 200 orders.

> **Caveat critico (F81):** Esses resultados foram depois REINTERPRETADOS
> apos o 3-layer diagnostic e stats ablation. gemma3 88% nao e compreensao
> do formato — e leitura de STATS. Ver secao 7.6.

---

## 7.3 G30 — Hiperparametros (qwen3:8b)

**Objetivo:** Isolar efeito de thinking e temperature.
**Modelo:** qwen3:8b
**Configs:** think on/off × temp 0/0.6 (4 combos)
**Formatos:** TCF L0, TCF L2
**Questoes:** 6
**Total:** 48 combinacoes

### Accuracy por config × formato

| Config | TCF L0 | TCF L2 |
|--------|--------|--------|
| think_on + t=0 | **100%** | 50% |
| think_on + t=0.6 | 83% | 50% |
| think_off + t=0.6 | 83% | **67%** |
| think_off + t=0 | 67% | 50% |

### Findings (F60-F63)

**F60:** Thinking ON + temp=0 = 100% em TCF L0 (melhor combo)

**F61:** TCF L0 >> TCF L2 em todas as configs (media 83% vs 54%)

**F62:** Temperature tem efeito nao-linear (com thinking: t=0 melhor;
sem thinking: t=0.6 melhor)

**F63:** Varios FAIL 0s sugerem respostas vazias/malformadas em L2

---

## 7.4 E-scale-progression (curva accuracy × rows)

**Objetivo:** Curva detalhada de accuracy por escala.
**Modelo:** gemma3:12b
**Formatos:** CSV, TCF L0, TCF L2
**Escalas:** 20, 50, 100, 200, 500, 1000
**Questoes:** 4 representativas (q1_sum, q3_max, q5_count, q6_top_product)
**Total:** 72 combinacoes

### Accuracy × escala

| Scale | Rows | CSV | TCF L0 | TCF L2 |
|-------|------|-----|--------|--------|
| 20 | 52 | 75% | 75% | 50% |
| 50 | 130 | 25% | 75% | 75% |
| 100 | 252 | 25% | **100%** | **100%** |
| 200 | 509 | 50% | **100%** | 75% |
| 500 | 1241 | 50% | 50% | 0% |
| 1000 | 2508 | 25% | 0% | 0% |

### Findings (F85-F89)

**F85:** TCF L0 pico em 100-200 rows (100%)

**F86:** CSV estavel mas mediano (~25-50%), nunca 100%

**F87:** TCF L2 colapsa antes de L0 (0% a 500 rows)

**F88:** Crossover TCF > CSV em 50-200 rows

**F89:** A 1000 rows, tudo colapsa (contexto excedido)

> **Caveat:** Dados refletem leitura de STATS, nao calculo real.
> O pico de 100% em 100-200 rows e onde os STATS sao mais "encontraveis"
> no contexto. Experimento STATS ablation (7.6) quantifica isso.

---

## 7.5 Diagnostic 3-Layer — O grande finding

**Objetivo:** Separar capacidade aritmetica, compreensao de formato,
e capacidade computacional em 3 camadas isoladas.

**Modelos:** gemma3:12b, qwen3:8b, phi4, mistral, llama3.1, gemma2:9b
**Layers:**
- **L0 math_control:** "Some estes 509 numeros: ..." (sem formato)
- **L1 decode_only:** "Liste todos os valores da coluna total" (ler formato)
- **L2 compute:** "Qual a soma de total?" (formato + calculo)

**Formatos (L1, L2):** TCF L0, TCF L2
**Total:** 48 combinacoes

### Accuracy por modelo × camada

| Modelo | L0 math | L1 decode | L2 compute |
|--------|---------|-----------|------------|
| **qwen3:8b** | **50%** | **100%** | 50% |
| gemma3:12b | 0% | 0% | **75%** |
| phi4:latest | 0% | 50% | 75% |
| llama3.1:8b | 0% | 50% | 50% |
| mistral:latest | 0% | 0% | 25% |
| gemma2:9b | 0% | 0% | 0% |

### Findings (F80-F84)

**F80: Nenhum modelo (exceto qwen3) faz aritmetica pura.**
5/6 modelos = 0% em math_control. qwen3 somou 509 numeros em 494s (8 min).

**F81: gemma3 usa STATS como shortcut.**
L0 math 0%, L1 decode 0%, L2 compute 75%. Como e possivel?
Resposta: os STATS lines (`# STATS total: n=509 sum=147445.47 ...`)
fornecem a resposta pronta. O modelo le, nao calcula.

**F82: qwen3 genuinamente processa dados.**
Unico modelo com L1=100% (listou todos 509 valores do TCF L0 e L2)
e com L0>0 (somou manualmente com thinking).

**F83:** phi4 e llama3.1 leem L2 melhor que L0 em decode_only.

**F84:** gemma2:9b = 0% absoluto em tudo (confirma Etapa 2).

> **Este e o finding tier S do paper.** Redefine o que significa
> "modelo entende TCF" — ver proxima secao.

---

## 7.6 E-stats-ablation — Quantificando o shortcut

**Objetivo:** Medir o quanto de accuracy de Etapa 2 vem de STATS.
**Modelos:** gemma3:12b, qwen3:8b, phi4, llama3.1
**Formatos:** TCF L0+stats, L0-stats, L2+stats, L2-stats
**Questoes:** 8
**Total:** 128 combinacoes

### Accuracy com vs sem STATS

| Modelo | L0+stats | L0-stats | Delta L0 | L2+stats | L2-stats | Delta L2 |
|--------|----------|----------|----------|----------|----------|----------|
| gemma3:12b | 88% | 62% | -25pp | 75% | 38% | **-38pp** |
| qwen3:8b | 75% | 12% | **-62pp** | 62% | 50% | -12pp |
| phi4:latest | 75% | 50% | -25pp | 62% | 25% | **-38pp** |
| llama3.1:8b | 75% | 38% | **-38pp** | 50% | 25% | -25pp |

### Accuracy por questao (gemma3:12b)

| Questao | L0+S | L0-S | L2+S | L2-S |
|---------|------|------|------|------|
| q1_sum | OK | **FAIL** | OK | **FAIL** |
| q2_avg | OK | **FAIL** | OK | **FAIL** |
| q3_max | OK | OK | OK | OK |
| q4_min | OK | OK | OK | OK |
| q5_count | OK | OK | FAIL | FAIL |
| q6_top_product | OK | OK | OK | FAIL |
| q7_top_spender | OK | OK | OK | OK |
| q8_distinct | FAIL | FAIL | FAIL | FAIL |

### Findings (F90-F94)

**F90:** STATS inflam accuracy em TODOS os 4 modelos. Delta medio:
-38pp em L0, -28pp em L2. Confirma F81 universalmente.

**F91:** qwen3:8b e o MAIS dependente em L0 (-62pp).
Refuta intuicao de que "thinking models nao precisam de hints".

**F92:** q1_sum e q2_avg sao SEMPRE FAIL sem STATS (4/4 modelos).
Aritmetica em massa nao e factivel para LLMs sem hints.

**F93:** q3_max, q4_min sobrevivem sem STATS (lookups visuais).

**F94:** L2 mais sensivel para gemma3/phi4; L0 mais para qwen3.

### Implicacao critica para o paper

A narrativa muda de:
> "TCF e melhor que CSV para LLMs entenderem dados tabulares"

Para:
> "TCF e uma ESTRATEGIA COMPOSTA: formato columnar compacto + hints
> meta-cognitivos (STATS) que compensam limitacoes aritmeticas dos LLMs.
> Ambos sao necessarios — sem STATS, accuracy cai 25-62pp."

Este e um finding ORIGINAL — nenhum paper anterior testa formatos com
hints embutidos. TCF e o primeiro a propor essa abordagem.

---

## 7.7 Transport Compression

**Objetivo:** Comparar TCF+gzip vs CSV+gzip vs JSONL+gzip (sem LLM).
**Formatos:** CSV, JSONL, TCF L0, L2, L3
**Escalas:** 50, 200, 500, 1000, 5000

### Tamanho apos gzip (bytes)

| Scale | csv+gz | jsonl+gz | L0+gz | L2+gz | L3+gz |
|-------|--------|----------|-------|-------|-------|
| 50 | 1479 | 1690 | 1470 | 1420 | 1467 |
| 200 | 5626 | 6376 | 5028 | 5147 | **4752** |
| 500 | 12681 | 14756 | 11110 | 11422 | **10440** |
| 1000 | 25209 | 30027 | 21572 | 22179 | **19859** |
| 5000 | 125948 | 151577 | 96643 | 100963 | **89472** |

### Findings (F70-F73)

**F70:** TCF L3+gzip e consistentemente menor que CSV+gzip
(29% menor em 5000 rows)

**F71:** L3 e o melhor para transporte (dict reduz vocabulario
para gzip comprimir)

**F72:** JSONL e sempre o pior (chaves JSON resistem ao gzip)

**F73:** Ganho cresce com escala (1% a 50 rows, 29% a 5000)

### Implicacao

Argumento triplo do TCF:
1. **Menos tokens no prompt** (formato columnar)
2. **Menos bytes no transporte** (gzip composto: sort+RLE+dict)
3. **Hints meta-cognitivos** (STATS)

---

## 7.8 Secoes Pendentes

| Experimento | Ticket | Prioridade |
|-------------|--------|------------|
| Etapa 2 Expandida (12 modelos novos 0.6B-14B) | E-benchmark-plan | IN PROGRESS |
| Prompt presentation ablation | E-prompt-presentation | MEDIUM |
| LLM decomprime TCF | E-llm-decompress | LOW |
| Formatos concorrentes (TOON, MD Table) | P-competing-formats | MEDIUM |
| Scaling curve por familia | E-benchmark-plan | HIGH |

## 7.9 Resumo dos Findings

| # | Finding | Ticket origem |
|---|---------|--------------|
| F30-F34 | TCF escala, CSV colapsa (Etapa 1) | Etapa 1 |
| F50-F55 | gemma3 melhor, 12 modelos ranking (Etapa 2) | Etapa 2 |
| F60-F63 | Thinking ON + t=0 = 100% L0 (G30) | H-G30 |
| F70-F73 | TCF+gzip 29% < CSV+gzip (Transport) | P-transport-compression |
| F80-F84 | STATS como shortcut cognitivo (Diagnostic) | H-diagnostic-3layer |
| F85-F89 | Scale sweet spot 100-200 rows (Scale) | E-scale-progression |
| F90-F94 | STATS inflam TODOS modelos (Stats Ablation) | E-stats-ablation |

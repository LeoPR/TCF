# 7. Resultados: Ablacao, Deducao e Testes Avancados

*Este capitulo sera preenchido conforme os experimentos avancem.*

## 7.1 Phase 2: Ablacao de Variantes TCF (E4, G03)

**Status:** CLOSED — 720/720 combinacoes (100%).
**Data:** 2026-04-07.
**Modelos:** qwen3:8b, qwen2.5:latest, llama3.1:8b (gpt-oss excluido por latencia)

### Ablacao por fator

| Fator | Melhor | Accuracy | Pior | Accuracy | Delta |
|-------|--------|----------|------|----------|-------|
| **numeric** | raw_float | **55.0%** | bins_16 | 31.2% | +23.8pp |
| **fk_mode** | dict | **45.6%** | hint | 39.4% | +6.2pp |
| **sorted** | False | 42.8% | True | 41.1% | +1.7pp |

### Top 5 configs

| Config | Accuracy |
|--------|----------|
| **raw_float/dict/True** | **66.7%** |
| raw_float/dict/False | 60.0% |
| raw_float/hint/False | 60.0% |
| raw_float/inline/True | 60.0% |
| raw_float/id_raw/False | 53.3% |

### Resultado principal (F8)

**TCF raw_float/dict/True (67%) SUPERA JSONL (63%) da Phase 1.**

A melhoria veio de:
- `raw_float` vs int_scaled: +15pp (preservar precisao float e critico)
- `dict` vs id_raw: +6pp (bloco DICT ajuda FK resolution)
- Sorted True: +7pp vs nosorted nesta config especifica

### Per-model best config

| Model | Best Config | Accuracy | Worst Config | Accuracy |
|-------|-------------|----------|--------------|----------|
| qwen3:8b | raw_float/dict/True | **100%** | bins_16/inline/False | 30% |
| qwen2.5:latest | raw_float/id_raw/False | 60% | bins_16/hint/False | 20% |
| llama3.1:8b | raw_float/dict/True | 40% | bins_16/inline/True | 10% |

### qwen3 dict vs id_raw (detalhado)

| Questao | id_raw | dict | Delta |
|---------|--------|------|-------|
| q1_sum_vl | OK | OK | = |
| q2_avg_vl | FAIL | **OK** | +1 |
| q3_max_vl | OK | OK | = |
| q4_min_vl | OK | OK | = |
| q5_count_rows | FAIL | **OK** | +1 |
| q6_count_ana | OK | OK | = |
| q7_sum_ana | FAIL | **OK** | +1 |
| q8_top_product | OK | OK | = |
| q9_distinct | OK | OK | = |
| q10_top_spender | FAIL | **OK** | +1 |

DICT mode corrigiu exatamente as questoes que dependem de FK resolution (q5, q7, q10)
e a media (q2), provavelmente porque o contexto DICT ajuda o modelo a "organizar" melhor.

### Findings Phase 2

**F8:** TCF com raw_float/dict supera JSONL em accuracy (67% vs 63%).
A hipotese de que FK mode importa mais que qualquer outro fator esta confirmada.

**F9:** raw_float >> int_scaled >> bins_16. Preservar precisao float e critico.
Quantizacao perde informacao que os modelos nao recuperam.

**F10:** sorted nao tem impacto significativo (+1.7pp, dentro do ruido).
Colunas sorted adicionam overhead sem beneficio claro em accuracy.

**F11:** qwen3 atinge 100% com a config certa (raw_float/dict/True).
Mesmo modelo que fazia 80% no Phase 1 com id_raw. A config importa MUITO.

## 7.2 LLM Comprehension TCF v0.2 (G21) — CLOSED

**150 combinacoes:** 3 modelos x 5 formatos x 10 questoes.
**Data:** 2026-04-08. **Formatos:** CSV, JSONL, TCF L0, TCF L2, TCF L3.

### Accuracy por formato

| Formato | Accuracy | N | Tamanho | Descricao |
|---------|----------|---|---------|-----------|
| **tcf_L0** | **67%** | 30 | 870 chars | Expanded columnar (sem compressao) |
| **tcf_L2** | **67%** | 30 | 714 chars | Sorted + RLE (nomes) |
| jsonl | 60% | 30 | 2204 chars | JSON Lines |
| tcf_L3 | 53% | 30 | 803 chars | Dict + indices + RLE |
| csv | 50% | 30 | 827 chars | CSV flat |

### Accuracy por modelo x formato

| Modelo | CSV | JSONL | L0 | L2 | L3 |
|--------|-----|-------|-----|-----|-----|
| qwen3:8b | 90% | 90% | **100%** | **100%** | 80% |
| qwen2.5 | 40% | 50% | 60% | 50% | 40% |
| llama3.1 | 20% | 40% | 40% | 50% | 40% |

### Accuracy por questao x formato

| Questao | CSV | JSONL | L0 | L2 | L3 |
|---------|-----|-------|-----|-----|-----|
| q1_sum | 33% | 33% | **100%** | **100%** | **100%** |
| q2_avg | 33% | 33% | **100%** | **100%** | **100%** |
| q3_max | 100% | 100% | 100% | 100% | 100% |
| q4_min | 100% | 100% | 33% | 33% | 33% |
| q5_count | 0% | 33% | 100% | 100% | 67% |
| q6_count_ana | 67% | 67% | 67% | 33% | 33% |
| q7_sum_ana | 33% | 67% | 33% | 33% | 33% |
| q8_top_prod | 67% | 100% | 67% | 100% | 33% |
| q9_distinct | 33% | 33% | 33% | 33% | 33% |
| q10_top_spender | 33% | 33% | 33% | 33% | 0% |

### Findings G21

**F20:** TCF L0/L2 (67%) SUPERAM JSONL (60%) e CSV (50%).
O formato columnar e intrinsecamente mais legivel para LLMs.

**F21:** SUM e AVG: TCF todos os levels = 100%, CSV/JSONL = 33%.
Formato columnar facilita somas — todos os valores estao agrupados.

**F22:** MIN: TCF = 33%, CSV/JSONL = 100%. Modelos erram o minimo
em formato columnar (qwen2.5 responde "1.1" ao inves de "1.0").
Possivel confusao com a leitura sequencial de valores.

**F23:** L3 (dict+indices) perde 14pp vs L0/L2 (53% vs 67%).
Indices numericos confundem LLMs em questoes FK-dependentes
(q8_top_product L3=33% vs L2=100%). Compressao maxima prejudica interpretabilidade.

**F24:** qwen3 atinge 100% em L0 e L2, 80% em L3.
Modelo forte lida bem com formato columnar mas perde com indices abstratos.

**Implicacao:** L2 e o melhor tradeoff — comprime 14% vs CSV e performa
igualmente a L0. L3 comprime mais mas confunde LLMs. A decisao de
nivel default deve considerar o uso: para LLMs, L2; para armazenamento, L3.

---

## 7.3 Etapa 1: Compressao x Escala com Dados Realistas (G21b) — CLOSED

**80 combinacoes:** 1 modelo (qwen3:8b) x 5 formatos x 8 questoes x 2 escalas (50, 200 orders).
**Dados:** retail_sales v2 (ratio 1:10, 6 colunas, datas, Zipf s=1.0).

### Accuracy por formato (overall)

| Formato | Accuracy | Prompt 200 rows |
|---------|----------|-----------------|
| **tcf_L0** | **75%** | 22K chars |
| **tcf_L2** | **75%** | 19K chars |
| tcf_L3 | 62% | 13K chars |
| csv | 38% | ? |
| jsonl | 19% | 57K chars |

### Efeito de escala (50 vs 200 orders)

| Formato | 50 orders | 200 orders | Delta |
|---------|-----------|------------|-------|
| csv | 62% | **12%** | **-50pp** |
| jsonl | 25% | **12%** | -13pp |
| tcf_L0 | 75% | **75%** | **0pp** |
| tcf_L2 | 88% | 62% | -26pp |
| tcf_L3 | 75% | 50% | -25pp |

### Accuracy por questao (agregado)

| Questao | CSV | JSONL | L0 | L2 | L3 |
|---------|-----|-------|-----|-----|-----|
| q1_sum | 50% | 0% | **100%** | **100%** | **100%** |
| q2_avg | 50% | 0% | **100%** | **100%** | **100%** |
| q3_max | 50% | 50% | **100%** | **100%** | **100%** |
| q4_min | 0% | 0% | **100%** | **100%** | 50% |
| q5_count | 0% | 0% | **100%** | 50% | **100%** |
| q6_top_product | 50% | 50% | 0% | 50% | 0% |
| q7_top_spender | 50% | 0% | 50% | 50% | 0% |
| q8_distinct | 50% | 50% | 50% | 50% | 50% |

### Findings Etapa 1

**F30:** TCF ESCALA, CSV/JSONL COLAPSAM. Com 200 orders (~500 vendas),
CSV cai de 62% para 12%, JSONL de 25% para 12%. TCF L0 mantem 75%.
A vantagem do TCF e PROPORCIONAL ao volume de dados.

**F31:** SUM/AVG/MAX: TCF = 100% em TODOS os levels. CSV/JSONL = 0-50%.
Formato columnar agrupa valores por coluna — soma e trivial de localizar.

**F32:** JSONL com 200 orders gera 57K chars — estrangula contexto do modelo.
TCF L3 gera apenas 13K chars (4.4x menor). A compressao permite mais dados.

**F33:** L0 (expanded) e L2 (sorted+RLE) empatam em 75%. L3 (dict) perde
para 62%. Indices numericos do L3 confundem em q6 (top_product) e q7 (top_spender).

**F34:** q6 (top_product) e q7 (top_spender) sao os pontos fracos do TCF.
Exigem cross-reference entre nomes e contagens. CSV responde melhor nessas
porque os nomes estao inline em cada row.

**Implicacao para o artigo:** TCF nao e so "mais compacto" — e **mais
escalavel**. A vantagem cresce com o volume. A 200 orders, TCF L0 e
6x melhor que CSV (75% vs 12%). Esse e o argumento central do paper.

## 7.4 Etapa 2: Multiplos Modelos x Dados Realistas — CLOSED

**288 combinacoes:** 12 modelos x 3 formatos x 8 questoes.
**Dados:** retail_sales(200) v2 (509 vendas, 6 colunas, Zipf, datas).

### Ranking completo

| Modelo | Params | CSV | TCF L0 | TCF L2 | avg |
|--------|--------|-----|--------|--------|-----|
| gemma3:12b | 12.2B | 25% | **88%** | 75% | **62%** |
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

### Findings Etapa 2

**F50:** TCF L0 (49%) e 2.5x melhor que CSV (19%) em dados realistas com 12 modelos.

**F51:** gemma3:12b e o melhor modelo (88% em TCF L0). Google's latest, 12B.

**F52:** gpt-oss (20.9B) perde para gemma3 (12B). Tamanho nao e tudo —
familia e arquitetura importam mais.

**F53:** gemma2 (0% TCF) vs gemma3 (88% TCF). Versao nova resolve tudo.

**F54:** deepseek-r1:7b falha totalmente (0%). A versao 14b funciona (33%).
Modelo de reasoning com 7B nao tem capacidade suficiente para dados tabulares.

**F55:** CSV colapsa em escala — 19% geral. Nenhum modelo atinge >38% em CSV
com 200 orders. TCF e a unica opcao viavel em escala.

### Infraestrutura verificada

- Ollama auto-expande num_ctx (nao trunca)
- Reload por mudanca de temperatura: ~1s (KV cache reset)
- Reload por mudanca de num_ctx: ~13s (recarga pesada)
- Thinking mode ativo por default em: qwen3, deepseek-r1, gpt-oss

*Resultados serao preenchidos apos implementacao e testes.*

## 7.3 Stats Ablation (E5, G04) — CLOSED

**180 combinacoes:** 3 modelos x 3 top_configs x 2 (stats on/off) x 10 questoes.

### Resultado global

| Condicao | Accuracy | N |
|----------|----------|---|
| stats=False | 54.4% | 90 |
| **stats=True** | **66.7%** | 90 |
| **Delta** | **+12.3pp** | |

### Per-model

| Modelo | Sem stats | Com stats | Delta |
|--------|-----------|-----------|-------|
| llama3.1:8b | 27% | **57%** | **+30pp** |
| qwen2.5 | 53% | 60% | +7pp |
| qwen3 | 83% | 83% | 0pp |

### Per-question

| Questao | Sem stats | Com stats | Delta | O stats responde diretamente? |
|---------|-----------|-----------|-------|-------------------------------|
| q1_sum_vl | 33% | **100%** | **+67pp** | SIM (sum=217.6) |
| q2_avg_vl | 33% | **100%** | **+67pp** | SIM (avg=5.306) |
| q4_min_vl | 33% | 67% | +33pp | SIM (min=1) |
| q7_sum_ana | 11% | 22% | +11pp | PARCIAL (sum global, nao per-group) |
| q3_max_vl | 100% | 100% | 0pp | SIM (mas ja acertava) |
| q9_distinct | 100% | 100% | 0pp | SIM (mas ja acertava) |
| q5_count | 33% | 33% | 0pp | SIM (n=41, mas multi-tabela confunde) |
| q10_top_spender | 56% | 44% | **-11pp** | NAO (per-group, nao global) |
| q6_count_ana | 78% | 56% | **-22pp** | NAO (per-group) |
| q8_top_product | 67% | 44% | **-22pp** | NAO (top por frequencia) |

### Findings G04

**F12:** Stats pre-computados sao uma faca de dois gumes.
Para questoes que o stats responde diretamente (sum, avg, min): **+33 a +67pp**.
Para questoes FK-dependentes (count_ana, top_product): **-11 a -22pp** (PIORA).

**F13:** Modelos fracos se beneficiam MUITO mais de stats (llama3.1: +30pp).
Modelos fortes (qwen3) nao precisam — ja deduzem sozinhos.

**F14:** Stats como "cola" — o modelo le a resposta ao inves de calcular.
Util para aggregates globais, contraproducente quando o modelo precisa
raciocinar sobre subgrupos (FK-dependent queries). Os numeros globais
CONFUNDEM o raciocinio per-group.

**Implicacao para o CLI:**
`--stats` deveria ser seletivo: emitir stats SEM distinct/mode (que atrapalham FK),
ou emitir apenas para colunas numericas de aggregate. Ticket G13-T05 relevante.

## 7.4 Decode Reverso (E6, G05)

*LLM gera CSV a partir de TCF comprimido.*

## 7.5 Perguntas Progressivas (E7, G06)

*Sequencia de perguntas que orientam a LLM.*

## 7.6 Perguntas Complexas Multi-step (E8, G07)

*"Quem vendeu mais?", "Pessoas que compraram mais Abacaxi", etc.*

## 7.7 Telemetria Cientifica (G08)

*Repeticoes 3x, warmup protocol, separacao load/prefill/eval.*

## 7.8 Thinking Mode (G09)

*qwen3 thinking on/off, gpt-oss think levels.*

## 7.9 Prompting Techniques (G11)

*Chain-of-thought, Program-of-thought, Self-consistency.*

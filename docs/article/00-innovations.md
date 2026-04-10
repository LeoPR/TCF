# Inovacoes Teoricas do TCF (v0.2)

Este arquivo registra as inovacoes teoricas **comprovadas por experimentos**
usando o encoder v0.2 e o dataset `retail_sales` (200 orders, 509 vendas).

Experimentos anteriores (v0.1, dataset 41 vendas) estao em
[archive_v01/](archive_v01/) apenas como registro historico.

---

## I1: Formato Columnar Textual (comprovado)

**Inovacao:** Primeiro formato columnar textual proposto para consumo por LLMs.
Toda a literatura (Sui et al. 2024, TabLLM 2023, PoT 2023) usa formatos
row-oriented (CSV, JSON, Markdown, HTML, NL).

**Evidencia:**
- Compression benchmark (55 tests): TCF L3 comprime em 10/12 cenarios sinteticos
- TCF L3 vs JSONL: **56-91% menor** em todos os cenarios
- TCF L3 vs CSV: 26-66% menor em dados com repeticao (retail, logs, survey)
- Roundtrip 100% reversivel (112 testes passando)

**Base teorica:** Orientacao columnar elimina repeticao de nomes de campo
(overhead O(K) vs O(N×K) em JSONL). Agrupamento de valores por coluna
permite RLE textual legivel.

---

## I2: RLE Textual como Compressao LLM-Friendly (comprovado)

**Inovacao:** Run-Length Encoding aplicado sobre colunas sorted como
compressao **textualmente interpretavel**. Notacao `N*val` e legivel
por humanos e LLMs.

**Evidencia:**
- Dataset retail_sales 5000 orders: TCF L2 45K chars vs CSV 73K chars (62%)
- LLMs leem RLE corretamente: diagnostic F82 (qwen3 100% em decode_only com L2)
- Phi4/llama3.1 leem L2 melhor que L0 em algumas questoes (F83)

**Base teorica:** RLE e a compressao textual mais simples que preserva
legibilidade. Alternativas (delta encoding, dict refs globais) sao candidatas
para investigacao futura mas nao comprovadas.

---

## I3: STATS como Hints Meta-Cognitivos (comprovado E-stats-ablation)

**Inovacao:** Incluir estatisticas pre-computadas (`# STATS col: n=... sum=... min=...`)
no header TCF como hints gratuitos para a LLM. **Primeiro formato a embutir
meta-cognicao no input.**

**Evidencia (128 combos, 4 modelos):**

| Modelo | L0+stats | L0-stats | Delta L0 | L2+stats | L2-stats | Delta L2 |
|--------|----------|----------|----------|----------|----------|----------|
| gemma3:12b | 88% | 62% | -25pp | 75% | 38% | -38pp |
| qwen3:8b | 75% | 12% | **-62pp** | 62% | 50% | -12pp |
| phi4:latest | 75% | 50% | -25pp | 62% | 25% | -38pp |
| llama3.1:8b | 75% | 38% | -38pp | 50% | 25% | -25pp |

**Findings:**
- **F90:** STATS inflam accuracy em TODOS os modelos (delta -25 a -62pp)
- **F92:** SUM e AVG sao IMPOSSIVEIS sem STATS (4/4 modelos FAIL)
- **F93:** MAX, MIN, COUNT sobrevivem sem STATS (lookups visuais)

**Base teorica:** LLMs nao conseguem somar 509 numeros em massa.
STATS atuam como "cola cognitiva" — o modelo le a resposta pronta
para agregacoes que nao saberia calcular. Overhead < 5%.

**Implicacao:** TCF nao e apenas um formato — e uma **estrategia composta**
formato columnar + hints meta-cognitivos. Ambos sao necessarios.

---

## I4: Niveis Progressivos de Compressao (comprovado)

**Inovacao:** 4 niveis progressivos onde cada um sacrifica algo especifico
em troca de compactacao:

| Level | O que mantem | O que perde | Reversivel |
|-------|-------------|-------------|------------|
| L0 | Tudo (ordem, nomes, valores) | Nada | 100% |
| L1 | Tudo (RLE de runs naturais) | Nada | 100% |
| L2 | Nomes, valores (reordena) | Ordem original | 100% dos dados |
| L3 | Indices + dict, valores | Nomes inline | 100% com dict |

**Evidencia:** Compression benchmark 12 cenarios × 4 levels = 48 testes
roundtrip, todos passando. L3 e o mais compacto, L0/L2 sao os melhores
para accuracy de LLMs.

**Base teorica:** Diferentes usos requerem diferentes tradeoffs.
Transporte → L3 (maximum compression). LLM reasoning → L0 ou L2.

---

## I5: Transport Compression Benefit (comprovado P-transport-compression)

**Inovacao:** TCF nao e apenas mais legivel — e **mais eficiente no
transporte binario** (gzip) que CSV e JSONL.

**Evidencia (5 escalas, 5 formatos):**

| Scale | csv+gz | L0+gz | L3+gz | L3 vs csv |
|-------|--------|-------|-------|-----------|
| 50 | 1479 | 1470 | 1467 | -0.8% |
| 200 | 5626 | 5028 | 4752 | -15.5% |
| 1000 | 25209 | 21572 | 19859 | -21.2% |
| 5000 | 125948 | 96643 | 89472 | **-29.0%** |

**Findings:**
- **F70:** TCF L3+gzip e 29% menor que CSV+gzip em 5000 rows
- **F71:** L3 e o melhor para transporte (dict reduz vocabulario para gzip)
- **F72:** JSONL e sempre o pior (chaves JSON resistem ao gzip)
- **F73:** Ganho cresce com escala

**Base teorica:** Sort + RLE pre-processa os dados de forma que o LZ77
do gzip comprime melhor. Nao ha redundancia — sao ganhos compostos.

**Implicacao:** Argumento triplo do TCF:
1. Menos tokens no prompt (formato columnar)
2. Menos bytes no transporte (gzip composto)
3. Hints meta-cognitivos (STATS)

---

## I6: Diagnostico 3-Layer (comprovado H-diagnostic-3layer)

**Inovacao:** Metodologia para separar 3 capacidades distintas do LLM:
- **Layer 0 (math_control):** aritmetica pura sem formato
- **Layer 1 (decode_only):** ler formato e listar valores
- **Layer 2 (compute):** formato + operacao (pipeline completo)

**Evidencia (6 modelos × 3 camadas):**

| Modelo | L0 math | L1 decode | L2 compute |
|--------|---------|-----------|------------|
| qwen3:8b | 50% | **100%** | 50% |
| gemma3:12b | 0% | 0% | **75%** |
| phi4:latest | 0% | 50% | 75% |
| llama3.1:8b | 0% | 50% | 50% |
| mistral:latest | 0% | 0% | 25% |
| gemma2:9b | 0% | 0% | 0% |

**Findings:**
- **F80:** 5/6 modelos falham em math_control (somar 509 numeros)
- **F81:** gemma3 falha L0 e L1 mas acerta L2 → le STATS, nao calcula
- **F82:** qwen3 e o unico que genuinamente processa dados (thinking real)

**Base teorica:** Metodologia diagnostica similar a ablation studies em ML.
Permite atribuir causalidade: "modelo X nao sabe formato" vs "nao sabe
calcular" vs "nao consegue compor".

**Implicacao critica:** "Accuracy alta em TCF" nao significa "modelo
entende TCF". Pode significar "modelo le STATS". O diagnostic 3-layer
e essencial para interpretar resultados de benchmarks.

---

## I7: Escalabilidade com Degradacao Conhecida (comprovado E-scale-progression)

**Inovacao:** Primeira caracterizacao sistematica de accuracy vs row count
para formatos tabulares em LLMs.

**Evidencia (gemma3:12b, 6 escalas):**

| Scale | CSV | TCF L0 | TCF L2 |
|-------|-----|--------|--------|
| 20 | 50% | **100%** | 75% |
| 50 | 25% | 75% | 75% |
| 100 | 25% | **100%** | **100%** |
| 200 | 50% | **100%** | 75% |
| 500 | 50% | 50% | 0% |
| 1000 | 25% | 0% | 0% |

**Findings:**
- **F85:** TCF L0 pico de 100% em 100-200 rows
- **F86:** CSV estavel mas mediano (~25-50%)
- **F88:** Crossover TCF>CSV em 50-200 rows
- **F89:** A 1000 rows, tudo colapsa (contexto excedido)

**Base teorica:** Sweet spot do TCF e onde os STATS ainda sao encontraveis
no contexto. Acima disso, o modelo "perde" os hints no meio do texto.

**Implicacao:** TCF nao e solucao universal — e otimizado para a faixa
50-500 rows. Para datasets maiores, chunking ou outras estrategias
sao necessarias.

---

## Inovacoes Pendentes (a comprovar)

| ID | Inovacao | Ticket | Prioridade |
|----|----------|--------|-----------|
| I8 | LLM decodifica TCF → CSV | E-llm-decompress | LOW |
| I9 | Ablacao de apresentacao (idioma, wording, decoracao) | E-prompt-presentation | MEDIUM |
| I10 | Formatos concorrentes (TOON, MD Table) no mesmo benchmark | P-competing-formats | MEDIUM |
| I11 | Scaling curve por familia (1B → 20B) | E-benchmark-plan | HIGH |
| I12 | Tipos de dados (base64, datas, mixed) | P-data-types | MEDIUM |
| I13 | Compressao alternativa (delta encoding, dict global) | H-compression-layers | LOW |

---

## Posicionamento vs Literatura

**Nenhum trabalho anterior testa:**
- Formato columnar para LLMs (todos usam row-oriented)
- RLE textual aplicado a serializacao LLM-friendly
- STATS embutidos como hints meta-cognitivos
- Transport compression de formatos LLM-friendly
- Diagnostico 3-layer para atribuir causalidade

**Relacao com estado da arte:**
- **Sui et al. 2024** testa HTML/MD/CSV/JSON/NL mas nao columnar nem compressao
- **TabLLM 2023** foca em classificacao, nao em format comparison
- **PoT 2023** poderia resolver a limitacao aritmetica (citar como futuro trabalho)

TCF preenche um gap — e o primeiro a combinar formato + compressao + hints.

# 7. Resultados: Linhas A e B em datasets canonicos com naturalidade controlada

Este capitulo apresenta os resultados centrais do paper. A organizacao
segue dois eixos ortogonais que estruturaram toda a M-series:

1. **Paradigma** — Linha A (LLM le TCF e calcula) vs Linha B (LLM gera SQL,
   SQLite executa)
2. **Naturalidade da pergunta** — N0 schema-aware -> N1 system-aware ->
   N2 business-intent -> N3 business + contexto

Cada celula da tabela 2D foi cobertura experimentalmente (Adult Census
single-table, TPC-H sf001 multi-tabela; modelos locais e comerciais;
familias OpenAI e Anthropic). Total: **2256 records** sobre 4 paradigmas
× 2 datasets × 7 modelos comerciais + 13 modelos locais.

Resultados anteriores com `retail_sales` sintetico (etapas 1+2 v0.2,
F-Q1..F-Q24) estao resumidos em [05-results-e1-e2.md](05-results-e1-e2.md)
e detalhados em
[../findings/01-origins-Q01-Q12.md](../findings/01-origins-Q01-Q12.md) +
[../findings/02-linha-b-Q13-Q24.md](../findings/02-linha-b-Q13-Q24.md).

---

## 7.1 Setup experimental

### Datasets canonicos

**Adult Census** (UCI ML Repository, 48,842 linhas, 15 colunas):
- Single-table com tipos mistos (INTEGER, TEXT) e colunas hifenadas
  (`hours-per-week`, `marital-status`)
- Coluna alvo `class` com distribuicao 76% `<=50K` / 24% `>50K`
- Nulos textuais (`?`) em ~6% das linhas

**TPC-H sf001** (TPC, 8 tabelas):
- Multi-tabela com FKs em topologia star/snowflake
- Tabela fact `partsupp` (8000 linhas), dim `supplier` (100), dim `part` (2000)
- Multiplas colunas com semantica monetaria (`ps_supplycost`,
  `p_retailprice`, `l_extendedprice`, `o_totalprice`) — fonte central
  de schema ambiguity

Sampling: `volume=100` linhas por seed, `stratify_by="class"` em Adult
e FK-preserving sampling em TPC-H. Metricas inline TVD/JSD/Hellinger/
Wilson registradas no manifest.

### Naturalidade — taxonomia N0..N3

Mesma pergunta logica em 4 wordings:

| Nivel | Caracteristica | Exemplo (q_avg_hours_male) |
|-------|----------------|---------------------------|
| **N0** | Nomes literais de coluna/tabela, hints tecnicos | "Qual a media de hours-per-week para linhas com sex igual a 'Male'?" |
| **N1** | Prosa do dominio, ainda system-aware | "Qual a media de horas trabalhadas por semana entre os homens?" |
| **N2** | Business intent, sem mencionar schema | "Em media, quantas horas semanais os homens trabalham?" |
| **N3** | Business + contexto implicito | "Quanto tempo a forca de trabalho masculina dedica ao trabalho por semana?" |

Ground truth e identico nos 4 niveis. 7 questoes por dataset cobrem
agg full-table, distinct count, top categorical, filter+count, filter+avg.

### Modelos testados

**Comerciais (OpenAI + Anthropic, 7 modelos):**

| Familia | Modelo | Tier | Reasoning? |
|---------|--------|------|-----------|
| OpenAI | gpt-5.4 | full | sim |
| OpenAI | gpt-5.4-mini | mid | sim |
| OpenAI | gpt-5.4-nano | nano | sim |
| OpenAI | gpt-4o-mini | controle | nao |
| Anthropic | claude-opus-4-7 | full | sim (adaptive) |
| Anthropic | claude-sonnet-4-6 | mid | sim (enabled) |
| Anthropic | claude-haiku-4-5 | nano | sim (enabled) |

**Locais (Ollama, 13 modelos):** qwen3 (0.6b, 1.7b, 4b, 4b-thinking,
8b, 14b), qwen2.5-coder:7b, phi4 (14b), gemma3 (4b, 12b),
mistral-nemo:latest (12b), granite3.3:8b, deepseek-r1:14b, gpt-oss:20b.

Setup: temperature=0, prompt caching ativo. Custo total: $9.46 USD.

---

## 7.2 Linha B em Adult — F-Q25, F-Q30, F-Q32

Baseline single-table com SQL gen + execucao SQLite.

### Locais (3 modelos baseline + 10 borda)

| Modelo | N0 | N1 | N2 | N3 |
|--------|----|----|----|----|
| qwen3:14b | 100% | 100% | 100% | 100% |
| phi4:latest | 100% | 100% | 100% | 86% |
| qwen2.5-coder:7b | 86% | 71% | 86% | 81% |

qwen3:14b atinge **100% em todos os niveis** — confirmou H-TCF2
generalizando para single-table com colunas hifenadas (F-Q25). Mecanismo
da unica falha persistente em qwen2.5-coder: nao usa aspas duplas em
`hours-per-week` em SQLite (limitacao de modelo, nao do paradigma).

### Comerciais

| Modelo | N0 | N1 | N2 | N3 |
|--------|----|----|----|----|
| gpt-5.4 | 100% | 100% | 100% | 100% |
| gpt-5.4-mini | 100% | 100% | 100% | 100% |
| gpt-5.4-nano | 100% | 86% | 86% | 90% |
| gpt-4o-mini | 86% | 86% | 86% | 86% |
| claude-haiku-4-5 | 100% | 100% | 100% | 95% |
| claude-sonnet-4-6 | 100% | 100% | 100% | 86% |
| claude-opus-4-7 | 100% | 100% | 100% | 86% |

**F-Q32**: gpt-5.4 e gpt-5.4-mini sao **100% imunes a naturalidade**
em Adult Linha B. Anthropic atinge 96-99% global. **Linha B em
single-table com colunas inequivocas e essencialmente um problema
resolvido** para modelos top.

---

## 7.3 Linha A em Adult — F-Q12 refinado, F-Q28, F-Q29, F-Q31

Mesmo dataset, mas LLM le os dados em TCF L2 e calcula direto sem SQL.

### Locais — bimodalidade revelada (F-Q28)

13 modelos × 4 niveis × 7 questoes × 3 seeds:

| Modelo | Adult Linha A overall |
|--------|----------------------|
| qwen2.5-coder:7b | 62% |
| phi4:latest | 56% |
| deepseek-r1:14b (reasoning local) | 57% |
| qwen3:14b | 51% |
| qwen3:1.7b | 46% |
| ... | 43-46% |
| gpt-oss:latest (20B MXFP4) | 29% |
| qwen3:0.6b | 7% (capacity floor) |

Ceiling estrutural ~50-62%. **Decomposicao por tipo de questao** revela
a verdadeira historia (F-Q28):

| Tipo de questao | Acc local | Mecanismo |
|-----------------|-----------|-----------|
| Full-table agg via STATS hint (count, avg, max, sum) | **100%** | LLM le STATS hint pre-computada |
| Lookup categorical (top_education) | 50-67% | LLM precisa contar ocorrencias |
| Filter + agg (`WHERE` + `COUNT/AVG`) | **0-11%** | LLM precisa iterar+filtrar mentalmente |
| Distinct count | **0%** | LLM precisa coletar valores unicos |

F-Q12 antigo ("Linha A satura em ~60-70%") fica refinado: nao e um
ceiling unico, e **bimodal** — 100% em casos onde STATS resolve, 0%
em casos onde precisa operar sobre dados.

### Naturalidade NAO degrada Linha A em locais — F-Q29

13 modelos × 4 niveis: variacao N0->N3 fica em **±5-14pp dentro do
CI Wilson** em todos os modelos. Cinco modelos com Δ=0pp.

| Modelo | N0 | N1 | N2 | N3 |
|--------|----|----|----|----|
| qwen3:14b | 51% | 48% | 48% | 48% |
| phi4 | 56% | 57% | 52% | 57% |
| qwen2.5-coder:7b | 62% | 62% | 57% | 52% |

**Mecanismo**: o gargalo de Linha A local e aritmetica sobre 100+ valores,
nao compreensao da pergunta. Wordings ficam invisiveis abaixo do floor
estrutural. **H_natural-1 rejeitada para Linha A em locais.**

### Comerciais reasoning quebram o ceiling — F-Q31

Substituindo locais por comerciais com reasoning:

| Modelo | Tipo | Adult Linha A |
|--------|------|---------------|
| **gpt-5.4** | reasoning | **95.2%** |
| gpt-5.4-nano | reasoning (cheap) | 86.9% |
| gpt-5.4-mini | reasoning | 82.1% |
| gpt-4o-mini | non-reasoning | 52.4% |
| claude-haiku-4-5 | reasoning (com thinking) | 79.8% |
| claude-sonnet-4-6 | reasoning | 77.4% |
| claude-opus-4-7 | reasoning (adaptive) | 76.2% |

**Achado central**: o eixo limitante NAO e tamanho, e **reasoning**.
gpt-4o-mini (non-reasoning, mesmo sendo da OpenAI) cai para 52% — range
dos locais. gpt-5.4-nano (reasoning, $0.20/1M tokens) faz 87% — quebra
o ceiling local com modelo barato.

Em filter+agg especificamente:

| Question | Locais top | gpt-5.4 | gpt-4o-mini |
|----------|-----------|---------|-------------|
| q_count_high_class | 0-7% | 100% | 0% |
| q_avg_hours_male | 0% | 100% | 0% |
| q_distinct_workclass | 0% | 100% | 33% |

**F-Q12/F-Q28 ceiling era propriedade de modelos non-reasoning**, nao
limitacao universal do paradigma.

---

## 7.4 Linha B em TPC-H — F-Q33, F-Q34

Multi-tabela introduz nova dimensao: schema com colunas semanticamente
proximas. TPC-H tem `ps_supplycost`, `p_retailprice`, `l_extendedprice`,
`o_totalprice` — todas plausiveis interpretacoes de "preco/valor".

### Naturalidade DEGRADA Linha B em TPC-H — locais (F-Q33)

| Modelo | N0 | N1 | N2 | N3 | Gap N0->N2 |
|--------|----|----|----|----|----|
| qwen3:14b | 95% | 95% | **62%** | 95% | -33pp |
| phi4:latest | 95% | 81% | 57% | 52% | -38pp |
| qwen2.5-coder:7b | 95% | 95% | **52%** | 67% | -43pp |

qwen3:14b — **imune em Adult** — cai 33pp em N2 TPC-H. F-Q30 (degradacao
seletiva em locais) era especifica de single-table.

**Mecanismo identificado** (3 padroes reproduzaveis):

1. **q_sum N2** ("valor total comprometido em fornecimento"): LLM gera
   `SUM(ps_supplycost * ps_availqty)` — interpretacao business-correct
   ("valor comprometido em estoque") mas divergente do GT (soma simples
   de cost).

2. **q_lookup N2** ("item mais caro do catalogo"): LLM usa
   `ORDER BY p.p_retailprice DESC` — escolhe **retail price** em vez de
   **supply cost**. Ambas existem, ambas plausiveis. **q_lookup N2 = 0/9
   em todos os locais.**

3. **q_lookup_value N2** ("qual o item mais caro"): LLM retorna NOME do
   part em vez de VALOR numerico. Ambiguidade de tipo de resposta.

### Naturalidade DEGRADA tambem em comerciais top — F-Q34

| Modelo | N0 | N1 | N2 | N3 | Gap N0->N2 |
|--------|----|----|----|----|----|
| gpt-5.4 | 100% | 100% | **57%** | 86% | **-43pp** |
| gpt-5.4-mini | 100% | 100% | **57%** | 86% | -43pp |
| gpt-5.4-nano | 95% | 95% | 52% | 81% | -43pp |
| gpt-4o-mini | 95% | 81% | 48% | 62% | -47pp |
| claude-sonnet-4-6 | 100% | 100% | 67% | 86% | -33pp |
| claude-opus-4-7 | 100% | 95% | 52% | 86% | -48pp |

**F-Q32 (imunidade comercial em Linha B) NAO generaliza para multi-tabela.**
Mesmo gpt-5.4 (frontier janeiro 2026) cai 43pp.

**q_sum N2/N3 = 0/12 universal** em todos os comerciais. **q_lookup_value
N2 = 0/12 universal.** Schema linking continua problema aberto em 2026.

Sub-finding contraintuitivo: comerciais frequentemente falham **MAIS**
que locais top em N2 (gpt-5.4 q_sum N2 = 0% vs qwen3:14b q_sum N2 = 22%).
Comerciais aplicam business semantics mais agressivamente, gerando
respostas business-correct-mas-GT-incorrect em taxa maior.

---

## 7.5 Linha A em TPC-H — F-Q35

Para fechar a tabela 2D: Linha A em multi-tabela com 4 modelos OpenAI.

| Modelo | Adult Linha A | TPC-H Linha A | Δ |
|--------|---------------|---------------|---|
| gpt-5.4-nano | 86.9% | **76.2%** | -11pp |
| gpt-5.4 | 95.2% | 73.8% | **-21pp** |
| gpt-5.4-mini | 82.1% | 65.5% | -17pp |
| gpt-4o-mini | 52.4% | 59.5% | **+7pp** (sobe!) |

Sub-finding contraintuitivo: **gpt-5.4-nano (76%) > gpt-5.4 full (74%)**
em Linha A TPC-H. Reasoning agressivo do full abre espaco para
interpretacoes criativas que divergem do GT.

**Sub-finding mais forte**: q_top_product Linha A = 17%; Linha B = 75%.
Diferenca de **58pp**. JOIN logico em chain-of-thought e catastrofico.

| Question N2 | Locais (qwen3) | gpt-5.4 (Linha A) | gpt-5.4 (Linha B) |
|-------------|----------------|--------------------|--------------------|
| q_lookup | 0% | 0% | 57% |
| q_sum | 22% | 42% | 0% |

Schema ambiguity ataca **paradigm-independent**: q_lookup N2 = 0%
universalmente em Linha A E Linha B. Resolver um paradigma nao resolve
o outro.

---

## 7.6 Eixo horizontal de schema — F-Q37, F-Q38

Variando schema visivel ao modelo de 1 (`minimal`) a 8 tabelas (`full`)
em TPC-H Linha B local: 1008 records.

### N0 (schema-aware) — escopo nao degrada (F-Q37)

| Level | Tabelas | qwen3:14b | qwen2.5-coder:7b | phi4 |
|-------|---------|-----------|-------------------|------|
| minimal | 1 | 95% | 95% | 86% |
| core | 2 | 95% | 95% | 95% |
| chain | 3 (M9 baseline) | 95% | 95% | 95% |
| full | 8 | 95% | 95% | 95% |

Variacao desprezivel em N0. **H_scope-1 (minimal causa falhas) e
H_scope-2 (full causa ruido) ambas rejeitadas em N0.**

Sub-finding: q_lookup minimal = 78% mesmo SEM tabela `supplier` no
payload. Modelos inferem `Supplier#NNNNNNNNN` via padrao lexical
TPC-H memorizado em training. **Risco metodologico de leakage**.

### Interacao escopo × naturalidade (F-Q38)

| Level | N0 | N1 | N2 | N3 |
|-------|----|----|----|----|
| minimal (1 tab) | 92% | 86% | **67%** | **81%** |
| core (2 tabs) | 95% | 92% | 52% | 70% |
| chain (3 tabs) | 95% | 90% | 56% | 73% |
| full (8 tabs) | 95% | 87% | **52%** | **48%** |

**Diferenca minimal vs full**:
- N0: -3pp (irrelevante)
- N3: **+33pp** (minimal melhor que full por larga margem!)

**H_scope-3 confirmada**: efeito do escopo e moderado pela naturalidade.
Em wordings naturais (N2/N3), schema reduzido protege contra interpretacoes
alternativas.

**Mecanismo**: full TPC-H tem 4-5 colunas $ candidatas. Wordings
business N2/N3 ativam interpretacoes alternativas plausiveis. Em
minimal com so `partsupp`, modelo e forcado a interpretacao correta.

**Conclusao pratica**: schema pruning (recomendacao universal Cortex
Analyst, DAIL-SQL, CHESS) fica **empiricamente justificado**. Nao e
otimizacao opcional — e parte da pipeline NL2SQL para wordings naturais.

---

## 7.7 Anthropic vs OpenAI — F-Q36

| Modelo | Adult-A | Adult-B | TPC-H-A | TPC-H-B |
|--------|---------|---------|---------|---------|
| **gpt-5.4** | **95.2%** | **100%** | 73.8% | 85.7% |
| gpt-5.4-mini | 82.1% | **100%** | 65.5% | 85.7% |
| gpt-5.4-nano | 86.9% | 90.5% | **76.2%** | 81.0% |
| gpt-4o-mini | 52.4% | 85.7% | 59.5% | 71.4% |
| claude-opus-4-7 | 76.2% | 96.4% | 75.0% | 83.3% |
| claude-sonnet-4-6 | 77.4% | 96.4% | 75.0% | **88.1%** |
| claude-haiku-4-5 | 79.8% | 98.8% | 63.1% | 79.8% |

**Achados:**
1. **Linha B**: paridade nas duas familias (96-99% Adult, 80-88% TPC-H)
2. **Linha A Adult**: OpenAI vence (gpt-5.x 82-95% vs Anthropic 76-80%)
3. **Linha A TPC-H**: paridade (sonnet/opus/gpt-5.4 todos ~74-75%)
4. **claude-sonnet-4-6 vence em TPC-H Linha B** (88.1% > gpt-5.4 85.7%) —
   unica celula onde Anthropic supera

**Hierarquia interna NAO e monotonica**:
- Adult Linha A: full > nano > mini (full melhor)
- Adult Linha B: convergencia (4 modelos em 100%)
- TPC-H Linha A: nano > full (!) > mini (nano supera)
- TPC-H Linha B: sonnet > full > mini > nano (sonnet ganha)

**Nao ha "modelo melhor" universal**. Escolha depende do paradigma +
schema + budget.

**Thinking parameter obrigatorio Anthropic**: sem ativar
`thinking={"type":"enabled","budget_tokens":2048}`, haiku/sonnet caem
para 57-58% (range non-reasoning). +20pp de ganho com thinking ativo.

---

## 7.8 Compressao e custo

### Compressao TCF L2 vs alternativas

| Formato | Adult vol=100 (bytes) | Roundtrip? |
|---------|----------------------|-----------|
| JSON  | ~14000 | ✅ |
| CSV  | ~9000 | ✅ |
| **TCF L2** (sorted by `class`) | **~7188** | ✅ |
| TCF L3 (schema-only) | ~470 | ❌ schema |

TCF L2 = **20% menor que CSV**, **49% menor que JSON**, com round-trip
exato. STATS hint adiciona ~30-80 bytes por coluna mas **massivamente**
melhora accuracy de agg em LLM (F-Q8).

### Custo M-Acomm completo

Total: **$9.46 USD** para 1968 records comerciais (Adult + TPC-H × 4
paradigmas × 7 modelos):

| Provider | Modelos | Records | Custo | $/call medio |
|----------|---------|---------|-------|--------------|
| OpenAI | gpt-5.4 family + 4o-mini | 1344 | $3.17 | $0.0024 |
| Anthropic | haiku/sonnet/opus 4.5-4.7 | 1008 | $6.29 | $0.0062 |

Sem prompt caching, custo seria ~$35-40 USD (75% economia via
`prompt_cache_key` OpenAI + `cache_control` Anthropic).

**Ponto Pareto custo × accuracy**: gpt-5.4-nano a $0.0007/call cacheado.

---

## 7.9 Sintese — tabela 2D paper-ready

|                    | Adult (single-table)              | TPC-H (multi-table)               |
|--------------------|-----------------------------------|-----------------------------------|
| Locais Linha A     | Plano N0=N3 ~50% (F-Q29)         | Nao testado*                      |
| Locais Linha B     | -15pp pior caso (F-Q30)          | **-43pp em N2** (F-Q33)           |
| Comerciais Linha A | Reasoning quebra ceiling (F-Q31)  | **-21pp em N2** (F-Q35)           |
| Comerciais Linha B | 100% imunes (F-Q32)              | **-43pp em N2** (F-Q34)           |

\* Locais Linha A em TPC-H: ceiling esperado proximo de 0% (filter+agg
+ context window 33K excede capacity de qwen3:14b).

### Achados centrais para o paper

1. **Linha A vs Linha B nao sao paradigmas equivalentes.** Linha B vence
   em multi-tabela por 10-15pp e custa 5× menos.

2. **Schema ambiguity e UNIVERSAL e PARADIGM-INDEPENDENT.** F-Q33+F-Q34+
   F-Q35 convergem: TPC-H N2 derruba accuracy 30-45pp em locais e
   comerciais top, em Linha A e Linha B.

3. **Reasoning e o eixo discriminante**, nao tamanho. gpt-5.4-nano
   (cheap reasoning) > gpt-4o-mini (cheap non-reasoning) em 30+pp.

4. **Schema pruning e OBRIGATORIO em wordings naturais.** F-Q38: -33pp
   N3 entre minimal e full TPC-H.

5. **F-Q12 nao e universal** — e propriedade de modelos non-reasoning.

6. **Anthropic e OpenAI sao equivalentes em Linha B**, com vantagem
   sutil OpenAI em Linha A. **Sonnet 4.6 vence TPC-H Linha B.**

### Recomendacoes praticas

- Workload single-table com cols inequivocas → **Linha B + qualquer
  modelo top** (incluindo locais como qwen3:14b)
- Workload single-table com filter+agg pesado → **Linha A + reasoning
  comercial** (gpt-5.4-nano e o ponto Pareto)
- Workload multi-tabela → **Linha B obrigatoriamente** (Linha A morre
  em q_top_product 17%) **+ schema pruning** (minimal/core schema
  em N2/N3 wordings)
- Workloads com schema ambiguity → **wordings N0 schema-aware
  obrigatorios** OU few-shot examples para ancorar

Catalogo completo dos 38 findings em [../findings/](../findings/).
Manifests JSONL em `experiments/results/{m_acomm,m_acomm_b,m_acommA_tpch,
m_acommB_tpch,m_alocal,m9_adult,m9_canonical,m_schema_scope}/`.

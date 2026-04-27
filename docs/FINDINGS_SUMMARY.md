---
type: summary
status: LIVING DOCUMENT — atualizado conforme M-series avanca
last_updated: 2026-04-27
source: docs/methodology/F-findings.md (fonte canonica completa)
---

# TCF — Achados principais (resumo paper-ready)

Este documento concentra os **achados de alto impacto** que serao o nucleo
do paper. Catalogo completo em
[methodology/F-findings.md](methodology/F-findings.md).

Para evolucao operacional ver [CONSOLIDATED_DEVELOPMENT.md](CONSOLIDATED_DEVELOPMENT.md);
para evolucao logica ver [CONSOLIDATED_SCIENCE.md](CONSOLIDATED_SCIENCE.md).

**Duas linhas de pesquisa**:
- **Linha A** — LLM le TCF e calcula direto
- **Linha B** — TCF como schema carrier, LLM gera SQL, SQLite executa

---

## Estado atual (2026-04-27)

- **2256+ records** sobre Adult + TPC-H × 4 paradigmas × 7+ modelos
  comerciais + 13 modelos locais
- **36 findings F-Q1..F-Q36** documentados
- **Tabela 2D paper-ready completa** em todas as 8 celulas
- **Custo total**: $9.46 USD (comerciais), $0 (locais)

---

## Os 7 achados centrais (top of paper)

### 1. Linha A vs Linha B nao sao paradigmas equivalentes

**F-Q28** (locais Adult): Linha A bimodal — 100% em full-table agg via
STATS hint; **0-11% em filter+agg**. F-Q12 antigo refinado.

**F-Q31** (comerciais Adult): comerciais com reasoning **quebram** o
ceiling Linha A — gpt-5.4 = 95%, gpt-5.4-nano = 87%. **Eixo limitante e
REASONING**, nao tamanho. gpt-4o-mini (non-reasoning) cai para 52%, range
dos locais.

**Tabela mestre 7 modelos x 4 paradigmas**:

| Modelo | Adult-A | Adult-B | TPC-H-A | TPC-H-B |
|---|---|---|---|---|
| gpt-5.4 | 95.2% | 100% | 73.8% | 85.7% |
| gpt-5.4-mini | 82.1% | 100% | 65.5% | 85.7% |
| gpt-5.4-nano | 86.9% | 90.5% | 76.2% | 81.0% |
| gpt-4o-mini | 52.4% | 85.7% | 59.5% | 71.4% |
| claude-opus-4-7 | 76.2% | 96.4% | 75.0% | 83.3% |
| claude-sonnet-4-6 | 77.4% | 96.4% | 75.0% | **88.1%** |
| claude-haiku-4-5 | 79.8% | 98.8% | 63.1% | 79.8% |

### 2. Schema ambiguity e UNIVERSAL e PARADIGM-INDEPENDENT

**F-Q33** (locais TPC-H Linha B): N2 cai **30-45pp** em todos os 3 modelos.
qwen3:14b — imune em Adult — tambem cai 33pp.

**F-Q34** (comerciais TPC-H Linha B): mesmo padrao, gpt-5.4 e gpt-5.4-mini
caem **-43pp em N2**. F-Q32 (imunidade comercial) era specific Adult.

**F-Q35** (comerciais TPC-H Linha A): mesma degradacao, paradigm-independent.
q_lookup N2 = 0/12 universal em Linha A E Linha B.

**Mecanismo**: TPC-H tem 2+ colunas $ proximas (ps_supplycost vs
p_retailprice) e wordings business N2 ativam consistentemente a
interpretacao errada do GT (ex: "valor comprometido" vira `cost x qty`).

**Schema linking continua problema aberto** mesmo em modelos frontier.

### 3. Naturalidade NAO degrada Linha A em locais

**F-Q29**: 13 modelos locais 0.6B-20B testados. Variacao N0->N3 e ±5-14pp,
dentro do CI Wilson. Cinco modelos com Δ=0pp. **H_natural-1 rejeitada**
para Linha A em locais.

**Mecanismo**: gargalo de Linha A local e aritmetica sobre 100+ valores,
nao compreensao da pergunta. Wordings ficam invisiveis abaixo do floor
estrutural.

### 4. Linha B comercial top e robusto a naturalidade em single-table

**F-Q32**: gpt-5.4 e gpt-5.4-mini = **100% em N0/N1/N2/N3** Adult Linha B.
Anthropic haiku/sonnet/opus = 96-99%. Zero gap.

**Mas**: F-Q34 mostra que essa imunidade NAO generaliza para multi-tabela
com schema ambiguo.

### 5. q_top_product (JOIN logico) e o caso limite Linha A vs B

**F-Q35**: q_top_product Linha A TPC-H = 17%. Linha B TPC-H = 75%.
Diferenca **58pp**.

LLMs com chain-of-thought nao mantem **estado relacional cruzado** durante
o reasoning. Em Linha B isso e 1 linha de SQL.

**Recomendacao**: workloads com JOIN logico devem usar Linha B sem
discussao.

### 6. Schema pruning é OBRIGATÓRIO em NL2SQL com wordings naturais

**F-Q38** (1008 records TPC-H Linha B local): schema reduzido (`minimal`,
1 tabela) atinge **+33pp** em N3 vs schema completo (`full`, 8 tabelas).
Em N0 (schema-aware) o efeito desaparece (~95% em todos os levels).

| Level | N0 | N1 | N2 | N3 |
|-------|----|----|----|----|
| minimal (1 tab) | 92% | 86% | **67%** | **81%** |
| full (8 tabs) | 95% | 87% | 52% | **48%** |

**Mecanismo**: TPC-H full tem 4-5 colunas $ candidatas; wordings business
N2/N3 ativam interpretacoes alternativas plausiveis. Em minimal com so
`partsupp`, modelo e forcado a interpretacao correta.

Confirma literatura industrial (Cortex Analyst, DAIL-SQL, CHESS).
**Schema pruning não é otimização opcional — é parte da pipeline.**

### 7. Anthropic vs OpenAI: paridade em B, gap em A

**F-Q36**: 1968 records comparativos.
- **Linha B**: paridade nas duas familias (96-99% Adult, 80-88% TPC-H)
- **Linha A Adult**: OpenAI vence (gpt-5.x 82-95% vs Anthropic 76-80%)
- **Linha A TPC-H**: paridade (sonnet/opus/gpt-5.4 todos ~74-75%)
- **claude-sonnet-4-6 vence TPC-H Linha B** (88.1% > gpt-5.4 85.7%)

**Thinking parameter obrigatorio** Anthropic — sem ativar, haiku/sonnet
caem para 57-58% (range non-reasoning).

---

## Tabela 2D paper-ready (8 celulas, completa)

|                    | Adult (single-table)                  | TPC-H (multi-table)                   |
|--------------------|---------------------------------------|---------------------------------------|
| Locais Linha A     | F-Q29 ~50% plano (N0=N3)             | Nao testado*                          |
| Locais Linha B     | F-Q30 -15pp pior caso                 | **F-Q33 -43pp em N2**                 |
| Comerciais Linha A | F-Q31 reasoning quebra ceiling (95%) | **F-Q35 -21pp em N2**                 |
| Comerciais Linha B | F-Q32 100% imunes                    | **F-Q34 -43pp em N2**                 |

\* Locais Linha A em TPC-H: ceiling esperado proximo de 0% (filter+agg
+ context window 33K excede capacity de qwen3:14b).

---

## Achados de protocolo (metodo)

- **F-Q26**: random ≈ stratified em Adult — paradigma robusto
- **F-Q27**: SQL quality structural metric correlaciona INVERSAMENTE com
  accuracy — descartado
- Stratified sampling com metricas inline TVD/JSD/Hellinger/Wilson e o
  default em todos os runners
- Dedup last-wins, scorer parametrico (ScoringConfig), prompt caching
  agressivo, structured outputs Pydantic — convencoes consolidadas

---

## Findings de origem (F-Q1..F-Q12)

Estes formaram a base do projeto. Detalhes em F-findings.md:
- F-Q1..F-Q9: Phase 1 LLM Comprehension. TCF 43% < JSONL 63%.
- F-Q10..F-Q12: qualificacao de modelos. F-Q12 ceiling Linha A
  refinado por F-Q28 e refutado em comerciais por F-Q31.

---

## Findings de Linha B sintetica (F-Q13..F-Q24)

Validacoes incrementais:
- F-Q13..F-Q17: schema-only payload, few-shot, cross-domain, format,
  TCF-progressive
- F-Q18..F-Q23: filter+agg, CTE/subquery, error types, style hints
  isolados/combinados
- F-Q24: synthetic ≈ canonical em accuracy

---

## Recomendacoes praticas (paper)

1. **Linha B e a recomendacao default** para datasets reais —
   80-100% em ambas familias, custo 5-10x menor que Linha A
2. **gpt-5.4-nano e o ponto Pareto** custo x accuracy
3. **claude-sonnet-4-6 e o melhor** para SQL gen multi-tabela
4. **Schema ambiguity exige design de wording** (N0 obrigatorio para
   schemas com >=2 colunas semanticamente proximas) — nao se resolve
   por escolha de modelo
5. **Linha A faz sentido apenas para single-table** com cols inequivocas
   E modelo com reasoning de qualidade comercial

---

## Custo total do experimento M-Acomm

- OpenAI: $3.17 / $30 budget (10.6% gasto)
- Anthropic: $6.29 / $20 budget (31.5% gasto)
- **Total: $9.46 USD** com prompt caching (~75% economia vs no-cache)

Sem cache: ~$35-40 USD estimate.

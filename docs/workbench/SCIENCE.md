---
title: TCF — Consolidação científica (timeline lógico de hipóteses)
date: 2026-04-27
type: consolidated
status: ATIVO — substitui partes científicas de research-notes legados
---

# CONSOLIDATED_SCIENCE — evolução lógica das hipóteses do TCF

Este documento traça **a ordem lógica em que as hipóteses foram formadas,
testadas, refutadas e refinadas**. Para a evolução **operacional do código**,
ver [CONSOLIDATED_DEVELOPMENT.md](CONSOLIDATED_DEVELOPMENT.md).

A ordem aqui **não é estritamente cronológica**: alguns achados emergiram
em paralelo e foram entendidos retrospectivamente. O que interessa é
**que pergunta veio antes na lógica**.

---

## Parte I — Hipóteses fundadoras (F-Q1..F-Q12)

### Pergunta zero — TCF é compreendido por LLMs?

**H_origem**: um formato textual columnar com RLE+STATS pode ser tão
legível por LLM quanto JSON.

**Fase 1 LLM Comprehension** testou em 12 modelos × 4 formatos × 4 questões.

**Refutado parcialmente** (F-Q1..F-Q9): TCF chega a 43% acc geral vs JSONL
63%. Modelos pequenos (<3B) não leem TCF de forma confiável; STATS hint
ajuda bastante mas tem teto. Para questions com agg full-table, TCF é
viável; para queries complexas, **a hipótese cai**.

### Pivô para Linha B — F-Q12

**Pergunta**: e se LLM gerar SQL ao invés de calcular?

**F-Q12** (sintetético antigo): Linha A (LLM calcula) satura em ~60-70%
em modelos locais 7-14B. Aritmética sobre 100+ valores falha. Linha B
(LLM gera SQL → SQLite executa) chega a 90-100% no mesmo dataset.

**Decisão central**: as duas linhas serão investigadas em paralelo.
Linha B vira o **caminho de maior valor prático**; Linha A continua para
medir o **gap fundamental** entre paradigmas.

---

## Parte II — Validação cross-domain e canonical (F-Q13..F-Q24)

### M1..M8 — refinamento Linha B em synthetic

**Hipóteses validadas em sequência**:
- F-Q13: schema-only payload é suficiente para SQL gen
- F-Q14: few-shot ajuda mas com saturação
- F-Q15-16: 3 domínios sintéticos (retail, medical, financial) dão
  resultados equivalentes
- F-Q17: TCF format vence CSV/JSONL como schema carrier
- F-Q18: TCF L0..L3 progressão bate accuracy
- F-Q19: HAVING + filter+agg é zona crítica universal
- F-Q20: CTE/subquery aninhada chega a 86% com fewshot
- F-Q21: erros SQL se dividem em **2 tipos** (detectáveis por invariante
  vs silenciosos)
- F-Q22: 4 style hints isolados melhoram SQL (com gain proporcional)
- F-Q23: **hints não compõem** — combinar gera interferência off-target

### M9 canonical — saída do synthetic

**Pergunta**: synthetic é representativo de datasets reais?

**F-Q24**: TPC-H sf001 (canonical) ≈ synthetic retail em accuracy global
(95%) — synthetic é representativo *quando o protocolo é igual*.

**F-Q25**: Adult Census single-table com colunas hifenadas (`hours-per-week`)
e categóricos ricos atinge **100%** em Linha B local. Generaliza H-TCF2.

---

## Parte III — Validação de protocolo (F-Q26..F-Q28)

### Pergunta de método — random vs stratified sampling?

**F-Q26**: random ≈ stratified em Adult Census (paradigma robusto).
"Floor effect": com Linha B em 100%, sampling não move o número.

### Pergunta de método — quality intrínseca de SQL prediz accuracy?

**F-Q27** (M-quality posthoc, 1551 SQLs): quality structural metric
**correlaciona INVERSAMENTE** com accuracy. SQL "feio" às vezes acerta
mais que SQL "elegante". O quality score original era um heurístico ruim;
descartado.

### Refinamento de F-Q12 em canonical — F-Q28

**Pergunta**: o ceiling 60-70% Linha A é universal ou era artifact do
synthetic?

**F-Q28**: Linha A em Adult canonical (M-Alocal) = **52% global**, mas
**bimodal**:
- Stats agregadas full-table: 100% (LLM lê STATS hint)
- Filter + agg (WHERE + AVG/COUNT): **0-11%** (LLM precisa iterar)
- Distinct count: 0%

**Refinamento**: F-Q12 não é "Linha A satura em X%". É: depende do tipo
de query. Decomposição por tipo de question é o que importa para o paper.

---

## Parte IV — Eixo de naturalidade (F-Q29..F-Q36)

Esta é a **fase mais densa cientificamente** do projeto. Foram 8 findings
em sequência que cobrem a tabela 2D completa.

### Pergunta — naturalidade da pergunta degrada accuracy?

Hipótese inicial **H_natural-1**: accuracy(N0 schema-aware) ≥ N1 ≥ N2 ≥
N3 (business+contexto). Inspirado em literatura industrial (Spider 2.0,
SiriusBI VLDB 2024) que aponta degradação por wordings naturais.

**Taxonomia formalizada**: 4 níveis N0-N3, definidos por:
- N0: nomes literais de tabela/coluna, hints técnicos
- N1: prosa do domínio com termos do sistema (ex: "fornecedor")
- N2: business-intent sem mencionar schema (ex: "qual o preço médio")
- N3: business + contexto implícito (ex: "qual o ticket médio da operação")

### F-Q29 — naturalidade NÃO degrada Linha A em locais

**Refuta H_natural-1 para Linha A.**

13 modelos locais 0.6B-20B testados em Adult Linha A com 4 níveis × 7
questões × 3 seeds (parcial). Variação entre níveis: ±5-14pp dentro do
CI Wilson em todos os modelos. **Cinco modelos com Δ=0pp** entre N0 e N3.

**Mecanismo**: o gargalo de Linha A em locais é **aritmética sobre 100+
valores**, não compreensão da pergunta. Floor por filter+agg + ceiling
por full-table-agg. Wordings ficam invisíveis abaixo desse padrão.

### F-Q30 — naturalidade DEGRADA Linha B local seletivamente

**Confirma H_natural-1 para Linha B em locais.**

3 modelos × 3 seeds × 4 níveis × 7q = 252 records sobre Adult Linha B.
- qwen3:14b: imune (100% em todos os níveis)
- phi4: -14pp em N3
- qwen2.5-coder:7b: -15pp em N1 (após correção wording)

**Dois mecanismos**:
1. Ambiguidade semântica de domínio (ex: "classe trabalhista" → SQL
   gerou `COUNT(DISTINCT class)` em vez de `workclass`)
2. Limitação do modelo com colunas hifenadas (qwen2.5-coder não usa
   aspas duplas em SQLite, fica `OperationalError`)

### F-Q31 — comerciais reasoning quebram ceiling Linha A

**Refuta universalidade de F-Q12/F-Q28.**

4 modelos OpenAI × 3 seeds × 4 níveis × 7q = 336 records.
- gpt-5.4 (reasoning): 95.2%
- gpt-5.4-nano (reasoning, cheap): 86.9%
- gpt-4o-mini (non-reasoning): **52.4%** — range dos locais

**Eixo limitante NÃO é tamanho, é REASONING.** Modelos com
chain-of-thought interno mantêm filter+agg em 75-100%. gpt-4o-mini sem
reasoning falha exatamente como locais.

### F-Q32 — comerciais top imunes a naturalidade Linha B Adult

3 modelos OpenAI × 3 seeds × 4 níveis × 7q = 252 records sobre Adult Linha B.
- gpt-5.4 e gpt-5.4-mini: **100%** em todos os níveis
- gpt-5.4-nano: -14pp gap em N1
- gpt-4o-mini: 86% flat (limitação fixa)

### F-Q33 — naturalidade DEGRADA Linha B local em TPC-H DRAMATICAMENTE

**Achado mais forte do eixo de naturalidade.**

3 modelos × 3 seeds × 4 níveis × 7q = 252 records sobre TPC-H Linha B local.
**N2 cai 30-45pp em TODOS os 3 modelos**. qwen3:14b — imune em Adult — também
cai -33pp. F-Q30 não generaliza para multi-tabela.

**Mecanismo**: schema ambiguity sistemática. TPC-H tem 2+ colunas $ próximas
(ps_supplycost, p_retailprice) e wordings business ativam consistentemente
a interpretação errada do GT.

### F-Q34 — schema ambiguity é UNIVERSAL: comerciais top também caem

4 modelos OpenAI × 3 seeds × 4 níveis × 7q = 336 records sobre TPC-H Linha B.
gpt-5.4 e gpt-5.4-mini caem **-43pp em N2** também. F-Q32 (imunidade)
era específico Adult.

**q_lookup N2 = 0/12 universal** em TODOS os 4 modelos. q_sum N2 = 0/12
universal. **Schema linking continua problema aberto** mesmo em modelos
frontier janeiro 2026.

### F-Q35 — Linha A comercial em multi-tabela cai para 60-76%

Fechamento da tabela 2D. 4 modelos OpenAI × 3 seeds × 4 níveis × 7q = 336
records sobre TPC-H Linha A.
- gpt-5.4: 73.8% (vs 95.2% Adult)
- gpt-5.4-nano: 76.2% (vs 86.9% Adult) — **supera o full em TPC-H!**
- gpt-4o-mini: 59.5% (sobe de 52% Adult — único que sobe)

**Schema ambiguity é paradigm-independent**: q_lookup N2 = 0/12 universal
tanto em Linha A quanto Linha B.

**q_top_product Linha A = 17%** (vs Linha B = 75%) — **JOIN lógico em
chain-of-thought é catastrófico**. Workloads com JOIN devem ir para Linha B.

### F-Q36 — Anthropic vs OpenAI: paridade em B, gap em A

3 modelos Anthropic + 4 OpenAI × 4 paradigmas = 1968 records.
- Linha B: paridade (96-99% Adult, 80-88% TPC-H ambas famílias)
- Linha A Adult: OpenAI vence (gpt-5.x 82-95% vs Anthropic 76-80%)
- Linha A TPC-H: paridade (sonnet/opus/gpt-5.4 todos ~74-75%)
- **claude-sonnet-4-6 vence em TPC-H Linha B** (88.1% > gpt-5.4 85.7%)

**Thinking parameter obrigatório** Anthropic — sem thinking, haiku/sonnet
caem para 57-58% (range non-reasoning).

---

## Parte V — Eixo horizontal de schema (F-Q37, F-Q38)

**Pergunta**: schema reduzido vs excessivo afeta accuracy SQL gen?

### F-Q37 — escopo NÃO degrada Linha B em N0

3 modelos × 3 seeds × 4 levels × 7q × N0 = 252 records. Variar schema
visível de 1 (`minimal`) a 8 tabelas (`full`) **não move accuracy**:
- qwen3:14b e qwen2.5-coder em 95% nos 4 níveis
- phi4 cai marginalmente em minimal (86%)

**Sub-finding**: modelos inferem `Supplier#NNNNNNNNN` via padrão lexical
mesmo sem ter `supplier` no payload — memorização do schema canônico
TPC-H. **Risco metodológico de leakage** documentado.

### F-Q38 — escopo × naturalidade: H_scope-3 CONFIRMADA

3 modelos × 3 seeds × 4 levels × 4 níveis × 7q = 1008 records. **Schema
reduzido AJUDA dramaticamente em wordings naturais**:

| Level | N0 | N1 | N2 | N3 |
|-------|----|----|----|----|
| minimal (1 tab) | 92% | 86% | **67%** | **81%** |
| full (8 tabs) | 95% | 87% | 52% | **48%** |

**Diferença minimal vs full:**
- N0: -3pp (irrelevante)
- N3: **+33pp** (minimal venceria por larga margem!)

Mecanismo: full tem 4-5 colunas $ candidatas (ps_supplycost,
p_retailprice, l_extendedprice, o_totalprice, l_discount) — wordings
business N2/N3 ativam interpretações alternativas plausíveis. Em
minimal com só `partsupp`, o modelo é forçado à interpretação correta.

**Schema pruning** (recomendação universal Cortex/DAIL-SQL/CHESS) fica
**empiricamente justificada**. Não é otimização opcional — é parte da
pipeline NL2SQL.

phi4 é mais sensível (-16pp minimal→full); qwen2.5-coder mais estável
(-3pp). Resposta varia por modelo mas direção é universal.

---

## Tabela 2D paper-ready (após M-Acomm)

|                    | Adult (single-table)         | TPC-H (multi-table)            |
|--------------------|------------------------------|--------------------------------|
| Locais Linha A     | F-Q29 ~50% plano             | Não testado*                   |
| Locais Linha B     | F-Q30 -15pp pior caso        | **F-Q33 -43pp em N2**          |
| Comerciais Linha A | F-Q31 reasoning quebra (95%) | **F-Q35 -21pp em N2**          |
| Comerciais Linha B | F-Q32 100% imunes            | **F-Q34 -43pp em N2**          |

\* Locais Linha A em TPC-H: ceiling esperado próximo de 0% (filter+agg +
context window 33K excede capacity de qwen3:14b).

---

## Achados centrais para o paper

1. **Linha A vs Linha B não são paradigmas equivalentes.** Linha B vence
   em multi-tabela por 10-15pp E custa 5× menos. Linha A tem nicho
   apenas em single-table com modelo reasoning.

2. **Reasoning é o eixo discriminante**, não tamanho. gpt-4o-mini (cheap,
   non-reasoning) cai no range dos locais; gpt-5.4-nano (cheap mas
   reasoning) quebra ceilings.

3. **Schema ambiguity é universal e paradigm-independent.** F-Q33+F-Q34+
   F-Q35 convergem: TPC-H N2 derruba accuracy 30-45pp em locais e
   comerciais top, em Linha A e Linha B. Não é resolvida por escala
   nem pelo provider.

4. **F-Q12 não é universal** — é propriedade de modelos non-reasoning.
   Refrasear como tal no paper.

5. **q_top_product (JOIN lógico) é o caso limite** que separa Linha A
   (17%) de Linha B (75%) em multi-tabela.

6. **Naturalidade é não-monotônica**: N1 às vezes pior que N0 e N3.
   "Mais natural" não é eixo monotônico — depende do mapping
   semântico para schema.

7. **Anthropic e OpenAI são equivalentes em Linha B**, com vantagem
   sutil OpenAI em Linha A. **Sonnet 4.6 vence TPC-H Linha B.**

---

## Decisões metodológicas que ficaram

1. **Stratified sampling default** com métricas inline (TVD/JSD/Wilson)
   no manifest — confirmado por F-Q26
2. **Dedup last-wins** em print_summary — bug fix em 10 runners
3. **Wordings N0 byte-identical** ao legacy para retrocompat de records
4. **Scorer paramétrico** (ScoringConfig) com lenient default + strict opcional
5. **Prompt caching agressivo** com `prompt_cache_key` por (model, seed)
6. **Structured outputs Pydantic** em comerciais — parse_failure < 0.5%
7. **Reasoning explícito** (`thinking` / `reasoning.effort`) obrigatório
   em modelos reasoning para tarefas tabulares

---

## Pendências científicas

1. **F-Q37** — efeito do escopo horizontal de schema (M-schema-scope, em curso)
2. **TPC-H comerciais Anthropic Linha A** já feito — falta apenas
   confirmar o achado central com mais um family
3. **Wordings TPC-H N1-N3 podem ter falsos amigos** análogos à
   "classe trabalhista" — auditoria pendente
4. **Tabela 2D × família** seria o experimento 3D completo, mas custo
   adicional não justifica hoje

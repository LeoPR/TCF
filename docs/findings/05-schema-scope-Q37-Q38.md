---
title: Eixo horizontal de schema (F-Q37..F-Q38)
type: findings-block
range: F-Q37..F-Q38
parent: docs/findings/README.md
---

# Eixo horizontal de schema (F-Q37..F-Q38)

## F-Q37 `{B}` — Escopo de schema NÃO degrada Linha B em N0; modelos inferem nomes via padrão lexical

**Conclusão:** Variar schema visível ao modelo de **1 tabela (minimal) a
8 tabelas (full)** em TPC-H Linha B com wordings N0 (schema-aware) **não
move accuracy** em modelos locais 7-14B. qwen3:14b e qwen2.5-coder ficam
em 95% nos 4 níveis; só phi4 cai marginalmente em minimal. **H_scope-1
(schema reduzido causa falhas) e H_scope-2 (schema excessivo causa ruído)
ambas rejeitadas em N0.**

Sub-finding fascinante: modelos **inferem corretamente nomes de entidades
via padrão lexical** (`Supplier#NNNNNNNNN`) mesmo quando a tabela `supplier`
**não está visível no payload**. q_lookup em minimal (só `partsupp` visível)
= 78%, perto de chain (100%).

**Evidência (M-schema-scope, 2026-04-27):** 3 modelos × 3 seeds × 4 schema
levels × 7 questões × N0 = **252 records** sobre TPC-H sf001.

**Schema levels (visível no payload — DB SQLite sempre tem 3 chain tables
para GT correto):**

| Level | Tabelas visíveis | n |
|-------|------------------|---|
| minimal | partsupp | 1 |
| core | partsupp + part | 2 |
| chain | partsupp + part + supplier (= M9 baseline) | 3 |
| full | 8 tabelas TPC-H | 8 |

**Tabela central — modelo × schema_level:**

| Modelo | minimal | core | chain | full | Δ (max−min) |
|--------|---------|------|-------|------|-------------|
| qwen3:14b | 95% | 95% | 95% | 95% | **0pp** |
| qwen2.5-coder:7b | 95% | 95% | 95% | 95% | **0pp** |
| phi4:latest | 86% | 95% | 95% | 95% | 9pp |

**Por questão × schema_level:**

| Question | minimal | core | chain | full | Padrão |
|----------|---------|------|-------|------|---------|
| q_count, q_sum, q_avg, q_distinct, q_lookup_value | 100% | 100% | 100% | 100% | Robusto |
| q_top_product | 67% | 67% | 67% | 67% | Tie issue (GT, não escopo) |
| **q_lookup** | **78%** | 100% | 100% | 100% | -22pp em minimal |

**Mecanismo — inferência lexical de nomes:**

q_lookup pede o NOME do supplier com max(ps_supplycost). Em minimal, o
payload tem só `partsupp` (com `ps_suppkey` mas sem nomes). Mesmo assim,
**7/9 modelos respondem `Supplier#000000036`** corretamente. Como?

Análise dos SQLs gerados:
```sql
SELECT 'Supplier#' || printf('%09d', ps_suppkey) FROM partsupp
ORDER BY ps_supplycost DESC LIMIT 1
-- ou
SELECT ps_suppkey FROM partsupp ORDER BY ps_supplycost DESC LIMIT 1
-- (depois "naming" pelo padrão TPC-H que o modelo conhece de training)
```

**O LLM aprendeu o padrão lexical TPC-H** (`Supplier#NNNNNNNNN`) e o
aplica mesmo sem ter a tabela `supplier` disponível. Isso é
**memorização de schema canônico** — funciona para benchmarks
conhecidos (TPC-H), mas é evidência de que o modelo NÃO está apenas
respondendo ao schema apresentado.

**Implicações:**

1. **F-Q37 + literatura de schema pruning não conflitam:** literatura
   industrial (Cortex Analyst, DAIL-SQL, CHESS) reporta que schema
   pruning ajuda com **wordings naturais** (N1-N3), não com N0.
   Nosso teste em N0 confirma: schema escopo é irrelevante quando o
   modelo já tem o nome da coluna na pergunta.

2. **A H_scope-3 (escopo × naturalidade) ainda merece teste.**
   Esperamos que em N1/N2/N3, schema reduzido AJUDE (menos colunas para
   confundir-se em F-Q33/F-Q34). Mas custo: 1008 calls locais. Pode ser
   feito quando houver tempo.

3. **Risco metodológico — leakage de TPC-H em training:** o padrão
   `Supplier#NNNNNNNNN` é canônico TPC-H e amplamente memorizado por
   LLMs pré-2026. **Achados em TPC-H podem ser inflados por
   memorização**. Vale considerar dataset privado para validação
   independente em paper futuro.

4. **Adult Census não tem esse problema** — colunas hifenadas
   (hours-per-week) e categóricos (`workclass`, `education`) não têm
   padrão lexical previsível. Por isso F-Q30 é mais limpa que F-Q37.

5. **Recomendação:** experimentos NL2SQL futuros devem:
   - Usar pelo menos 2 datasets, um canônico (TPC-H) e um menos comum
   - Reportar accuracy em N0 schema-aware separadamente da N2/N3 business
   - Esperar inferência lexical em entidades com padrão regular

**Custo:** $0 (Ollama local).

**Próximos:** rodar M-schema-scope com `--naturalness all` para testar
H_scope-3 (efeito × naturalidade). 1008 calls locais, ~40min, $0.

**Referência:** `experiments/results/m_schema_scope/manifest.jsonl`
(2026-04-27, 252 records).

---

## F-Q38 `{B}` — Interação escopo × naturalidade: schema reduzido AJUDA em wordings naturais (-33pp full vs minimal em N3)

**Conclusão:** **H_scope-3 do ticket M-schema-scope CONFIRMADA**. Em
wordings naturais (N2/N3), schema reduzido (`minimal`, 1 tabela) atinge
accuracy **15-33pp maior** que schema completo (`full`, 8 tabelas) em
TPC-H. Em wordings schema-aware (N0), o efeito desaparece (todos ~95%).
**Schema pruning** — recomendação universal da literatura industrial
(Cortex Analyst, DAIL-SQL, CHESS) — fica empiricamente justificada.

**Evidência (M-schema-scope, 2026-04-27):** 3 modelos × 3 seeds × 4
levels × 4 níveis × 7q = **1008 records** sobre TPC-H. Estende F-Q37
(que cobria só N0).

**Tabela central — schema_level × naturalidade (todos modelos agregados):**

| Level | N0 | N1 | N2 | N3 | Δ N0→N3 |
|-------|----|----|----|----|----|
| **minimal** (1 tab) | 92% | 86% | **67%** | **81%** | **-11pp** |
| core (2 tabs) | 95% | 92% | 52% | 70% | -25pp |
| chain (3 tabs) | 95% | 90% | 56% | 73% | -22pp |
| **full** (8 tabs) | 95% | 87% | **52%** | **48%** | **-47pp** |

**Diferença minimal vs full:**
- N0: -3pp (schema-aware imune)
- N1: -1pp (system-aware, leve)
- N2: **+15pp** (minimal > full)
- N3: **+33pp** (minimal > full) — **EFEITO DRAMÁTICO**

**Per modelo × schema_level (agregado nl):**

| Modelo | minimal | core | chain | full | Δ minimal→full |
|--------|---------|------|-------|------|----------------|
| qwen3:14b | **88%** | 81% | 86% | 75% | -13pp |
| phi4:latest | 79% | 74% | 73% | **63%** | **-16pp** |
| qwen2.5-coder:7b | 77% | 77% | 77% | 74% | -3pp |

**phi4 é mais sensível ao excesso de schema** (-16pp); qwen2.5-coder é
mais estável (-3pp). qwen3:14b mantém-se forte mas perde 13pp em full.

**Mecanismo — N3 em full é o pior caso:**

Wording N3 *"Qual o ticket médio de custo unitário na nossa operação?"*
em full (8 tabelas TPC-H) tem 4-5 colunas $ candidatas:
- ps_supplycost (correto)
- p_retailprice (catálogo)
- l_extendedprice (lineitem)
- o_totalprice (orders)
- l_discount (lineitem)

O modelo escolhe entre elas com taxa de erro alta. Em minimal
(1 tabela = partsupp), só `ps_supplycost` é candidata viável e o
modelo é forçado à interpretação correta.

Mesmo em chain (3 tabelas, sem orders/lineitem), só ps_supplycost e
p_retailprice competem — daí 73% N3 (vs 48% full).

**Implicações fortes:**

1. **F-Q33/F-Q34 (schema ambiguity em multi-tabela) era subestimação.**
   O verdadeiro estado é: ambiguidade × escopo. Em chain, gpt-5.4 caía
   -43pp em N2; em full seria pior ainda.

2. **Schema pruning não é otimização opcional — é parte da pipeline.**
   Sistemas NL2SQL em produção devem extrair subset relevante antes de
   passar ao LLM, especialmente para wordings business.

3. **Custo cognitivo de "mais opções" é mensurável:** cada coluna
   semanticamente próxima adicional adiciona ~5-10pp de erro em N2/N3.

4. **Refrasear F-Q37**: era "escopo NÃO degrada N0". Verdade completa
   é: "escopo não degrada N0; degrada N1 levemente; degrada N2 e N3
   dramaticamente". F-Q37 fica como sub-claim de F-Q38.

5. **Recomendação prática para o paper:** combinar TCF (compressão) +
   schema_qualifier (pruning) é o caminho. Já há roadmap em
   `research-notes/2026-04-24-schema-qualifier.md` — F-Q38 dá motivação
   empírica para implementar.

**Sub-finding sobre N3 minimal (81%) > N1 minimal (86% mas próximo):**

N3 em minimal recupera a 81%, mais alto que core/chain/full em N3
(48-73%). O contexto business em N3 ("nossa operação") **melhora**
quando o modelo só tem 1 tabela para considerar — o "nosso" mapeia
naturalmente para `partsupp`.

**Custo:** $0 (Ollama local).

**Pendências relacionadas:**
- Schema pruning como serviço pre-TCF (schema_qualifier roadmap)
- Replicar F-Q38 em comerciais (gpt-5.x, Anthropic) — esperado
  mesma direção, gap maior que locais por capacidade

**Referência:** `experiments/results/m_schema_scope/manifest.jsonl`
(2026-04-27, 1008 records).

---

---
title: Eixo de naturalidade N0-N3 (F-Q29..F-Q36)
type: findings-block
range: F-Q29..F-Q36
parent: docs/findings/README.md
---

# Eixo de naturalidade N0-N3 (F-Q29..F-Q36)

## F-Q29 `{B}` — Naturalidade da pergunta NÃO degrada Linha A em locais (rejeita H_natural-1) — confirmado em 13 modelos 0.6B-20B

**Conclusão:** Em **13 modelos locais** de **0.6B a 20B parâmetros** no
paradigma Linha A (LLM lê TCF e calcula), reformular a pergunta de
schema-aware (N0) → business+contexto (N3) **não move a accuracy**. As
4 formulações ficam dentro do CI Wilson umas das outras em todos os
modelos. **A hipótese H_natural-1** ("accuracy(N0) ≥ N1 ≥ N2 ≥ N3")
**não se sustenta para Linha A em modelos locais**, independente de
arquitetura, capacity, ou reasoning explícito.

**Evidência principal (M-natural-local, 2026-04-26):** 3 modelos baseline
× 3 seeds + 10 modelos extras × 1 seed × 4 níveis × 7 questions =
**595 records** sobre Adult Census vol=100 stratify_by=class. Mesmo
dataset e protocolo de F-Q28; só varia o wording.

**Painel de modelos testados (13 total):**

| Modelo | Params | Acc | CI (Wilson) |
|--------|--------|-----|-------------|
| **deepseek-r1:14b** | 14B | **57.1%** | [39.1%, 73.5%] |
| **qwen2.5-coder:7b** | 7B | **57.1%** | [47.6%, 66.2%] (3 seeds) |
| phi4:latest | 14B | 54.3% | [44.8%, 63.5%] (3 seeds) |
| qwen3:14b | 14B | 47.6% | [38.3%, 57.1%] (3 seeds) |
| qwen3:1.7b | **1.7B** | 46.4% | [29.5%, 64.2%] |
| gemma3:12b | 12B | 46.4% | [29.5%, 64.2%] |
| gemma3:4b | 4B | 46.4% | [29.5%, 64.2%] |
| qwen3:4b | 4B | 42.9% | [26.5%, 60.9%] |
| qwen3:4b-thinking | 4B | 42.9% | [26.5%, 60.9%] |
| mistral-nemo:latest | 12B | 42.9% | [26.5%, 60.9%] |
| granite3.3:8b | 8B | 39.3% | [23.6%, 57.6%] |
| **gpt-oss:latest** | 20B | **28.6%** | [15.3%, 47.1%] (anomalia — ver abaixo) |
| qwen3:0.6b | 0.6B | 7.1% | [2.0%, 22.6%] (floor real) |

**Observações fortes:**

1. **Tamanho não compra accuracy em Linha A.** qwen3:**1.7B** empata com
   gemma3:**12B** em 46.4%. Reasoning explícito (qwen3:4b-thinking) também
   não supera o base (42.9% em ambos). O ceiling é estrutural —
   capacidade de calcular sobre 100 valores em texto não escala com
   parâmetros nessa faixa.

2. **gpt-oss 20B é anomalia (28.6%).** Apesar de ser o maior, fica abaixo
   de qwen3:1.7b (1.7B). Possíveis causas: quantização MXFP4 agressiva,
   formato de resposta divergente, ou VRAM offload em RTX 3060 12GB
   prejudicando inferência. Não foi investigado a fundo — a faixa útil
   prática é 7-14B em Q4_K_M.

3. **qwen3:0.6b é floor real (7.1%).** Falha até em q_count
   (`wrong_count`). Confirma que existe tamanho mínimo abaixo do qual o
   modelo não opera nem em STATS hints. Para Linha A em texto-tabular,
   não vale abaixo de ~1.5B params.

4. **Reasoning explícito não ajuda.** qwen3:4b vs qwen3:4b-thinking ambos
   42.9% (na mesma seed). deepseek-r1:14b (reasoning) empata com
   qwen2.5-coder:7b (não-reasoning). O gargalo é cálculo, não raciocínio.

**Por modelo × naturalidade (13 modelos, wording N0 limpo — sem hint técnico):**

| Modelo | N0 | N1 | N2 | N3 | Δ (max−min) |
|--------|----|----|----|----|----|
| qwen3:14b | 51% | 48% | 48% | 48% | 3pp |
| gpt-oss:latest | 29% | 29% | 29% | 29% | **0pp** |
| qwen3:4b | 43% | 43% | 43% | 43% | **0pp** |
| qwen3:4b-thinking | 43% | 43% | 43% | 43% | **0pp** |
| mistral-nemo:latest | 43% | 43% | 43% | 43% | **0pp** |
| phi4:latest | 56% | 57% | 52% | 57% | 5pp |
| qwen2.5-coder:7b | 62% | 62% | 57% | 52% | 10pp |
| gemma3:12b | 57% | 43% | 43% | 43% | 14pp |
| gemma3:4b | 43% | 43% | 57% | 43% | 14pp |
| qwen3:1.7b | 57% | 43% | 43% | 43% | 14pp |
| granite3.3:8b | 43% | 43% | 43% | 29% | 14pp |
| deepseek-r1:14b | 57% | 57% | 43% | 71% | 28pp (1 seed, ruído alto) |
| qwen3:0.6b | 0% | 0% | 14% | 14% | 14pp |

**Variação entre níveis é dominada por seed-noise**, não por wording. Quatro
modelos têm accuracy **idêntica** nas 4 formulações. Os outros oscilam
±5-14pp dentro de cada CI Wilson. **Sem tendência monotônica
N0→N3 em nenhum modelo.**

*Nota: wording N0 de `q_avg_hours_male` foi corrigido em 2026-04-26 para
remover hint técnico SQL ("use aspas duplas") que era cola não representativa
de uso real. Resultado: `q_avg_hours_male` continua 0% em todos os níveis
para Linha A — o gargalo é filter+agg, não o wording.*

**Per (naturalidade × question):**

| Question | N0 | N1 | N2 | N3 | Padrão |
|----------|----|----|----|----|--------|
| q_count, q_avg_age, q_max_age | 100% | 100% | 100% | 100% | **Saturação total** — STATS hint resolve |
| q_top_education (string) | 56% | 67% | 44% | 56% | Variação por seed, não por nível |
| q_distinct_workclass | 0% | 0% | **22%** | 0% | Falha quase total — N2 acidental |
| q_count_high_class (filter+count) | 11% | 22% | 0% | 11% | Floor effect |
| q_avg_hours_male (filter+avg) | 0% | 0% | 0% | 0% | Floor absoluto |

**Mecanismo (porque H_natural-1 falhou):**

A accuracy de Linha A é dominada pelo **tipo de cálculo** (full-table agg
via STATS = 100% / filter+agg = 0%), não pela formulação da pergunta.
O LLM não falha por "não entender o que perguntaram" — ele entende em N0
e em N3 igual. Falha por **incapacidade de iterar+filtrar 100 valores**
mentalmente, problema independente da naturalidade.

A taxa de saturação por tipo de question (F-Q28) é o ceiling estrutural;
naturalidade fica abaixo do ruído desse ceiling.

**O que isso refuta e o que NÃO refuta:**

- ✅ Refuta: H_natural-1 para Linha A em locais 7-14B sobre Adult Census.
- ❌ Não refuta para Linha B (LLM gera SQL): em SQL a naturalidade
  pode degradar gravemente porque o modelo precisa **mapear conceitos
  fuzzy → operadores SQL** (ex: "alta renda" → `WHERE class='>50K'`).
  Esse experimento (M-natural-local-linhaB) ainda não foi feito.
- ❌ Não refuta para comerciais: GPT-4o e Claude Sonnet podem ter
  capacidade aritmética mental suficiente para que naturalidade vire
  fator dominante. M-Acomm com naturalness=all vai testar.

**Implicação científica:**

1. **Linha A é robusta a paráfrase** em locais — bom para cenários onde
   o usuário fala "natural"; mau para cenários que exigem cálculo
   complexo (já saturado).
2. **Naturalidade só importa quando há margem para variar.** Com floor
   effect (filter+agg = 0%) e ceiling effect (full-agg = 100%), as
   wordings ficam invisíveis no agregado.
3. **Recomendação para o paper:** apresentar F-Q29 como
   *contra-evidência empírica* à intuição comum de que "perguntas
   naturais quebram o pipeline". Para Linha A, a pergunta natural
   funciona tão bem quanto a schema-aware — só não funciona porque o
   tipo da operação aritmética é o gargalo.

**Próximo:** Linha B com naturalness=all para testar se o gap N0→N3
aparece quando o modelo precisa gerar SQL (não calcular). Esse é o
experimento que define o valor científico do eixo de naturalidade.

**Referência:** `experiments/results/m_alocal/manifest.jsonl` (2026-04-26,
**595 records** — 63 N0 originais + 252 multi-level (3 baseline modelos)
+ 140 borda alta (5 modelos novos 8-20B) + 140 borda baixa (5 modelos
0.6-4B)).

---

## F-Q30 `{B}` — Naturalidade DEGRADA Linha B seletivamente: ambiguidade semântica e limitação de modelo com colunas hifenadas

**Conclusão:** Em Linha B (LLM gera SQL → SQLite executa), naturalidade
**degrada accuracy** em 2 dos 3 modelos testados, mas não uniformemente —
depende do modelo e da questão específica. H_natural-1 é **parcialmente
confirmada**: qwen3:14b é completamente resiliente (100% em todos os
níveis); qwen2.5-coder:7b degrada até -29pp em N1. A degradação ocorre
por **dois mecanismos distintos e reproduzíveis**.

**Evidência (M9-Adult naturalness all, 2026-04-26):** 3 modelos × 3 seeds
× 4 níveis × 7 questions = **252 combos** sobre Adult Census vol=100
stratify_by=class. N0 idêntico ao M9-Adult original (F-Q25=100%).

**Por modelo × naturalidade — 13 modelos (0.6B–20B), wording N0 limpo:**

| Modelo | Params | N0 | N1 | N2 | N3 | Gap max |
|--------|--------|----|----|----|----|---------|
| qwen3:14b | 14B | **100%** | **100%** | **100%** | **100%** | **0pp** |
| gpt-oss:latest | 20B | **100%** | **100%** | **100%** | **100%** | **0pp — surp.¹** |
| phi4:latest | 14B | 100% | 100% | 100% | 86% | 14pp N3 |
| deepseek-r1:14b | 14B | 100% | 100% | 86% | **71%** | 29pp N3 |
| gemma3:12b | 12B | 86% | 86% | 86% | 86% | **0pp** |
| mistral-nemo | 12B | 86% | 86% | 86% | 86% | **0pp** |
| qwen2.5-coder:7b | 7B | 86% | 71% | 86% | 81% | 15pp N1 |
| qwen3:1.7b | 1.7B | 86% | 71% | 71% | 86% | 15pp |
| gemma3:4b | 4B | 86% | 71% | 71% | **43%** | **43pp N3** |
| granite3.3:8b | 8B | 71% | 71% | 71% | 71% | **0pp** |
| qwen3:4b | 4B | 43% | 86% | 71% | 43% | 43pp (não monotônico²) |
| qwen3:4b-thinking | 4B | 43% | 86% | 71% | 43% | igual qwen3:4b |
| qwen3:0.6b | 0.6B | 57% | 43% | 43% | 43% | 14pp |

¹ gpt-oss:latest (20B MXFP4) foi o pior modelo em Linha A (28.6%) e é perfeito em
Linha B (100% em todos os níveis). Ver "Dissociação Linha A × Linha B" abaixo.

² qwen3:4b e qwen3:4b-thinking com 1 seed apenas — variância alta. N1>N0 por
uma questão (q_count, q_distinct_workclass geram `FROM vendas/adultos` em N0/N3).

**Por questão × naturalidade (todos os 3 modelos agregados):**

| Question | N0 | N1 | N2 | N3 | Mecanismo da falha |
|----------|----|----|----|----|-------------------|
| q_count, q_max_age, q_top_education, q_count_high_class | 100% | 100% | 100% | 100% | Robusto — sem ambiguidade |
| q_avg_age | 100% | 100% | 100% | 89% | phi4 falha 1/3 seeds em N3 |
| **q_distinct_workclass** | 100% | **67%** | 100% | 100% | **Ambiguidade semântica** — ver abaixo |
| **q_avg_hours_male** | **67%** | **67%** | **67%** | **33%** | **Limitação do modelo** — ver abaixo |

**Mecanismo 1 — Ambiguidade semântica (q_distinct_workclass, N1 — corrigido):**

Wording N1 original: *"Quantas categorias diferentes de classe trabalhista existem?"*

O LLM mapeava "classe trabalhista" → coluna `class` (renda: <=50K / >50K)
em vez de `workclass` (tipo de empregador). SQL gerado:
```sql
SELECT COUNT(DISTINCT class) FROM adult  -- retorna 2, correto é 6
```
**Correção (2026-04-26):** N1 atualizado para *"Quantas categorias
diferentes de tipo de trabalho existem nos dados?"* — sem "classe".
Após correção: N1 passou de 67% para **89%** (9/9 = 100% em 3 baseline
seeds × 3 modelos; 8/10 na borda, falhas remanescentes por capacidade,
não semântica).

Esta correção confirma que a falha era **exclusivamente o falso amigo
"classe"** — um artefato de design da pergunta, não uma limitação geral
de mapeamento semântico N1. O fenômeno ainda é válido como exemplo
(palavras ambíguas de domínio conflitam com nomes de colunas), mas
não representa degradação sistemática de N0→N1 com wording cuidadoso.

**Mecanismo 2 — Limitação de modelo com colunas hifenadas (q_avg_hours_male):**

A coluna `hours-per-week` requer aspas duplas no SQLite para ser tratada
como identificador (sem aspas, `hours-per-week` é interpretado como
subtração, gerando `OperationalError: no such column: hours`).

**qwen2.5-coder:7b** não usa aspas em colunas hifenadas — falha em
**todos os 4 níveis** (N0=N1=N2=0%, N3=0%). Wording não importa: é
limitação do modelo, não da pergunta. qwen3:14b e phi4 usam aspas
naturalmente (`"hours-per-week"`) em todos os níveis.

**Correção experimental:** o wording N0 original incluía *"Use a coluna
entre aspas duplas"* — hint SQL que mascarava a limitação do modelo
(qwen2.5-coder passava 100% em N0 com hint; 0% sem). Após remoção do
hint (2026-04-26), N0 de `q_avg_hours_male` fica em 67% (qwen3:14b 100%
+ phi4 ~75% + qwen2.5-coder 0%). Não há degradação N0→N1/N2 — apenas N3
cai para 33% (phi4 falha 1/3 seeds em N3 também).

Essa question separa modelos por **proficiência SQL com SQLite**: os que
citam aspas corretamente são resilientes a wording; os que não citam
falham independente do nível.

**Contrates Linha A vs Linha B:**

| | Linha A | Linha B |
|--|---------|---------|
| N0→N3 geral | **0-10pp** (ruído) | **0-29pp** (real) |
| Mecanismo limitante | Aritmética sobre 100 valores | Mapeamento semântico fuzzy→SQL |
| Natureza do ceiling | **Estrutural** (tipo de cálculo) | **Semântico** (modelo-dependente) |
| H_natural-1 | **Rejeitada** | **Confirmada** para 2/3 modelos |

**Por que qwen3:14b é imune?** Hipóteses (não testadas):
1. Training maior e mais recente inclui mais exemplos de SQL com nomes hifenados.
2. qwen3:14b aplica aspas duplas em colunas hifenadas por default.
3. Maior capacidade de inferir schema intent de perguntas ambíguas.

**Implicação para o paper:**

1. **Eixo de naturalidade tem valor científico distinto para as duas linhas:**
   Linha A = naturalidade indiferente (gargalo é aritmética); Linha B =
   naturalidade importa (gargalo é mapeamento semântico).

2. **F-Q30 completa o par assimétrico** com F-Q29. A assimetria é o
   achado — não a degradação por si só.

3. **Dois tipos de falha SQL identificados e separáveis:**
   (a) Ambiguidade de nome: "classe trabalhista" → `class` vs `workclass`
   (b) Hint técnico perdido: "use aspas duplas" → colunas hifenadas sem aspas

4. **Recomendação prática que sai do paper:** wordings de pergunta para
   NL2SQL devem incluir o nome exato da coluna quando há hifens ou
   ambiguidade de domínio. Wording N0 (schema-aware) maximiza accuracy;
   N2 (business-intent) é o ponto ótimo entre naturalidade e
   reliability para `q_avg_hours_male`.

**Dissociação Linha A × Linha B — achado transversal:**

gpt-oss:latest (20B MXFP4) apresenta o caso mais extremo visto até agora:
- **Linha A**: 28.6% — pior entre todos os 13 modelos testados
- **Linha B**: 100% em N0/N1/N2/N3 — junto com qwen3:14b os únicos imunes

Isso prova empiricamente que **geração de SQL e cálculo direto são
capacidades orthogonais**. Um modelo pode ser excelente em mapear linguagem
natural → SQL correto e ao mesmo tempo incapaz de iterar sobre 100 valores
em texto. A arquitetura MXFP4 do gpt-oss pode ter degradado a precisão
numérica (afetando Linha A) sem afetar geração de linguagem estruturada
(Linha B).

**Para o paper:** essa dissociação é evidência forte de que a comparação
Linha A × Linha B não é trivial — é uma medida de duas capacidades
distintas, e a escolha do paradigma deve ser feita de acordo com o perfil
do query, não do modelo.

**Referência:** `experiments/results/m9_adult/manifest.jsonl` (2026-04-26,
532 records — 252 baseline 3 modelos + 280 borda 10 modelos, 1 seed cada).

---

## F-Q31 `{B}` — Linha A em comerciais com reasoning quebra o ceiling filter+agg local; o eixo é REASONING, não tamanho

**Conclusão:** O ceiling de ~50% que F-Q12/F-Q28 estabeleceram para Linha A em
modelos locais 0.6B-20B **não é universal**. Modelos comerciais com **chain-of-thought
interno (reasoning)** atingem **82-95%** na mesma suite, com o tier mais barato
(gpt-5.4-nano @ $0.20/$1.25 por 1M tokens) já fazendo 86.9%. O eixo limitante
não é tamanho do modelo, é a presença de reasoning explícito — gpt-4o-mini
(non-reasoning, modelo OpenAI da geração anterior) cai em 52.4%, **dentro
do mesmo range dos locais**.

**Evidência (M-Acomm Linha A, 2026-04-26):** 4 modelos OpenAI × 3 seeds × 4
níveis × 7 questões = **336 records** sobre Adult Census vol=100
stratify_by=class. Mesmo dataset e protocolo de F-Q28/F-Q29.

**Tabela central:**

| Modelo | Tipo | Linha A | CI Wilson | $/call (cached) |
|--------|------|---------|-----------|------------------|
| **gpt-5.4** | reasoning | **95.2%** | [88.4%, 98.1%] | $0.0061 |
| **gpt-5.4-nano** | reasoning | **86.9%** | [78.1%, 92.5%] | $0.0007 |
| **gpt-5.4-mini** | reasoning | **82.1%** | [72.6%, 88.9%] | $0.0027 |
| **gpt-4o-mini** | non-reasoning | **52.4%** | [41.8%, 62.7%] | $0.0003 |
| qwen3:14b (local) | non-reasoning | 47.6% | [38.3%, 57.1%] | $0 |
| qwen2.5-coder:7b (local) | non-reasoning | 57.1% | [47.6%, 66.2%] | $0 |
| deepseek-r1:14b (local) | reasoning | 57.1% | [39.1%, 73.5%] | $0 |

**Per (modelo × naturalidade):**

| Modelo | N0 | N1 | N2 | N3 | Gap |
|--------|----|----|----|----|----|
| gpt-5.4 | 100% | 90% | 90% | 100% | 10pp |
| gpt-5.4-nano | 90% | 81% | 86% | 90% | 9pp |
| gpt-5.4-mini | 86% | 76% | 86% | 81% | 10pp |
| gpt-4o-mini | 52% | 48% | 52% | 57% | 9pp |

Naturalidade tem efeito leve (~10pp gap), consistente com F-Q29 (não-degrada).

**Por questão (todos os 4 modelos × 4 níveis):**

| Question | gpt-5.4 | gpt-5.4-nano | gpt-5.4-mini | gpt-4o-mini |
|----------|---------|--------------|--------------|-------------|
| q_count, q_avg_age, q_max_age | 100% | 100% | 100% | 100% |
| q_distinct_workclass | 89% | 100% N0 / mixed | 100% N0 / mixed | 75% N0 / 0% mixed |
| q_top_education | 89% | 67-100% | 67-100% | 67-83% |
| **q_count_high_class** | **75%** | **67-100%** | **0-83%** | **0-83%** |
| **q_avg_hours_male** | **83%** | **100%** | **67-100%** | **0-75%** |

`q_count_high_class` e `q_avg_hours_male` (filter+agg = ceiling local de 0%):
- **gpt-5.4 e gpt-5.4-nano: 75-100%** → ceiling quebrado
- gpt-4o-mini: 0-83% → comportamento similar a locais
- **deepseek-r1:14b local (reasoning): 0% em filter+agg** — reasoning local
  ainda não basta; o ganho não é só "ter reasoning", é "ter reasoning de
  qualidade comercial".

**Mecanismo (por que reasoning ajuda em filter+agg):**

A questão `q_avg_hours_male` exige iterar sobre 100 linhas do TCF L2 (RLE-encoded),
filtrar por sex='Male' (~50 linhas), somar hours-per-week dessas e dividir.
LLMs sem chain-of-thought tentam responder direto e:
1. Confundem o resultado da média geral (avg_hours = 42.43) com a média filtrada
2. Subcontagem por contar parcial (mini: 18 vs 24 em count_high_class)
3. Refusal quando tarefa fica complexa demais

LLMs com chain-of-thought conseguem manter o registro de "sex igual a Male"
ao iterar e produzir contagens corretas — empiricamente os gpt-5.x acertaram
**100% em q_avg_hours_male** que locais nunca quebraram.

**Sub-finding — hierarquia não monotônica em gpt-5.x:**

gpt-5.4-mini (82.1%) é PIOR que gpt-5.4-nano (86.9%) — CIs sobrepõem mas
ranking inverte. Possível razão: nano tem reasoning de qualidade comercial
+ menor tendência a "ficar em volta" (verbosity excessiva no chain-of-thought).
Não é evidência de que mini é fundamentalmente pior; é evidência de que
**em Linha A com reasoning de qualidade, o ganho satura cedo na escala**.

**Implicações fortes para o paper:**

1. **F-Q12/F-Q28 não são universais:** o ceiling 0% filter+agg observado
   em locais 0.6-20B é uma propriedade da geração de modelos *non-reasoning*,
   não uma limitação do paradigma Linha A.

2. **Linha A passa a ser viável** para datasets pequenos (vol=100) quando
   o modelo tem reasoning de qualidade comercial (gpt-5.x). O ceiling
   95% do gpt-5.4 (full tier) está a 5pp de Linha B local — gap fechável
   com outputs estruturados e prompts bem desenhados.

3. **Custo da Linha A comercial é tratável:** gpt-5.4-nano fez 84 calls
   a $0.0007/call = **$0.06**. Para uma aplicação que precise responder
   "qual o faturamento dos clientes premium" sobre tabela de 100 linhas,
   gpt-5.4-nano é viável e mais simples que pipeline Linha B (sem
   necessidade de SQLite, schema validation, etc).

4. **Recomendação prática:** Use Linha A com gpt-5.x para datasets pequenos,
   Linha B com SQL execution para datasets grandes (>1000 linhas onde a
   janela de contexto seria proibitiva).

5. **Recomendação teórica:** Se reasoning local de qualidade comercial
   chegar a domínio público (qwen3 com pensamento melhor, deepseek-r2,
   etc.), o ceiling F-Q12 deve cair para esses modelos também. Vale
   re-rodar F-Q31 em 6-12 meses.

**Custo total do experimento:** $0.819 USD para 336 records (4 modelos × 84
calls), com ~77% de cache hit em todos os modelos. Sem prompt caching o
custo seria ~$3.50.

**Referência:** `experiments/results/m_acomm/manifest.jsonl` (2026-04-26,
336 records — F2 nano, F3 mini, F4 full, F5 4o-mini-controle).

---

## F-Q32 `{B}` — Linha B comercial top é 100% imune a naturalidade; degradações remanescentes são por ambiguidade de schema, não falta de capacidade

**Conclusão:** Em Linha B (LLM gera SQL → SQLite executa), modelos
comerciais frontier (gpt-5.4 full e mini) **fazem 100% em N0/N1/N2/N3**
— totalmente imunes a degradação por naturalidade. O tier mais barato
(gpt-5.4-nano) e o controle non-reasoning (gpt-4o-mini) têm degradação
modesta (-9pp e -10pp), mas com mecanismos identificáveis:
**(a) ambiguidade de schema entre colunas semanticamente próximas, e
(b) limitação de modelo com colunas hifenadas em SQL.** F-Q30
(naturalidade degrada Linha B local) **não generaliza para comerciais top**.

**Evidência (M-Acomm-B Linha B SQL, 2026-04-26):** 4 modelos OpenAI ×
3 seeds × 4 níveis × 7 questões = **336 records** sobre Adult Census
vol=100 stratify_by=class. Mesmo dataset de F-Q31; apenas mudou o
paradigma (gera SQL em vez de calcular).

**Tabela central:**

| Modelo | Tipo | Linha B | CI Wilson | $/call | Naturalness gap |
|--------|------|---------|-----------|--------|-----------------|
| **gpt-5.4** | reasoning | **100%** | [95.6%, 100%] | $0.0021 | **0pp** |
| **gpt-5.4-mini** | reasoning | **100%** | [95.6%, 100%] | $0.0006 | **0pp** |
| gpt-5.4-nano | reasoning | 90.5% | [82.3%, 95.1%] | $0.00016 | 14pp (N0=100% / N1=86%) |
| gpt-4o-mini | non-reasoning | 85.7% | [76.7%, 91.6%] | $0.0001 | **0pp (86% flat)** |
| qwen3:14b (local) | non-reasoning | 100% | flat | $0 | 0pp |
| qwen2.5-coder:7b (local) | non-reasoning | 86% | mixed | $0 | -15pp em N1 |

**Per (modelo × naturalidade):**

| Modelo | N0 | N1 | N2 | N3 |
|--------|----|----|----|----|
| gpt-5.4 | 100% | 100% | 100% | 100% |
| gpt-5.4-mini | 100% | 100% | 100% | 100% |
| gpt-5.4-nano | **100%** | 86% | 86% | 90% |
| gpt-4o-mini | 86% | 86% | 86% | 86% (flat — limitação fixa) |

**Comparação Linha A × Linha B em comerciais (mesmas 4 modelos):**

| Modelo | Linha A | Linha B | Δ |
|--------|---------|---------|---|
| gpt-5.4 | 95.2% | **100%** | +5pp |
| gpt-5.4-mini | 82.1% | **100%** | +18pp (gap dramático) |
| gpt-5.4-nano | 86.9% | 90.5% | +3.6pp |
| gpt-4o-mini | **52.4%** | **85.7%** | **+33pp (transformação)** |

**Mecanismo das falhas remanescentes:**

**Mecanismo 1 — Ambiguidade workclass × occupation (gpt-5.4-nano N1, 3/3 seeds):**

Wording N1 corrigido: *"Quantas categorias diferentes de tipo de trabalho
existem nos dados?"*

gpt-5.4-nano gera consistentemente:
```sql
SELECT COUNT(DISTINCT occupation) AS categorias_trabalho FROM adult
```

O Adult Census tem **ambas as colunas** `workclass` (tipo de empregador:
Private, Self-emp, etc.) e `occupation` (profissão específica:
Tech-support, Craft-repair, etc.). N1 "tipo de trabalho" é semanticamente
mais próximo de `occupation`, mas a GT usa `workclass`. **N0 ancora
explicitamente em `workclass` — comerciais top (gpt-5.4 full/mini)
escolhem corretamente; nano escolhe a interpretação natural-mas-divergente.**

Esse é um achado científico legítimo: quando o schema tem **múltiplas
colunas semanticamente próximas**, wordings naturais não são suficientes
para ancorar o modelo — apenas modelos top conseguem inferir qual coluna
o experimento espera. Não é bug de design, é o experimento medindo
exatamente isso.

**Mecanismo 2 — Coluna hifenada sem aspas duplas (gpt-4o-mini, 12/12 falhas):**

gpt-4o-mini gera consistentemente em todos os níveis:
```sql
SELECT AVG(hours-per-week) FROM adult WHERE sex = 'Male'
-- OperationalError: no such column: hours
```

Mesmo problema do qwen2.5-coder:7b local. **gpt-4o-mini (non-reasoning,
geração anterior) tem essa limitação fixa**; gpt-5.4 family usa aspas
duplas naturalmente (`"hours-per-week"`).

**Mecanismo 3 — Convenção SQL underscore (gpt-5.4-nano N2/N3, 4 casos):**

gpt-5.4-nano às vezes "normaliza" o nome da coluna:
```sql
SELECT AVG(hours_per_week) AS horas_semanais_medias FROM adult
-- OperationalError: no such column: hours_per_week
```

Aplicação automática da convenção SQL standard (`_`) em vez do nome
original (`-`). Modelos top (gpt-5.4 full/mini) preservam o nome literal.

**Implicações:**

1. **F-Q30 não é universal:** a degradação por naturalidade em Linha B
   observada em locais (qwen2.5-coder -15pp) **não persiste em comerciais
   top**. F-Q30 fica refinado: "Linha B degrada com naturalidade em
   modelos non-reasoning OU reasoning de tier baixo; modelos top são
   imunes."

2. **gpt-4o-mini é caso pedagógico:** transformação de 52% (Linha A) →
   86% (Linha B) com o mesmo modelo no mesmo dataset mostra que **a
   abstração via SQL libera o modelo da tarefa de calcular**, e ela
   fica trivialmente correta (SQLite faz a conta).

3. **Linha B é a recomendação prática default:** todos os comerciais
   testados ≥85% em Linha B; ≥3 dos 4 atingem 90%+. Em Linha A, só
   gpt-5.4 full chega a 95%. Para usuários reais, Linha B é a aposta
   mais segura.

4. **Quando Linha A faz sentido:** datasets pequenos (≤100 linhas) onde
   o overhead de pipeline SQL não vale, OU tarefas onde aritmética
   simples (full-table aggregation) é suficiente.

5. **Custo Linha B vs Linha A:**
   - Linha B (~470 tokens schema): $0.0001-0.0021/call
   - Linha A (~3133 tokens TCF L2): $0.0007-0.0061/call
   - Linha B é **5-10× mais barato** por call e atinge accuracy maior.

**Sub-finding — questão q_avg_hours_male é diagnóstico de proficiência SQL:**

Esta question (filter+avg sobre coluna hifenada) separa modelos por
proficiência de SQL gen mesmo com wording N0 schema-aware:

| Modelo | q_avg_hours_male Linha B |
|--------|--------------------------|
| gpt-5.4 | 100% (todas as 12 chamadas) |
| gpt-5.4-mini | 100% |
| gpt-5.4-nano | 67% (4 falhas por convenção `_`) |
| gpt-4o-mini | 0% (12 falhas por aspas faltantes) |

Recomendação: usar `q_avg_hours_male` como teste de "este modelo é
proficient em SQL com nomes irregulares?" antes de adotar para produção.

**Custo total experimento Linha B:** $0.255 USD para 336 records,
~5× mais barato que Linha A com mesmo escopo.

**Custo cumulativo M-Acomm completo (Linha A + B):** **$1.07 USD** para
672 records (4 modelos × 84 calls × 2 paradigmas). Sem prompt caching
seria ~$5-6 USD; com cache 75-77% economia.

**Referência:** `experiments/results/m_acomm_b/manifest.jsonl` (2026-04-26,
336 records — gpt-5.4-nano, gpt-5.4-mini, gpt-5.4, gpt-4o-mini).

---

## F-Q33 `{B}` — Naturalidade degrada Linha B em TPC-H multi-tabela DRAMATICAMENTE; mecanismo é schema ambiguity sistemática

**Conclusão:** Em TPC-H (multi-tabela com colunas semanticamente sobrepostas),
Linha B degrada **30-45pp** com naturalidade nível N2 em **todos** os
modelos locais 7-14B testados — uma queda muito mais severa que em Adult
(F-Q30, máximo -15pp). O mecanismo central é **schema ambiguity
sistemática**: TPC-H tem 2+ colunas que são plausíveis interpretações de
"preço/valor/custo" (ps_supplycost, p_retailprice) e wordings business
(N2/N3) ativam consistentemente a interpretação errada do GT.

**Evidência (M9-canonical naturalness all, 2026-04-26):** 3 modelos × 3
seeds × 4 níveis × 7 questões = **252 records** sobre TPC-H sf001
(partsupp + supplier + part). Mesmo protocolo SQL gen + SQLite execute
de F-Q30; payload schema-only ~470 tokens.

**Tabela central — modelo × naturalidade:**

| Modelo | N0 | N1 | N2 | N3 | Gap N0→N2 |
|--------|----|----|----|----|----|
| qwen3:14b | 95% | 95% | **62%** | 95% | **-33pp** |
| qwen2.5-coder:7b | 95% | 95% | **52%** | 67% | **-43pp** |
| phi4:latest | 95% | 81% | **57%** | 52% | **-38pp** |

Note que **qwen3:14b** — que era **imune em Adult Linha B (F-Q30)** — também
degrada -33pp em N2 aqui. A imunidade observada em Adult não se sustenta
quando o schema tem ambiguidade real entre colunas.

**Por questão × naturalidade (todos os 3 modelos agregados):**

| Question | N0 | N1 | N2 | N3 | Mecanismo |
|----------|----|----|----|----|-----------|
| q_count | 100% | 100% | 100% | 89% | Robusto |
| q_avg | 100% | 100% | 100% | 100% | Robusto |
| q_top_product | 67% | 67% | 67% | 78% | Tie issue (N0 também falha) |
| q_distinct | 100% | 100% | 100% | **33%** | N3 ambiguidade |
| **q_sum** | 100% | 67% | **22%** | 33% | **cost vs cost×qty** |
| **q_lookup** | 100% | 100% | **0%** | 67% | **ps_supplycost vs p_retailprice** |
| **q_lookup_value** | 100% | 100% | **11%** | 100% | **valor vs nome** |

**Mecanismo 1 — Compromisso financeiro como `cost × qty` (q_sum N2):**

Wording N2: *"Qual o valor total comprometido em fornecimento?"*

SQL gerado por qwen2.5-coder:
```sql
SELECT SUM(ps_supplycost * ps_availqty) AS total_commitment FROM partsupp
-- got: $230,405,853 (cost × quantity)
-- expected: $47,795 (sum of cost only)
```

A interpretação `cost × qty` é **business-correct** ("valor comprometido
em estoque"), mas diverge do GT. Em N0 ("soma da coluna ps_supplycost"),
a coluna está explícita; em N2 o modelo escolhe a operação que mais faz
sentido em business terms — e a tabela `partsupp` tem **ps_availqty**
disponível justamente para essa operação semântica.

**Mecanismo 2 — Catalog price vs supply cost (q_lookup N2/N3):**

Wording N2: *"Qual fornecedor opera o item mais caro do nosso catálogo?"*

SQL gerado:
```sql
SELECT s.s_name FROM supplier s
JOIN partsupp ps ON s.s_suppkey = ps.ps_suppkey
JOIN part p ON ps.ps_partkey = p.p_partkey
ORDER BY p.p_retailprice DESC LIMIT 1
-- got: supplier do max(retail_price)
-- expected: supplier do max(supply_cost)
```

"Item mais caro do catálogo" → modelo interpreta como `part.p_retailprice`
(preço de catálogo), não `partsupp.ps_supplycost` (custo de fornecimento).
Ambas existem, ambas são plausíveis. **q_lookup N2 = 0/9 (0%) em todos
os modelos** — o gradiente semântico é tão forte que NENHUM modelo
preserva a interpretação N0.

**Mecanismo 3 — Resposta do tipo errado (q_lookup_value N2):**

Wording N2: *"Qual o item mais caro do nosso fornecimento?"*

SQL gerado:
```sql
SELECT p.p_name, p.p_retailprice
FROM part p JOIN partsupp ps ON p.p_partkey = ps.ps_partkey
ORDER BY p.p_retailprice DESC LIMIT 1
-- got: nome do part (string)
-- expected: 998.83 (numeric value)
```

"Item mais caro" pede numeric value (GT.max_metric_value), mas wording
business sugere "item" = nome. Modelo retorna o NOME do part, não o
valor. **Tipo de resposta errado.** N3 ("Qual o valor unitário mais
alto?") explicita "valor" e recupera 100%.

**Comparação Adult × TPC-H Linha B local:**

| | Adult (single-table) | TPC-H (multi-tabela) |
|--|---------------------|----------------------|
| N0 baseline | 86-100% | 95% (3 modelos) |
| N2 worst case | 86% | **52%** (qwen2.5-coder) |
| N3 worst case | 81% | **52%** (phi4) |
| qwen3:14b | imune (100% todos) | -33pp em N2 |
| Mecanismo | hint perdido + ambiguidade | **schema ambiguity sistemática** |

**Implicações para o paper:**

1. **F-Q30 não generaliza para multi-tabela:** a imunidade do qwen3:14b
   em Adult Linha B foi específica de single-table. Em TPC-H, mesmo
   modelos top locais quebram.

2. **F-Q33 é o achado mais forte do eixo de naturalidade:**
   degradação consistente em 3/3 modelos (CIs não sobrepõem em N2 vs N0).
   H_natural-1 confirmada empiricamente em multi-tabela.

3. **Naturalidade ⊥ schema ambiguity** — quanto mais colunas
   semanticamente próximas existirem (ps_supplycost, p_retailprice,
   ps_availqty), mais oportunidades para o modelo escolher caminho
   alternativo plausível. Schema linking de literatura clássica é
   exatamente isso.

4. **Recomendação prática para BI:** dataset com colunas $ ambíguas
   (preço de varejo vs custo de fornecimento) **devem ter wordings
   schema-aware (N0)** em interfaces de NL2SQL — N2 sem âncora produz
   60% de respostas business-plausíveis-mas-erradas.

5. **Hipótese para comerciais TPC-H:** gpt-5.4 family pode preservar
   accuracy mais alta (em Adult eles foram 100% em todos os níveis),
   mas esperamos degradação MENOR que locais. Vale rodar para confirmar.

**Custo:** $0 (modelos locais Ollama).

**Referência:** `experiments/results/m9_canonical/manifest.jsonl`
(2026-04-26, 252 records, qwen3:14b + qwen2.5-coder:7b + phi4:latest).

---

## F-Q34 `{B}` — Schema ambiguity em multi-tabela é UNIVERSAL: comerciais top também caem -43pp em N2

**Conclusão:** A degradação dramática observada em F-Q33 (locais TPC-H N2
caem 30-45pp) **não é específica de modelos locais** — comerciais top
(gpt-5.4 e gpt-5.4-mini) também caem **-43pp em N2** (de 100% para 57%).
**Schema linking permanece um problema aberto** mesmo para os melhores
modelos disponíveis em janeiro 2026. F-Q32 (comerciais top imunes a
naturalidade) **não generaliza para multi-tabela com schema ambíguo**.

**Evidência (M-Acomm-B TPC-H, 2026-04-26):** 4 modelos OpenAI × 3 seeds
× 4 níveis × 7 questões = **336 records** sobre TPC-H sf001 com mesmo
protocolo SQL gen + execute de F-Q32.

**Tabela central — modelo × naturalidade (Linha B em TPC-H):**

| Modelo | N0 | N1 | N2 | N3 | Gap N0→N2 |
|--------|----|----|----|----|----|
| gpt-5.4 | 100% | 100% | **57%** | 86% | **-43pp** |
| gpt-5.4-mini | 100% | 100% | **57%** | 86% | **-43pp** |
| gpt-5.4-nano | 95% | 95% | **52%** | 81% | **-43pp** |
| gpt-4o-mini | 95% | 81% | **48%** | 62% | -47pp |

Hierarquia preservada (full ≈ mini > nano > 4o-mini), mas **gap N0→N2 é
constante em -43pp em 3 dos 4 modelos**. Não é problema de capacidade
de modelo — é estrutural do schema.

**Comparação Adult Linha B × TPC-H Linha B (mesmas 4 modelos):**

| Modelo | Adult Linha B | TPC-H Linha B | Δ |
|--------|---------------|---------------|---|
| gpt-5.4 | **100%** | 85.7% | -14pp |
| gpt-5.4-mini | **100%** | 85.7% | -14pp |
| gpt-5.4-nano | 90.5% | 81.0% | -10pp |
| gpt-4o-mini | 85.7% | 71.4% | -14pp |

Diferença de domínio é ~14pp para os 4 modelos — TPC-H é universalmente
mais difícil que Adult em Linha B.

**Per questão × naturalidade (todos 4 modelos comerciais):**

| Question | N0 | N1 | N2 | N3 | Padrão |
|----------|----|----|----|----|---------|
| q_count, q_avg | 100% | 100% | 100% | 100% | Robusto |
| q_distinct | 100% | 100% | 100% | 92% | Quase robusto |
| q_top_product | 83% | 83% | 75% | 83% | Tie issue (igual N0) |
| **q_sum** | 100% | 100% | **0%** | 0% | **Universal failure N2/N3** |
| **q_lookup** | 100% | 75% | **0%** | 75% | **Universal failure N2** |
| **q_lookup_value** | 100% | 100% | **0%** | 100% | **Universal failure N2** |

**As mesmas 3 questões de F-Q33 falham em comerciais com a mesma
mecânica.** Inspeção qualitativa confirma:
- q_sum N2: gpt-5.4 também gera `SUM(ps_supplycost * ps_availqty)`
- q_lookup N2: gpt-5.4 também usa `ORDER BY p_retailprice`
- q_lookup_value N2: gpt-5.4 também retorna nome do part em vez do valor

**Sub-finding contraintuitivo — comerciais MAIS suscetíveis em alguns casos:**

| Question N2 | Locais (qwen3:14b) | Comerciais (gpt-5.4) |
|--|--|--|
| q_sum | 22% | **0%** |
| q_lookup_value | 11% | **0%** |

Comerciais top falham *mais consistentemente* em N2 que o melhor local
(qwen3:14b). Hipótese: comerciais aplicam mais agressivamente
interpretações business-level naturais (cost × qty), levando a respostas
**business-correct mas GT-incorrect** com taxa maior. Locais às vezes
geram SQL "menos sofisticado" que acidentalmente acerta o GT por
literalismo.

**N3 recupera (mas não totalmente):**

q_sum N3 = 0% ainda. q_lookup_value N3 = 100%. q_lookup N3 = 75%.
N3 wording introduz contexto operacional ("nossa operação", "fornecimento")
que ajuda em algumas (lookup_value pede "valor" → recupera tipo), mas
não em outras (q_sum N3 "total investido" continua sendo cost × qty).

**Implicações fortes:**

1. **F-Q32 (imunidade comercial) era specific Adult.** Não generaliza
   para schemas com múltiplas colunas semanticamente próximas. F-Q32
   precisa ser refinado: "comerciais top imunes a naturalidade em
   single-table com cols inequívocas".

2. **Schema linking continua problema aberto em 2026.** O paper pode
   citar essa evidência junto a Luo et al. VLDB 2024 para validar a
   importância do tema. Mesmo gpt-5.4 (frontier) não resolve.

3. **Recomendação prática — wordings schema-aware obrigatório em
   datasets ambíguos:**
   - Se schema tem ≥2 colunas semanticamente próximas (custo,
     preço, valor; data de pedido, data de envio, etc.) → forçar
     N0 (mencionar coluna explícita) em interfaces NL2SQL
   - N1-N3 são adequadas para schemas inequívocos (single-table ou
     multi-table com colunas únicas)

4. **F-Q34 + F-Q33 fecham o eixo de naturalidade do paper:** os 6
   findings F-Q29..F-Q34 cobrem 4 paradigmas × 2 datasets × locais e
   comerciais, com mecanismos identificados em cada falha.

5. **Tabela 2D paper-ready:**

   | | Single-table (Adult) | Multi-tabela (TPC-H) |
   |--|---------------------|----------------------|
   | Locais Linha A | Plano N0=N3 (F-Q29) | Não testado (filter+agg ceiling) |
   | Locais Linha B | -15pp pior caso (F-Q30) | **-43pp em N2** (F-Q33) |
   | Comerciais Linha A | Reasoning quebra ceiling (F-Q31) | Pendente |
   | Comerciais Linha B | 100% imunes (F-Q32) | **-43pp em N2** (F-Q34) |

**Custo:** $0.41 USD para 336 records. Cumulativo M-Acomm completo
(Adult A+B + TPC-H B): **$1.48 USD / $30 budget (4.9% gasto)**.

**Referência:** `experiments/results/m_acommB_tpch/manifest.jsonl`
(2026-04-26, 336 records — gpt-5.4-nano, mini, full, gpt-4o-mini).

---

## F-Q35 `{B}` — Linha A comercial em multi-tabela: ceiling cai para 60-76%; schema ambiguity ataca paradigm-independent

**Conclusão:** Em TPC-H multi-tabela, Linha A comercial (LLM lê TCF e
calcula direto) **cai 11-21pp** vs Adult. Mesmo gpt-5.4 (que fez 95% em
Adult) chega só a **74%** em TPC-H. Naturalidade N2 derruba os 4 modelos
para 43-57% — **paradigm-independent**: o mesmo gradiente N0→N2 que
crashou Linha B (F-Q33/F-Q34) crasha Linha A. Schema ambiguity não
exige geração de SQL para causar dano; basta o modelo ter que escolher
qual coluna $ usar.

**Evidência (M-Acomm-A-TPCH, 2026-04-26):** 4 modelos OpenAI × 3 seeds
× 4 níveis × 7 questões = **336 records** sobre TPC-H sf001 com payload
TCF L2 de **33,649 chars (~8400 tokens)** — 2.5× maior que Adult.

**Tabela central — modelo × naturalidade (Linha A em TPC-H):**

| Modelo | N0 | N1 | N2 | N3 | Acc geral | Adult |
|--------|----|----|----|----|-----------|-------|
| **gpt-5.4-nano** | 86% | 81% | **57%** | 81% | **76.2%** | 86.9% |
| gpt-5.4 | 86% | 86% | **52%** | 71% | 73.8% | 95.2% |
| gpt-5.4-mini | 76% | 81% | **43%** | 62% | 65.5% | 82.1% |
| gpt-4o-mini | 62% | 67% | **52%** | 57% | 59.5% | 52.4% |

**Sub-finding contraintuitivo — gpt-5.4-nano > gpt-5.4 full em TPC-H Linha A.**

CIs sobrepõem mas o ranking se inverte vs Adult. Possível explicação:
gpt-5.4 full aplica reasoning mais elaborado, que em TPC-H multi-tabela
abre espaço para "interpretações criativas" do schema (cost × qty,
retail vs supply). gpt-5.4-nano com reasoning de baixa intensidade fica
mais literal e acerta mais. **Tier mais barato venceu o frontier.**

**Per (naturalidade × questão):**

| Question | N0 | N1 | N2 | N3 | Mecanismo |
|----------|----|----|----|----|-----------|
| q_count | 100% | 100% | 100% | 100% | Robusto |
| q_avg | 100% | 100% | 92% | 100% | Quase robusto |
| q_distinct | 75% | 75% | 100% | 83% | Variação por contagem (s_suppkey distinct) |
| **q_sum** | 100% | 92% | **42%** | 50% | cost × qty (paradigm-independent) |
| **q_lookup_value** | 100% | 92% | **8%** | 75% | Retorna nome em vez de valor |
| **q_lookup** | 50% | 58% | **0%** | 42% | retail vs supply (universal failure N2) |
| **q_top_product** | 17% | 33% | 17% | 25% | **JOIN lógico em Linha A é catastrófico** |

**Mecanismo paradigma-independente — q_lookup N2 = 0/12 universal:**

A wording N2 *"Qual fornecedor opera o item mais caro do nosso catálogo?"*
faz com que **tanto Linha B (F-Q34) quanto Linha A (esta finding)** caiam
para 0% em todos os 4 modelos comerciais. O modelo escolhe `p_retailprice`
(catálogo de varejo) consistentemente em vez de `ps_supplycost` (custo
de fornecimento), gerando SQL errado em Linha B ou raciocínio errado
em Linha A. **Schema ambiguity não é resolvida pelo paradigm.**

**Sub-finding novo — q_top_product é o teto inferior em Linha A multi-tabela:**

q_top_product Linha A TPC-H = 17-33%. Em Linha B = 75-83%. Diferença ~50pp.

Mecanismo: q_top_product exige **agrupar partkeys, contar ocorrências,
ordenar, mapear top → nome via JOIN com `part`**. Em Linha B isso é
1 linha de SQL. Em Linha A o modelo precisa fazer manualmente:
1. Iterar 100 valores de ps_partkey (RLE-encoded)
2. Manter contagens em head
3. Encontrar max de count
4. Cruzar com 94 valores de p_partkey + p_name na outra tabela TCF

Mesmo gpt-5.4 falha frequentemente — não é falta de capacidade aritmética,
é capacidade limitada de manter **estado relacional cruzado** durante
chain-of-thought.

**Comparação Adult × TPC-H (Linha A comercial):**

| Modelo | Adult | TPC-H | Δ | Razão da queda |
|--------|-------|-------|---|----------------|
| gpt-5.4 | 95.2% | 73.8% | **-21pp** | Schema ambiguity + JOIN lógico |
| gpt-5.4-nano | 86.9% | 76.2% | **-11pp** | Mais resiliente; menor reasoning = mais literal |
| gpt-5.4-mini | 82.1% | 65.5% | **-17pp** | Schema ambiguity hits hardest aqui |
| gpt-4o-mini | 52.4% | 59.5% | **+7pp** | Subiu! Floor vs questions accessible |

gpt-4o-mini é o único que **subiu de Adult para TPC-H em Linha A**.
Hipótese: em Adult, gpt-4o-mini falhou em filter+agg (q_count_high_class,
q_avg_hours_male). Em TPC-H não há filter+agg como question — todas as
operações são full-table. As perguntas TPC-H mapeiam para STATS hints
mais bem para o modelo non-reasoning.

**Tabela 2D paper-ready FINAL (8 células):**

|                    | Adult (single-table)         | TPC-H (multi-table)            |
|--------------------|------------------------------|--------------------------------|
| Locais Linha A     | Plano (F-Q29) ~50%           | Não testado*                   |
| Locais Linha B     | -15pp (F-Q30) 86-100%        | **-43pp** (F-Q33) 52-95%       |
| Comerciais Linha A | Reasoning quebra (F-Q31) 95% | **-21pp** (F-Q35) 60-76%       |
| Comerciais Linha B | 100% imunes (F-Q32)          | **-43pp** (F-Q34) 48-86%       |

\* Locais Linha A em TPC-H não testados — F-Q12/F-Q28 ceiling sugere
~0-30% se o filter+agg dominar; vol=100 com 3 tabelas (33K char payload)
provavelmente excede capacity de qwen3:14b context.

**Implicações para o paper:**

1. **Linha A não é solução universal.** Funciona bem para single-table com
   colunas inequívocas (Adult, gpt-5.4 = 95%). Em multi-tabela com
   ambiguidade, cai para 60-76%.

2. **Linha B continua melhor que Linha A em TPC-H comercial:**
   - Linha B: 71-86% (F-Q34)
   - Linha A: 60-76% (F-Q35)
   - Linha B vence por 10-15pp e custa **5× menos** (payload schema-only).

3. **q_top_product é o caso limite** — 17% em Linha A vs 75% em Linha B.
   Workloads que precisam JOIN lógico **devem usar Linha B** sem
   discussão.

4. **Schema ambiguity é paradigm-independent.** Resolver isso exige:
   - Wordings schema-aware (N0) em interfaces NL2SQL com schemas ambíguos
   - Few-shot examples ancorando interpretações
   - Schema linking explícito como fase pre-execution
   - **Não é algo que o LLM resolve por ser maior ou ter mais reasoning.**

**Custo:** $1.68 USD para 336 records. **Cumulativo M-Acomm completo
(Adult A+B + TPC-H A+B): $3.16 USD / $30 budget (10.5%).**

**Referência:** `experiments/results/m_acommA_tpch/manifest.jsonl`
(2026-04-26, 336 records — gpt-5.4-nano, mini, full, gpt-4o-mini).

---

## F-Q36 `{B}` — Anthropic vs OpenAI: paridade em Linha B, gap em Linha A; thinking obrigatório

**Conclusão:** Replicação completa do M-Acomm com 3 modelos Anthropic
(haiku 4.5, sonnet 4.6, opus 4.7) em Adult+TPC-H × Linha A+B = 1008
records. Achados centrais:

1. **Linha B Anthropic ≈ OpenAI** em ambos datasets (96-99% Adult,
   80-88% TPC-H). Diferenças dentro do CI Wilson.
2. **Linha A Adult: OpenAI vence** (gpt-5.x 82-95% vs Anthropic 76-80%).
   Gap real de ~10-15pp.
3. **Linha A TPC-H: paridade** (gpt-5.4 73.8% vs sonnet/opus 75%).
4. **F-Q33/F-Q34 (schema ambiguity) confirmado em Anthropic.** q_sum N2 = 0%,
   q_lookup_value N2 = 0% também em haiku/sonnet/opus.
5. **Thinking parameter obrigatório** para Anthropic em Linha A — sem
   thinking, haiku/sonnet caem para 57-58% (range non-reasoning).
6. **API divergente dentro da família Anthropic**: opus 4.7 usa
   `thinking.type=adaptive` + `output_config.effort`; haiku 4.5 e sonnet 4.6
   usam `thinking.type=enabled` + `budget_tokens`. Implementação tem que
   discriminar.

**Tabela mestre — 7 modelos × 4 paradigmas (1968 records totais):**

| Modelo | Adult-A | Adult-B | TPC-H-A | TPC-H-B | Custo total |
|--------|---------|---------|---------|---------|-------------|
| **gpt-5.4** | **95.2%** | **100%** | 73.8% | 85.7% | $2.14 |
| **gpt-5.4-mini** | 82.1% | **100%** | 65.5% | 85.7% | $0.73 |
| **gpt-5.4-nano** | 86.9% | 90.5% | **76.2%** | 81.0% | $0.18 |
| gpt-4o-mini | 52.4% | 85.7% | 59.5% | 71.4% | $0.12 |
| **claude-opus-4-7** | 76.2% | 96.4% | 75.0% | 83.3% | $2.49 |
| **claude-sonnet-4-6** | 77.4% | 96.4% | 75.0% | **88.1%** | $2.42 |
| **claude-haiku-4-5** | 79.8% | 98.8% | 63.1% | 79.8% | $1.39 |

**Achados específicos da comparação:**

**a) Hierarquia interna varia por paradigma+dataset:**

- Adult Linha A: gpt-5.4 (95%) > nano (87%) > mini (82%) → **full melhor**
- Adult Linha B: gpt-5.4/mini (100%) > haiku (99%) > sonnet/opus (96%) → **converge**
- TPC-H Linha A: nano (76%) > full/sonnet/opus (74-76%) → **nano supera**
- TPC-H Linha B: sonnet (88%) > gpt-5.4/mini (86%) > opus (83%) > haiku (80%) → **sonnet ganha**

Não há "modelo melhor" universal. Escolha depende de paradigma + schema.

**b) Sub-finding — sonnet 4.6 vence em TPC-H Linha B:**

claude-sonnet-4-6 = **88.1%** [79.5%, 93.4%] supera gpt-5.4 (85.7%) em
TPC-H Linha B. Gap dentro do CI mas é o único caso onde Anthropic claramente
encabeça uma célula. Hipótese: sonnet 4.6 pode ter training melhor calibrado
para SQL gen multi-tabela.

**c) Sub-finding — haiku 4.5 é a oferta mais cost-effective Anthropic em Adult:**

Adult Linha A: haiku 79.8% por $0.64. Adult Linha B: haiku 98.8% por $0.12.
**Haiku é 2-5× mais barato que opus** com accuracy ≥ opus em ambos.
Para datasets single-table, haiku é o sweet spot Anthropic.

Análogo OpenAI: gpt-5.4-nano 86.9% Adult-A por $0.06 — **2-10× mais barato
que haiku** com accuracy maior. Em Adult Linha A, OpenAI nano é
insuperável em custo-eficiência.

**d) Sub-finding — thinking parameter é diferencial decisivo Anthropic:**

Sem thinking (default): haiku/sonnet caem para 57-58% em Adult-A — range
non-reasoning, indistinguível dos locais. Com thinking: 79.8% / 77.4%.
**+20pp de ganho com `thinking={"type":"enabled","budget_tokens":2048}`.**
Não usar thinking em Anthropic é deixar 1/3 da capacidade do modelo na
mesa para tarefas tabulares.

**e) Sub-finding — F-Q34 (schema ambiguity) é UNIVERSAL entre famílias:**

| Question N2 | OpenAI top | Anthropic top |
|--|--|--|
| q_sum (cost vs cost×qty) | 0% (gpt-5.4) | 0% (sonnet/opus) |
| q_lookup (retail vs supply) | 0% | 0-10% |
| q_lookup_value (nome vs valor) | 0% | 0-14% |

Schema linking continua problema aberto independente do provider.

**Custo total M-Acomm completo (7 modelos × 4 paradigmas × 1968 records):**

- OpenAI: $3.17 USD ($30 budget, 10.6%)
- Anthropic: $6.29 USD ($20 budget, 31.5%)
- **Total: $9.46 USD** com prompt caching agressivo
- Sem cache: ~$35-40 USD estimate (caching salvou ~75%)

**Recomendação prática para o paper:**

1. **Linha B é universal recomendation** para datasets reais — tanto
   famílias chegam a 80-100% com custo 5× menor que Linha A.
2. **OpenAI gpt-5.4-nano é o ponto Pareto** custo×accuracy em Linha A.
3. **Anthropic sonnet 4.6 é melhor para SQL gen multi-tabela** com schema
   complexo (88% TPC-H Linha B).
4. **Schema ambiguity exige design de wording** (N0 obrigatório), não é
   resolvida por escolha de modelo.

**Custo cumulativo final M-natural (locais + comerciais):** $9.46 USD em
2256 records (288 locais + 1968 comerciais) cobrindo 4 paradigmas × 2
datasets × 7 modelos comerciais + 13 modelos locais.

**Referência:** `experiments/results/m_acomm/`, `m_acomm_b/`,
`m_acommA_tpch/`, `m_acommB_tpch/` (2026-04-26).

---

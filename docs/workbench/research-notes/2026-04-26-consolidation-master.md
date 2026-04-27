---
title: Master de consolidação — auditoria de hipóteses, taxonomia de perguntas, organização bibliográfica
date: 2026-04-26
type: research-note
status: PROPOSTA — aguarda aprovação para execução
---

# Master de consolidação — antes de comerciais

## Contexto

Antes de gastar comerciais (M-Acomm) faz sentido auditar:

1. **Hipóteses** (F-Q1..F-Q28): quais foram superadas, quais precisam re-teste,
   quais consolidar
2. **Perguntas usadas nos experimentos**: hoje 95% são "schema-aware"
   (mencionam coluna e tabela explicitamente). Pouco realistas.
3. **Documentação bibliográfica**: tickets em `open/` com status DONE,
   findings sem ticket equivalente, organização desbalanceada

Este documento consolida tudo isso em **5 partes** com plano executável.

---

## Parte A — Auditoria F-Q1 a F-Q28

### Tabela consolidada por status

| F-Q | Tópico | Status | Ação |
|-----|--------|--------|------|
| F-Q1 | Intrinsic thinking arquitetural | **ATIVO** | Manter; aplicar a M-Acomm também |
| F-Q2 | Multimodal degrada text-only | **ATIVO** | Manter (não afeta canonical) |
| F-Q3 | PT ≈ EN canônico | **ATIVO mas LIMITADO** | Re-testar com perguntas naturais (Parte C) |
| F-Q4 | Ambiguidade lexical contagem | **ATIVO** | Manter |
| F-Q5 | Capacity floor < 1B | **ATIVO** | Manter |
| F-Q6 | Cold-start primeira chamada PT | **ATIVO** | Manter |
| F-Q7 | Catálogo modelos modernos | **ATIVO** | Manter |
| F-Q8 | Thinking consome num_predict | **ATIVO** | Manter |
| F-Q9 | keep_alive em options ignorado | **ATIVO** | Manter |
| F-Q10 | Non-convergent thinking | **ATIVO (escopo narrow)** | Manter caveats |
| F-Q11 | Determinismo CPU↔GPU | **ATIVO** | Manter |
| F-Q12 | Aritmética ceiling 60-70% | **SUPERSEDED por F-Q28** | Marcar como "antiga; ver F-Q28" |
| F-Q13 | Schema-only > data-full | **ATIVO** | Reforçado por F-Q24/Q25 |
| F-Q14 | SQL scale-invariant | **ATIVO** | Manter |
| F-Q15 | Few-shot elimina alucinação | **ATIVO** | Manter; testar em natural |
| F-Q16 | Cross-domain synthetic | **PARCIALMENTE SUPERSEDED** | Re-fazer canonical (M3-canonical) |
| F-Q17 | TCF ≈ JSON > CSV | **ATIVO** | Re-validar com TOON em Linha B |
| F-Q18 | SQL > Pandas > Polars | **ATIVO** | Manter |
| F-Q19 | HAVING fail | **ATIVO** | Manter |
| F-Q19b | HAVING fix subquery | **ATIVO** | Manter |
| F-Q20 | L3 com fewshot | **ATIVO** | Re-testar com perguntas naturais |
| F-Q21 | Invariant types A/B | **ATIVO + addendum** | F-Q21b: 0 falhas em canonical |
| F-Q22 | Style hints isolados | **ATIVO** | Re-validar em natural |
| F-Q23 | Style hints não compõem | **ATIVO** | Re-validar em natural |
| F-Q24 | Canonical ≈ synthetic | **ATIVO** | Reforçado por F-Q25 |
| F-Q25 | Adult 100% | **ATIVO** | **Caveat: perguntas schema-aware** |
| F-Q26 | Random ≈ Stratify Adult | **ATIVO (floor effect)** | M-strat-vol-low pendente |
| F-Q27 | Quality SQL invertido | **ATIVO** | Achado metodológico independente |
| F-Q28 | Linha A bimodal canonical | **ATIVO — supersede F-Q12** | Comparar com M-Acomm |

### Findings que precisam re-teste com perguntas naturais

Os achados **mais sensíveis** a phrasing das perguntas são:
- **F-Q25** (Adult 100%): com perguntas schema-aware, comerciais devem fazer 100%. Com perguntas naturais ("Qual a faixa de renda mais comum?"), pode cair.
- **F-Q19** (HAVING fail): pergunta atual é "Quantos clientes distintos aparecem mais de N vezes" — schema-aware. Versão natural: "Quais clientes mais ativos?"
- **F-Q20** (L3 86%): perguntas atuais elaboradas mas schema-aware
- **F-Q22/Q23** (safe-sql): testados só com perguntas atuais

**Achados que NÃO precisam re-teste:**
- F-Q1..F-Q11 (infrastructure/qualificação) — independem de phrasing
- F-Q14 (scale invariance) — propriedade da execução SQLite
- F-Q18 (SQL>Pandas>Polars) — sobre formato de execução, não phrasing
- F-Q26 (random≈stratify) — sobre sampling, não phrasing

---

## Parte B — Taxonomia de naturalidade das perguntas

### Lacuna na literatura

Pesquisei Spider 2.0 (2024), BIRD (2024), SiriusBI (VLDB 2024), Snowflake
Cortex Analyst (2025-2026), Luo et al. SoTA review (VLDB 2024). **Achado
crítico:** *Não existe taxonomia formal de naturalidade* em NL2SQL —
benchmarks classificam por complexidade SQL (sintaxe), não por intent
de negócio. Luo et al. (VLDB 2024) explicitam: "intent understanding vs
schema linking" é problema aberto.

**Esta é uma contribuição em aberto que nosso paper pode preencher.**

### Proposta: 4 níveis de naturalidade

```
N0 — Schema-aware (atual, controle):
     "Qual a soma da coluna total na tabela vendas?"
     Menciona explicitamente coluna E tabela.
     Útil como CONTROLE — testa se modelo entende o schema literal.

N1 — System-aware (intermediário):
     "Qual o total de vendas?"
     Sabe que existe vendas, mas não menciona coluna específica.
     Modelo precisa inferir qual coluna agregar.

N2 — Business-intent (natural):
     "Qual o faturamento total?"
     Linguagem de negócio — não menciona schema.
     Modelo precisa mapear "faturamento" → tabela.coluna.

N3 — Business with context (avançado):
     "Qual o faturamento do último trimestre comparado ao anterior?"
     Requer interpretação temporal + comparação.
     Pode ter ambiguidade (último = mês corrente? trimestre fiscal?).
```

### Exemplos por question type (M9-Adult)

| Question atual (N0) | N1 (System) | N2 (Business) | N3 (Context) |
|---------------------|-------------|---------------|--------------|
| Quantas linhas existem na tabela adult? | Quantos registros? | Qual o tamanho da nossa população amostrada? | Quantas pessoas no censo? |
| Qual a media da coluna age? | Qual a idade media? | Qual a idade media dos respondentes? | Qual a idade media — homens vs mulheres? |
| Qual valor de education aparece mais? | Qual education mais comum? | Qual o nivel de educação predominante? | Qual o nivel educacional dominante e como muda por idade? |
| Quantas linhas têm class igual a '>50K'? | Quantos com class >50K? | Quantas pessoas ganham mais de 50 mil? | Que proporção da população esta na faixa salarial >50K? |
| Qual a media de hours-per-week para Male? | Quantas horas semanais homens trabalham? | Em media quantas horas os homens trabalham por semana? | Homens trabalham mais que mulheres? |

### Como tratar ambiguidade

Para N3 (perguntas com ambiguidade real), proposta inspirada em SiriusBI
(VLDB 2024) — pedir o modelo para **flagar incertezas**:

```
## Estilo de resposta
Antes do SQL, se a pergunta tem ambiguidade, gere um comentario:
-- AMBIGUITY: "ultimo trimestre" pode ser civil ou fiscal; assumindo civil

Depois gere o SQL com a interpretacao escolhida.
```

Permite avaliar 2 dimensões: (a) detecção de ambiguidade; (b) escolha
defensável.

---

## Parte C — Plano de re-execução com perguntas naturais

### Princípio

**Ter as 4 versões (N0-N3) das mesmas questions em paralelo** permite:
1. Comparar accuracy por nível de naturalidade
2. Identificar onde modelos quebram (provavelmente N2/N3)
3. Reportar achado: "modelos atuais resolvem X% das business questions"

### Novo experimento M-natural (substitui retesting parcial)

**Design:**
- Datasets: Adult Census (1 single-table) + TPC-H subset (3 tables)
- Modelos: 3 locais + (depois) 4 comerciais
- 7 questions × 4 níveis de naturalidade = 28 questions por dataset
- 3 seeds (vol=100 stratified)
- Ambos paradigmas: Linha A (LLM calcula) e Linha B (LLM gera SQL)

**Total combos:**
- 2 datasets × 3 locais × 28 q × 3 seeds × 2 paradigmas = 1008 calls locais (~4h)
- + 2 datasets × 4 comerciais × 28 q × 3 seeds × 2 paradigmas = 1344 calls (~$5)

### Implementação

1. **Question framework refatorado** em `experiments/eval/llm_eval/question_naturalness.py`:
   - Cada question type tem 4 wordings (N0-N3)
   - GT é compartilhado entre níveis (mesma resposta esperada)
   - "Ambiguity flag" opcional para N3

2. **Runners atualizados** para aceitar `--naturalness N0|N1|N2|N3|all`

3. **Manifest schema enriquecido** com campo `naturalness_level`

### Hipóteses testáveis

- **H_natural-1**: accuracy(N0) ≥ accuracy(N1) ≥ accuracy(N2) ≥ accuracy(N3)
- **H_natural-2**: gap N0→N3 é maior em locais que em comerciais
- **H_natural-3**: Linha A degrada mais que Linha B com naturalidade
  (Linha A precisa "decodificar" mais a intenção)
- **H_natural-4**: F-Q25 (Adult 100%) cai significativamente em N2/N3
  para modelos locais

### Ordem proposta de execução M-natural

1. **M-natural-local**: 3 locais × 2 datasets × 28 q × 3 seeds × 2 paradigmas
   = 1008 combos (~4h compute, $0)
2. **M-natural-comercial-mini**: 2 cheap comerciais × 2 datasets × 28 q ×
   3 seeds × 2 paradigmas = 672 calls (~$1-2)
3. **M-natural-comercial-pro**: 2 expensive comerciais (Sonnet, GPT-4o) ×
   subset selecionado (~336 calls, ~$5)

**Total esperado: ~$7-10 USD** para validação completa multi-naturalidade.

---

## Parte D — Reorganização bibliográfica de tickets

### Diagnóstico atual

- **34 tickets em `open/`**, dos quais:
  - **13 com status=DONE** (não migrados — bug bibliográfico)
  - 2 IN_PROGRESS
  - 19 OPEN (vários provavelmente já feitos)
- **27 tickets em `closed/`** (legacy v0.1)
- **5 em `frozen/`** (futuro distante)

### Problemas identificados

1. **DONE em open/**: tickets 01-11 + E-stats-ablation + H-diagnostic-3layer-v02
   estão DONE mas em open/ — devem migrar
2. **OPEN não-atualizados**: tickets 13-22 (Shaper) marcados OPEN mas Shaper
   foi entregue (Etapa 1+2). 25-27 (encode-columns/rows/compat) também
   feitos.
3. **Findings sem ticket**: F-Q19..F-Q28 (10 findings) não têm tickets
   correspondentes documentando os experimentos M-series
4. **Tickets sem finding**: alguns OPEN (ex: 30-E-progressive-diagnostic)
   podem ser experimentos válidos sem entrega

### Plano de reorganização

**Fase D1 — migrar DONE para closed/ (~30min):**
```
13 tickets de open/ → closed/
- 01-M-datasets-setup, 02-08-T-datasets-*, 09-T-datasets-questions,
  10-T-datasets-cleanup, 11-T-telemetry, E-stats-ablation,
  H-diagnostic-3layer-v02
```

**Fase D2 — auditar OPEN para fechar implicitamente concluídos (~1h):**
- 13-22 (Shaper): verificar quais subtarefas foram entregues
- 23 (numeric-precision): verificar se foi resolvido
- 25-27 (encode-rows/columns/compat): foram entregues, fechar
- 29 (decoder bug): testar se ainda existe
- 30 (progressive-diagnostic): verificar se há código

**Fase D3 — criar tickets retroativos para experimentos M-series (~2h):**
Cada finding F-Q* deveria ter ticket equivalente:
```
tickets/closed/M-series/
  M01-codegen-baseline.md           (F-Q13, F-Q14, F-Q15)
  M02-fewshot-ablation.md            (F-Q15)
  M03-cross-domain.md                (F-Q16)
  M04-format-baseline.md             (F-Q17)
  M05-intermediate-forms.md          (F-Q18)
  M06-filter-questions.md            (F-Q19)
  M06b-having-fix.md                 (F-Q19b)
  M07-complex-queries.md             (F-Q20)
  M08-safe-sql-isolated.md           (F-Q22)
  M08b-safe-sql-combos.md            (F-Q23)
  M09-canonical-tpch.md              (F-Q24)
  M09-canonical-adult.md             (F-Q25)
  M-strat-random-vs-stratified.md   (F-Q26)
  M-quality-sql-posthoc.md           (F-Q27)
  M-Alocal-linha-a-canonical.md      (F-Q28)
  M-inv-invariant-analysis.md        (F-Q21)
```
Cada ticket: link bidirecional com seu finding F-Q*. Documentação
formal ↔ achado científico.

**Fase D4 — atualizar índice de tickets:**
- `tickets/README.md` reflete estrutura atual
- Status da Fase 1 (datasets), Fase 2 (TCF v0.2), Fase 3 (M-series)

### Custo D1+D2+D3 estimado

~3-4 horas de engenharia de documentação. Sem riscos.

---

## Parte E — Ordem de execução proposta

### Pré-comerciais (offline, $0)

**Fase 1 — Reorganização bibliográfica (~3-4h):**
1. D1: migrar 13 DONE de open/ → closed/
2. D2: auditar OPEN restantes
3. D3: criar tickets retroativos para M-series
4. Atualizar tickets/README.md

**Fase 2 — Question naturalness framework (~3-4h):**
5. Pesquisar mais profundamente literatura BI questions (especialmente
   Snowflake Cortex Analyst e SiriusBI) para refinar N0-N3
6. Implementar `question_naturalness.py` com 28 questions × 4 níveis
   para Adult e TPC-H
7. Adaptar runners para `--naturalness` flag
8. Manifest schema com `naturalness_level`

**Fase 3 — M-natural-local (~4h compute, $0):**
9. Rodar 1008 combos (Adult + TPC-H × 3 locais × 28 q × 3 seeds × 2
   paradigmas)
10. Análise: H_natural-1/2/3/4 com Wilson CIs
11. Registrar F-Q29 (taxonomia naturalidade local)

### Pós-comerciais (online, ~$7-10)

**Fase 4 — M-natural-comercial:**
12. Cheap comerciais (Haiku + 4o-mini) em todos os 28 q × 2 datasets
13. Pro comerciais (Sonnet + 4o) em subset selecionado por hipótese
14. Comparação cross-modelo, registrar F-Q30+

**Fase 5 — Consolidação para paper:**
15. Re-rodar M-Acomm (Linha A original) com perguntas naturais
16. Tabelas finais multi-modelo × multi-naturalidade
17. Paper draft

### Tempo total estimado

| Fase | Tempo | Custo |
|------|-------|-------|
| 1 (reorg) | 3-4h | $0 |
| 2 (naturalness framework) | 3-4h | $0 |
| 3 (M-natural-local) | 4h | $0 |
| 4 (comercial) | 1h | $7-10 |
| 5 (consolidação) | 4-6h | $0 |
| **Total** | **~16-20h trabalho** | **~$7-10** |

---

## Decisões pendentes (você decide)

1. **Ordem dentro da Parte A**: começar por reorganização bibliográfica
   (Parte D, ~3-4h) ou pelo framework de naturalidade (Parte B, ~3-4h)?
   
   **Sugestão:** D primeiro — sem ele, rastreabilidade fica solta para o
   paper. Mas é mecânico/aborrecido.

2. **Escopo do M-natural inicial**: começar com Adult (single-table mais
   simples) ou já com Adult + TPC-H?
   
   **Sugestão:** Adult primeiro — valida framework, depois expande.

3. **Aposentar F-Q12 explicitamente**: marcar como "DEPRECATED — ver F-Q28"
   ou fundir os dois textos?
   
   **Sugestão:** Marcar como deprecated com seção "Histórico (synthetic)"
   em F-Q12 e link para F-Q28 como versão atual.

4. **Comerciais com perguntas atuais (M-Acomm pendente)**: rodar antes da
   refatoração de naturalidade ou depois?
   
   **Sugestão:** Depois. M-Acomm com N0 schema-aware seria gasto pequeno
   para um achado fraco. Com N0..N3 fica ~3x mais informativo pelo mesmo
   custo.

---

## Adendum (2026-04-26): Audit completo concluído

Audit sistemático de 22 tickets em `open/` (resultado consolidado):

### Encontrado (correção do master original)

- **`compressibility` e `join` strategies NÃO eram placeholders.** Ambos
  estão implementados e funcionais (4.5KB e 4.9KB respectivamente).
  Corrigido em `data-pipeline.md` e `assembly-overview.md`.
- **Todas as 7 estratégias do Shaper estão ATIVAS** (não havia placeholder).

### Bugs/issues que NÃO impactam resultados passados

- **Bug 29 (decoder freetext com `:`):** afeta apenas roundtrip
  encode→decode em Python para colunas de texto livre. **Não afeta**
  Linha A (apenas encode) nem Linha B (SQL execute, não decode).
  Workaround documentado já em uso. Resolução: TCF v0.3 (futuro).
- **Issue 23 (numeric precision):** **research idea**, não bug. Feature
  para v0.3.
- **Bug 28 (encode tests canonical):** PARTIAL — testes existem mas
  cobertura pode ser ampliada. Não invalida testes M-series existentes.

### Decisão final

**Nenhum ticket open atual invalida resultados passados.** F-Q1..F-Q28
permanecem válidos. M-natural pode prosseguir.

### Estado final dos tickets `open/`

Após audit (6 tickets):
- `M-natural.md` — priority 1 (próximo)
- `M-schema-scope.md` — priority 2
- `23-P-numeric-precision.md` — research idea v0.3
- `29-B-decoder-freetext-bug.md` — known bug, fix em v0.3
- `H-advanced-compression-v03.md` — futuro
- `P-phase-closure.md` — meta paper

17 tickets adicionais migrados para `closed/` em 2026-04-26 (audit).

---

## Adendum (2026-04-26): M-schema-scope

Pergunta levantada após auditoria: **escopo horizontal de schema afeta
accuracy?** Hoje todos os experimentos M-series fixam o schema em 1-3
tabelas. Nunca variamos isolando o eixo horizontal.

3 eixos ortogonais de complexidade:
- Vertical (rows): testado em M-strat
- Horizontal (tabelas): **gap — M-schema-scope endereça**
- Depth (samples): parcialmente testado em M2

F-Q14 (scale-invariant) é sobre rows, não tabelas — **não cobre eixo 2**.

Hipóteses (ver ticket):
- H_scope-1: pouco schema vence quando query é simples (menos ruído)
- H_scope-2: muito schema vence quando query é ambígua (mais contexto)
- H_scope-3: efeito moderado pela naturalidade — N0 indiferente, N2/N3 sensível

Lacuna na literatura confirmada: Cortex Analyst e CHESS usam schema
pruning empiricamente, mas nenhum paper mediu o efeito × naturalidade.
Outra contribuição em aberto.

Custo: 252-432 combos locais (~45-90min, $0). Pode rodar antes ou
depois de M-natural.

Ticket: [tickets/open/M-schema-scope.md](../../tickets/open/M-schema-scope.md)

---

## TL;DR para sua revisão

- 28 findings auditados; F-Q12 deprecated por F-Q28; outros active mas
  alguns precisam re-teste com perguntas naturais
- Lacuna real na literatura: nenhuma taxonomia formal de naturalidade
  NL2SQL — oportunidade para o paper
- Proposta: 4 níveis (N0 schema-aware → N3 business+contexto)
- 13 tickets DONE em open/ precisam migrar para closed/
- 16+ findings F-Q sem tickets retroativos correspondentes
- Plano: reorg bibliográfica (3-4h) → framework naturalidade (3-4h) →
  M-natural-local ($0, 4h compute) → M-natural-comercial (~$10) → paper
- M-Acomm original DEVERIA ser adiado: comerciais com N0..N3 é mais
  informativo que comerciais só com N0 atual

---
title: Cap 8 — Discussao do paper
type: paper
status: OPEN
priority: HIGH
created: 2026-04-27
origin: Pos-fechamento M-natural + M-schema-scope (commit 4e919d0)
see_also:
  - docs/article/07-results.md (cap 7 reescrito)
  - docs/article/README.md (status capitulos)
  - docs/findings/ (catalogo F-Q1..F-Q38)
---

# Cap 8 — escrever a Discussao do paper

## Estado

Placeholder em [`docs/article/08-discussion.md`](../../../article/08-discussion.md).
Cap 7 ja contem 6 achados centrais e tabela 2D paper-ready.

## O que precisa entrar (proposta de roadmap do capitulo)

### 8.1 Implicacoes para teoria de NL2SQL

- Schema linking continua problema aberto em jan/2026 — F-Q33+F-Q34+F-Q35
  convergem mostrando que mesmo gpt-5.4 (frontier) cai 43pp em N2 TPC-H
- Reasoning e o eixo discriminante (F-Q31), nao tamanho — questiona
  literatura que correlaciona accuracy com numero de parametros
- F-Q12 era propriedade de modelos non-reasoning, nao limitacao
  universal do paradigma

### 8.2 Implicacoes para design de TCF

- Linha B vence Linha A em multi-tabela por 10-15pp e custa 5x menos
  → recomendar Linha B como default
- Linha A faz sentido em nicho: single-table com modelo reasoning
  (gpt-5.4-nano = $0.0007/call, 87%)
- Schema pruning empiricamente justificado (F-Q38: -33pp full vs minimal
  em N3) — implica que TCF deveria ter "schema_qualifier" como camada
  pre-LLM (ja existe roadmap em workbench/research-notes)

### 8.3 Limitacoes do estudo

- Apenas 2 datasets (Adult single-table + TPC-H sf001 multi-tabela)
- TPC-H tem viés de memorização em LLMs (F-Q37 sub-finding) —
  Adult eh mais limpo metodologicamente
- Sem teste em Gemini ou outros providers
- vol=100 fixo; nao testamos escala
- 7 questoes por dataset; nao representa toda a riqueza de NL2SQL

### 8.4 Relacao com literatura industrial

- Cortex Analyst (Snowflake): recomenda schema pruning — F-Q38 confirma
- DAIL-SQL, CHESS: schema linking continua aberto — F-Q34 atesta
- Spider 2.0 / SiriusBI / Luo et al. VLDB 2024: alinham com nossos achados
- (refs detalhadas em [02-related-work.md](../../../article/02-related-work.md)
  adendo)

### 8.5 Trabalhos futuros (o que nao foi feito + por que)

- Schema_qualifier como camada operacional (roadmap em
  workbench/research-notes)
- TPC-H em escala maior (sf01, sf1)
- Dataset privado para evitar leakage de TPC-H
- Multi-turn dialog (atual e single-turn)
- Comparacao com TOON com mesmo protocolo

## Criterio de aceite

- [ ] 5 secoes 8.1-8.5 escritas em PT-BR
- [ ] Cada claim ancorado em F-Q especifico
- [ ] Tabela de implicacoes praticas
- [ ] Bibliografia integrada (refs do adendo de Cap 2)
- [ ] Conexao explicita com Cap 7 (resultados) e Cap 9 (conclusao)
- [ ] ~3000-5000 palavras

## Dependencias

- Cap 7 finalizado ✅ (commit 4e919d0)
- Findings consolidados ✅ (docs/findings/)

## Impacto estimado

3-5 dias de escrita focada apos M-Acomm. Sem nova execucao
experimental requerida — todos os dados existem.

## Notas de revisao futura

Caso queiramos revisar este ticket no futuro:
- Manifest dos experimentos em `experiments/results/m_acomm*/`
- Findings em `docs/findings/`
- Snapshot do Cap 7 em commit 4e919d0

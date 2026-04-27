---
title: Linhas de pesquisa do TCF
date: 2026-04-23
type: overview
---

# Duas linhas de pesquisa sobre LLM + dados tabulares

O projeto TCF investiga duas abordagens distintas para habilitar LLMs a
responderem perguntas sobre dados tabulares. Ambas usam o formato TCF, mas
com paradigmas de avaliação opostos.

---

## Contraste — duas teses, uma ferramenta

| Aspecto | Linha A — LLM como analista direto | Linha B — LLM como gerador de plano |
|---------|-----------------------------------|------------------------------------|
| **Pergunta central** | O LLM consegue ler TCF/CSV/JSON e responder valores numéricos? | O LLM consegue gerar SQL válido a partir do schema TCF? |
| **Papel do LLM** | Calculador (faz a aritmética) | Tradutor (converte NL em operação formal) |
| **Executor final** | O próprio LLM | SQLite |
| **Formato TCF usado como** | Carregador de dados | Carregador de schema |
| **Accuracy atingida** | 40–70% (teto) | 86–100% |
| **Gargalo observado** | Aritmética sobre muitas linhas falha (F-Q12) | Complexidade de agregação (F-Q19, F-Q20) |
| **Papel dos STATS hints** | +25-62pp (F-Q3..F-Q9) | Irrelevantes (modelo gera SQL, SQLite executa) |
| **Experimentos** | phase1..6, stats_ablation, diagnostic, scale, frontier_search | M1-M7, m6b |

---

## Por que as duas linhas existem

### Linha A veio primeiro (cronologicamente)
A motivação original do TCF foi servir como formato legível por LLM —
columnar + RLE + STATS para que o modelo pudesse raciocinar diretamente sobre
dados. Experimentos estabeleceram que mesmo com hints, a **aritmética sobre
muitas linhas satura em ~60-70%** (F-Q12). Esse é o teto dessa abordagem em
modelos 7-14B locais.

### Linha B emergiu da limitação de A
Em vez de pedir ao LLM que calcule, pedir que ele **descreva a operação**
via SQL — e deixar o SQLite executar com precisão exata. TCF serve agora
como carregador de schema (cardinalidades, FK, tipos) em vez de dados completos.
Resultado: 96%+ em perguntas L1-L2 e 86% em L3.

**A Linha B não depreca a Linha A** — são resultados sobre problemas distintos:
- Linha A responde: "modelos locais conseguem ser calculadores sobre tabelas?"
- Linha B responde: "TCF como schema carrier habilita text-to-SQL confiável?"

Ambos são achados publicáveis, com implicações diferentes.

---

## Documentos detalhados por linha

- [A-direct-reasoning.md](A-direct-reasoning.md) — Linha A detalhada (experimentos, findings, limites)
- [B-schema-carrier.md](B-schema-carrier.md) — Linha B detalhada (H-TCF2, M1-M7, failure modes)

## Achados canônicos por linha

Ver [F-findings.md](../methodology/F-findings.md) com tags `{A}`, `{B}`, `{shared}`.

## Exemplos e artefatos de prova

Exemplos concretos de prompts, respostas e SQL gerado ficam em
`experiments/results/` (não inline na documentação narrativa):

- Linha A: `experiments/results/{etapa1,etapa2,stats_ablation,diagnostic_3layer,frontier_search}/manifest.jsonl`
- Linha B: `experiments/results/sql_samples/` (padrões SQL por question type)

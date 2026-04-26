---
title: M-natural — Taxonomia de naturalidade das perguntas (N0-N3)
type: experiment
status: PARTIAL — Adult Linha A+B locais DONE (F-Q29+F-Q30); pendentes: comerciais, TPC-H
priority: 1
date: 2026-04-26
related: docs/research-notes/2026-04-26-consolidation-master.md
findings: F-Q29 (Linha A local: NAO degrada), F-Q30 (Linha B local: DEGRADA seletivamente)
---

# M-natural — perguntas naturais vs schema-aware

## Motivação

Perguntas atuais em M-series (M3-M_strat) são **schema-aware** —
mencionam coluna e tabela explicitamente:

> "Qual e a soma de todos os valores da coluna total em vendas?"

Isso é controle válido mas **não corresponde a uso real** de BI/CRM/ERP.
Pesquisa de literatura (Spider 2.0, BIRD, SiriusBI VLDB 2024, Cortex
Analyst) confirma: **nenhum paper formaliza taxonomia de naturalidade**
em NL2SQL. Lacuna real para nossa contribuição.

## Proposta — 4 níveis

```
N0 — Schema-aware (atual):    "Qual a soma da coluna total em vendas?"
N1 — System-aware:            "Qual o total de vendas?"
N2 — Business-intent:         "Qual o faturamento total?"
N3 — Business + contexto:     "Faturamento do último trimestre?"
```

## Hipóteses testáveis

- **H_natural-1**: accuracy(N0) ≥ N1 ≥ N2 ≥ N3 (degradação com naturalidade)
- **H_natural-2**: gap N0→N3 maior em locais que comerciais
- **H_natural-3**: Linha A degrada mais que Linha B com naturalidade
- **H_natural-4**: F-Q25 (Adult 100%) cai em N2/N3 para locais

## Design

- Datasets: Adult Census (single-table) + TPC-H subset (3 tables)
- 7 question types × 4 níveis = 28 questions por dataset
- 3 modelos locais × 3 seeds × 2 paradigmas (Linha A + Linha B)
- Total local: 1008 combos (~4h, $0)
- + comerciais: ~672 cheap + 336 pro = ~$7-10

## Implementação técnica

### Novo módulo

`experiments/eval/llm_eval/question_naturalness.py` com:
- `Question` dataclass com 4 wordings (n0, n1, n2, n3)
- `NaturalnessLevel` enum
- Função `get_questions(dataset, level)` retorna 7 questions no nível pedido
- Mecanismo opcional de ambiguity flagging para N3

### Manifest schema

Adicionar campo `naturalness_level: "N0"|"N1"|"N2"|"N3"` em todos os
records de runners participantes.

### Runners

- Adicionar `--naturalness {N0,N1,N2,N3,all}` aos runners M9-Adult,
  M9-canonical, M-Acomm, M-Alocal
- `all` rola os 4 níveis sequencialmente

## Critério de aceite

- [ ] Todas as 7 question types têm 4 wordings (28 entries por dataset)
- [ ] GT é compartilhado entre níveis (mesma resposta esperada)
- [ ] Manifest registra `naturalness_level`
- [ ] Wilson CI por (model, level, paradigm)
- [ ] Tabela final accuracy × naturalidade × paradigma

## Dependências

- Reorganização bibliográfica (Fase D do master) já completa
- Schema-scope (M-schema-scope) pode rodar em paralelo
- M-Acomm comercial deve usar este framework (não as perguntas antigas)

## Findings esperados

- F-Q29 (a registrar): degradação por naturalidade em modelos locais
- F-Q30 (a registrar): comparação locais × comerciais por naturalidade

## Status (2026-04-26)

- [x] Adult — Linha A local (3 modelos × 3 seeds × 4 levels) → **F-Q29 registrada**:
      naturalidade NAO degrada accuracy em Linha A local. Variacao <5pp entre niveis,
      dentro do CI Wilson. Saturacao por tipo de question (filter+agg = 0%, full-agg = 100%)
      domina. H_natural-1 nao se sustenta para Linha A local.
- [ ] Adult — Linha B local (gera SQL): teste critico — se H_natural-1 valer aqui,
      eixo de naturalidade tem valor cientifico real. Se nao valer, framework e descartavel.
- [x] Adult — borda alta (5 modelos 8-20B): deepseek-r1:14b, gemma3:12b, gpt-oss:20b,
      mistral-nemo, granite3.3:8b — top 57% (deepseek-r1, qwen2.5-coder); gpt-oss anomalia 29%
- [x] Adult — borda baixa (5 modelos 0.6-4B): qwen3:4b-thinking, qwen3:4b, gemma3:4b,
      qwen3:1.7b, qwen3:0.6b — qwen3:1.7b 46% (empata gemma3:12b!); qwen3:0.6b floor 7%
- [x] Adult — Linha B local (SQL gen): H_natural-1 CONFIRMADA parcialmente. qwen3:14b=100%
      em todos os niveis; qwen2.5-coder:7b -29pp em N1; phi4 -14pp em N3. 2 mecanismos:
      (a) ambiguidade "classe trabalhista" -> class vs workclass, (b) hint tecnico perdido.
      F-Q30 registrada.
- [ ] Adult — comerciais (M-Acomm com naturalness=all)
- [ ] TPC-H — questions catalog (apos comerciais)

## Referências

- Master plan: docs/research-notes/2026-04-26-consolidation-master.md
- Lit gap: Luo et al. VLDB 2024 explicita "intent vs schema linking" como aberto
- SiriusBI VLDB 2024 — ambiguity recovery em BI

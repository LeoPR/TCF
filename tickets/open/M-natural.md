---
title: M-natural — Taxonomia de naturalidade das perguntas (N0-N3)
type: experiment
status: ADULT_DONE — Adult dataset 4 paradigmas DONE; TPC-H pendente (Phase 2.5)
priority: 1
date: 2026-04-26
related: docs/research-notes/2026-04-26-consolidation-master.md
findings:
  - F-Q29 (Linha A local: naturalidade NAO degrada)
  - F-Q30 (Linha B local: DEGRADA seletivamente)
  - F-Q31 (Linha A comercial reasoning: quebra ceiling local; eixo eh REASONING)
  - F-Q32 (Linha B comercial top: 100% imune a naturalidade; falhas remanescentes por ambiguidade schema)
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
- [x] Adult — Linha A comercial (M-Acomm): 4 modelos OpenAI x 3s x 4lvl = 336 records.
      gpt-5.4=95%, gpt-5.4-nano=87%, gpt-5.4-mini=82%, gpt-4o-mini=52%. Ceiling local
      F-Q12/F-Q28 quebrado por modelos com REASONING (eixo limitante e reasoning, nao
      tamanho). Custo: $0.82. F-Q31 registrada.
- [x] Adult — Linha B comercial (M-Acomm-B): 4 modelos x 3s x 4lvl = 336 records.
      gpt-5.4 e gpt-5.4-mini = 100% em N0/N1/N2/N3 (imunes); nano=90%, 4o-mini=86% flat.
      Falhas remanescentes por ambiguidade workclass/occupation e cols hifenadas.
      Custo: $0.25. F-Q32 registrada.
- [x] TPC-H Linha B local: F-Q33. N2 cai 30-45pp em todos os 3 modelos. qwen3:14b
      perde imunidade. Mecanismo: schema ambiguity sistematica (cost x qty,
      retail vs supply cost, nome vs valor). 252 records.
- [x] TPC-H Linha B comercial: F-Q34. Universal -43pp em N2 (gpt-5.4 e mini
      tambem caem!). Schema linking continua problema aberto em jan/2026.
      Comerciais falham MAIS que qwen3:14b em q_sum N2 (business semantics
      aplicado mais agressivamente). 336 records, $0.41.

## Tabela 2D final paper-ready (todas as 8 celulas com 1 lacuna)

|  | Single-table (Adult) | Multi-tabela (TPC-H) |
|--|---------------------|----------------------|
| Locais Linha A | Plano N0=N3 (F-Q29) | Nao testado (filter+agg ceiling) |
| Locais Linha B | -15pp pior caso (F-Q30) | **-43pp em N2** (F-Q33) |
| Comerciais Linha A | Reasoning quebra ceiling (F-Q31) | **-21pp em N2** (F-Q35) |
| Comerciais Linha B | 100% imunes (F-Q32) | **-43pp em N2** (F-Q34) |

Achados centrais:
1. Schema ambiguity em multi-tabela e UNIVERSAL — mesmo comerciais
   frontier (gpt-5.4) nao resolvem (F-Q33, F-Q34, F-Q35).
2. **Schema ambiguity e paradigm-independent**: N2 quebra TANTO
   Linha A quanto Linha B em TPC-H. Resolvendo um dos paradigmas
   nao resolve o outro.
3. Em Linha A TPC-H, gpt-5.4-nano (76%) > gpt-5.4 full (74%) —
   reasoning agressivo abre espaco para interpretacoes criativas
   que divergem do GT.
4. Linha B vence Linha A em TPC-H por 10-15pp e custa 5x menos.
5. q_top_product e teto inferior universal (17% Linha A vs 75% Linha B)
   — JOIN logico em Linha A e catastrofico.

Recomendacao pratica para o paper:
- Schemas com cols ambiguas (>=2 colunas $ proximas) -> wordings N0
  obrigatorios em interfaces NL2SQL
- Workloads com JOIN logico -> Linha B sem excecao
- Linha A util apenas para single-table com cols inequivocas

## Anthropic completo (F-Q36)

7 modelos comerciais × 4 paradigmas = 1968 records:
- 3 OpenAI (gpt-5.4 family) + 1 controle (gpt-4o-mini)
- 3 Anthropic (haiku 4.5, sonnet 4.6, opus 4.7) com thinking habilitado

Achados:
- Linha B Anthropic ≈ OpenAI (96-99% Adult, 80-88% TPC-H)
- Linha A: OpenAI vence Adult (gpt-5.x 82-95% vs Anthropic 76-80%)
- Sonnet 4.6 vence TPC-H Linha B (88.1% > gpt-5.4 85.7%)
- Schema ambiguity F-Q33+F-Q34 confirmado em ambas familias
- Thinking parameter obrigatorio Anthropic (+20pp ganho em Adult-A)
- API divergente: opus 4.7 usa adaptive + output_config.effort;
  haiku/sonnet usam enabled + budget_tokens

Custo total M-Acomm (locais + comerciais):
- OpenAI: $3.17 / $30 (10.6%)
- Anthropic: $6.29 / $20 (31.5%)
- **Total: $9.46** com cache; ~$35-40 sem cache (75% economia)

Status: M-natural ENCERRADO. Tabela 2D paper-ready completa em todas
8 celulas. F-Q29..F-Q36 documentados.

## Referências

- Master plan: docs/research-notes/2026-04-26-consolidation-master.md
- Lit gap: Luo et al. VLDB 2024 explicita "intent vs schema linking" como aberto
- SiriusBI VLDB 2024 — ambiguity recovery em BI

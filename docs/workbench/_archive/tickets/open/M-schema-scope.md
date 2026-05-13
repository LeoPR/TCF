---
title: M-schema-scope — efeito do escopo horizontal de schema em accuracy
type: experiment
status: OPEN
priority: 2
date: 2026-04-26
related: docs/research-notes/2026-04-26-consolidation-master.md
---

# M-schema-scope — pouco vs muito schema afeta accuracy?

## Motivação

Os 3 eixos ortogonais de complexidade:

```
Eixo 1 — VERTICAL (rows): testado em M-strat (vol=100), M2 (scale)
Eixo 2 — HORIZONTAL (tabelas): NUNCA TESTADO ISOLADAMENTE
Eixo 3 — DEPTH (samples): testado parcialmente em M2
```

F-Q14 ("SQL é scale-invariant") é sobre rows, **não tabelas**. Eixo 2 é
gap real.

Literatura industrial (Cortex Analyst, DAIL-SQL, CHESS) usa **schema
pruning** — confirma que mais schema causa confusão. Mas nenhum paper
mediu sistematicamente o efeito em função da naturalidade da pergunta.

## Hipóteses

```
H_scope-1: schema minimal (1 table) é VANTAGEM quando pergunta pode ser
           respondida sem JOIN — menos paths para LLM se confundir.

H_scope-2: schema full (8 tabelas TPC-H) é VANTAGEM quando pergunta
           tem ambiguidade — mais contexto ajuda LLM a escolher.

H_scope-3: efeito do escopo é MODERADO pela naturalidade (N0..N3):
           - N0 schema-aware: escopo irrelevante (LLM sabe qual tabela)
           - N2/N3 business intent: escopo IMPORTA — mais opções = mais
             chances de errar
```

## Design

- Dataset: TPC-H sf001 (8 tabelas — único que permite variar escopo)
- Schema levels (já implementados em Shaper):
  - `minimal` = ["customer"] (1 tabela)
  - `core` = ["customer", "orders"] (2 tabelas)
  - `chain` = ["customer", "orders", "lineitem"] (3 tabelas)
  - `full` = todas 8 tabelas
- 7 questions adaptadas por level
- 3 modelos locais × 3 seeds × 4 levels = 252 combos (~45min, $0)

**Cruzamento com M-natural (se for executado depois):**
- 4 levels × 4 niveis naturalidade = 16 cells
- Por modelo × seed = 144 combos por modelo = 432 total
- Esta seria a tabela 2D mais informativa cientificamente

## Implementação

- Reusar `Shaper(ShapeRequest(schema="minimal"))` etc. — já existe
- Questions devem ser adaptadas por level (volume question diferente
  para customer-only vs lineitem-only)
- Manifest registra `schema_level`

## Critério de aceite

- [ ] Questions definidas por level (alguns reaproveitam, outros
  específicos)
- [ ] 4 levels rodam o mesmo conjunto de queries que faz sentido
  para todos
- [ ] Tabela 2D level × question type
- [ ] Wilson CI cruzado

## Findings esperados

- F-Q31 (a registrar): efeito do escopo de schema em accuracy
- F-Q32 (se M-natural rodar antes): interação escopo × naturalidade

## Dependências

- Pode rodar **antes** ou **depois** de M-natural
- Não depende de comerciais

## Referências

- Master plan: docs/research-notes/2026-04-26-consolidation-master.md
- Schema pruning: DAIL-SQL, CHESS, Cortex Analyst (industrial)
- Luo et al. VLDB 2024 — schema linking como problema aberto

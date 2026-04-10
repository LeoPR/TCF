---
title: META — Fase 1: Setup de Datasets Canonicos
type: meta
status: IN_PROGRESS
priority: 1
created: 2026-04-10
---

# META: Fase 1 — Setup de Datasets Canonicos

## Contexto

Voltamos a prancheta em 2026-04-10. Antes de implementar TCF, TOON
ou qualquer formato, vamos estabelecer uma **base de dados solida**
usando datasets canonicos da literatura.

Motivacao: nossos experimentos ate agora usaram `retail_sales` sintetico
com nomes minimalistas (Ana, Bruno, Caneta). Isso impede comparacao
com literatura e faz os findings parecerem fragieis.

**Nao vamos testar NADA de formato ate esta fase estar completa.**

## Decisao de datasets (para fase 1)

Apos pesquisa detalhada (ver [docs/research-notes/2026-04-10-canonical-datasets.md](../../docs/research-notes/2026-04-10-canonical-datasets.md)),
escolhemos **2 datasets** para comecar:

1. **TPC-H SF=0.01** — schema relacional padrao da industria
2. **Adult (Census Income)** — dados demograficos reais da UCI

Outros ~18 datasets pesquisados ficam documentados como **backlog**
no mesmo arquivo (nao apagar).

## Sub-tickets (em ordem de execucao)

### Etapa A — Preparacao

1. [`02-T-datasets-structure.md`](02-T-datasets-structure.md) — criar estrutura de pastas
2. [`03-T-datasets-deps.md`](03-T-datasets-deps.md) — adicionar deps opcionais (duckdb, sklearn)

### Etapa B — Download

3. [`04-T-datasets-tpch.md`](04-T-datasets-tpch.md) — TPC-H via DuckDB
4. [`05-T-datasets-adult.md`](05-T-datasets-adult.md) — Adult via sklearn

### Etapa C — SQLite Hub

5. [`06-T-datasets-sqlite.md`](06-T-datasets-sqlite.md) — converter para SQLite com tipos/PK/FK

### Etapa D — Qualidade

6. [`07-T-datasets-quality.md`](07-T-datasets-quality.md) — gerar quality reports por dataset

### Etapa E — Derivacoes

7. [`08-T-datasets-csv-jsonl.md`](08-T-datasets-csv-jsonl.md) — derivar CSV/JSONL/MD a partir do SQLite

### Etapa F — Perguntas

8. [`09-T-datasets-questions.md`](09-T-datasets-questions.md) — banco de perguntas canonicas por dataset

### Etapa G — Limpeza

9. [`10-T-datasets-cleanup.md`](10-T-datasets-cleanup.md) — mover retail_sales para poor-reference, marcar experimentos antigos

## Criterio de conclusao

Esta fase esta completa quando:
- `datasets/canonical/tpch-sf001/` tem CSVs e SQLite
- `datasets/canonical/adult-census/` tem CSV e SQLite
- Cada um tem `metadata.json`, `quality-report.md`, `questions.json`
- Derivacoes em CSV, JSONL, MD geradas a partir do SQLite
- Testes passam: `pytest tests/test_datasets.py` (novo)
- Documentacao atualizada: `datasets/README.md` explica tudo

## Apos esta fase

Apos Fase 1 completa, decidiremos a **Fase 2** (pergunta cientifica nuclear).
Provaveis candidatas:
- STATS-based hints como contribuicao central
- Comparacao de formatos com dados reais
- Algo ainda nao pensado

**Nao pensar em Fase 2 agora.** Focar 100% em dados.

## Nao faz parte desta fase

- TCF encoder (congelado)
- TOON encoder (congelado)
- Experimentos LLM novos (congelado)
- Tokens, streaming, advanced encodings (congelado)
- Qualquer uso de Ollama para rodar perguntas

Essas coisas virao DEPOIS que tivermos a fundacao de dados pronta.

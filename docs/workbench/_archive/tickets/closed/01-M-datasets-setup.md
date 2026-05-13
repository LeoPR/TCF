---
title: META — Fase 1: Setup de Datasets Canonicos
type: meta
status: DONE
priority: 1
created: 2026-04-10
completed: 2026-04-11
---

## STATUS: FASE 1 COMPLETA (2026-04-11)

Todos os 10 sub-tickets concluidos. Fundacao pronta para a Fase 2.

### Sub-tickets concluidos

| # | Ticket | Commit |
|---|--------|--------|
| 02 | storage structure | `a468408` |
| 03 | datasets deps | `a67826e` |
| 04 | TPC-H download | `b2ace89` |
| 05 | Adult download | `7fe0805` |
| 06 | SQLite hub | `054773a` |
| 07 | dataset_reader + quality_report | `7973eb2` |
| 08 | writers + derive_formats | `80618ab` |
| 09 | questions + ground_truth | `20d61b4` |
| 10 | cleanup retail_sales | (este commit) |
| 11 | tcf.timing module | (este commit) |

### O que existe agora

**Em git (Camada A):**
```
config/
  storage.json.example
  .gitignore
scripts/
  _paths.py              — storage resolver
  setup_tpch.py          — TPC-H download (DuckDB)
  setup_adult.py         — Adult download (sklearn)
  csv_to_sqlite.py       — CSV → SQLite tipado
  dataset_reader.py      — le SQLite → structures
  quality_report.py      — gera markdown reports
  derive_formats.py      — CSV/JSONL/MD writers orchestrator
  compute_ground_truth.py — executa SQL das perguntas
  writers/
    csv_writer.py
    jsonl_writer.py
    markdown_writer.py
src/tcf/
  timing.py              — honest phase timing (core, nao script)
tests/
  test_timing.py         — 12 novos tests
datasets/
  README.md
  canonical/
    tpch-sf001/          metadata.json + README
    adult-census/        metadata.json + README
  samples/               (7 arquivos pequenos, ~35KB total)
  quality-reports/
    tpch-sf001.md        (14.7 KB)
    adult-census.md      (2.7 KB)
  questions/
    tpch-sf001.json      (15 perguntas + ground truth)
    adult-census.json    (10 perguntas + ground truth)
  poor-reference/        (explicacao do legacy)
data-local/              (fallback placeholder)
```

**Fora do git (Camada B, em Z:\tcf-data):**
```
external/                (dados raw, ~15 MB)
  tpch-sf001/            (8 CSVs, 10.4 MB)
  adult-census/          (1 CSV, 5.2 MB)
interim/                 (SQLite tipado, ~17 MB)
  tpch-sf001.db          (12 MB, 8 tables, 5 FKs, composite PKs)
  adult-census.db        (5 MB, NULLs preservados)
processed/               (derivacoes baseline, ~61 MB)
  tpch-sf001/{csv,jsonl,markdown}/
  adult-census/{csv,jsonl,markdown}/
archives/                (vazio, reservado para LZMA futuro)
```

Total em disco: ~93 MB. Total em git: ~130 KB (tudo pequeno e util).

### Testes

- **124/124 passando** (112 existentes + 12 novos de timing)
- Nenhuma regressao introduzida
- `FK check OK` em ambos os SQLite databases
- 25 ground truths computados via SQL

### Principios arquiteturais validados

1. **Separacao core/scripts:** `src/tcf/` nao depende de `scripts/`.
   Usuarios do TCF podem escrever seus proprios readers/writers.
2. **Reader generico:** `DatasetReader` retorna estruturas Python
   (list[dict], dict[list]) — fonte pode ser trocada sem mexer nos
   consumidores (quality, derivations, ground truth).
3. **Writers modulares:** cada formato em seu arquivo, assinatura
   identica `(path, columns, rows)`. Novos formatos faceis de adicionar.
4. **Storage em 3 camadas:** git / disco / archive funcionando.
5. **Reproducibilidade total:** qualquer um com o repo + Python 3.10+
   e `pip install -e .[datasets]` consegue regenerar tudo.

### Findings prematuros (sem LLM)

Ja visiveis nos relatorios de qualidade:
- JSONL e ~3.2x pior que CSV em tamanho (real, nao sintetico)
- Adult: `workclass` dominado por "Private" (69.4%), entropia 1.42 bits
- TPC-H lineitem e o candidato ideal para testar compressao columnar
  (60K rows, 16 cols, muita repeticao em returnflag/linestatus/shipmode)

### Proxima fase

**Fase 2 nao definida ainda.** Este meta-ticket fica como referencia
mas o foco agora e: **parar, olhar o que temos, e decidir qual a
pergunta cientifica nuclear** que a Fase 1 nos permite responder de
forma honesta.

Candidatas:
- STATS-based hints como contribuicao central (apenas agora com
  dados canonicos)
- Comparacao honesta TCF vs CSV/JSONL/TOON em TPC-H lineitem
- Outra direcao que surgir ao analisar os dados reais

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

---
title: llm_query — geração de query de consulta por LLM (gadget)
status: v0.6-broken
tags: [gadget, llm, sql, query-gen, nao-core]
updated: 2026-07-19
---

# llm_query

Gadget auxiliar (**NÃO** TCF-core; fora do wheel/sdist, dev-only sob `src/`).
Produto vivo extraído do antigo harness `llm-benchmark/` (dissolvido 2026-07-19).

## O que é

Geração de **query de consulta por LLM** — a "Linha B" do estudo: dado um
schema/pergunta de negócio + payload TCF, a LLM **produz uma query executável**
(SQL principalmente; também polars/pandas em `run_m5_intermediate`), o runner
**executa** contra SQLite/DataFrame e **pontua** comparando valores.

Distinto da "Linha A" (jogar dados na LLM para ela *deduzir* a resposta) —
refutada na literatura e arquivada em [`old/llm-benchmark/`](../../old/llm-benchmark/).

## Estado

**v0.6-QUEBRADO hoje.** Os runners foram escritos contra a API v0.5 do TCF
(importam `EncodeConfig`, que não existe em `tcf` v0.6 — só em `old/tcf/`).
Revivê-los para rodar = port de API v0.6 (ticket `T-RECOVER-LLM-SCHEMA-MODE`,
follow-up .9). O move de 2026-07-19 apenas **relocou** o produto; não portou.

Dependências ao rodar: `tcf` (encode), `scripts/dataset_reader`, `tests/fixtures`,
`pydantic` (só os runners comerciais), Ollama/APIs comerciais.

## Layout

- `run_m1_codegen.py` — raiz do cluster SQL (define `build_sqlite_from_tables`,
  `extract_sql`, `score_sql`, prompt/payload). Todos os outros puxam dele.
- `run_m2..m9_*`, `run_m_acomm_b`, `run_m_acommB_tpch`, `run_m_schema_scope`,
  `run_m_strat` — variações (few-shot, escala, cross-domain, comercial, scope).
- `run_m_quality`, `run_minv_invariant_check` — análise pós-hoc (sem LLM).
- `llm_eval/` — engine: `ollama_client`, `commercial_client`, `sql_quality`,
  `python_executor`, `question_naturalness`, `stats`.
- `data_sources.py`, `analyze_results.py` — carga de dados + relatório.

Cada `run_*.py` é standalone: insere o próprio dir + repo-root no `sys.path` e
importa os irmãos flat.

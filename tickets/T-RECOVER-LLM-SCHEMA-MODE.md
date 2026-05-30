---
title: T-RECOVER-LLM-SCHEMA-MODE — LLM mode pra gerar SQL a partir do schema
status: de-prontidao
priority: P3
created: 2026-05-27
blocked-by: [T-RECOVER-SCHEMA-MULTI-TABLE]
related:
  - docs/findings/  (Phase 1 LLM Q01-Q38, historic v0.5)
  - src/tcf/schema.py
  - tickets/T-RECOVER-SCHEMA-MULTI-TABLE.md
---

# T-RECOVER-LLM-SCHEMA-MODE

## Contexto

Owner mencionou (2026-05-27) que a infraestrutura LLM da Phase 1 (v0.5,
arquivada em [docs/findings/](../docs/findings/) e [old/tcf/](../old/tcf/))
pode ser recuperada com novo proposito: **modo schema LLM pra gerar SQL**.

Nao tem relacao direta com o algoritmo TCF (compressao), mas e' uma
**ferramenta complementar**: dado um schema (do `build_schema`), o LLM
gera SQL inteligente pra extrair dados; essa extracao mais inteligente
alimenta o encoder TCF com input ja' otimizado (ex: ORDER BY que ajuda
seq-RLE, JOIN que cria correlacao pra cross-table dedup).

## Hipotese / Objetivo

**Fluxo proposto**:
```
schema (TableSchema multi-tabela) → LLM com prompt schema-aware →
SQL gerado (com ORDER BY, JOINs, projeções) → executa em SQLite/DuckDB →
dados ordenados/joined → encode(dados) → TCF eficiente
```

Beneficio: ordenacao explicita melhora cadence detection (auto_cadence),
JOINs pre-computados habilitam cross-table dedup futuro (V2-G).

## Estado atual

- **Existe**: infraestrutura Phase 1 LLM em old/tcf/ + docs/findings/
  (Q01-Q38 benchmark, modelos qualificados). Marcada `historic` mas
  funcional.
- **Existe**: `pip install -e ".[eval]"` instala requests pra Ollama client
- **NAO existe**: ponte entre schema TCF e LLM (prompt schema-aware,
  validador SQL → schema)

## Plano (futuro)

### Fase 0 — Reavaliar infraestrutura Phase 1
- old/tcf/ e' v0.5 columnar (NAO usado pro algoritmo). Mas o eval module
  + qualified models pode ser refrescado independente
- Decidir: spin-off como pacote separado (`tcf-llm-bridge`)? Ou submodulo
  opcional?

### Fase 1 — Prompt schema-aware
- Template: "Given this schema {TableSchema.to_dict()}, write SQL to..."
- Usar qualified models do Phase 1 (sem re-qualificacao se estaveis)

### Fase 2 — Validador SQL → schema
- Parse SQL gerado, valida que projeções/joins fazem sentido pro schema
- Feedback loop: se SQL invalido, re-prompt com diagnostico

### Fase 3 — Pipeline integrado
- `extract_via_llm(schema, intent) → dataframe` em scripts/
- Mede TCF efficiency com input extraido via LLM vs naive

## Conexao

- T-RECOVER-SCHEMA-MULTI-TABLE (pre-req: schema multi-tabela enriquecido
  pra alimentar o LLM)
- Phase 1 LLM benchmark (recursos existentes)
- V2-G cross-column atom sharing (ADR-0018) — beneficiaria de input
  JOINed pre-computado
- Filosofia: TCF e' explicavel; schema+LLM e' ponte entre "intent humano"
  e "compressao eficiente"

## Riscos

- Mission creep: TCF e' lib de compressao, nao plataforma de query
- Ollama/local-LLM dependency adiciona setup-friction
- Reactivacao de codigo v0.5 (old/tcf/) pode confundir (NUNCA imports
  destes em src/tcf)

## Mitigations

- Spin-off como **pacote separado** (`tcf-llm-bridge`) ou **modulo
  opcional** em tcf[llm], importacao opt-in
- Pure stdlib core; LLM client e' addon

## Status

**De prontidao** (registrado 2026-05-27). Bloqueado por
T-RECOVER-SCHEMA-MULTI-TABLE (precisa schema multi-tabela primeiro).
Atacar apos H-PERF-06-v2 + studio owner.

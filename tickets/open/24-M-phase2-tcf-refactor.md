---
title: META — Fase 2: Refatorar TCF encoder + testar com dados canonicos
type: meta
status: IN_PROGRESS
priority: 23
created: 2026-04-12
---

# META: Fase 2 — TCF Encoder Refactoring + Benchmarks Reais

## Contexto

Fase 1 (datasets) e 1.5 (shaper) deram fundacao solida.
Agora refatorar o TCF encoder para:
1. Aceitar dados genericos (nao so CSV do filesystem)
2. Funcionar com dados do shaper (dicts Python)
3. Manter compatibilidade com CLI e testes existentes

Depois: medir compressao e tokens reais em dados canonicos.

## Sub-tickets (em ordem)

### Etapa A — Refatorar encoder

| # | Ticket | Descricao |
|---|--------|-----------|
| 25 | T-encode-columns | Criar `encode_columns()` que aceita `dict[str, list]` puro |
| 26 | T-encode-rows | Criar `encode_rows()` que aceita `list[dict]` (converte internamente) |
| 27 | T-encode-compat | Manter `encode()` original como wrapper (nao quebrar CLI/testes) |
| 28 | T-encode-tests | Testes roundtrip com dados canonicos (TPC-H lineitem, Adult) |

### Etapa B — Medir compressao sem LLM

| # | Ticket | Descricao |
|---|--------|-----------|
| 29 | T-compression-benchmark | TCF L0-L3 vs CSV vs JSONL em TPC-H lineitem + Adult |
| 30 | T-gzip-benchmark | Todos formatos apos gzip/brotli (chars + bytes) |
| 31 | T-token-measurement | Tokens reais via Ollama prompt_eval_count |

### Etapa C — Comparacao com TOON

| # | Ticket | Descricao |
|---|--------|-----------|
| 32 | T-toon-encoder | Implementar encoder/decoder TOON real |
| 33 | T-format-comparison | Tabela completa: TCF vs CSV vs JSONL vs TOON (tamanho + tokens) |

### Etapa D — LLM Accuracy

| # | Ticket | Descricao |
|---|--------|-----------|
| 34 | T-llm-accuracy-canonical | Rodar perguntas em dados canonicos (25 Q × modelos) |
| 35 | T-stats-ablation-canonical | STATS on/off em dados canonicos |

### Etapa E — Numeric precision

| # | Ticket | Descricao |
|---|--------|-----------|
| 36 | T-numeric-shaper | Implementar arredondamento controlado no shaper |
| 37 | T-numeric-tcf | Implementar compressao numerica no encoder TCF |

## Criterio de conclusao

Fase 2 esta completa quando:
- encode_columns() aceita dados do shaper sem IO
- Compressao medida em dados canonicos (chars + bytes + tokens)
- Comparacao honesta TCF vs CSV vs JSONL vs TOON
- Opcional: LLM accuracy replicada em dados reais

## Principio arquitetural

O TCF core (`src/tcf/`) aceita dados genericos.
Adaptadores (scripts/) conectam fontes especificas ao core.
O encoder NUNCA importa sqlite3, pandas, ou shaper.

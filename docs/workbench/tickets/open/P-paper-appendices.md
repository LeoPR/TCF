---
title: Apendices A/B/C do paper — preencher placeholders
type: paper
status: OPEN
priority: MEDIUM
created: 2026-04-27
origin: Auditoria pos-reorg (commit f3a56a6)
see_also:
  - docs/article/appendices/
  - docs/article/README.md (status apendices)
---

# Apendices do paper — preencher placeholders

## Estado

3 placeholders + 1 completo em [`docs/article/appendices/`](../../../article/appendices/):

| Apendice | Arquivo | Status atual | Prioridade |
|----------|---------|--------------|-----------|
| A — Especificacao TCF v0.2 | A-tcf-spec.md | placeholder | **CRITICAL** |
| B — Prompts utilizados | B-prompts.md | placeholder | HIGH |
| C — Tabelas completas de resultados | C-full-tables.md | placeholder | HIGH |
| D — Comparacao lado-a-lado de formatos | D-format-comparison.md | completo ✅ | — |

## Apendice A — Especificacao TCF v0.2

**Conteudo proposto:**
- Gramatica formal do formato (header, sections, columns, RLE notation)
- 4 niveis L0..L3 com diff exato entre eles
- Encoding rules: RLE threshold, DICT decisao, STATS computation
- Decoding rules: regras inversas
- Exemplos de cada construct
- Limitations: numeric precision, nested types

**Fonte de dados**: codigo `src/tcf/encoder.py` + `decoder.py` +
`compression.py` + `schema.py`. Gerar a partir do codigo + testes.

## Apendice B — Prompts utilizados

**Conteudo proposto:**
- LINHA_A_SYSTEM_PROMPT (encode + question)
- PROMPT_TEMPLATE Linha B (schema + question)
- AnswerCell + SqlAnswer Pydantic schemas
- Wordings completos das 28 perguntas Adult + 28 TPC-H × 4 niveis
- Modelos parametros: temperature=0, num_predict, reasoning effort

**Fonte**: `experiments/eval/run_m_*.py` + `experiments/eval/llm_eval/
question_naturalness.py`. Pode ser quase 100% extraido por script.

## Apendice C — Tabelas completas de resultados

**Conteudo proposto:**
- Tabela mestra: 7 modelos × 4 paradigmas × 4 niveis = 112 celulas
- Per-question breakdown × naturalidade (4 datasets, 4 cells each)
- Custo por modelo (Adult+TPC-H)
- Latencia mediana por modelo
- Cache hit rate por modelo

**Fonte**: `experiments/results/{m_acomm,m_acomm_b,m_acommA_tpch,
m_acommB_tpch}/manifest.jsonl`. Script em `experiments/eval/analyze_*.py`
ja agrega; precisa formatar como markdown table.

## Criterio de aceite

- [ ] Apendice A: spec formal + exemplos por nivel + limitations
- [ ] Apendice B: prompts copiados literalmente do codigo + schemas
- [ ] Apendice C: 4-6 tabelas auto-geradas de manifests
- [ ] Cross-refs entre apendices e capitulos
- [ ] Cada apendice tem 800-2000 palavras

## Dependencias

- Cap 7 finalizado ✅
- (Apendice C) script de geracao de tabelas a partir de manifest

## Impacto estimado

- Apendice A: 1-2 dias (escrita + revisao formal)
- Apendice B: 0.5 dia (extracao + organizacao)
- Apendice C: 1 dia (script + verificacao)
- Total: 3-4 dias

## Notas de revisao futura

Quando revisitar:
- Codigo encoder/decoder pode ter evoluido para v0.3 — atualizar Apendice A
- Manifests podem ter ganho colunas novas — Apendice C generator deve
  adaptar

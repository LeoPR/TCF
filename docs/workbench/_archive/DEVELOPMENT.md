---
title: TCF — Consolidação de desenvolvimento (timeline operacional)
date: 2026-04-26
type: consolidated
status: ATIVO — substitui partes operacionais de history.md e research-notes legados
---

# CONSOLIDATED_DEVELOPMENT — evolução operacional do TCF

Este documento traça **a ordem em que o código foi escrito**, ferramentas
construídas e infraestrutura amadurecida. Para a evolução **das hipóteses
e do desenho experimental**, ver [CONSOLIDATED_SCIENCE.md](CONSOLIDATED_SCIENCE.md).

---

## Fase 0 — origem (abril 2026, primeira semana)

**Rascunho v0.0** — esboço manual de um formato textual columnar para LLM ler
tabelas relacionais. Sintaxe primitiva com cabeçalho + colunas tipadas.

**Pivô crítico**: descobriu-se que o objetivo era **comprimir mantendo
legibilidade LLM**, não apenas comprimir. Todos os experimentos posteriores
trabalham sobre esse compromisso.

---

## Fase 1 — encoder/decoder v0.1 (semana 1-2)

Ver [docs/history.md](history.md) para detalhes da v0.0→v0.1.

- `src/tcf/encoder.py` + `decoder.py`: primeira implementação funcional
- Formato L0..L6 progressivo (raw → RLE → STATS → schema-only)
- Roundtrip CSV → TCF → CSV verificado em testes G01

**Resultado**: encode trivialmente reversível, mas com erros conceituais
(DICT com `=`, `[sorted]` confuso, IDs redundantes). v0.1 fica para
referência histórica em `docs/archive/`.

---

## Fase 2 — Phase 1 LLM Comprehension (semana 3-4)

**Objetivo**: testar se LLMs realmente leem TCF tão bem quanto CSV/JSONL.

- 12 modelos locais via Ollama
- 4 formatos: TCF, CSV, JSONL, NDJSON
- Escalas 50-5000 linhas
- 4 questões agregadas (count, sum, avg, max)

**Achados centrais (F-Q1..F-Q12)**: ver `CONSOLIDATED_SCIENCE.md`.
Resumo operacional: TCF chega a 43% acc vs JSONL 63% — TCF é **mais
denso** mas **menos compreensível** que JSON puro para o que importa.
Pivô para Linha B começa aqui.

**Sub-fases**: phase1..6, stats_ablation, diagnostic_3layer,
scale_progression, frontier_search.

---

## Fase 3 — Phase 2 refactor (semana 4-5)

Tickets 24+25-28 fechados (`tickets/closed/`):
- `encoder_v02.py` + `decoder_v02.py` substituem v0.1
- `compression.py` separado (RLE + DICT + STATS)
- `EncodeConfig` dataclass para opções (level, include_stats, etc.)
- Testes canonical sobre encode/decode L0..L6

API pública estabilizada: `from tcf import encode, decode, EncodeConfig`.

**Resultado**: pipeline encode/decode pronto para uso em larga escala.

---

## Fase 4 — Shaper + data_sources unified (semana 5)

**Problema operacional**: cada experimento M1..M8 tinha sua própria função
de carregamento. Inconsistência de seeds, samples e schema entre runners.

**Solução** (commits `e9e08a2` Etapa 1, `b6cc8f1` Etapa 2):
- `scripts/shaper/`: framework de extração estratificada com 7 estratégias:
  schema_filter, join, compressibility, stratify, fk_preserving, volume,
  ordering
- `experiments/eval/data_sources.py`: ponto único `load_dataset(source, **kw)`
- Datasets canônicos: TPC-H sf001 + Adult Census via `Z:/tcf-data/`

Todos os runners M1..M9 migrados para `load_dataset`. Imports diretos de
fixtures eliminados.

**Resultado**: pipeline de dados unificado, FK-preserving sampling com
metadados de stratificação inline (TVD/JSD/Hellinger/Wilson).

---

## Fase 5 — M-series locais (semana 5-6)

Ordem cronológica de execução dos M-runners:

| Runner | Data | Resultado | Achado |
|--------|------|-----------|--------|
| M1 codegen | 04-15 | Baseline schema only | F-Q13 |
| M2 codegen | 04-16 | Few-shot ablation | F-Q14 |
| M3 cross-domain | 04-17 | Synthetic 3 domínios | F-Q15-16 |
| M4 baseline | 04-18 | TCF format vs alternatives | F-Q17 |
| M5 intermediate | 04-19 | TCF L0..L3 progressive | F-Q18 |
| M6 filter questions | 04-20 | HAVING + filter+agg | F-Q19 |
| M6b having fix | 04-20 | Bug fix HAVING | (closed) |
| M7 complex queries | 04-21 | CTE + nested subquery | F-Q20 |
| M8 safe-sql | 04-22 | 4 flags isolados | F-Q22 |
| M8b safe-sql combos | 04-22 | combinações de flags | F-Q23 |
| M9 canonical TPC-H | 04-23 | First canonical dataset run | F-Q24 |
| M9 Adult | 04-24 | Single-table canonical | F-Q25 |
| M-strat | 04-25 | Random vs stratified | F-Q26 |
| M-quality | 04-25 | SQL quality posthoc | F-Q27 |
| M-Alocal | 04-25 | Linha A em locais (controle M-Acomm) | F-Q28 |

Trace dos commits mais relevantes: `c8b6266`, `204e8bc`, `4dd4d8f`,
`c673481`, `0c7d1e3`.

---

## Fase 6 — M-natural (Adult, semana 6)

Após auditoria de estabilidade (commit `39ce12c`, 17 tickets fechados),
inaugurou-se o **eixo de naturalidade da pergunta**.

**Implementação técnica**:
- `experiments/eval/llm_eval/question_naturalness.py`: dataclass
  `Question` com 4 wordings (N0..N3); 28 questões por dataset
- Runners adaptados: `run_m9_adult`, `run_m_alocal`, `run_m_acomm`
  todos aceitam `--naturalness {N0|N1|N2|N3|all|comma-list}`
- Manifest registra `naturalness_level` e `question_text` por record
- Scorer ganhou `ScoringConfig` (string_match strict/normalized/lenient,
  tol_rel/tol_abs paramétricos)

**Resultados Adult locais**:
- Linha A (M-Alocal): 13 modelos × 4 níveis × 7q = 595 records → **F-Q29**
- Linha B (M9-Adult): 3 modelos × 3 seeds × 4 níveis × 7q = 252 records → **F-Q30**

**Custo**: $0 (Ollama local).

Commits: `7f15afd`, `c289f08`, `534fbe8`, `27ceb9e`, `0000a81`, `a33a4fa`.

---

## Fase 7 — M-Acomm (comerciais, semana 6)

**OpenAI** (commit `e167cd8`, `23945b0`, `0e1461d`, `9a2c599`):
- `commercial_client.py`: cliente unificado com PRICING table verificada
- Migrado para **Responses API** (recomendação oficial 2026):
  `client.responses.parse(text_format=AnswerCell, ...)`
- Structured outputs Pydantic — parse_failure < 0.5%
- Prompt caching agressivo (`prompt_cache_key` por model+seed)
- gpt-5.x reasoning models: `reasoning={"effort":"low"}` +
  `max_output_tokens=2048`
- 4 modelos: gpt-5.4-nano, gpt-5.4-mini, gpt-5.4, gpt-4o-mini (controle)
- Ablação progressiva F1..F5 ($0.001 → $0.51 por modelo)
- **Custo**: $3.17 USD para 672 records (Adult A+B + TPC-H A+B)

**Anthropic** (commit `903909f`):
- 3 modelos: haiku 4.5, sonnet 4.6, opus 4.7
- API divergente: opus 4.7 usa `thinking.type=adaptive` +
  `output_config.effort`; haiku/sonnet usam `thinking.type=enabled` +
  `budget_tokens`
- opus 4.7 não aceita `temperature` (deprecated)
- **Custo**: $6.29 USD para 1008 records

**Total M-Acomm: $9.46 USD** (com cache ~75% economia).

---

## Fase 8 — M-schema-scope (semana 6-7)

`run_m_schema_scope.py` — eixo horizontal: 4 níveis de schema visível
(minimal/core/chain/full) em TPC-H Linha B local. Em curso na hora desta
consolidação. 252 calls Ollama, $0.

---

## Convenções de runner consolidadas

Todos os runners M-series seguem:

1. **Argumentos comuns**: `--models`, `--seeds`, `--naturalness`, `--summary`
2. **Manifest JSONL**: 1 record por call em
   `experiments/results/{runner}/manifest.jsonl`
3. **Dedup last-wins**: re-runs sobrescrevem records anteriores no summary
4. **Cache de records**: re-rodar pula keys que já estão no manifest
   (a menos que estejam marcadas `reason=exception`)
5. **Naturalness-aware**: N0 mantém retrocompat byte-identical com
   wordings legacy; N1+ vai para nova key namespace

---

## Convenções de finding consolidadas

`docs/methodology/F-findings.md` é a **fonte canônica**. Cada F-Qxx tem:
- Conclusão direta em 1 parágrafo
- Tabela central de evidência
- Mecanismo identificado
- Implicações para o paper
- Referência ao manifest

`docs/FINDINGS_SUMMARY.md` é o **resumo paper-ready** com top findings.

---

## Estado atual

- **2256 records totais** (288 locais + 1968 comerciais) sobre Adult+TPC-H
- **36 findings F-Q1..F-Q36** documentados
- **Tabela 2D paper-ready** completa em todas as 8 células
- **Custo total**: $9.46 USD comerciais, $0 locais

Pendências em `tickets/open/`:
- M-natural (encerrável)
- M-schema-scope (em curso)
- 23-numeric-precision (research idea v0.3)
- 29-decoder-freetext-bug (não afeta Linha A/B)
- H-advanced-compression-v03
- P-phase-closure (meta)

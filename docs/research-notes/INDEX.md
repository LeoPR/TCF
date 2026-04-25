# Research Notes — Index

Cada nota e evidencia ou diario de processo. Os achados cientificos
consolidados vivem em [F-findings.md](../methodology/F-findings.md).

Cada nota e tagueada com a linha de pesquisa que a motivou:
- `{A}` — Linha A (LLM como analista direto; ver [research-lines/A-direct-reasoning.md](../research-lines/A-direct-reasoning.md))
- `{B}` — Linha B (schema carrier + SQL; ver [research-lines/B-schema-carrier.md](../research-lines/B-schema-carrier.md))
- `{shared}` — infraestrutura/metodologia compartilhada

| Data | Linha | Nota | F-findings | Manifests |
|------|-------|------|-----------|-----------|
| 2026-04-10 | `{shared}` | [canonical-datasets](2026-04-10-canonical-datasets.md) | F-Q1 (representatividade) | — |
| 2026-04-10 | `{A}` | [compression-tokens-streaming](2026-04-10-compression-tokens-streaming.md) | F-Q3 (compressao tokens) | — |
| 2026-04-10 | `{shared}` | [critical-review](2026-04-10-critical-review.md) | F-Q1..F-Q5 (contexto geral) | — |
| 2026-04-10 | `{shared}` | [storage-architecture](2026-04-10-storage-architecture.md) | — (infra) | — |
| 2026-04-12 | `{shared}` | [dataset-shaper](2026-04-12-dataset-shaper.md) | — (infra) | — |
| 2026-04-14 | `{shared}` | [evaluation-metrics](2026-04-14-evaluation-metrics.md) | F-Q6..F-Q9 (metodo avaliacao) | — |
| 2026-04-14 | `{shared}` | [general-review](2026-04-14-general-review.md) | F-Q1..F-Q9 (revisao geral) | — |
| 2026-04-14 | `{A}` | [question-enrichment](2026-04-14-question-enrichment.md) | F-Q7 (tipos de pergunta) | — |
| 2026-04-14 | `{A}` | [stats-ablation-results](2026-04-14-stats-ablation-results.md) | F-Q8 (ablation estatistico) | stats_ablation |
| 2026-04-14 | `{A}` | [stats-questions-heuristics](2026-04-14-stats-questions-heuristics.md) | F-Q7..F-Q8 (heuristicas) | — |
| 2026-04-15 | `{A}` | [compression-tokenization-strategy](2026-04-15-compression-tokenization-strategy.md) | F-Q3 (tokens/compressao) | — |
| 2026-04-18 | `{shared}` | [cpu-bench-findings](2026-04-18-cpu-bench-findings.md) | F-Q14 (CPU vs GPU) | frontier_search |
| 2026-04-18 | `{A}` | [rle-notation-tokenization](2026-04-18-rle-notation-tokenization.md) | F-Q13 (RLE tokenizacao) | frontier_search |
| 2026-04-20 | `{shared}` | [model-known-issues](2026-04-20-model-known-issues.md) | F-Q10..F-Q12 (qualificacao) | m0_qualification |
| 2026-04-20 | `{shared}` | [qualification-findings](2026-04-20-qualification-findings.md) | F-Q10..F-Q12 (qualificacao) | m0_qualification |
| 2026-04-20 | `{shared}` | [tcf-retrospective](2026-04-20-tcf-retrospective.md) | F-Q1..F-Q15 (retrospectiva) | todos |
| 2026-04-21 | `{A}` | [thinking-non-convergence](2026-04-21-thinking-non-convergence.md) | F-Q10 (thinking mode) | frontier_search |
| 2026-04-22 | `{B}` | [coverage-and-intermediate-forms](2026-04-22-coverage-and-intermediate-forms.md) | F-Q18 (Pandas/Polars/CoT) | m5_intermediate |
| 2026-04-22 | `{shared}` | [timing-measurement-methodology](2026-04-22-timing-measurement-methodology.md) | ALERTA perf (pre-M_perf) | m1..m6 |
| 2026-04-23 | `{B}` | [embedded-query-invariants](2026-04-23-embedded-query-invariants.md) | F-Q21 — âncoras matemáticas | m6, m7 |
| 2026-04-23 | `{B}` | [conservative-sql-flag](2026-04-23-conservative-sql-flag.md) | F-Q22 — validado por M8 | m6b, m7, m8_safe_sql |
| 2026-04-23 | `{B}` | [query-theory](2026-04-23-query-theory.md) | HIPÓTESES conceituais pré-SQL | — (pré-experimento) |
| 2026-04-24 | `{shared}` | [schema-qualifier](2026-04-24-schema-qualifier.md) | ROADMAP — qualifier de schema antes do TCF | — (pré-implementação) |
| 2026-04-25 | `{shared}` | [shaper-as-standalone-tool](2026-04-25-shaper-as-standalone-tool.md) | IDEIA — Shaper como biblioteca pública | — (pós-paper) |

## Notas por tema

**Formato e compressao:** compression-tokens-streaming, compression-tokenization-strategy, rle-notation-tokenization

**Avaliacao e metodo:** evaluation-metrics, stats-ablation-results, stats-questions-heuristics, question-enrichment, timing-measurement-methodology

**Modelos:** model-known-issues, qualification-findings, thinking-non-convergence

**Datasets e infra:** canonical-datasets, storage-architecture, dataset-shaper

**Revisoes:** critical-review, general-review, tcf-retrospective, coverage-and-intermediate-forms, cpu-bench-findings

**Hipoteses de pesquisa:** embedded-query-invariants, conservative-sql-flag

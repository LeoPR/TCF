# Research Notes — Index

Cada nota e evidencia ou diario de processo. Os achados cientificos
consolidados vivem em [F-findings.md](../methodology/F-findings.md).

| Data | Nota | F-findings relacionados | Manifests |
|------|------|------------------------|-----------|
| 2026-04-10 | [canonical-datasets](2026-04-10-canonical-datasets.md) | F-Q1 (representatividade) | — |
| 2026-04-10 | [compression-tokens-streaming](2026-04-10-compression-tokens-streaming.md) | F-Q3 (compressao tokens) | — |
| 2026-04-10 | [critical-review](2026-04-10-critical-review.md) | F-Q1..F-Q5 (contexto geral) | — |
| 2026-04-10 | [storage-architecture](2026-04-10-storage-architecture.md) | — (infra) | — |
| 2026-04-12 | [dataset-shaper](2026-04-12-dataset-shaper.md) | — (infra) | — |
| 2026-04-14 | [evaluation-metrics](2026-04-14-evaluation-metrics.md) | F-Q6..F-Q9 (metodo avaliacao) | — |
| 2026-04-14 | [general-review](2026-04-14-general-review.md) | F-Q1..F-Q9 (revisao geral) | — |
| 2026-04-14 | [question-enrichment](2026-04-14-question-enrichment.md) | F-Q7 (tipos de pergunta) | — |
| 2026-04-14 | [stats-ablation-results](2026-04-14-stats-ablation-results.md) | F-Q8 (ablation estatistico) | m1_stats_fs |
| 2026-04-14 | [stats-questions-heuristics](2026-04-14-stats-questions-heuristics.md) | F-Q7..F-Q8 (heuristicas) | — |
| 2026-04-15 | [compression-tokenization-strategy](2026-04-15-compression-tokenization-strategy.md) | F-Q3 (tokens/compressao) | — |
| 2026-04-18 | [cpu-bench-findings](2026-04-18-cpu-bench-findings.md) | F-Q14 (CPU vs GPU) | frontier_search |
| 2026-04-18 | [rle-notation-tokenization](2026-04-18-rle-notation-tokenization.md) | F-Q13 (RLE tokenizacao) | frontier_search |
| 2026-04-20 | [model-known-issues](2026-04-20-model-known-issues.md) | F-Q10..F-Q12 (qualificacao) | m0_qualification |
| 2026-04-20 | [qualification-findings](2026-04-20-qualification-findings.md) | F-Q10..F-Q12 (qualificacao) | m0_qualification |
| 2026-04-20 | [tcf-retrospective](2026-04-20-tcf-retrospective.md) | F-Q1..F-Q15 (retrospectiva) | todos |
| 2026-04-21 | [thinking-non-convergence](2026-04-21-thinking-non-convergence.md) | F-Q15 (thinking mode) | frontier_search |
| 2026-04-22 | [coverage-and-intermediate-forms](2026-04-22-coverage-and-intermediate-forms.md) | F-Q18 (Pandas/Polars/CoT) | m5_intermediate |
| 2026-04-22 | [timing-measurement-methodology](2026-04-22-timing-measurement-methodology.md) | ALERTA perf (pre-M_perf) | m1..m6 |
| 2026-04-23 | [embedded-query-invariants](2026-04-23-embedded-query-invariants.md) | HIPÓTESE M_inv — âncoras matemáticas | m6, m7 |
| 2026-04-23 | [conservative-sql-flag](2026-04-23-conservative-sql-flag.md) | HIPÓTESE --safe-sql: CTE/decomposed vs HAVING | m6b, m7 |

## Notas por tema

**Formato e compressao:** compression-tokens-streaming, compression-tokenization-strategy, rle-notation-tokenization

**Avaliacao e metodo:** evaluation-metrics, stats-ablation-results, stats-questions-heuristics, question-enrichment, timing-measurement-methodology

**Modelos:** model-known-issues, qualification-findings, thinking-non-convergence

**Datasets e infra:** canonical-datasets, storage-architecture, dataset-shaper

**Revisoes:** critical-review, general-review, tcf-retrospective, coverage-and-intermediate-forms, cpu-bench-findings

**Hipoteses de pesquisa:** embedded-query-invariants, conservative-sql-flag

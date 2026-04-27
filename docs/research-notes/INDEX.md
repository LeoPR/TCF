# Research Notes — Index

Cada nota e evidencia ou diario de processo. Os achados cientificos
consolidados vivem em [F-findings.md](../methodology/F-findings.md);
a sintese paper-ready em [FINDINGS_SUMMARY.md](../FINDINGS_SUMMARY.md).

Para evolucao temporal do projeto:
- [CONSOLIDATED_DEVELOPMENT.md](../CONSOLIDATED_DEVELOPMENT.md) — ordem operacional
- [CONSOLIDATED_SCIENCE.md](../CONSOLIDATED_SCIENCE.md) — ordem logica das hipoteses

Notas obsoletas (cobertas pelos consolidados) foram movidas para
[_archive/](_archive/).

## Notas ATIVAS (referencia atual)

| Data | Nota | Por que persiste |
|------|------|------------------|
| 2026-04-10 | [storage-architecture](2026-04-10-storage-architecture.md) | Arquitetura `Z:/tcf-data/` em uso |
| 2026-04-12 | [dataset-shaper](2026-04-12-dataset-shaper.md) | Decisoes de design do Shaper |
| 2026-04-14 | [stats-ablation-results](2026-04-14-stats-ablation-results.md) | Dados de F-Q8 (STATS hint) |
| 2026-04-24 | [schema-qualifier](2026-04-24-schema-qualifier.md) | Roadmap qualifier de schema |
| 2026-04-25 | [shaper-as-standalone-tool](2026-04-25-shaper-as-standalone-tool.md) | Research idea — Shaper como biblioteca publica |
| 2026-04-25 | [stratification-metrics](2026-04-25-stratification-metrics.md) | TVD/JSD/Hellinger validados; metodologia em producao |
| 2026-04-25 | [tabular-formats-literature](2026-04-25-tabular-formats-literature.md) | Lit review formatos LLM 2024-26 |
| 2026-04-26 | [consolidation-master](2026-04-26-consolidation-master.md) | Auditoria F-Q1..Q28 + taxonomia naturalidade |

## Notas arquivadas

[_archive/](_archive/) contem 21 notas que cobrem F-Q1..F-Q23 e
metodologia inicial. Foram consumidas pelos consolidados acima e por
F-findings.md. Mantemos por rastreabilidade historica; podem ser
deletadas no fechamento do projeto se desejado.

Lista resumida (tudo em `_archive/`):
- F-Q1..F-Q9 origins: canonical-datasets, critical-review, general-review,
  evaluation-metrics
- Compression: compression-tokens-streaming, compression-tokenization-strategy,
  rle-notation-tokenization
- Modelos: model-known-issues, qualification-findings, thinking-non-convergence,
  cpu-bench-findings
- Metodo: question-enrichment, stats-questions-heuristics,
  timing-measurement-methodology
- Linha B inicial: coverage-and-intermediate-forms, embedded-query-invariants,
  conservative-sql-flag, query-theory
- Plans (executados): canonical-migration-plan, validation-master-plan
- Outros: tcf-retrospective

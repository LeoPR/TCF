# M-series — tickets retroativos

Cada experimento M-* tem ticket retroativo aqui ligando à F-finding
correspondente em `docs/methodology/F-findings.md`.

Convenção: ticket descreve **o que foi feito + por quê**; finding descreve
**o que foi descoberto**. Bidirecional.

| Ticket | Experimento | Finding | Manifest |
|--------|------------|---------|----------|
| [M01](M01-codegen-baseline.md) | M1 schema carrier baseline | F-Q13, F-Q14 | m1_codegen |
| [M02](M02-fewshot-ablation.md) | M2 fewshot ablation | F-Q15 | m2_codegen |
| [M03](M03-cross-domain.md) | M3 cross-domain synthetic | F-Q16, F-Q17 | m3_crossdomain |
| [M04](M04-format-baseline.md) | M4 CSV/JSON/TCF | F-Q17 | m4_baseline |
| [M05](M05-intermediate-forms.md) | M5 SQL/Pandas/Polars/CoT | F-Q18 | m5_intermediate |
| [M06](M06-filter-questions.md) | M6 WHERE/HAVING/GROUP-BY | F-Q19 | m6_filter |
| [M06b](M06b-having-fix.md) | M6b HAVING subquery fewshot | F-Q19b | m6b_having_fix |
| [M07](M07-complex-queries.md) | M7 subquery/CTE/COUNT DISTINCT | F-Q20 | m7_complex |
| [M08](M08-safe-sql-isolated.md) | M8 safe-sql flags isolados | F-Q22 | m8_safe_sql |
| [M08b](M08b-safe-sql-combos.md) | M8b safe-sql combinações | F-Q23 | m8b_safe_sql_combos |
| [M09](M09-canonical-tpch.md) | M9 canonical TPC-H | F-Q24 | m9_canonical |
| [M09-Adult](M09-Adult-canonical.md) | M9-Adult single-table | F-Q25 | m9_adult |
| [M-strat](M-strat-random-vs-stratified.md) | M-strat sampling modes | F-Q26 | m_strat |
| [M-quality](M-quality-sql-posthoc.md) | M-quality post-hoc SQL quality | F-Q27 | m_quality |
| [M-Alocal](M-Alocal-linha-a-canonical.md) | M-Alocal Linha A canonical | F-Q28 | m_alocal |
| [M-inv](M-inv-invariant-analysis.md) | M_inv post-hoc invariants | F-Q21 | (post-hoc) |

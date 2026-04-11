# Quality Report — adult-census

_Generated: 2026-04-11 07:04 UTC_

- **Source:** UCI ML Repository (via OpenML id=1590)
- **Origin:** https://archive.ics.uci.edu/dataset/2/adult
- **License:** CC BY 4.0
- **Citation:** Becker, B. and Kohavi, R. (1996). Adult. UCI Machine Learning Repository. https://doi.org/10.24432/C5XW20

## Schema Summary

| Table | Rows | Cols | PK | FKs |
|-------|------|------|-----|-----|
| `adult` | 48,842 | 15 | `—` | `—` |

**Total:** 48,842 rows across 1 tables (15 columns combined)

## Table: `adult`

- **Rows:** 48,842
- **Columns:** 15

### Column Statistics

| Column | Type | Nulls | Distinct/Min | Max | Mean | StdDev |
|--------|------|-------|--------------|-----|------|--------|
| `age` | int | 0 | 17 | 90 | 38.6436 | 13.8722 |
| `workclass` | string | 2,799 | 8 | — | — | — |
| `fnlwgt` | int | 0 | 12,285 | 1,490,400 | 189,664.1346 | 105,046.3408 |
| `education` | string | 0 | 16 | — | — | — |
| `education-num` | int | 0 | 1 | 16 | 10.0781 | 2.5697 |
| `marital-status` | string | 0 | 7 | — | — | — |
| `occupation` | string | 2,809 | 14 | — | — | — |
| `relationship` | string | 0 | 6 | — | — | — |
| `race` | string | 0 | 5 | — | — | — |
| `sex` | string | 0 | 2 | — | — | — |
| `capital-gain` | int | 0 | 0 | 99,999 | 1,079.0676 | 8,000.2485 |
| `capital-loss` | int | 0 | 0 | 4,356 | 87.5023 | 405.4412 |
| `hours-per-week` | int | 0 | 1 | 99 | 40.4224 | 12.4168 |
| `native-country` | string | 857 | 41 | — | — | — |
| `class` | string | 0 | 2 | — | — | — |

### Top values (categorical columns)


**`workclass`** — distinct: 8, entropy: 1.423 bits
- `Private`: 33,906 (69.4%)
- `Self-emp-not-inc`: 3,862 (7.9%)
- `Local-gov`: 3,136 (6.4%)
- `State-gov`: 1,981 (4.1%)
- `Self-emp-inc`: 1,695 (3.5%)

**`education`** — distinct: 16, entropy: 2.9307 bits
- `HS-grad`: 15,784 (32.3%)
- `Some-college`: 10,878 (22.3%)
- `Bachelors`: 8,025 (16.4%)
- `Masters`: 2,657 (5.4%)
- `Assoc-voc`: 2,061 (4.2%)

**`marital-status`** — distinct: 7, entropy: 1.8357 bits
- `Married-civ-spouse`: 22,379 (45.8%)
- `Never-married`: 16,117 (33.0%)
- `Divorced`: 6,633 (13.6%)
- `Separated`: 1,530 (3.1%)
- `Widowed`: 1,518 (3.1%)

_(showing 3 of 9 categorical columns — see metadata.json for full list)_

### Sample rows (first 3)

_ (showing 6 of 15 columns)_
| `age` | `workclass` | `fnlwgt` | `education` | `education-num` | `marital-status` |
|---|---|---|---|---|---|
| 25 | Private | 226802 | 11th | 7 | Never-married |
| 38 | Private | 89814 | HS-grad | 9 | Married-civ-spouse |
| 28 | Local-gov | 336951 | Assoc-acdm | 12 | Married-civ-spouse |

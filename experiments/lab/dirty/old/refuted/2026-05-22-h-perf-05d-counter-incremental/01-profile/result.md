# Sub-exp 01 — profile breakdown _detect_compositions

## Setup

Profile com instrumentacao manual (subclass InstrumentedSyntax).
Lineitem 5k, 3 colunas representativas (l_comment, l_extendedprice, l_partkey).

## Breakdown por coluna

| Col | bytes | iters | encode (s) | _dc (s) | rebuild_counter (s/%) | build_alias_first_line | build_candidates | substitute |
|---|---:|---:|---:|---:|---|---|---|---|
| l_comment | 133426 | 99 | 7.903 | 7.253 | 3.374 (46.5%) | 0.440 (6.1%) | 2.056 (28.3%) | 1.339 (18.5%) |
| l_extendedprice | 51408 | 1 | 0.216 | 0.003 | 0.002 (52.2%) | 0.002 (47.6%) | 0.000 (0.1%) | 0.000 (0.0%) |
| l_partkey | 26549 | 1 | 0.047 | 0.001 | 0.001 (59.1%) | 0.001 (40.7%) | 0.000 (0.2%) | 0.000 (0.0%) |

## Linhas afetadas por iter (% do total)

| Col | lines_total | lines_affected avg | % |
|---|---:|---:|---:|
| l_comment | 4987 | 16.4 | 0.3% |
| l_extendedprice | 4769 | 0.0 | 0.0% |
| l_partkey | 1832 | 0.0 | 0.0% |

## Veredito

**Max rebuild_counter pct entre colunas testadas: 59.1%**

**GO**: counter incremental vale prototype (rebuild_counter dominante).

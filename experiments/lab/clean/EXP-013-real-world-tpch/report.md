# EXP-013 — Real-world TPC-H (report)

Cap: 5000 rows por tabela. Tabelas com mais rows sao truncadas.

## Resumo por tabela

| Tabela | rows | full | cols | raw (B) | TCF (B) | TCF/raw | ratio | RT | enc ms |
|---|---:|---:|---:|---:|---:|---:|---:|---|---:|
| `region` | 5 | 5 | 3 | 415 | 429 | +14 | 103.4% | OK | 1 |
| `nation` | 25 | 25 | 4 | 2252 | 2213 | -39 | 98.3% | OK | 3 |
| `supplier` | 100 | 100 | 7 | 13848 | 12556 | -1292 | 90.7% | OK | 17 |
| `customer` | 1500 | 1500 | 8 | 241155 | 210428 | -30727 | 87.3% | OK | 2598 |
| `part` | 2000 | 2000 | 9 | 235202 | 147639 | -87563 | 62.8% | OK | 6101 |
| `partsupp` | 5000* | 8000 | 5 | 723936 | 721666 | -2270 | 99.7% | OK | 8484 |
| `orders` | 5000* | 15000 | 9 | 545678 | 435033 | -110645 | 79.7% | OK | 18429 |
| `lineitem` | 5000* | 60175 | 16 | 601788 | 498271 | -103517 | 82.8% | OK | 40523 |

`*` = capped a 5000 rows (tabela maior).

## Totais (somando todas tabelas truncadas)

- Raw total: 2,364,274 B
- TCF total: 2,028,235 B  (-336,039, 85.8%)
- RT: 8/8

## Stats per-coluna (orders se disponivel)

| Coluna | det? | runs | uniq |
|---|---|---:|---:|
| `o_orderkey` | True | 626 | 5000 |
| `o_custkey` | True | 167 | 982 |
| `o_orderstatus` | False | 0 | 3 |
| `o_totalprice` | True | 0 | 4999 |
| `o_orderdate` | False | 0 | 2115 |
| `o_orderpriority` | False | 0 | 5 |
| `o_clerk` | True | 313 | 994 |
| `o_shippriority` | False | 0 | 1 |
| `o_comment` | False | 0 | 4997 |

## Validacao

- ✓ RT 8/8 OK

## Limitacoes

- Tabelas maiores capadas em 5000 rows (encode O(N²))
- lineitem full (60k rows) nao testado
- order natural fixo
- shaper nao usado (DatasetReader.rows direto)


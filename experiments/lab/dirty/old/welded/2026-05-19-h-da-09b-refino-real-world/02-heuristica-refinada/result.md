# Sub-exp 02 — heuristica refinada v2

Total colunas: 76

## Matriz de confusao

(TP = enable em HELP; TN = skip em HURT/NO-OP; FP = enable em HURT/NO-OP; FN = skip em HELP)

| metric | v1 (existente) | **v2 (refinada)** |
|---|---:|---:|
| TP | 4 | 12 |
| TN | 56 | 49 |
| FP | 8 | 15 |
| FN | 8 | 0 |

## Bytes

| heuristica | bytes total | delta vs off |
|---|---:|---:|
| Always-off | 145516 | 0 |
| **v1** (existente) | 145629 | +113 |
| **v2** (refinada) | 145068 | -448 |
| Oracle (best-of) | 143890 | -1626 |

## Detalhes per coluna (so' divergencias entre v1 e v2)

| dataset.table.col | outcome | v1 | v2 | rule v2 | actual delta |
|---|---|---|---|---|---:|
| `adult-census.adult.fnlwgt` | HELP | False | True | 2-numeric-high-cardinality | -193 |
| `tpch-sf001.region.r_regionkey` | NO-OP | False | True | 2-numeric-high-cardinality | +0 |
| `tpch-sf001.nation.n_nationkey` | NO-OP | False | True | 2-numeric-high-cardinality | +0 |
| `tpch-sf001.supplier.s_suppkey` | NO-OP | False | True | 2-numeric-high-cardinality | +0 |
| `tpch-sf001.supplier.s_acctbal` | NO-OP | False | True | 2-numeric-high-cardinality | +1 |
| `tpch-sf001.customer.c_custkey` | NO-OP | False | True | 2-numeric-high-cardinality | +0 |
| `tpch-sf001.customer.c_acctbal` | HELP | False | True | 2-numeric-high-cardinality | -60 |
| `tpch-sf001.part.p_partkey` | NO-OP | False | True | 2-numeric-high-cardinality | +0 |
| `tpch-sf001.partsupp.ps_availqty` | HELP | False | True | 2-numeric-high-cardinality | -8 |
| `tpch-sf001.partsupp.ps_supplycost` | HELP | False | True | 2-numeric-high-cardinality | -106 |
| `tpch-sf001.orders.o_orderkey` | NO-OP | False | True | 2-numeric-high-cardinality | +0 |
| `tpch-sf001.orders.o_custkey` | HELP | False | True | 2-numeric-high-cardinality | -10 |
| `tpch-sf001.orders.o_totalprice` | HELP | False | True | 2-numeric-high-cardinality | -102 |
| `tpch-sf001.lineitem.l_partkey` | HELP | False | True | 2-numeric-high-cardinality | -11 |
| `tpch-sf001.lineitem.l_extendedprice` | HELP | False | True | 2-numeric-high-cardinality | -72 |

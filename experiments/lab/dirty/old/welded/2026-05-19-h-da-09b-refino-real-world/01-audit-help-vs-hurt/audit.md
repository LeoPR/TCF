# Sub-exp 01 — Audit help-vs-hurt

Total colunas analisadas: 76

## Resumo por outcome

| Outcome | Count |
|---|---:|
| HELP | 12 |
| HURT | 22 |
| NO-OP | 42 |
| ERROR | 0 |

## HELP (12)

| dataset.table.col | n | uniq | card | avg_len | len_rng | uniform | LCP+LCS | num? | bytes_off | bytes_on | delta |
|---|---:|---:|---:|---:|---:|---|---:|---|---:|---:|---:|
| `adult-census.adult.fnlwgt` | 500 | 498 | 0.996 | 5.8 | 1 | False | 0.06 | True | 4372 | 4179 | -193 |
| `tpch-sf001.supplier.s_name` | 100 | 100 | 1.000 | 18.0 | 0 | True | 0.94 | False | 311 | 68 | -243 |
| `tpch-sf001.customer.c_name` | 200 | 200 | 1.000 | 18.0 | 0 | True | 0.94 | False | 614 | 75 | -539 |
| `tpch-sf001.customer.c_acctbal` | 200 | 200 | 1.000 | 6.8 | 3 | False | 0.04 | False | 2022 | 1962 | -60 |
| `tpch-sf001.part.p_brand` | 200 | 25 | 0.125 | 8.0 | 0 | True | 0.78 | False | 788 | 778 | -10 |
| `tpch-sf001.partsupp.ps_availqty` | 200 | 196 | 0.980 | 3.9 | 2 | False | 0.08 | True | 1337 | 1329 | -8 |
| `tpch-sf001.partsupp.ps_supplycost` | 200 | 200 | 1.000 | 5.8 | 2 | False | 0.07 | False | 1878 | 1772 | -106 |
| `tpch-sf001.orders.o_custkey` | 200 | 176 | 0.880 | 3.2 | 3 | False | 0.07 | True | 1116 | 1106 | -10 |
| `tpch-sf001.orders.o_totalprice` | 200 | 200 | 1.000 | 8.5 | 2 | False | 0.03 | False | 2405 | 2303 | -102 |
| `tpch-sf001.orders.o_clerk` | 200 | 182 | 0.910 | 15.0 | 0 | True | 0.80 | False | 1513 | 1242 | -271 |
| `tpch-sf001.lineitem.l_partkey` | 200 | 195 | 0.975 | 3.4 | 3 | False | 0.17 | True | 1158 | 1147 | -11 |
| `tpch-sf001.lineitem.l_extendedprice` | 200 | 199 | 0.995 | 7.6 | 2 | False | 0.07 | False | 2199 | 2127 | -72 |

## HURT (22)

| dataset.table.col | n | uniq | card | avg_len | len_rng | uniform | LCP+LCS | num? | bytes_off | bytes_on | delta |
|---|---:|---:|---:|---:|---:|---|---:|---|---:|---:|---:|
| `adult-census.adult.education` | 500 | 16 | 0.032 | 8.5 | 9 | False | 0.15 | False | 1573 | 1580 | +7 |
| `adult-census.adult.marital-status` | 500 | 6 | 0.012 | 14.1 | 14 | False | 0.10 | False | 1388 | 1394 | +6 |
| `adult-census.adult.occupation` | 500 | 14 | 0.028 | 12.2 | 17 | False | 0.00 | False | 1735 | 1741 | +6 |
| `tpch-sf001.nation.n_comment` | 25 | 25 | 1.000 | 74.3 | 83 | False | 0.00 | False | 1869 | 1889 | +20 |
| `tpch-sf001.supplier.s_phone` | 100 | 100 | 1.000 | 15.0 | 0 | True | 0.04 | False | 1935 | 2007 | +72 |
| `tpch-sf001.supplier.s_comment` | 100 | 100 | 1.000 | 61.1 | 75 | False | 0.01 | False | 6120 | 6222 | +102 |
| `tpch-sf001.customer.c_phone` | 200 | 200 | 1.000 | 15.0 | 0 | True | 0.06 | False | 3958 | 4007 | +49 |
| `tpch-sf001.customer.c_comment` | 200 | 200 | 1.000 | 71.8 | 87 | False | 0.00 | False | 14249 | 14568 | +319 |
| `tpch-sf001.part.p_name` | 200 | 200 | 1.000 | 33.1 | 22 | False | 0.02 | False | 5969 | 6833 | +864 |
| `tpch-sf001.part.p_type` | 200 | 114 | 0.570 | 20.6 | 9 | False | 0.20 | False | 1432 | 2798 | +1366 |
| `tpch-sf001.part.p_container` | 200 | 40 | 0.200 | 7.7 | 4 | False | 0.23 | False | 891 | 940 | +49 |
| `tpch-sf001.part.p_retailprice` | 200 | 200 | 1.000 | 6.4 | 2 | False | 0.73 | False | 639 | 1816 | +1177 |
| `tpch-sf001.part.p_comment` | 200 | 198 | 0.990 | 13.3 | 17 | False | 0.04 | False | 2755 | 2859 | +104 |
| `tpch-sf001.partsupp.ps_comment` | 200 | 200 | 1.000 | 124.3 | 148 | False | 0.01 | False | 24859 | 25055 | +196 |
| `tpch-sf001.orders.o_orderdate` | 200 | 188 | 0.940 | 10.0 | 0 | True | 0.32 | False | 2084 | 2315 | +231 |
| `tpch-sf001.orders.o_comment` | 200 | 200 | 1.000 | 49.7 | 59 | False | 0.00 | False | 9906 | 10140 | +234 |
| `tpch-sf001.lineitem.l_quantity` | 200 | 49 | 0.245 | 3.9 | 1 | False | 0.66 | False | 854 | 906 | +52 |
| `tpch-sf001.lineitem.l_discount` | 200 | 11 | 0.055 | 3.8 | 1 | False | 0.79 | False | 646 | 670 | +24 |
| `tpch-sf001.lineitem.l_shipdate` | 200 | 190 | 0.950 | 10.0 | 0 | True | 0.50 | False | 2178 | 2324 | +146 |
| `tpch-sf001.lineitem.l_commitdate` | 200 | 187 | 0.935 | 10.0 | 0 | True | 0.58 | False | 2129 | 2298 | +169 |
| `tpch-sf001.lineitem.l_receiptdate` | 200 | 188 | 0.940 | 10.0 | 0 | True | 0.47 | False | 2138 | 2306 | +168 |
| `tpch-sf001.lineitem.l_comment` | 200 | 200 | 1.000 | 26.6 | 33 | False | 0.01 | False | 5347 | 5533 | +186 |

## NO-OP (42)

| dataset.table.col | n | uniq | card | avg_len | len_rng | uniform | LCP+LCS | num? | bytes_off | bytes_on | delta |
|---|---:|---:|---:|---:|---:|---|---:|---|---:|---:|---:|
| `adult-census.adult.age` | 500 | 60 | 0.120 | 2.0 | 0 | True | 0.17 | True | 1920 | 1920 | +0 |
| `adult-census.adult.workclass` | 500 | 7 | 0.014 | 7.9 | 16 | False | 0.14 | False | 1043 | 1047 | +4 |
| `adult-census.adult.education-num` | 500 | 16 | 0.032 | 1.6 | 1 | False | 0.17 | True | 1493 | 1493 | +0 |
| `adult-census.adult.relationship` | 500 | 6 | 0.012 | 9.4 | 10 | False | 0.02 | False | 1452 | 1452 | +0 |
| `adult-census.adult.race` | 500 | 5 | 0.010 | 5.6 | 13 | False | 0.00 | False | 678 | 678 | +0 |
| `adult-census.adult.sex` | 500 | 2 | 0.004 | 4.7 | 2 | False | 0.75 | False | 968 | 968 | +0 |
| `adult-census.adult.capital-gain` | 500 | 25 | 0.050 | 1.2 | 4 | False | 0.06 | True | 404 | 404 | +0 |
| `adult-census.adult.capital-loss` | 500 | 19 | 0.038 | 1.2 | 3 | False | 0.17 | True | 311 | 310 | -1 |
| `adult-census.adult.hours-per-week` | 500 | 50 | 0.100 | 2.0 | 1 | False | 0.17 | True | 1526 | 1526 | +0 |
| `adult-census.adult.native-country` | 500 | 22 | 0.044 | 12.0 | 13 | False | 0.02 | False | 643 | 646 | +3 |
| `adult-census.adult.class` | 500 | 2 | 0.004 | 4.8 | 1 | False | 0.75 | False | 800 | 800 | +0 |
| `tpch-sf001.region.r_regionkey` | 5 | 5 | 1.000 | 1.0 | 0 | True | 0.00 | True | 15 | 15 | +0 |
| `tpch-sf001.region.r_name` | 5 | 5 | 1.000 | 6.8 | 7 | False | 0.33 | False | 44 | 44 | +0 |
| `tpch-sf001.region.r_comment` | 5 | 5 | 1.000 | 66.0 | 84 | False | 0.01 | False | 342 | 342 | +0 |
| `tpch-sf001.nation.n_nationkey` | 25 | 25 | 1.000 | 1.6 | 1 | False | 0.00 | True | 26 | 26 | +0 |
| `tpch-sf001.nation.n_name` | 25 | 25 | 1.000 | 7.1 | 10 | False | 0.17 | False | 204 | 209 | +5 |
| `tpch-sf001.nation.n_regionkey` | 25 | 5 | 0.200 | 1.0 | 0 | True | 0.00 | True | 75 | 75 | +0 |
| `tpch-sf001.supplier.s_suppkey` | 100 | 100 | 1.000 | 1.9 | 2 | False | 0.00 | True | 30 | 30 | +0 |
| `tpch-sf001.supplier.s_address` | 100 | 100 | 1.000 | 25.4 | 30 | False | 0.01 | False | 2983 | 2983 | +0 |
| `tpch-sf001.supplier.s_nationkey` | 100 | 25 | 0.250 | 1.6 | 1 | False | 0.22 | True | 379 | 379 | +0 |
| `tpch-sf001.supplier.s_acctbal` | 100 | 100 | 1.000 | 6.8 | 2 | False | 0.05 | False | 982 | 983 | +1 |
| `tpch-sf001.customer.c_custkey` | 200 | 200 | 1.000 | 2.5 | 2 | False | 0.00 | True | 37 | 37 | +0 |
| `tpch-sf001.customer.c_address` | 200 | 200 | 1.000 | 25.1 | 30 | False | 0.01 | False | 5867 | 5867 | +0 |
| `tpch-sf001.customer.c_nationkey` | 200 | 25 | 0.125 | 1.6 | 1 | False | 0.22 | True | 733 | 733 | +0 |
| `tpch-sf001.customer.c_mktsegment` | 200 | 5 | 0.025 | 9.0 | 2 | False | 0.00 | False | 621 | 621 | +0 |
| `tpch-sf001.part.p_partkey` | 200 | 200 | 1.000 | 2.5 | 2 | False | 0.00 | True | 37 | 37 | +0 |
| `tpch-sf001.part.p_mfgr` | 200 | 5 | 0.025 | 14.0 | 0 | True | 0.93 | False | 607 | 607 | +0 |
| `tpch-sf001.part.p_size` | 200 | 48 | 0.240 | 1.8 | 1 | False | 0.33 | True | 783 | 783 | +0 |
| `tpch-sf001.partsupp.ps_partkey` | 200 | 50 | 0.250 | 1.8 | 1 | False | 0.00 | True | 31 | 31 | +0 |
| `tpch-sf001.partsupp.ps_suppkey` | 200 | 100 | 0.500 | 1.9 | 2 | False | 0.11 | True | 681 | 681 | +0 |
| `tpch-sf001.orders.o_orderkey` | 200 | 200 | 1.000 | 2.8 | 2 | False | 0.11 | True | 267 | 267 | +0 |
| `tpch-sf001.orders.o_orderstatus` | 200 | 3 | 0.015 | 1.0 | 0 | True | 0.00 | False | 463 | 463 | +0 |
| `tpch-sf001.orders.o_orderpriority` | 200 | 5 | 0.025 | 8.1 | 10 | False | 0.00 | False | 620 | 620 | +0 |
| `tpch-sf001.orders.o_shippriority` | 200 | 1 | 0.005 | 1.0 | 0 | True | 0.00 | True | 15 | 15 | +0 |
| `tpch-sf001.lineitem.l_orderkey` | 200 | 50 | 0.250 | 2.4 | 2 | False | 0.11 | True | 326 | 326 | +0 |
| `tpch-sf001.lineitem.l_suppkey` | 200 | 88 | 0.440 | 1.9 | 2 | False | 0.11 | True | 839 | 839 | +0 |
| `tpch-sf001.lineitem.l_linenumber` | 200 | 7 | 0.035 | 1.0 | 0 | True | 0.00 | True | 594 | 594 | +0 |
| `tpch-sf001.lineitem.l_tax` | 200 | 9 | 0.045 | 3.9 | 1 | False | 0.81 | False | 613 | 613 | +0 |
| `tpch-sf001.lineitem.l_returnflag` | 200 | 3 | 0.015 | 1.0 | 0 | True | 0.00 | False | 329 | 329 | +0 |
| `tpch-sf001.lineitem.l_linestatus` | 200 | 2 | 0.010 | 1.0 | 0 | True | 0.00 | False | 175 | 175 | +0 |
| `tpch-sf001.lineitem.l_shipinstruct` | 200 | 4 | 0.020 | 11.5 | 13 | False | 0.02 | False | 590 | 590 | +0 |
| `tpch-sf001.lineitem.l_shipmode` | 200 | 7 | 0.035 | 4.3 | 4 | False | 0.17 | False | 603 | 605 | +2 |

## Patterns observados

- HELP avg cardinality: 0.905
- HELP avg LCP+LCS ratio: 0.336
- HELP uniform_length frac: 0.33
- HELP numeric frac: 0.33
- HURT avg cardinality: 0.723
- HURT avg LCP+LCS ratio: 0.224
- HURT uniform_length frac: 0.27
- HURT numeric frac: 0.00

(analise visual + pattern detection: ver result.md)
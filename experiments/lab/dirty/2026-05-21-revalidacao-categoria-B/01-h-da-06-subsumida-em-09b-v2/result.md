# Sub-exp 01 — H-DA-06 inspecao subsumida em H-DA-09b-v2

## Pergunta

H-DA-09b-v2 (numeric+high-cardinality, welded ADR-0008) ja' captura
colunas-alvo de H-DA-06 (numeric IDs sequenciais) em real-world?

## Tabela completa

| Source | Col | n_rows | avg_len | num? | card | hit | rule |
|---|---|---:|---:|---|---:|---|---|
| D16a-ids-3digits | val | 13 | 3.0 | Y | 1.0 | ✓ | 2-numeric-high-cardinality |
| D16b-ids-4digits | val | 13 | 4.0 | Y | 1.0 | ✓ | 1-uniform-length-high-lcp-lcs |
| D16c-ids-prefixados | val | 13 | 7.0 | n | 1.0 | ✓ | 1-uniform-length-high-lcp-lcs |
| adult-1000 | age | 1000 | 2.0 | Y | 0.062 | · | - |
| adult-1000 | workclass | 1000 | 7.9 | n | 0.007 | · | - |
| adult-1000 | fnlwgt | 1000 | 5.8 | Y | 0.979 | ✓ | 2-numeric-high-cardinality |
| adult-1000 | education | 1000 | 8.4 | n | 0.016 | · | - |
| adult-1000 | education-num | 1000 | 1.5 | Y | 0.016 | · | - |
| adult-1000 | marital-status | 1000 | 14.7 | n | 0.007 | · | - |
| adult-1000 | occupation | 1000 | 12.4 | n | 0.015 | · | - |
| adult-1000 | relationship | 1000 | 9.0 | n | 0.006 | · | - |
| adult-1000 | race | 1000 | 5.5 | n | 0.005 | · | - |
| adult-1000 | sex | 1000 | 4.6 | n | 0.002 | · | - |
| adult-1000 | capital-gain | 1000 | 1.3 | Y | 0.043 | · | - |
| adult-1000 | capital-loss | 1000 | 1.1 | Y | 0.024 | ✓ | 1-uniform-length-high-lcp-lcs |
| adult-1000 | hours-per-week | 1000 | 2.0 | Y | 0.056 | · | - |
| adult-1000 | native-country | 1000 | 12.4 | n | 0.028 | ✓ | 1-uniform-length-high-lcp-lcs |
| adult-1000 | class | 1000 | 4.8 | n | 0.002 | · | - |
| adult-5000 | age | 5000 | 2.0 | Y | 0.014 | · | - |
| adult-5000 | workclass | 5000 | 7.8 | n | 0.002 | · | - |
| adult-5000 | fnlwgt | 5000 | 5.8 | Y | 0.922 | ✓ | 2-numeric-high-cardinality |
| adult-5000 | education | 5000 | 8.4 | n | 0.003 | · | - |
| adult-5000 | education-num | 5000 | 1.5 | Y | 0.003 | · | - |
| adult-5000 | marital-status | 5000 | 14.3 | n | 0.001 | · | - |
| adult-5000 | occupation | 5000 | 12.1 | n | 0.003 | · | - |
| adult-5000 | relationship | 5000 | 9.2 | n | 0.001 | · | - |
| adult-5000 | race | 5000 | 5.5 | n | 0.001 | · | - |
| adult-5000 | sex | 5000 | 4.7 | n | 0.0 | · | - |
| adult-5000 | capital-gain | 5000 | 1.3 | Y | 0.017 | · | - |
| adult-5000 | capital-loss | 5000 | 1.1 | Y | 0.011 | ✓ | 1-uniform-length-high-lcp-lcs |
| adult-5000 | hours-per-week | 5000 | 2.0 | Y | 0.016 | · | - |
| adult-5000 | native-country | 5000 | 12.3 | n | 0.008 | ✓ | 1-uniform-length-high-lcp-lcs |
| adult-5000 | class | 5000 | 4.8 | n | 0.0 | · | - |
| tpch.region-5k | r_regionkey | 5 | 1.0 | Y | 1.0 | ✓ | 2-numeric-high-cardinality |
| tpch.region-5k | r_name | 5 | 6.8 | n | 1.0 | · | - |
| tpch.region-5k | r_comment | 5 | 66.0 | n | 1.0 | · | - |
| tpch.customer-5k | c_custkey | 1500 | 3.3 | Y | 1.0 | ✓ | 2-numeric-high-cardinality |
| tpch.customer-5k | c_name | 1500 | 18.0 | n | 1.0 | ✓ | 1-uniform-length-high-lcp-lcs |
| tpch.customer-5k | c_address | 1500 | 24.7 | n | 1.0 | · | - |
| tpch.customer-5k | c_nationkey | 1500 | 1.6 | Y | 0.017 | · | - |
| tpch.customer-5k | c_phone | 1500 | 15.0 | n | 1.0 | · | - |
| tpch.customer-5k | c_acctbal | 1500 | 6.8 | Y | 0.999 | ✓ | 2-numeric-high-cardinality |
| tpch.customer-5k | c_mktsegment | 1500 | 9.0 | n | 0.003 | · | - |
| tpch.customer-5k | c_comment | 1500 | 73.2 | n | 1.0 | · | - |
| tpch.lineitem-5k | l_orderkey | 5000 | 3.8 | Y | 0.248 | ✓ | 1-uniform-length-high-lcp-lcs |
| tpch.lineitem-5k | l_partkey | 5000 | 3.5 | Y | 0.366 | · | - |
| tpch.lineitem-5k | l_suppkey | 5000 | 1.9 | Y | 0.02 | · | - |
| tpch.lineitem-5k | l_linenumber | 5000 | 1.0 | Y | 0.001 | · | - |
| tpch.lineitem-5k | l_quantity | 5000 | 3.8 | Y | 0.01 | · | - |
| tpch.lineitem-5k | l_extendedprice | 5000 | 7.6 | Y | 0.954 | ✓ | 2-numeric-high-cardinality |
| tpch.lineitem-5k | l_discount | 5000 | 3.8 | Y | 0.002 | · | - |
| tpch.lineitem-5k | l_tax | 5000 | 3.9 | Y | 0.002 | ✓ | 1-uniform-length-high-lcp-lcs |
| tpch.lineitem-5k | l_returnflag | 5000 | 1.0 | n | 0.001 | ✓ | 1-uniform-length-high-lcp-lcs |
| tpch.lineitem-5k | l_linestatus | 5000 | 1.0 | n | 0.0 | ✓ | 1-uniform-length-high-lcp-lcs |
| tpch.lineitem-5k | l_shipdate | 5000 | 10.0 | n | 0.432 | · | - |
| tpch.lineitem-5k | l_commitdate | 5000 | 10.0 | n | 0.418 | · | - |
| tpch.lineitem-5k | l_receiptdate | 5000 | 10.0 | n | 0.427 | · | - |
| tpch.lineitem-5k | l_shipinstruct | 5000 | 12.0 | n | 0.001 | · | - |
| tpch.lineitem-5k | l_shipmode | 5000 | 4.3 | n | 0.001 | · | - |
| tpch.lineitem-5k | l_comment | 5000 | 26.6 | n | 0.997 | · | - |

## Analise

- Total colunas numericas: **26**
- Disparam regra 2 (H-DA-09b-v2): **7**
- Disparam alguma regra: **12**
- Cobertura sobre numeric+high-card (>0.5): **7/8 (87.5%)**

### Numericas que NAO disparam (casos H-DA-06 potenciais)

| Col | card | reason |
|---|---:|---|
| adult-1000/age | 0.062 | nenhuma regra acionou |
| adult-1000/education-num | 0.016 | nenhuma regra acionou |
| adult-1000/capital-gain | 0.043 | nenhuma regra acionou |
| adult-1000/hours-per-week | 0.056 | nenhuma regra acionou |
| adult-5000/age | 0.014 | nenhuma regra acionou |
| adult-5000/education-num | 0.003 | nenhuma regra acionou |
| adult-5000/capital-gain | 0.017 | nenhuma regra acionou |
| adult-5000/hours-per-week | 0.016 | nenhuma regra acionou |
| tpch.customer-5k/c_nationkey | 0.017 | nenhuma regra acionou |
| tpch.lineitem-5k/l_partkey | 0.366 | nenhuma regra acionou |
| tpch.lineitem-5k/l_suppkey | 0.02 | nenhuma regra acionou |
| tpch.lineitem-5k/l_linenumber | 0.001 | nenhuma regra acionou |
| tpch.lineitem-5k/l_quantity | 0.01 | nenhuma regra acionou |
| tpch.lineitem-5k/l_discount | 0.002 | nenhuma regra acionou |

## Veredito

**Cobertura**: 87.5%

**SUBSUMIDA — H-DA-09b-v2 ja' captura caso de H-DA-06 em real-world**

**Status sugerido roadmap H-DA-06**: `subsumida em H-DA-09b-v2 (welded ADR-0008)`


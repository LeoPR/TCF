# Sub-exp 02 — H-DA-01 HCC seq-RLE real-world

## Pergunta

HCC seq-RLE near-identical (`*N+delta|template`) isolado da' quanto
em Adult Census + TPC-H comparado aos -22.2% em D11a-h sinteticos?

## Tabela por coluna

| Source | Col | n_rows | base (B) | treat (B) | delta | pct | RT |
|---|---|---:|---:|---:|---:|---:|---|
| sintetico | D11a-datas-dia/val | 12 | 87 | 84 | -3 | -3.45% | OK |
| sintetico | D11b-datas-borda/val | 14 | 173 | 173 | +0 | +0.00% | OK |
| sintetico | D11c-datas-mensal/val | 13 | 109 | 78 | -31 | -28.44% | OK |
| sintetico | D11d-datetime-min/val | 13 | 110 | 73 | -37 | -33.64% | OK |
| sintetico | D11e-datetime-mensal/val | 13 | 121 | 90 | -31 | -25.62% | OK |
| sintetico | D11f-datetime-ms/val | 13 | 115 | 78 | -37 | -32.17% | OK |
| sintetico | D11g-datetime-us/val | 13 | 120 | 83 | -37 | -30.83% | OK |
| sintetico | D11h-datetime-ns/val | 13 | 123 | 86 | -37 | -30.08% | OK |
| realworld | adult-1000/age | 1000 | 3,796 | 3,823 | +27 | +0.71% | OK |
| realworld | adult-1000/workclass | 1000 | 2,178 | 2,178 | +0 | +0.00% | OK |
| realworld | adult-1000/fnlwgt | 1000 | 9,042 | 9,048 | +6 | +0.07% | OK |
| realworld | adult-1000/education | 1000 | 3,029 | 3,029 | +0 | +0.00% | OK |
| realworld | adult-1000/education-num | 1000 | 2,947 | 2,949 | +2 | +0.07% | OK |
| realworld | adult-1000/marital-status | 1000 | 2,599 | 2,599 | +0 | +0.00% | OK |
| realworld | adult-1000/occupation | 1000 | 3,352 | 3,352 | +0 | +0.00% | OK |
| realworld | adult-1000/relationship | 1000 | 2,726 | 2,726 | +0 | +0.00% | OK |
| realworld | adult-1000/race | 1000 | 1,174 | 1,174 | +0 | +0.00% | OK |
| realworld | adult-1000/sex | 1000 | 1,871 | 1,871 | +0 | +0.00% | OK |
| realworld | adult-1000/capital-gain | 1000 | 1,057 | 1,059 | +2 | +0.19% | OK |
| realworld | adult-1000/capital-loss | 1000 | 508 | 508 | +0 | +0.00% | OK |
| realworld | adult-1000/hours-per-week | 1000 | 2,976 | 2,985 | +9 | +0.30% | OK |
| realworld | adult-1000/native-country | 1000 | 960 | 960 | +0 | +0.00% | OK |
| realworld | adult-1000/class | 1000 | 1,704 | 1,704 | +0 | +0.00% | OK |
| realworld | adult-5000/age | 5000 | 18,899 | 18,926 | +27 | +0.14% | OK |
| realworld | adult-5000/workclass | 5000 | 10,341 | 10,341 | +0 | +0.00% | OK |
| realworld | adult-5000/fnlwgt | 5000 | 60,457 | 60,457 | +0 | +0.00% | OK |
| realworld | adult-5000/education | 5000 | 14,887 | 14,887 | +0 | +0.00% | OK |
| realworld | adult-5000/education-num | 5000 | 14,805 | 14,807 | +2 | +0.01% | OK |
| realworld | adult-5000/marital-status | 5000 | 13,247 | 13,247 | +0 | +0.00% | OK |
| realworld | adult-5000/occupation | 5000 | 16,127 | 16,127 | +0 | +0.00% | OK |
| realworld | adult-5000/relationship | 5000 | 13,814 | 13,814 | +0 | +0.00% | OK |
| realworld | adult-5000/race | 5000 | 5,796 | 5,796 | +0 | +0.00% | OK |
| realworld | adult-5000/sex | 5000 | 10,012 | 10,012 | +0 | +0.00% | OK |
| realworld | adult-5000/capital-gain | 5000 | 4,104 | 4,106 | +2 | +0.05% | OK |
| realworld | adult-5000/capital-loss | 5000 | 2,409 | 2,409 | +0 | +0.00% | OK |
| realworld | adult-5000/hours-per-week | 5000 | 15,043 | 15,052 | +9 | +0.06% | OK |
| realworld | adult-5000/native-country | 5000 | 4,667 | 4,667 | +0 | +0.00% | OK |
| realworld | adult-5000/class | 5000 | 8,229 | 8,229 | +0 | +0.00% | OK |
| realworld | tpch.region-5k/r_regionkey | 5 | 15 | 8 | -7 | -46.67% | OK |
| realworld | tpch.region-5k/r_name | 5 | 37 | 37 | +0 | +0.00% | OK |
| realworld | tpch.region-5k/r_comment | 5 | 335 | 335 | +0 | +0.00% | OK |
| realworld | tpch.customer-5k/c_custkey | 1500 | 7,893 | 636 | -7257 | -91.94% | OK |
| realworld | tpch.customer-5k/c_name | 1500 | 14,117 | 7,880 | -6237 | -44.18% | OK |
| realworld | tpch.customer-5k/c_address | 1500 | 43,416 | 43,416 | +0 | +0.00% | OK |
| realworld | tpch.customer-5k/c_nationkey | 1500 | 5,394 | 5,403 | +9 | +0.17% | OK |
| realworld | tpch.customer-5k/c_phone | 1500 | 33,836 | 33,836 | +0 | +0.00% | OK |
| realworld | tpch.customer-5k/c_acctbal | 1500 | 17,326 | 17,326 | +0 | +0.00% | OK |
| realworld | tpch.customer-5k/c_mktsegment | 1500 | 4,367 | 4,367 | +0 | +0.00% | OK |
| realworld | tpch.customer-5k/c_comment | 1500 | 108,461 | 108,461 | +0 | +0.00% | OK |
| realworld | tpch.lineitem-5k/l_orderkey | 5000 | 11,021 | 10,565 | -456 | -4.14% | OK |
| realworld | tpch.lineitem-5k/l_partkey | 5000 | 28,134 | 28,223 | +89 | +0.32% | OK |
| realworld | tpch.lineitem-5k/l_suppkey | 5000 | 19,553 | 19,606 | +53 | +0.27% | OK |
| realworld | tpch.lineitem-5k/l_linenumber | 5000 | 14,916 | 14,906 | -10 | -0.07% | OK |
| realworld | tpch.lineitem-5k/l_quantity | 5000 | 19,120 | 19,120 | +0 | +0.00% | OK |
| realworld | tpch.lineitem-5k/l_extendedprice | 5000 | 71,446 | 71,446 | +0 | +0.00% | OK |
| realworld | tpch.lineitem-5k/l_discount | 5000 | 15,748 | 15,749 | +1 | +0.01% | OK |
| realworld | tpch.lineitem-5k/l_tax | 5000 | 14,826 | 14,826 | +0 | +0.00% | OK |
| realworld | tpch.lineitem-5k/l_returnflag | 5000 | 8,075 | 8,075 | +0 | +0.00% | OK |
| realworld | tpch.lineitem-5k/l_linestatus | 5000 | 4,137 | 4,137 | +0 | +0.00% | OK |
| realworld | tpch.lineitem-5k/l_shipdate | 5000 | 41,249 | 41,240 | -9 | -0.02% | OK |
| realworld | tpch.lineitem-5k/l_commitdate | 5000 | 40,023 | 40,010 | -13 | -0.03% | OK |
| realworld | tpch.lineitem-5k/l_receiptdate | 5000 | 40,013 | 40,013 | +0 | +0.00% | OK |
| realworld | tpch.lineitem-5k/l_shipinstruct | 5000 | 14,071 | 14,071 | +0 | +0.00% | OK |
| realworld | tpch.lineitem-5k/l_shipmode | 5000 | 14,645 | 14,645 | +0 | +0.00% | OK |
| realworld | tpch.lineitem-5k/l_comment | 5000 | 163,073 | 163,073 | +0 | +0.00% | OK |

## Agregado

| Cohort | base (B) | treat (B) | delta | pct |
|---|---:|---:|---:|---:|
| Sintetico D11a-h | 958 | 745 | -213 | -22.23% |
| Real-world | 1,008,003 | 994,252 | -13751 | -1.36% |

## Comparacao sintetico vs real

- Sintetico: 22.23% ganho
- Real-world: 1.36% ganho
- **Reducao**: 16.3x menor em real-world

## Veredito

**MARGINAL real-world: ganho 1-5%**

**Status sugerido roadmap H-DA-01**: `A-revalidar (marginal real-world)`

## Notas metodologicas

- Baseline e' M8AVirtualRefsSyntax canonical (com `*N|linha` RLE puro
  para linhas IDENTICAS adjacentes — feature standard).
- Tratamento e' HCCSeqRLE (extends M8A com `*N+delta|template` para
  linhas NEAR-IDENTICAL via escape-digit shifts).
- A diferenca isola EXATAMENTE o ganho do near-identical detector.


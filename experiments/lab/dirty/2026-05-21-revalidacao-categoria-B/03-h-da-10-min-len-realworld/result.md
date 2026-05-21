# Sub-exp 03 — H-DA-10 min_len trade-off real-world

## Pergunta

Em Adult Census + TPC-H, algum min_len != 3 (default)
da' ganho >= 2.0% em pelo menos 3 colunas?

## Tabela completa (bytes por min_len)

| Source | Col | ml=2 | ml=3 | ml=4 | ml=5 | ml=6 | best |
|---|---|---:|---:|---:|---:|---:|---:|
| sintetico | D9-frequencia-alta/val | 158 | 158 | 150 | 174 | 174 | **ml=4** |
| realworld | adult-1000/age | 3,796 | 3,796 | 3,796 | 3,796 | 3,796 | **ml=2** |
| realworld | adult-1000/workclass | 2,178 | 2,178 | 2,178 | 2,178 | 2,178 | **ml=2** |
| realworld | adult-1000/fnlwgt | 9,439 | 9,042 | 8,043 | 7,751 | 7,757 | **ml=5** |
| realworld | adult-1000/education | 3,029 | 3,029 | 3,029 | 3,029 | 3,029 | **ml=2** |
| realworld | adult-1000/education-num | 2,947 | 2,947 | 2,947 | 2,947 | 2,947 | **ml=2** |
| realworld | adult-1000/marital-status | 2,599 | 2,599 | 2,599 | 2,599 | 2,599 | **ml=2** |
| realworld | adult-1000/occupation | 3,352 | 3,352 | 3,354 | 3,354 | 3,354 | **ml=2** |
| realworld | adult-1000/relationship | 2,726 | 2,726 | 2,726 | 2,726 | 2,726 | **ml=2** |
| realworld | adult-1000/race | 1,174 | 1,174 | 1,174 | 1,174 | 1,174 | **ml=2** |
| realworld | adult-1000/sex | 1,871 | 1,871 | 1,872 | 1,872 | 1,872 | **ml=2** |
| realworld | adult-1000/capital-gain | 1,057 | 1,057 | 1,050 | 1,050 | 1,050 | **ml=4** |
| realworld | adult-1000/capital-loss | 508 | 508 | 507 | 507 | 507 | **ml=4** |
| realworld | adult-1000/hours-per-week | 2,976 | 2,976 | 2,976 | 2,976 | 2,976 | **ml=2** |
| realworld | adult-1000/native-country | 960 | 960 | 961 | 969 | 969 | **ml=2** |
| realworld | adult-1000/class | 1,704 | 1,704 | 1,706 | 1,706 | 1,706 | **ml=2** |
| realworld | adult-5000/age | 18,899 | 18,899 | 18,899 | 18,899 | 18,899 | **ml=2** |
| realworld | adult-5000/workclass | 10,341 | 10,341 | 10,341 | 10,341 | 10,341 | **ml=2** |
| realworld | adult-5000/fnlwgt | 66,388 | 60,457 | 45,847 | 38,457 | 38,219 | **ml=6** |
| realworld | adult-5000/education | 14,887 | 14,887 | 14,887 | 14,887 | 14,887 | **ml=2** |
| realworld | adult-5000/education-num | 14,805 | 14,805 | 14,805 | 14,805 | 14,805 | **ml=2** |
| realworld | adult-5000/marital-status | 13,247 | 13,247 | 13,247 | 13,247 | 13,247 | **ml=2** |
| realworld | adult-5000/occupation | 16,127 | 16,127 | 16,129 | 16,129 | 16,129 | **ml=2** |
| realworld | adult-5000/relationship | 13,814 | 13,814 | 13,814 | 13,814 | 13,814 | **ml=2** |
| realworld | adult-5000/race | 5,796 | 5,796 | 5,796 | 5,796 | 5,796 | **ml=2** |
| realworld | adult-5000/sex | 10,012 | 10,012 | 10,013 | 10,013 | 10,013 | **ml=2** |
| realworld | adult-5000/capital-gain | 4,104 | 4,104 | 4,084 | 4,085 | 4,085 | **ml=4** |
| realworld | adult-5000/capital-loss | 2,409 | 2,409 | 2,401 | 2,401 | 2,401 | **ml=4** |
| realworld | adult-5000/hours-per-week | 15,043 | 15,043 | 15,043 | 15,043 | 15,043 | **ml=2** |
| realworld | adult-5000/native-country | 4,667 | 4,667 | 4,668 | 4,680 | 4,680 | **ml=2** |
| realworld | adult-5000/class | 8,229 | 8,229 | 8,231 | 8,231 | 8,231 | **ml=2** |
| realworld | tpch.region-5k/r_regionkey | 15 | 15 | 15 | 15 | 15 | **ml=2** |
| realworld | tpch.region-5k/r_name | 37 | 37 | 37 | 39 | 39 | **ml=2** |
| realworld | tpch.region-5k/r_comment | 335 | 335 | 335 | 335 | 335 | **ml=2** |
| realworld | tpch.customer-5k/c_custkey | 7,893 | 7,893 | 7,893 | 7,893 | 7,893 | **ml=2** |
| realworld | tpch.customer-5k/c_name | 14,160 | 14,117 | 13,358 | 13,358 | 13,358 | **ml=4** |
| realworld | tpch.customer-5k/c_address | 43,416 | 43,416 | 43,408 | 43,408 | 43,408 | **ml=4** |
| realworld | tpch.customer-5k/c_nationkey | 5,394 | 5,394 | 5,394 | 5,394 | 5,394 | **ml=2** |
| realworld | tpch.customer-5k/c_phone | 33,836 | 33,836 | 29,354 | 29,281 | 29,687 | **ml=5** |
| realworld | tpch.customer-5k/c_acctbal | 18,571 | 17,326 | 15,741 | 14,591 | 14,658 | **ml=5** |
| realworld | tpch.customer-5k/c_mktsegment | 4,367 | 4,367 | 4,367 | 4,367 | 4,367 | **ml=2** |
| realworld | tpch.customer-5k/c_comment | 108,461 | 108,461 | 106,498 | 105,646 | 105,151 | **ml=6** |
| realworld | tpch.lineitem-5k/l_orderkey | 11,021 | 11,021 | 10,373 | 10,373 | 10,373 | **ml=4** |
| realworld | tpch.lineitem-5k/l_partkey | 28,134 | 28,134 | 26,549 | 26,549 | 26,549 | **ml=4** |
| realworld | tpch.lineitem-5k/l_suppkey | 19,553 | 19,553 | 19,553 | 19,553 | 19,553 | **ml=2** |
| realworld | tpch.lineitem-5k/l_linenumber | 14,916 | 14,916 | 14,916 | 14,916 | 14,916 | **ml=2** |
| realworld | tpch.lineitem-5k/l_quantity | 19,120 | 19,120 | 19,174 | 19,174 | 19,174 | **ml=2** |
| realworld | tpch.lineitem-5k/l_extendedprice | 76,825 | 71,446 | 61,038 | 52,348 | 51,408 | **ml=6** |
| realworld | tpch.lineitem-5k/l_discount | 15,748 | 15,748 | 15,774 | 15,774 | 15,774 | **ml=2** |
| realworld | tpch.lineitem-5k/l_tax | 14,826 | 14,826 | 14,849 | 14,849 | 14,849 | **ml=2** |
| realworld | tpch.lineitem-5k/l_returnflag | 8,075 | 8,075 | 8,075 | 8,075 | 8,075 | **ml=2** |
| realworld | tpch.lineitem-5k/l_linestatus | 4,137 | 4,137 | 4,137 | 4,137 | 4,137 | **ml=2** |
| realworld | tpch.lineitem-5k/l_shipdate | 43,682 | 41,249 | 42,286 | 36,715 | 36,201 | **ml=6** |
| realworld | tpch.lineitem-5k/l_commitdate | 43,713 | 40,023 | 41,010 | 36,161 | 35,779 | **ml=6** |
| realworld | tpch.lineitem-5k/l_receiptdate | 44,433 | 40,013 | 41,910 | 36,626 | 36,139 | **ml=6** |
| realworld | tpch.lineitem-5k/l_shipinstruct | 14,071 | 14,071 | 14,071 | 14,071 | 14,071 | **ml=2** |
| realworld | tpch.lineitem-5k/l_shipmode | 14,645 | 14,645 | 14,647 | 14,647 | 14,647 | **ml=2** |
| realworld | tpch.lineitem-5k/l_comment | 163,994 | 163,073 | 149,944 | 140,795 | 133,426 | **ml=6** |

## Colunas que preferem min_len != 3 com ganho relevante

Threshold: ganho >= 2.0% vs default min_len=3

| Col | best_ml | default (B) | best (B) | gain |
|---|---:|---:|---:|---:|
| D9-frequencia-alta/val | 4 | 158 | 150 | 5.06% |
| adult-1000/fnlwgt | 5 | 9,042 | 7,751 | 14.28% |
| adult-5000/fnlwgt | 6 | 60,457 | 38,219 | 36.78% |
| tpch.customer-5k/c_name | 4 | 14,117 | 13,358 | 5.38% |
| tpch.customer-5k/c_phone | 5 | 33,836 | 29,281 | 13.46% |
| tpch.customer-5k/c_acctbal | 5 | 17,326 | 14,591 | 15.79% |
| tpch.customer-5k/c_comment | 6 | 108,461 | 105,151 | 3.05% |
| tpch.lineitem-5k/l_orderkey | 4 | 11,021 | 10,373 | 5.88% |
| tpch.lineitem-5k/l_partkey | 4 | 28,134 | 26,549 | 5.63% |
| tpch.lineitem-5k/l_extendedprice | 6 | 71,446 | 51,408 | 28.05% |
| tpch.lineitem-5k/l_shipdate | 6 | 41,249 | 36,201 | 12.24% |
| tpch.lineitem-5k/l_commitdate | 6 | 40,023 | 35,779 | 10.60% |
| tpch.lineitem-5k/l_receiptdate | 6 | 40,013 | 36,139 | 9.68% |
| tpch.lineitem-5k/l_comment | 6 | 163,073 | 133,426 | 18.18% |

## Agregado

- Total colunas testadas: **58**
- Colunas com ganho relevante (!= 3, >= 2.0%): **14**
- Bytes economizados (best vs default, weighted): **100,024 / 1,008,161 = 9.92%**

## Veredito

**CONFIRMADA real-world: 14 colunas com ganho >= 2.0% (mas marginais)**

**Status sugerido roadmap H-DA-10**: `confirmada-empirica real-world marginal`

## Notas metodologicas

- min_len controla tamanho minimo de prefix/suffix em OBAT
- Default = 3 (decisao M0 fase exploratoria)
- H-DA-10 original: D9 sintetico mostrou min_len=5 da -33B (N=3 datasets, N=4 valores)
- Real-world: testa generalizacao do trade-off


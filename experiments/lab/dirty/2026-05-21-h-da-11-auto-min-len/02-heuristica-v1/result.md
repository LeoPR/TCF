# Sub-exp 02 — H-DA-11 heuristica auto-min_len

## Estrategias

- **ORACLE**: best per column (upper bound real)
- **DEFAULT**: ml=3 sempre (baseline)
- **HEUR v1**: thresholds em avg_len: >=25→6, >=15→5, >=8→4, else→3
- **HEUR v2**: card + avg_len + is_numeric:
    - card<0.2 → 3 (low-card seguro)
    - card>0.2: usa avg_len + numeric pra decidir ml ∈ {4,5,6}

## Tabela completa

| col | avg | card | num | oracle | v1 | v2 | v3 | gain v3 |
|---|---:|---:|---|---:|---:|---:|---:|---:|
| sintetico/D9-frequencia-alta/val | 17.6 | 1.00 | n | **4** | 5 | 6 | 6 | -10.13% |
| adult-1000/age | 2.0 | 0.06 | Y | **2** | 3 | 3 | 3 | +0.00% |
| adult-1000/workclass | 7.9 | 0.01 | n | **2** | 3 | 3 | 3 | +0.00% |
| adult-1000/fnlwgt | 5.8 | 0.98 | Y | **5** | 3 | 4 | 6 | +14.21% |
| adult-1000/education | 8.4 | 0.02 | n | **2** | 4 | 3 | 3 | +0.00% |
| adult-1000/education-num | 1.5 | 0.02 | Y | **2** | 3 | 3 | 3 | +0.00% |
| adult-1000/marital-status | 14.7 | 0.01 | n | **2** | 4 | 3 | 3 | +0.00% |
| adult-1000/occupation | 12.4 | 0.01 | n | **2** | 4 | 3 | 3 | +0.00% |
| adult-1000/relationship | 9.0 | 0.01 | n | **2** | 4 | 3 | 3 | +0.00% |
| adult-1000/race | 5.5 | 0.01 | n | **2** | 3 | 3 | 3 | +0.00% |
| adult-1000/sex | 4.6 | 0.00 | n | **2** | 3 | 3 | 3 | +0.00% |
| adult-1000/capital-gain | 1.3 | 0.04 | Y | **4** | 3 | 3 | 3 | +0.00% |
| adult-1000/capital-loss | 1.1 | 0.02 | Y | **4** | 3 | 3 | 3 | +0.00% |
| adult-1000/hours-per-week | 2.0 | 0.06 | Y | **2** | 3 | 3 | 3 | +0.00% |
| adult-1000/native-country | 12.4 | 0.03 | n | **2** | 4 | 3 | 3 | +0.00% |
| adult-1000/class | 4.8 | 0.00 | n | **2** | 3 | 3 | 3 | +0.00% |
| adult-5000/age | 2.0 | 0.01 | Y | **2** | 3 | 3 | 3 | +0.00% |
| adult-5000/workclass | 7.8 | 0.00 | n | **2** | 3 | 3 | 3 | +0.00% |
| adult-5000/fnlwgt | 5.8 | 0.92 | Y | **6** | 3 | 4 | 6✓ | +36.78% |
| adult-5000/education | 8.4 | 0.00 | n | **2** | 4 | 3 | 3 | +0.00% |
| adult-5000/education-num | 1.5 | 0.00 | Y | **2** | 3 | 3 | 3 | +0.00% |
| adult-5000/marital-status | 14.3 | 0.00 | n | **2** | 4 | 3 | 3 | +0.00% |
| adult-5000/occupation | 12.1 | 0.00 | n | **2** | 4 | 3 | 3 | +0.00% |
| adult-5000/relationship | 9.2 | 0.00 | n | **2** | 4 | 3 | 3 | +0.00% |
| adult-5000/race | 5.5 | 0.00 | n | **2** | 3 | 3 | 3 | +0.00% |
| adult-5000/sex | 4.7 | 0.00 | n | **2** | 3 | 3 | 3 | +0.00% |
| adult-5000/capital-gain | 1.3 | 0.02 | Y | **4** | 3 | 3 | 3 | +0.00% |
| adult-5000/capital-loss | 1.1 | 0.01 | Y | **4** | 3 | 3 | 3 | +0.00% |
| adult-5000/hours-per-week | 2.0 | 0.02 | Y | **2** | 3 | 3 | 3 | +0.00% |
| adult-5000/native-country | 12.3 | 0.01 | n | **2** | 4 | 3 | 3 | +0.00% |
| adult-5000/class | 4.8 | 0.00 | n | **2** | 3 | 3 | 3 | +0.00% |
| tpch.region-5k/r_regionkey | 1.0 | 1.00 | Y | **2** | 3 | 3 | 3 | +0.00% |
| tpch.region-5k/r_name | 6.8 | 1.00 | n | **2** | 3 | 5 | 4 | +0.00% |
| tpch.region-5k/r_comment | 66.0 | 1.00 | n | **2** | 6 | 6 | 6 | +0.00% |
| tpch.customer-5k/c_custkey | 3.3 | 1.00 | Y | **2** | 3 | 4 | 4 | +0.00% |
| tpch.customer-5k/c_name | 18.0 | 1.00 | n | **4** | 5 | 6 | 6 | +5.38% |
| tpch.customer-5k/c_address | 24.7 | 1.00 | n | **4** | 5 | 6 | 6 | +0.02% |
| tpch.customer-5k/c_nationkey | 1.6 | 0.02 | Y | **2** | 3 | 3 | 3 | +0.00% |
| tpch.customer-5k/c_phone | 15.0 | 1.00 | n | **5** | 5✓ | 6 | 6 | +12.26% |
| tpch.customer-5k/c_acctbal | 6.8 | 1.00 | Y | **5** | 3 | 6 | 6 | +15.40% |
| tpch.customer-5k/c_mktsegment | 9.0 | 0.00 | n | **2** | 4 | 3 | 3 | +0.00% |
| tpch.customer-5k/c_comment | 73.2 | 1.00 | n | **6** | 6✓ | 6✓ | 6✓ | +3.05% |
| tpch.lineitem-5k/l_orderkey | 3.8 | 0.25 | Y | **4** | 3 | 4✓ | 4✓ | +5.88% |
| tpch.lineitem-5k/l_partkey | 3.5 | 0.37 | Y | **4** | 3 | 4✓ | 4✓ | +5.63% |
| tpch.lineitem-5k/l_suppkey | 1.9 | 0.02 | Y | **2** | 3 | 3 | 3 | +0.00% |
| tpch.lineitem-5k/l_linenumber | 1.0 | 0.00 | Y | **2** | 3 | 3 | 3 | +0.00% |
| tpch.lineitem-5k/l_quantity | 3.8 | 0.01 | Y | **2** | 3 | 3 | 3 | +0.00% |
| tpch.lineitem-5k/l_extendedprice | 7.6 | 0.95 | Y | **6** | 3 | 6✓ | 6✓ | +28.05% |
| tpch.lineitem-5k/l_discount | 3.8 | 0.00 | Y | **2** | 3 | 3 | 3 | +0.00% |
| tpch.lineitem-5k/l_tax | 3.9 | 0.00 | Y | **2** | 3 | 3 | 3 | +0.00% |
| tpch.lineitem-5k/l_returnflag | 1.0 | 0.00 | n | **2** | 3 | 3 | 3 | +0.00% |
| tpch.lineitem-5k/l_linestatus | 1.0 | 0.00 | n | **2** | 3 | 3 | 3 | +0.00% |
| tpch.lineitem-5k/l_shipdate | 10.0 | 0.43 | n | **6** | 4 | 4 | 6✓ | +12.24% |
| tpch.lineitem-5k/l_commitdate | 10.0 | 0.42 | n | **6** | 4 | 4 | 6✓ | +10.60% |
| tpch.lineitem-5k/l_receiptdate | 10.0 | 0.43 | n | **6** | 4 | 4 | 6✓ | +9.68% |
| tpch.lineitem-5k/l_shipinstruct | 12.0 | 0.00 | n | **2** | 4 | 3 | 3 | +0.00% |
| tpch.lineitem-5k/l_shipmode | 4.3 | 0.00 | n | **2** | 3 | 3 | 3 | +0.00% |
| tpch.lineitem-5k/l_comment | 26.6 | 1.00 | n | **6** | 6✓ | 6✓ | 6✓ | +18.18% |

## Agregados weighted

| Estrategia | bytes | gain | captura oracle |
|---|---:|---:|---:|
| default (ml=3) | 1,008,161 | 0.00% | — |
| **oracle** | 908,137 | **9.92%** | 100% (upper bound) |
| heur v1 | 973,825 | 3.41% | 34.3% |
| heur v2 | 933,679 | 7.39% | 74.5% |
| **heur v3** | 908,676 | **9.87%** | **99.5%** |

**Match best_ml = oracle**: v1=3, v2=5, v3=9 / 58
**Regressoes vs default**: v1=8, v2=5, v3=1

## Veredito

**CONFIRMADA: heuristica v3 captura 9.87% (>= 7% — candidato welding)**

**Status sugerido H-DA-11**: `confirmada-empirica real-world (candidato welding)`


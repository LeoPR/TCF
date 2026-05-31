# Sub-exp 01 — analise features H-DA-11

## Tabela features por coluna

| source | col | n_rows | avg_len | max_len | card | num | best_ml | gain |
|---|---|---:|---:|---:|---:|---|---:|---:|
| sintetico | D9-frequencia-alta/val | 20 | 17.6 | 18 | 1.000 | n | **4** | 5.06% |
| adult-1000 | age | 1000 | 2.0 | 2 | 0.062 | Y | **2** | 0.00% |
| adult-1000 | workclass | 1000 | 7.9 | 16 | 0.007 | n | **2** | 0.00% |
| adult-1000 | fnlwgt | 1000 | 5.8 | 6 | 0.979 | Y | **5** | 14.28% |
| adult-1000 | education | 1000 | 8.4 | 12 | 0.016 | n | **2** | 0.00% |
| adult-1000 | education-num | 1000 | 1.5 | 2 | 0.016 | Y | **2** | 0.00% |
| adult-1000 | marital-status | 1000 | 14.7 | 21 | 0.007 | n | **2** | 0.00% |
| adult-1000 | occupation | 1000 | 12.4 | 17 | 0.015 | n | **2** | 0.00% |
| adult-1000 | relationship | 1000 | 9.0 | 14 | 0.006 | n | **2** | 0.00% |
| adult-1000 | race | 1000 | 5.5 | 18 | 0.005 | n | **2** | 0.00% |
| adult-1000 | sex | 1000 | 4.6 | 6 | 0.002 | n | **2** | 0.00% |
| adult-1000 | capital-gain | 1000 | 1.3 | 5 | 0.043 | Y | **4** | 0.66% |
| adult-1000 | capital-loss | 1000 | 1.1 | 4 | 0.024 | Y | **4** | 0.20% |
| adult-1000 | hours-per-week | 1000 | 2.0 | 2 | 0.056 | Y | **2** | 0.00% |
| adult-1000 | native-country | 1000 | 12.4 | 18 | 0.028 | n | **2** | 0.00% |
| adult-1000 | class | 1000 | 4.8 | 5 | 0.002 | n | **2** | 0.00% |
| adult-5000 | age | 5000 | 2.0 | 2 | 0.014 | Y | **2** | 0.00% |
| adult-5000 | workclass | 5000 | 7.8 | 16 | 0.002 | n | **2** | 0.00% |
| adult-5000 | fnlwgt | 5000 | 5.8 | 7 | 0.922 | Y | **6** | 36.78% |
| adult-5000 | education | 5000 | 8.4 | 12 | 0.003 | n | **2** | 0.00% |
| adult-5000 | education-num | 5000 | 1.5 | 2 | 0.003 | Y | **2** | 0.00% |
| adult-5000 | marital-status | 5000 | 14.3 | 21 | 0.001 | n | **2** | 0.00% |
| adult-5000 | occupation | 5000 | 12.1 | 17 | 0.003 | n | **2** | 0.00% |
| adult-5000 | relationship | 5000 | 9.2 | 14 | 0.001 | n | **2** | 0.00% |
| adult-5000 | race | 5000 | 5.5 | 18 | 0.001 | n | **2** | 0.00% |
| adult-5000 | sex | 5000 | 4.7 | 6 | 0.000 | n | **2** | 0.00% |
| adult-5000 | capital-gain | 5000 | 1.3 | 5 | 0.017 | Y | **4** | 0.49% |
| adult-5000 | capital-loss | 5000 | 1.1 | 4 | 0.011 | Y | **4** | 0.33% |
| adult-5000 | hours-per-week | 5000 | 2.0 | 2 | 0.016 | Y | **2** | 0.00% |
| adult-5000 | native-country | 5000 | 12.3 | 26 | 0.008 | n | **2** | 0.00% |
| adult-5000 | class | 5000 | 4.8 | 5 | 0.000 | n | **2** | 0.00% |
| tpch.region-5k | r_regionkey | 5 | 1.0 | 1 | 1.000 | Y | **2** | 0.00% |
| tpch.region-5k | r_name | 5 | 6.8 | 11 | 1.000 | n | **2** | 0.00% |
| tpch.region-5k | r_comment | 5 | 66.0 | 115 | 1.000 | n | **2** | 0.00% |
| tpch.customer-5k | c_custkey | 1500 | 3.3 | 4 | 1.000 | Y | **2** | 0.00% |
| tpch.customer-5k | c_name | 1500 | 18.0 | 18 | 1.000 | n | **4** | 5.38% |
| tpch.customer-5k | c_address | 1500 | 24.7 | 40 | 1.000 | n | **4** | 0.02% |
| tpch.customer-5k | c_nationkey | 1500 | 1.6 | 2 | 0.017 | Y | **2** | 0.00% |
| tpch.customer-5k | c_phone | 1500 | 15.0 | 15 | 1.000 | n | **5** | 13.46% |
| tpch.customer-5k | c_acctbal | 1500 | 6.8 | 7 | 0.999 | Y | **5** | 15.79% |
| tpch.customer-5k | c_mktsegment | 1500 | 9.0 | 10 | 0.003 | n | **2** | 0.00% |
| tpch.customer-5k | c_comment | 1500 | 73.2 | 116 | 1.000 | n | **6** | 3.05% |
| tpch.lineitem-5k | l_orderkey | 5000 | 3.8 | 4 | 0.248 | Y | **4** | 5.88% |
| tpch.lineitem-5k | l_partkey | 5000 | 3.5 | 4 | 0.366 | Y | **4** | 5.63% |
| tpch.lineitem-5k | l_suppkey | 5000 | 1.9 | 3 | 0.020 | Y | **2** | 0.00% |
| tpch.lineitem-5k | l_linenumber | 5000 | 1.0 | 1 | 0.001 | Y | **2** | 0.00% |
| tpch.lineitem-5k | l_quantity | 5000 | 3.8 | 4 | 0.010 | Y | **2** | 0.00% |
| tpch.lineitem-5k | l_extendedprice | 5000 | 7.6 | 8 | 0.954 | Y | **6** | 28.05% |
| tpch.lineitem-5k | l_discount | 5000 | 3.8 | 4 | 0.002 | Y | **2** | 0.00% |
| tpch.lineitem-5k | l_tax | 5000 | 3.9 | 4 | 0.002 | Y | **2** | 0.00% |
| tpch.lineitem-5k | l_returnflag | 5000 | 1.0 | 1 | 0.001 | n | **2** | 0.00% |
| tpch.lineitem-5k | l_linestatus | 5000 | 1.0 | 1 | 0.000 | n | **2** | 0.00% |
| tpch.lineitem-5k | l_shipdate | 5000 | 10.0 | 10 | 0.432 | n | **6** | 12.24% |
| tpch.lineitem-5k | l_commitdate | 5000 | 10.0 | 10 | 0.418 | n | **6** | 10.60% |
| tpch.lineitem-5k | l_receiptdate | 5000 | 10.0 | 10 | 0.427 | n | **6** | 9.68% |
| tpch.lineitem-5k | l_shipinstruct | 5000 | 12.0 | 17 | 0.001 | n | **2** | 0.00% |
| tpch.lineitem-5k | l_shipmode | 5000 | 4.3 | 7 | 0.001 | n | **2** | 0.00% |
| tpch.lineitem-5k | l_comment | 5000 | 26.6 | 43 | 0.997 | n | **6** | 18.18% |

## Distribuicao best_ml por avg_len bucket

| Bucket | n | dist best_ml |
|---|---:|---|
| avg<8 | 36 | {2: 26, 4: 6, 5: 2, 6: 2} |
| 8<=avg<15 | 15 | {2: 12, 6: 3} |
| 15<=avg<30 | 5 | {4: 3, 5: 1, 6: 1} |
| avg>=30 | 2 | {2: 1, 6: 1} |

## Distribuicao por (is_numeric, cardinality)

| Grupo | n | dist best_ml |
|---|---:|---|
| numeric+highcard (>0.5) | 6 | {2: 2, 5: 2, 6: 2} |
| numeric+lowcard | 18 | {2: 12, 4: 6} |
| text+highcard | 8 | {2: 2, 4: 3, 5: 1, 6: 2} |
| text+lowcard | 26 | {2: 23, 6: 3} |

## Ganho oracle weighted

**9.92%** (100,024B / 1,008,161B baseline)

(reproduz 9.92% do sub-exp 03 da revalidacao-categoria-B, com adicao de D9 controle)

## Observacoes pra heuristica v1

Padrao geral: bucket de `avg_len` predice bem o best_ml.
Tabela acima orienta thresholds. Regra base candidata:

```
def detect_min_len(values):
    avg = sum(len(v) for v in values) / len(values)
    if avg >= 30: return 6
    if avg >= 15: return 5
    if avg >= 8:  return 4
    return 3  # default
```

Sub-exp 02 valida essa heuristica vs oracle.


# Sub-exp 01 — caracterizar low-card cols

## Setup

- Threshold low-card: cardinality < 0.05
- Total colunas testadas: 66
- Low-card cols: 37

## Estimativa enumerated (lower bound)

```
dict_bytes = sum(len(atom) for atom in unicas) + (N-1) seps
body_bytes = n_rows * digits_per_idx + (n_rows-1) seps
total = dict_bytes + body_bytes
```

Real encoder teria overhead extra (marker prefix etc.) —
isso e' LOWER BOUND teorico.

## Tabela low-card cols

| Source | Col | n_rows | n_uniq | card | M10 (B) | enum LB (B) | delta | gain |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| tpch.lineitem-5k | l_linenumber | 5000 | 7 | 0.001 | 14,906 | 10,012 | -4894 | +32.83% |
| tpch.lineitem-5k | l_tax | 5000 | 9 | 0.002 | 14,826 | 10,042 | -4784 | +32.27% |
| tpch.lineitem-5k | l_shipmode | 5000 | 7 | 0.001 | 14,645 | 10,035 | -4610 | +31.48% |
| tpch.lineitem-5k | l_shipinstruct | 5000 | 4 | 0.001 | 14,071 | 10,050 | -4021 | +28.58% |
| tpch.lineitem-5k | l_quantity | 5000 | 50 | 0.010 | 19,120 | 15,239 | -3881 | +20.30% |
| adult-5000 | relationship | 5000 | 6 | 0.001 | 13,814 | 10,060 | -3754 | +27.18% |
| adult-5000 | age | 5000 | 71 | 0.014 | 18,926 | 15,211 | -3715 | +19.63% |
| adult-5000 | marital-status | 5000 | 7 | 0.001 | 13,247 | 10,098 | -3149 | +23.77% |
| tpch.customer-5k | c_mktsegment | 1500 | 5 | 0.003 | 4,367 | 3,048 | -1319 | +30.20% |
| adult-5000 | occupation | 5000 | 15 | 0.003 | 16,127 | 15,203 | -924 | +5.73% |
| tpch.customer-5k | c_nationkey | 1500 | 25 | 0.017 | 5,403 | 4,563 | -840 | +15.55% |
| tpch.lineitem-5k | l_discount | 5000 | 11 | 0.002 | 15,749 | 15,051 | -698 | +4.43% |
| adult-1000 | relationship | 1000 | 6 | 0.006 | 2,726 | 2,060 | -666 | +24.43% |
| adult-1000 | marital-status | 1000 | 7 | 0.007 | 2,599 | 2,098 | -501 | +19.28% |
| adult-5000 | workclass | 5000 | 8 | 0.002 | 10,341 | 10,081 | -260 | +2.51% |
| adult-1000 | occupation | 1000 | 15 | 0.015 | 3,352 | 3,203 | -149 | +4.45% |
| adult-1000 | workclass | 1000 | 7 | 0.007 | 2,178 | 2,069 | -109 | +5.00% |
| adult-5000 | sex | 5000 | 2 | 0.000 | 10,012 | 10,010 | -2 | +0.02% |
| adult-1000 | education-num | 1000 | 16 | 0.016 | 2,949 | 3,037 | +88 | -2.98% |
| adult-1000 | education | 1000 | 16 | 0.016 | 3,029 | 3,133 | +104 | -3.43% |
| adult-1000 | sex | 1000 | 2 | 0.002 | 1,871 | 2,010 | +139 | -7.43% |
| adult-5000 | hours-per-week | 5000 | 81 | 0.016 | 15,052 | 15,232 | +180 | -1.20% |
| adult-5000 | education-num | 5000 | 16 | 0.003 | 14,807 | 15,037 | +230 | -1.55% |
| adult-5000 | education | 5000 | 16 | 0.003 | 14,887 | 15,133 | +246 | -1.65% |
| adult-1000 | class | 1000 | 2 | 0.002 | 1,704 | 2,009 | +305 | -17.90% |
| tpch.lineitem-5k | l_suppkey | 5000 | 100 | 0.020 | 19,606 | 20,290 | +684 | -3.49% |
| adult-1000 | race | 1000 | 5 | 0.005 | 1,174 | 2,054 | +880 | -74.96% |
| adult-5000 | class | 5000 | 2 | 0.000 | 8,229 | 10,009 | +1780 | -21.63% |
| tpch.lineitem-5k | l_returnflag | 5000 | 3 | 0.001 | 8,075 | 10,004 | +1929 | -23.89% |
| adult-1000 | capital-gain | 1000 | 43 | 0.043 | 1,059 | 3,217 | +2158 | -203.78% |
| adult-1000 | native-country | 1000 | 28 | 0.028 | 960 | 3,225 | +2265 | -235.94% |
| adult-1000 | capital-loss | 1000 | 24 | 0.024 | 508 | 3,114 | +2606 | -512.99% |
| adult-5000 | race | 5000 | 5 | 0.001 | 5,796 | 10,054 | +4258 | -73.46% |
| tpch.lineitem-5k | l_linestatus | 5000 | 2 | 0.000 | 4,137 | 10,002 | +5865 | -141.77% |
| adult-5000 | native-country | 5000 | 41 | 0.008 | 4,667 | 15,355 | +10688 | -229.01% |
| adult-5000 | capital-gain | 5000 | 86 | 0.017 | 4,106 | 15,438 | +11332 | -275.99% |
| adult-5000 | capital-loss | 5000 | 54 | 0.011 | 2,409 | 15,263 | +12854 | -533.58% |

## Agregados

| Cohort | bytes M10 | bytes enum LB | delta | gain |
|---|---:|---:|---:|---:|
| Low-card total | 311,434 | 331,749 | +20,315 | -6.52% |
| Low-card real-world apenas | 311,434 | 331,749 | +20,315 | -6.52% |

**Weighted over all RW cols (incl. high-card)**: -2.28%
(real-world total: 889,714B em todas as cols)

## Veredito

**NO-GO: ganho weighted total -2.28% < 2%. M10 ja' captura bem. Encoder enumerated nao vale.**

**Status**: `no-go-m10-suficiente`


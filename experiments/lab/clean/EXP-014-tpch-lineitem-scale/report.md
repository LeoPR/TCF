# EXP-014 — lineitem scale (report)

## Tabela

| volume | rows | raw (B) | TCF (B) | ratio | encode (s) | decode (s) | RT | cad/16 |
|---:|---:|---:|---:|---:|---:|---:|---|---:|
| 1000 | 1000 | 120,690 | 102,366 | 84.8% | 7.9 | 0.04 | OK | 8/16 |
| 5000 | 5000 | 601,788 | 498,271 | 82.8% | 40.5 | 0.24 | OK | 8/16 |
| 10000 | 10000 | 1,204,174 | 1,003,986 | 83.4% | 86.6 | 0.50 | OK | 8/16 |
| 20000 | 20000 | 2,418,120 | 2,048,101 | 84.7% | 232.0 | 0.93 | OK | 8/16 |

## Extrapolacao

Fit em ultimos 2 pontos: `T = k * N^1.42`
- alpha = 1.42  (1.0 = linear, 2.0 = quadratic)
- estimativa lineitem full (60175): **1110s (18.5 min)**


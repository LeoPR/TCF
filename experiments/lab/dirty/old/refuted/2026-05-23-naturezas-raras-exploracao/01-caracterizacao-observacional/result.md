# Sub-exp 01 — caracterizar naturezas raras #5 (range) e #8 (suffix)

## Setup

Caracterizacao observacional de padroes em Adult+TPC-H + D1-D9 controle.

Total colunas analisadas: 66
Real-world (excl sintetico): 57

## Padroes #8 — Suffix comum

Colunas com suffix comum (>= 80%): 12

| Source | Col | Suffix | Frac | M10 | Enc | Gain |
|---|---|---|---:|---:|---:|---:|
| tpch.lineitem-5k | l_quantity | `.0` | 1.00 | 19,120 | 14,065 | +26.44% |
| sintetico | D2-emails-quote-id | `om` | 1.00 | 166 | 226 | -36.14% |
| sintetico | D1-emails-simples | `om` | 1.00 | 118 | 170 | -44.07% |
| adult-5000 | sex | `le` | 1.00 | 10,012 | 18,385 | -83.63% |
| sintetico | D3-stress-substring | `on` | 0.83 | 177 | 326 | -84.18% |
| adult-1000 | sex | `le` | 1.00 | 1,871 | 3,611 | -93.00% |
| adult-1000 | class | `0K` | 1.00 | 1,704 | 3,763 | -120.83% |
| adult-5000 | class | `0K` | 1.00 | 8,229 | 18,831 | -128.84% |
| sintetico | D8-cabeca-cauda | `ix` | 1.00 | 100 | 363 | -263.00% |
| adult-1000 | race | `te` | 0.85 | 1,174 | 4,755 | -305.03% |
| adult-5000 | race | `te` | 0.85 | 5,796 | 24,076 | -315.39% |
| sintetico | D9-frequencia-alta | `@@` | 1.00 | 66 | 334 | -406.06% |

## Padroes #5 — Range narrow numerico

Colunas com range narrow: 4

| Source | Col | Min | Max | M10 | Enc | Gain |
|---|---|---:|---:|---:|---:|---:|
| tpch.lineitem-5k | l_linenumber | 1 | 7 | 14,906 | 10,001 | +32.91% |
| adult-1000 | age | 17 | 90 | 3,823 | 3,002 | +21.48% |
| adult-5000 | age | 17 | 90 | 18,926 | 15,002 | +20.73% |
| tpch.region-5k | r_regionkey | 0 | 4 | 8 | 11 | -37.50% |

## Agregado real-world

- Total M10: 889,714B
- **#8 Suffix potential**: -39,580B (-4.45% weighted)
- **#5 Range potential**: +9,647B (+1.08% weighted)

## Veredito

**NO-GO: ambas naturezas < 2% weighted (M10 ja' captura bem ou padroes raros)**

**Status**: `no-go`


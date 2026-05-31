# Sub-exp 01 — H-DA-09c varrer threshold detect_cadence

## Setup

- Thresholds testados: [0.5, 0.6, 0.7, 0.8]
- Default atual: 0.7
- Total colunas: 66

## Agregado por threshold

| Cohort | thr=0.5 | thr=0.6 | thr=0.7 (default) | thr=0.8 |
|---|---:|---:|---:|---:|
| Total | 918,431 | 918,431 | 891,237 | 891,237 |
| Real-world (57) | 916,908 | 916,908 | 889,714 | 889,714 |
| Sintetico (9) | 1523 | 1523 | 1523 | 1523 |

## Distribuicao melhor threshold per col

| Threshold | n_cols preferem |
|---|---:|
| 0.5 | 63/66 |
| 0.6 | 0/66 |
| 0.7 | 3/66 |
| 0.8 | 0/66 |

## Veredito

**NO-GO: threshold 0.7 atual ja' otimo (ganho 0.00% << 2%)**

**Status**: `no-go-threshold-07-otimo`


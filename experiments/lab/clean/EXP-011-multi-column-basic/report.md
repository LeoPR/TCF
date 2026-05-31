# EXP-011 — Multi-column basic (report)

Dataset: D17a-multi-column-mixed (13 rows, 4 cols)
Raw CSV: 601 bytes

## Resumo

- **multi-encoding** (per-coluna): 322 bytes, RT=OK
- **single-encoding** (concat 1 coluna): 402 bytes, RT=OK
- **raw CSV** (sem compressao): 601 bytes

multi vs single: -80 bytes (-19.9%)
multi vs raw: -279 bytes (-46.4%)

## Por coluna

| Coluna | uniq | det? | hint | runs | bytes (body, sem header) |
|---|---:|---|---|---:|---:|
| `timestamp` | 13 | True | True | 2 | 68 |
| `id` | 13 | True | True | 2 | 35 |
| `email` | 13 | False | False | 0 | 151 |
| `categoria` | 3 | False | False | 0 | 43 |

## Validacao

✓ **RT OK**: ambos pipelines reconstroem exatos.

## Limitacoes

- 1 dataset sintetico (D17a). Real-world (TPC-H, Adult Census) NAO testado neste EXP.
- Sem ordering/cross-column (ver `futuras-otimizacoes-formato.md`).
- Header verboso (`# COL=name bytes=N`); otimizacao adiada.


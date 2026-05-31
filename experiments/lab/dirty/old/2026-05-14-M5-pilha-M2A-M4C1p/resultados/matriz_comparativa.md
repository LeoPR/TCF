# M5 — Matriz comparativa (pilha M2.A + M4.C1')

Sintaxes: M1-E-range, M2-A-alias-tupla, M4-C1p-batch-subsequencias, M5-A-pilha-hibrida
Datasets: D1-emails-simples, D2-emails-quote-id, D3-stress-substring, D4-caos-mix

Cada micro tem suas pastas output/decoded/debug autocontidas:
- `M1-E-range/output/<dataset>.tcf`
- `M1-E-range/decoded/<dataset>.csv`
- `M1-E-range/debug/<dataset>.txt`
- `M2-A-alias-tupla/output/<dataset>.tcf`
- `M2-A-alias-tupla/decoded/<dataset>.csv`
- `M2-A-alias-tupla/debug/<dataset>.txt`
- `M4-C1p-batch-subsequencias/output/<dataset>.tcf`
- `M4-C1p-batch-subsequencias/decoded/<dataset>.csv`
- `M4-C1p-batch-subsequencias/debug/<dataset>.txt`
- `M5-A-pilha-hibrida/output/<dataset>.tcf`
- `M5-A-pilha-hibrida/decoded/<dataset>.csv`
- `M5-A-pilha-hibrida/debug/<dataset>.txt`

## Bytes por (sintaxe x dataset)

| dataset | M1-E-range | M2-A-alias-tupla | M4-C1p-batch-subsequencias | M5-A-pilha-hibrida | delta_min_max |
|---|---|---|---|---|---|
| D1-emails-simples | 149 | 141 | 138 | 138 | 11 |
| D2-emails-quote-id | 180 | 178 | 174 | 174 | 6 |
| D3-stress-substring | 206 | 206 | 196 | 196 | 10 |
| D4-caos-mix | 141 | 141 | 128 | 128 | 13 |
| **TOTAL** | **676** | **666** | **636** | **636** | --- |

## Roundtrip

| dataset | M1-E-range | M2-A-alias-tupla | M4-C1p-batch-subsequencias | M5-A-pilha-hibrida |
|---|---|---|---|---|
| D1-emails-simples | OK | OK | OK | OK |
| D2-emails-quote-id | OK | OK | OK | OK |
| D3-stress-substring | OK | OK | OK | OK |
| D4-caos-mix | OK | OK | OK | OK |
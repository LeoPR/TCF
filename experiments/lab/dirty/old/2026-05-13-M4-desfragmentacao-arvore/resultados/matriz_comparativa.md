# M3 — Matriz comparativa entre micros

Sintaxes: M1-E-range, M4-C1-batch-greedy-implicito, M4-C1p-batch-subsequencias
Datasets: D1-emails-simples, D2-emails-quote-id, D3-stress-substring, D4-caos-mix

Cada micro tem suas pastas output/decoded/debug autocontidas:
- `M1-E-range/output/<dataset>.tcf`
- `M1-E-range/decoded/<dataset>.csv`
- `M1-E-range/debug/<dataset>.txt`
- `M4-C1-batch-greedy-implicito/output/<dataset>.tcf`
- `M4-C1-batch-greedy-implicito/decoded/<dataset>.csv`
- `M4-C1-batch-greedy-implicito/debug/<dataset>.txt`
- `M4-C1p-batch-subsequencias/output/<dataset>.tcf`
- `M4-C1p-batch-subsequencias/decoded/<dataset>.csv`
- `M4-C1p-batch-subsequencias/debug/<dataset>.txt`

## Bytes por (sintaxe × dataset)

| dataset | M1-E-range | M4-C1-batch-greedy-implicito | M4-C1p-batch-subsequencias | delta_min_max |
|---|---|---|---|---|
| D1-emails-simples | 149 | 148 | 138 | 11 |
| D2-emails-quote-id | 180 | 178 | 174 | 6 |
| D3-stress-substring | 206 | 203 | 196 | 10 |
| D4-caos-mix | 141 | 137 | 128 | 13 |
| **TOTAL** | **676** | **666** | **636** | — |

## Roundtrip

| dataset | M1-E-range | M4-C1-batch-greedy-implicito | M4-C1p-batch-subsequencias |
|---|---|---|---|
| D1-emails-simples | OK | OK | OK |
| D2-emails-quote-id | OK | OK | OK |
| D3-stress-substring | OK | OK | OK |
| D4-caos-mix | OK | OK | OK |
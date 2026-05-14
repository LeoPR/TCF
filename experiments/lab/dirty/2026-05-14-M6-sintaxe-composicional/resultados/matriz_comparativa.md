# M6 — Matriz comparativa (sintaxe composicional)

Sintaxes: M1-E-range, M4-C1p-batch-subsequencias, M6-A-m2a-inline, M6-C-composicional
Datasets: D1-emails-simples, D2-emails-quote-id, D3-stress-substring, D4-caos-mix

Cada micro tem suas pastas output/decoded/debug autocontidas.

## Bytes por (sintaxe x dataset)

| dataset | M1-E-range | M4-C1p-batch-subsequencias | M6-A-m2a-inline | M6-C-composicional | delta_min_max |
|---|---|---|---|---|---|
| D1-emails-simples | 149 | 138 | 142 | 128 | 21 |
| D2-emails-quote-id | 180 | 174 | 177 | 175 | 6 |
| D3-stress-substring | 206 | 196 | 203 | 194 | 12 |
| D4-caos-mix | 141 | 128 | 142 | 122 | 20 |
| **TOTAL** | **676** | **636** | **664** | **619** | --- |

## Roundtrip

| dataset | M1-E-range | M4-C1p-batch-subsequencias | M6-A-m2a-inline | M6-C-composicional |
|---|---|---|---|---|
| D1-emails-simples | OK | OK | OK | OK |
| D2-emails-quote-id | OK | OK | OK | OK |
| D3-stress-substring | OK | OK | OK | OK |
| D4-caos-mix | OK | OK | OK | OK |
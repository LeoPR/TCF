# M3 — Matriz comparativa entre micros

Sintaxes: M3-A-no-compartilhado, M3-B-encadeamento
Datasets: D1-emails-simples, D2-emails-quote-id, D3-stress-substring, D4-caos-mix

Cada micro tem suas pastas output/decoded/debug autocontidas:
- `M3-A-no-compartilhado/output/<dataset>.tcf`
- `M3-A-no-compartilhado/decoded/<dataset>.csv`
- `M3-A-no-compartilhado/debug/<dataset>.txt`
- `M3-B-encadeamento/output/<dataset>.tcf`
- `M3-B-encadeamento/decoded/<dataset>.csv`
- `M3-B-encadeamento/debug/<dataset>.txt`

## Bytes por (sintaxe × dataset)

| dataset | M3-A-no-compartilhado | M3-B-encadeamento | delta_min_max |
|---|---|---|---|
| D1-emails-simples | 149 | 149 | 0 |
| D2-emails-quote-id | 180 | 180 | 0 |
| D3-stress-substring | 206 | 206 | 0 |
| D4-caos-mix | 141 | 141 | 0 |
| **TOTAL** | **676** | **676** | — |

## Roundtrip

| dataset | M3-A-no-compartilhado | M3-B-encadeamento |
|---|---|---|
| D1-emails-simples | OK | OK |
| D2-emails-quote-id | OK | OK |
| D3-stress-substring | OK | OK |
| D4-caos-mix | OK | OK |
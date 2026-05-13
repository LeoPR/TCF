# M3 — Matriz comparativa entre micros

Sintaxes: M3-A-no-compartilhado, M3-B-encadeamento
Datasets: DE7-hierarquia-profunda

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
| DE7-hierarquia-profunda | 119 | 119 | 0 |
| **TOTAL** | **119** | **119** | — |

## Roundtrip

| dataset | M3-A-no-compartilhado | M3-B-encadeamento |
|---|---|---|
| DE7-hierarquia-profunda | OK | OK |
# M7 — Matriz comparativa (refactor)

Sintaxes: M1-E-range, M6-C-composicional, M7-A-composicional
Datasets: D1-emails-simples, D2-emails-quote-id, D3-stress-substring, D4-caos-mix

Layout do debug: `resultados/tokens/`, `<micro>/output/`,
`<micro>/decoded/`, `<micro>/debug/`, `<micro>/detector_trace/`,
`<micro>/redes/`.

## Bytes por (sintaxe x dataset)

| dataset | M1-E-range | M6-C-composicional | M7-A-composicional | delta |
|---|---|---|---|---|
| D1-emails-simples | 149 | 128 | 128 | 21 |
| D2-emails-quote-id | 180 | 175 | 175 | 5 |
| D3-stress-substring | 206 | 194 | 194 | 12 |
| D4-caos-mix | 141 | 122 | 122 | 19 |
| **TOTAL** | **676** | **619** | **619** | --- |

## Roundtrip

| dataset | M1-E-range | M6-C-composicional | M7-A-composicional |
|---|---|---|---|
| D1-emails-simples | OK | OK | OK |
| D2-emails-quote-id | OK | OK | OK |
| D3-stress-substring | OK | OK | OK |
| D4-caos-mix | OK | OK | OK |
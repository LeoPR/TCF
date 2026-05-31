# Resumo — Sub-exp 08 (min_len trade-off)

## Tabela por (dataset, min_len)

| Dataset | min_len | canon (B) | fork (B) | RT |
|---|---:|---:|---:|---|
| D16a-ids-3digits | 2 | 60 | 33 | OK |
| D16a-ids-3digits | 3 | 65 | 11 | OK |
| D16a-ids-3digits | 4 | 65 | 11 | OK |
| D16a-ids-3digits | 5 | 65 | 11 | OK |
| D11d-datetime-min | 2 | 110 | 73 | OK |
| D11d-datetime-min | 3 | 110 | 73 | OK |
| D11d-datetime-min | 4 | 121 | 121 | OK |
| D11d-datetime-min | 5 | 134 | 134 | OK |
| D9-frequencia-alta | 2 | 158 | 127 | OK |
| D9-frequencia-alta | 3 | 158 | 127 | OK |
| D9-frequencia-alta | 4 | 150 | 113 | OK |
| D9-frequencia-alta | 5 | 174 | 94 | OK |

## Melhor min_len por dataset (pelo fork bytes)

| Dataset | Melhor min_len | Bytes fork |
|---|---:|---:|
| D16a-ids-3digits | 3 | 11 |
| D11d-datetime-min | 2 | 73 |
| D9-frequencia-alta | 5 | 94 |

## Observacoes

- **D16a-ids-3digits**: ml=2→33B, ml=3→11B, ml=4→11B, ml=5→11B
- **D11d-datetime-min**: ml=2→73B, ml=3→73B, ml=4→121B, ml=5→134B
- **D9-frequencia-alta**: ml=2→127B, ml=3→127B, ml=4→113B, ml=5→94B


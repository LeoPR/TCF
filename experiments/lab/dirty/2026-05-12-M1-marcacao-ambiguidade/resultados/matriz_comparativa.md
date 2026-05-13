# Matriz comparativa — Macro M1

Sintaxes: M1-A-escape, M1-A-escape-escopo, M1-B-quote, M1-E-range, M1-C-sumida, M1-D-slice
Datasets: D1-emails-simples, D2-emails-quote-id, D3-stress-substring, D4-caos-mix

## Bytes por (sintaxe × dataset)

| dataset | M1-A-escape | M1-A-escape-escopo | M1-B-quote | M1-E-range | M1-C-sumida | M1-D-slice | vencedor | diff_min_max |
|---|---|---|---|---|---|---|---|---|
| D1-emails-simples | 162 | 162 | 162 | 149 | 149 | 162 | M1-E-range | 13 (8.0%) |
| D2-emails-quote-id | 200 | 197 | 198 | 180 | 180 | 207 | M1-E-range | 27 (13.0%) |
| D3-stress-substring | 242 | 233 | 233 | 206 | 206 | 218 | M1-E-range | 36 (14.9%) |
| D4-caos-mix | 152 | 152 | 160 | 141 | 141 | 141 | M1-E-range | 19 (11.9%) |
| **TOTAL** | **756** | **744** | **753** | **676** | **676** | **728** | **M1-E-range** | 80 |

## Roundtrip por sintaxe × dataset

| dataset | M1-A-escape | M1-A-escape-escopo | M1-B-quote | M1-E-range | M1-C-sumida | M1-D-slice |
|---|---|---|---|---|---|---|
| D1-emails-simples | OK | OK | OK | OK | OK | OK |
| D2-emails-quote-id | OK | OK | OK | OK | OK | OK |
| D3-stress-substring | OK | OK | OK | OK | OK | OK |
| D4-caos-mix | OK | OK | OK | OK | OK | OK |

## Como interpretar

- Cada celula e bytes do TCF gerado pela sintaxe no dataset.
- `X` = sintaxe falhou (encode ou decode).
- `vencedor` = sintaxe com menor bytes no dataset.
- `diff_min_max` = diferenca entre maior e menor bytes (potencial de escolha errada).
- **TOTAL** = soma de bytes em todos os datasets validos.

Para detalhes por sintaxe x dataset, ver:
- `resultados/<sintaxe>/<dataset>.tcf` (encode)
- `resultados/<sintaxe>/<dataset>.decoded.csv` (decode)
- `resultados/<sintaxe>/<dataset>.debug.txt` (input + tokens + frag + encode + decode)
- `resultados/tokens/<dataset>.txt` (tokens raiz, compartilhados entre sintaxes)
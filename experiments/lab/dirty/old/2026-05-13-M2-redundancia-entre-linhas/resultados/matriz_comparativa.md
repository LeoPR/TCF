# Matriz comparativa — Macro M1

Sintaxes: M1-E-range, M2-A-alias-tupla
Datasets: D1-emails-simples, D2-emails-quote-id, D3-stress-substring, D4-caos-mix

## Bytes por (sintaxe × dataset)

| dataset | M1-E-range | M2-A-alias-tupla | vencedor | diff_min_max |
|---|---|---|---|---|
| D1-emails-simples | 149 | 141 | M2-A-alias-tupla | 8 (5.4%) |
| D2-emails-quote-id | 180 | 178 | M2-A-alias-tupla | 2 (1.1%) |
| D3-stress-substring | 206 | 206 | M1-E-range | 0 (0.0%) |
| D4-caos-mix | 141 | 141 | M1-E-range | 0 (0.0%) |
| **TOTAL** | **676** | **666** | **M2-A-alias-tupla** | 10 |

## Roundtrip por sintaxe × dataset

| dataset | M1-E-range | M2-A-alias-tupla |
|---|---|---|
| D1-emails-simples | OK | OK |
| D2-emails-quote-id | OK | OK |
| D3-stress-substring | OK | OK |
| D4-caos-mix | OK | OK |

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
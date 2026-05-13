# Matriz comparativa — Macro M1

Sintaxes: M1-A-escape, M1-A-escape-escopo, M1-B-quote, M1-E-range, M1-C-sumida
Datasets: DE1-adversarial-E, DE2-favoravel-E, DE3-adversarial-C, DE4-favoravel-C

## Bytes por (sintaxe × dataset)

| dataset | M1-A-escape | M1-A-escape-escopo | M1-B-quote | M1-E-range | M1-C-sumida | vencedor | diff_min_max |
|---|---|---|---|---|---|---|---|
| DE1-adversarial-E | 53 | 53 | 63 | 53 | 53 | M1-A-escape | 10 (15.9%) |
| DE2-favoravel-E | 132 | 132 | 132 | 82 | 82 | M1-E-range | 50 (37.9%) |
| DE3-adversarial-C | 101 | 100 | 100 | 96 | 96 | M1-E-range | 5 (5.0%) |
| DE4-favoravel-C | 84 | 77 | 77 | 77 | 69 | M1-C-sumida | 15 (17.9%) |
| **TOTAL** | **370** | **362** | **372** | **308** | **300** | **M1-C-sumida** | 72 |

## Roundtrip por sintaxe × dataset

| dataset | M1-A-escape | M1-A-escape-escopo | M1-B-quote | M1-E-range | M1-C-sumida |
|---|---|---|---|---|---|
| DE1-adversarial-E | OK | OK | OK | OK | OK |
| DE2-favoravel-E | OK | OK | OK | OK | OK |
| DE3-adversarial-C | OK | OK | OK | OK | OK |
| DE4-favoravel-C | OK | OK | OK | OK | OK |

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
# Matriz comparativa — Macro M1

Sintaxes: M1-A-escape, M1-A-escape-escopo, M1-B-quote, M1-E-range, M1-C-sumida, M1-D-slice
Datasets: DE1-adversarial-E, DE2-favoravel-E, DE3-adversarial-C, DE4-favoravel-C, DE5-adversarial-D, DE6-favoravel-D

## Bytes por (sintaxe × dataset)

| dataset | M1-A-escape | M1-A-escape-escopo | M1-B-quote | M1-E-range | M1-C-sumida | M1-D-slice | vencedor | diff_min_max |
|---|---|---|---|---|---|---|---|---|
| DE1-adversarial-E | 53 | 53 | 63 | 53 | 53 | 78 | M1-A-escape | 25 (32.1%) |
| DE2-favoravel-E | 132 | 132 | 132 | 82 | 82 | 85 | M1-E-range | 50 (37.9%) |
| DE3-adversarial-C | 101 | 100 | 100 | 96 | 96 | 121 | M1-E-range | 25 (20.7%) |
| DE4-favoravel-C | 84 | 77 | 77 | 77 | 69 | 110 | M1-C-sumida | 41 (37.3%) |
| DE5-adversarial-D | 54 | 54 | 64 | 54 | 54 | 78 | M1-A-escape | 24 (30.8%) |
| DE6-favoravel-D | 58 | 58 | 58 | 57 | 57 | 70 | M1-E-range | 13 (18.6%) |
| **TOTAL** | **482** | **474** | **494** | **419** | **411** | **542** | **M1-C-sumida** | 131 |

## Roundtrip por sintaxe × dataset

| dataset | M1-A-escape | M1-A-escape-escopo | M1-B-quote | M1-E-range | M1-C-sumida | M1-D-slice |
|---|---|---|---|---|---|---|
| DE1-adversarial-E | OK | OK | OK | OK | OK | OK |
| DE2-favoravel-E | OK | OK | OK | OK | OK | OK |
| DE3-adversarial-C | OK | OK | OK | OK | OK | OK |
| DE4-favoravel-C | OK | OK | OK | OK | OK | OK |
| DE5-adversarial-D | OK | OK | OK | OK | OK | OK |
| DE6-favoravel-D | OK | OK | OK | OK | OK | OK |

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
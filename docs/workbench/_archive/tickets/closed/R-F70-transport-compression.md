---
title: Finding F70-F73 — TCF+gzip 29% menor que CSV+gzip
type: finding
status: CLOSED (2026-04-09)
origin: P-transport-compression
---

# TCF+gzip comprime mais que CSV+gzip

## Finding

TCF L3+gzip e consistentemente menor que CSV+gzip em todas as escalas.
O ganho cresce com escala: 1% a 50 rows, 29% a 5000 rows.

## Dados

| Scale | csv+gz | L0+gz | L3+gz | L3 vs csv |
|-------|--------|-------|-------|-----------|
| 50 | 1479 | 1470 | 1467 | -0.8% |
| 200 | 5626 | 5028 | 4752 | -15.5% |
| 1000 | 25209 | 21572 | 19859 | -21.2% |
| 5000 | 125948 | 96643 | 89472 | **-29.0%** |

## Mecanismo

A compressao textual do TCF (sort + RLE + dict) pre-ordena os dados
de forma que o LZ77 do gzip comprime melhor. Nao e redundante.
JSONL e sempre o pior (chaves JSON repetidas resistem parcialmente ao gzip).

## Implicacao

TCF nao e apenas mais interpretavel para LLMs — e tambem mais eficiente
no transporte (APIs, HTTP responses). Argumento triplo:
1. Menos tokens no prompt
2. Menos bytes no transporte  
3. Hints meta-cognitivos (STATS)

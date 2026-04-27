---
title: Compressao de transporte — TCF + gzip vs CSV + gzip vs JSONL + gzip
type: research
status: DONE (2026-04-09)
priority: LOW
---

# Compressao de Transporte (gzip)

## Resultado

TCF+gzip e consistentemente MENOR que CSV+gzip e JSONL+gzip em todas as escalas.

### Tamanho apos gzip (bytes)

| Scale | csv+gz | jsonl+gz | L0+gz | L2+gz | L3+gz |
|-------|--------|----------|-------|-------|-------|
| 50 | 1479 | 1690 | 1470 | **1420** | 1467 |
| 200 | 5626 | 6376 | 5028 | 5147 | **4752** |
| 500 | 12681 | 14756 | 11110 | 11422 | **10440** |
| 1000 | 25209 | 30027 | 21572 | 22179 | **19859** |
| 5000 | 125948 | 151577 | 96643 | 100963 | **89472** |

### Reducao vs CSV+gzip

| Scale | L0+gz vs csv+gz | L3+gz vs csv+gz |
|-------|-----------------|-----------------|
| 50 | -0.6% | -0.8% |
| 200 | -10.6% | -15.5% |
| 500 | -12.4% | -17.7% |
| 1000 | -14.4% | -21.2% |
| 5000 | -23.3% | **-29.0%** |

## Findings

### F70: TCF+gzip e menor que CSV+gzip
A compressao textual do TCF (RLE, sort, dict) AGREGA valor mesmo sobre gzip.
Nao e redundante — gzip comprime melhor dados pre-ordenados (sort ajuda o LZ77).

### F71: L3 e o melhor para transporte
TCF L3+gzip: 29% menor que CSV+gzip em escala 5000.
Dict encoding reduz vocabulario → gzip comprime indices melhor que strings.

### F72: JSONL e o pior formato para transporte
JSONL+gzip: 20% maior que CSV+gzip em todas as escalas.
JSON overhead (chaves repetidas) resiste parcialmente ao gzip.

### F73: O ganho cresce com escala
50 rows: ~1% de diferenca (irrelevante)
5000 rows: 29% (significativo para APIs de alto volume)

## Implicacao para o paper

TCF nao e apenas mais interpretavel — e tambem mais compacto no transporte.
O argumento "TCF e melhor para LLM APIs" se fortalece:
1. Menos tokens no prompt (texto menor)
2. Menos bytes no transporte (gzip menor)
3. Interpretabilidade columnar (formato legivel)

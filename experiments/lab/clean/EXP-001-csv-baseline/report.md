# EXP-001 — CSV Baseline (Resultados)

Total: 12 execucoes (4 datasets × 3 compressoes)

## Tabela mestra

| Dataset | Rows × Cols | Compressao | Bytes raw | Bytes comp | Ratio | Encode (ms) | Decode (ms) | Roundtrip |
|---------|-------------|------------|-----------|------------|-------|-------------|-------------|-----------|
| micro | 5×4 | none | 103 | 103 | 100.0% | 0.04 | 0.03 | ✓ |
| micro | 5×4 | gzip | 103 | 100 | 97.1% | 0.03 | 0.05 | ✓ |
| micro | 5×4 | brotli | 103 | 97 | 94.2% | 0.04 | 0.04 | ✓ |
| small | 20×5 | none | 383 | 383 | 100.0% | 0.08 | 0.29 | ✓ |
| small | 20×5 | gzip | 383 | 191 | 49.9% | 0.08 | 0.34 | ✓ |
| small | 20×5 | brotli | 383 | 160 | 41.8% | 0.08 | 0.32 | ✓ |
| categorical_heavy | 100×6 | none | 3350 | 3350 | 100.0% | 0.41 | 1.63 | ✓ |
| categorical_heavy | 100×6 | gzip | 3350 | 761 | 22.7% | 0.36 | 1.86 | ✓ |
| categorical_heavy | 100×6 | brotli | 3350 | 639 | 19.1% | 0.35 | 1.82 | ✓ |
| wide_random | 100×11 | none | 7336 | 7336 | 100.0% | 1.18 | 2.92 | ✓ |
| wide_random | 100×11 | gzip | 7336 | 3469 | 47.3% | 1.06 | 3.13 | ✓ |
| wide_random | 100×11 | brotli | 7336 | 2901 | 39.5% | 1.25 | 3.53 | ✓ |

## Observacoes

- **Roundtrip**: CSV com `infer_types=True` faz roundtrip exato
  para datasets sem ambiguidade (str/int/float/bool).
- **Compressao**: gzip e brotli efetivos em datasets com repeticao
  categorical (`categorical_heavy`); pouco efetivos em
  `wide_random` (sem padrao).
- **Timing**: encode/decode CSV sao da ordem de microsegundos para
  datasets pequenos. brotli compress eh ~10× mais lento que gzip.

Comparacao com TCF: ver EXP-002.
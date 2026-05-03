# EXP-002 — TCF v0.2 Baseline (Resultados)

Total: 36 execucoes (4 datasets × 3 niveis TCF × 3 compressoes)

## TCF — tabela mestra

| Dataset | Rows × Cols | TCF Level | Compressao | Bytes raw | Bytes comp | Ratio | Encode (ms) | Decode (ms) | Roundtrip |
|---------|-------------|-----------|------------|-----------|------------|-------|-------------|-------------|-----------|
| micro | 5×4 | L0 | none | 222 | 222 | 100.0% | 0.04 | 0.08 | ✗ |
| micro | 5×4 | L0 | gzip | 222 | 172 | 77.5% | 0.04 | 0.08 | ✗ |
| micro | 5×4 | L0 | brotli | 222 | 158 | 71.2% | 0.06 | 0.08 | ✗ |
| micro | 5×4 | L2 | none | 257 | 257 | 100.0% | 0.09 | 0.05 | ✗ |
| micro | 5×4 | L2 | gzip | 257 | 204 | 79.4% | 0.09 | 0.08 | ✗ |
| micro | 5×4 | L2 | brotli | 257 | 186 | 72.4% | 0.09 | 0.08 | ✗ |
| micro | 5×4 | L3 | none | 299 | 299 | 100.0% | 0.12 | 0.09 | L3 |
| micro | 5×4 | L3 | gzip | 299 | 226 | 75.6% | 0.11 | 0.09 | L3 |
| micro | 5×4 | L3 | brotli | 299 | 201 | 67.2% | 0.12 | 0.10 | L3 |
| small | 20×5 | L0 | none | 526 | 526 | 100.0% | 0.23 | 0.32 | ✗ |
| small | 20×5 | L0 | gzip | 526 | 246 | 46.8% | 0.19 | 0.18 | ✗ |
| small | 20×5 | L0 | brotli | 526 | 220 | 41.8% | 0.23 | 0.33 | ✗ |
| small | 20×5 | L2 | none | 453 | 453 | 100.0% | 0.29 | 0.27 | ✗ |
| small | 20×5 | L2 | gzip | 453 | 281 | 62.0% | 0.31 | 0.25 | ✗ |
| small | 20×5 | L2 | brotli | 453 | 282 | 62.3% | 0.31 | 0.22 | ✗ |
| small | 20×5 | L3 | none | 494 | 494 | 100.0% | 0.35 | 0.28 | L3 |
| small | 20×5 | L3 | gzip | 494 | 304 | 61.5% | 0.29 | 0.20 | L3 |
| small | 20×5 | L3 | brotli | 494 | 281 | 56.9% | 0.26 | 0.28 | L3 |
| categorical_heavy | 100×6 | L0 | none | 3391 | 3391 | 100.0% | 0.56 | 1.31 | ✗ |
| categorical_heavy | 100×6 | L0 | gzip | 3391 | 798 | 23.5% | 0.67 | 1.58 | ✗ |
| categorical_heavy | 100×6 | L0 | brotli | 3391 | 642 | 18.9% | 0.59 | 1.84 | ✗ |
| categorical_heavy | 100×6 | L2 | none | 2541 | 2541 | 100.0% | 0.81 | 1.48 | ✗ |
| categorical_heavy | 100×6 | L2 | gzip | 2541 | 797 | 31.4% | 0.96 | 1.11 | ✗ |
| categorical_heavy | 100×6 | L2 | brotli | 2541 | 671 | 26.4% | 0.97 | 1.21 | ✗ |
| categorical_heavy | 100×6 | L3 | none | 1465 | 1465 | 100.0% | 1.21 | 1.11 | L3 |
| categorical_heavy | 100×6 | L3 | gzip | 1465 | 750 | 51.2% | 1.29 | 1.33 | L3 |
| categorical_heavy | 100×6 | L3 | brotli | 1465 | 636 | 43.4% | 1.15 | 1.39 | L3 |
| wide_random | 100×11 | L0 | none | 7925 | 7925 | 100.0% | 3.51 | 2.65 | ✓ |
| wide_random | 100×11 | L0 | gzip | 7925 | 3671 | 46.3% | 3.44 | 2.74 | ✓ |
| wide_random | 100×11 | L0 | brotli | 7925 | 3080 | 38.9% | 3.32 | 1.96 | ✓ |
| wide_random | 100×11 | L2 | none | 7967 | 7967 | 100.0% | 3.96 | 2.61 | ✗ |
| wide_random | 100×11 | L2 | gzip | 7967 | 3716 | 46.6% | 3.94 | 2.59 | ✗ |
| wide_random | 100×11 | L2 | brotli | 7967 | 3106 | 39.0% | 3.85 | 2.91 | ✗ |
| wide_random | 100×11 | L3 | none | 7967 | 7967 | 100.0% | 4.55 | 2.79 | L3 |
| wide_random | 100×11 | L3 | gzip | 7967 | 3716 | 46.6% | 4.38 | 2.74 | L3 |
| wide_random | 100×11 | L3 | brotli | 7967 | 3094 | 38.8% | 4.53 | 2.81 | L3 |

## Comparativo TCF L2 vs CSV (mesma compressao)

Bytes comprimidos (menor e melhor):

| Dataset | CSV none | TCF L2 none | CSV gzip | TCF L2 gzip | CSV brotli | TCF L2 brotli |
|---------|----------|-------------|----------|-------------|------------|----------------|
| micro |   103 |   257 |   100 |   204 |    97 |   186 |
| small |   383 |   453 |   191 |   281 |   160 |   282 |
| categorical_heavy |  3350 |  2541 |   761 |   797 |   639 |   671 |
| wide_random |  7336 |  7967 |  3469 |  3716 |  2901 |  3106 |

## Win/loss vs CSV (mesmo compressor)

| Dataset | TCF L2 vence CSV em? |
|---------|---------------------|
| micro | none(+154B perde) / gzip(+104B perde) / brotli(+89B perde) |
| small | none(+70B perde) / gzip(+90B perde) / brotli(+122B perde) |
| categorical_heavy | none(-809B) / gzip(+36B perde) / brotli(+32B perde) |
| wide_random | none(+631B perde) / gzip(+247B perde) / brotli(+205B perde) |

## Observacoes

- **TCF L0** e raw columnar — base sem compressao algoritmica.
- **TCF L2** ativa RLE+STATS. Ganho real depende de repeticao.
- **TCF L3** e schema-only (lossy). Roundtrip nao se aplica;
  bytes sao minimos (uso: enviar so o schema para LLM).
- **Encoder TCF v0.2** e o atual. v0.4 (futuro) deve melhorar:
  DICT, stratified STATS, auto-sort, type-preserving decode.

## Proximos experimentos

- EXP-003: TCF L2 com `sort_by` manual (ver impacto RLE)
- EXP-004: TCF v0.4 com DICT por coluna
- EXP-005: TCF v0.4 com cross-column DICT
- EXP-006: comparativo direto TCF vs CSV vs JSON em todos cenarios
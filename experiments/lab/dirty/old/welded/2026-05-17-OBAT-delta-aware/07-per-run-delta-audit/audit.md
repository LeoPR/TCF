# Audit per-run delta encoding (H-DA-08)

## Resumo

| Dataset | total lines | pairs qualificaveis | bytes potencial (savings) |
|---|---:|---:|---:|
| D11a (fork+fork) | 7 | 1 | 3 |
| D11b (fork+fork) | 14 | 2 | 6 |
| D11c (fork+fork) | 6 | 0 | 0 |
| D11d (fork+fork) | 4 | 0 | 0 |
| D11e (fork+fork) | 6 | 0 | 0 |
| D11f (fork+fork) | 4 | 0 | 0 |
| D11g (fork+fork) | 4 | 0 | 0 |
| D11h (fork+fork) | 4 | 0 | 0 |
| D16a (fork+fork) | 1 | 0 | 0 |
| D16b (fork+fork) | 3 | 0 | 0 |
| D16c (fork+fork) | 4 | 0 | 0 |
| **TOTAL** | | **3** | **9** |

## Detalhes — pares qualificaveis

### D11a (fork+fork)

- Linhas 6-7: `1\6-\01` → `1\6-\15` (runs deltas mixtos: [0, 14])

### D11b (fork+fork)

- Linhas 3-4: `9\2-\28` → `9\2-\29` (runs deltas mixtos: [0, 1])
- Linhas 4-5: `9\2-\29` → `9\3-\01` (runs deltas mixtos: [1, -28])


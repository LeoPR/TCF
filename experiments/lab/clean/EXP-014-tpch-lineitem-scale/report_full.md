# EXP-014 FULL — lineitem 60175 (report)

## Resumo executivo

- **Encode**: 1277s (21.3 min)
- **Estimativa pos-ADR-0009**: 1110s (18.5 min) — diff +15%
- **Bytes**: 6,497,250 / 7,302,534 (89.0%)
- **Decode**: 2.77s
- **RT**: OK
- **Cadence detected**: 8/16 colunas

## Tabela

| volume | rows | raw (B) | TCF (B) | ratio | encode (s) | encode (min) | decode (s) | RT | cad/16 |
|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|
| 60175 | 60175 | 7,302,534 | 6,497,250 | 89.0% | 1277.5 | 21.3 | 2.77 | OK | 8/16 |

## Comparacao com volumes anteriores (do report.md original)

| volume | encode (s) | tempo por 1k rows |
|---:|---:|---:|
| 1000 | 7.9 | 7.9ms |
| 5000 | 40.5 | 8.1ms |
| 10000 | 86.6 | 8.7ms |
| 20000 | 232.0 | 11.6ms |
| **60175** | **1277.5** | **21.2ms** |

## Validacao extrapolacao

- Extrapolacao do run.py (alpha=1.42 fit em 10k+20k): 1110s (18.5 min)
- Real medido: 1277s (21.3 min)
- Diff: +15%

**Aceite OK** (margem 35% sobre extrapolacao). H-RW-05 mitigada confirmada.

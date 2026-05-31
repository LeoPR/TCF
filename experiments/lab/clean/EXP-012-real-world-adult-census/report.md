# EXP-012 — Real-world Adult Census (report)

## Resumo (variando volume)

| Vol req | rows | cols | raw (B) | TCF (B) | TCF/raw | ratio | RT | enc ms | dec ms |
|---:|---:|---:|---:|---:|---:|---:|---|---:|---:|
| 100 | 100 | 15 | 10895 | 4576 | -6319 | 42.0% | OK | 10 | 3 |
| 500 | 500 | 15 | 54079 | 20242 | -33837 | 37.4% | OK | 36 | 10 |
| 1000 | 1000 | 15 | 108226 | 39615 | -68611 | 36.6% | OK | 63 | 19 |
| 5000 | 5000 | 15 | 539921 | 193010 | -346911 | 35.7% | OK | 331 | 78 |

## Stats per coluna (vol=1000)

| Coluna | det? | hint | runs | uniq |
|---|---|---|---:|---:|
| `age` | True | True | 15 | 63 |
| `workclass` | False | False | 0 | 7 |
| `fnlwgt` | True | True | 404 | 985 |
| `education` | False | False | 0 | 16 |
| `education-num` | True | True | 3 | 16 |
| `marital-status` | False | False | 0 | 6 |
| `occupation` | False | False | 0 | 14 |
| `relationship` | False | False | 0 | 6 |
| `race` | False | False | 0 | 5 |
| `sex` | False | False | 0 | 2 |
| `capital-gain` | True | True | 0 | 40 |
| `capital-loss` | True | True | 3 | 29 |
| `hours-per-week` | True | True | 4 | 60 |
| `native-country` | False | False | 0 | 31 |
| `class` | False | False | 0 | 2 |

## Validacao

- RT OK: 4/4
- ✓ Todos volumes RT byte-canonical OK

## Limitacoes

- 1 dataset real (Adult Census). TPC-H pendente.
- 4 volumes amostrados. Full 48k nao testado.
- order=natural fixo; outras orderings nao testadas.


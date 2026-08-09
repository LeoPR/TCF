# Data — hipóteses restantes (esboço de triagem)

`n=600`. `sem_spec`/`com_spec` são wire real com RT conferido; `h_*_naive` é cálculo sobre os mesmos dados (o piso a bater), não wire.

## H1-spec-bn

| caso | sem_spec | com_spec | spec_usou | ordinal_com_bn_estimado | lacuna_B | rota_do_ordinal |
|---|---|---|---|---|---|---|
| `k5` | 364 | 364 | False | 345 | 19 | #TCF.8B3258 |
| `k12` | 529 | 529 | False | 459 | 70 | #TCF.8B4258 |
| `k60` | 976 | 976 | False | 678 | 298 | #TCF.8B6258 |

## H2-dias-uteis

| caso | sem_spec | com_spec | spec_usou | h_delta_naive |
|---|---|---|---|---|
| `diario-controle` | 414 | 32 | True | 27 |
| `uteis` | 2471 | 1590 | True | 233 |
| `uteis-feriados` | 2878 | 1889 | True | 339 |

## H3-sentinelas

| caso | n_sentinelas | sem_spec | com_spec | spec_usou |
|---|---|---|---|---|
| `limpa` | 0 | 414 | 32 | True |
| `1-sentinela` | 1 | 445 | 56 | True |
| `3-sentinelas` | 3 | 501 | 108 | True |
| `zero-date-mysql` | 1 | 445 | 62 | True |
| `5pct-sentinela` | 30 | 2323 | 533 | True |

## H4-quase-null

| caso | sem_spec | com_spec | spec_usou |
|---|---|---|---|
| `95pct-null` | 483 | 401 | True |
| `99pct-null` | 105 | 97 | True |
| `um-so-valor` | 27 | 27 | False |

## H5-resolucao-mista

| caso | sem_spec | com_spec | spec_usou |
|---|---|---|---|
| `mes-e-dia` | 3764 | 3637 | True |
| `so-ano-mes` | 1037 | 1037 | False |

## H6-delta-coluna

| caso | sem_spec | com_spec | spec_usou | h_delta_naive | teto_da_lacuna_B |
|---|---|---|---|---|---|
| `espalhado-ordenado` | 5529 | 3759 | True | 643 | 3116 |

## H7-colunas-irmas

| caso | multi_col_independente | h_delta_entre_colunas_naive | lacuna_B | nota |
|---|---|---|---|---|
| `created-updated-shipped` | 2959 | 2870 | 89 | naive soma 3 wires separados; o real pagaria o envelope multi-col |


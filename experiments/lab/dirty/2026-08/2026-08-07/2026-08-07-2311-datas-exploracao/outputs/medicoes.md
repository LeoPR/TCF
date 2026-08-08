# DATA como tipo — exploração

`bytes/valor` = bytes do wire ÷ n. É a métrica que compara formatos de tamanhos
diferentes; o wire cru favoreceria sempre o formato mais curto.

## Eixo FORMATO — a mesma sequência diária, 10 grafias

### n = 12

| formato | len | k | bytes | bytes/valor | rota |
|---|---:|---:|---:|---:|---|
| `ano` | 4 | 1 | 17 | 1.42 | core |
| `ano-mes` | 7 | 1 | 21 | 1.75 | core |
| `br` | 10 | 12 | 33 | 2.75 | core+pol |
| `ponto` | 10 | 12 | 33 | 2.75 | core+pol |
| `iso-invertido` | 10 | 12 | 33 | 2.75 | core+pol |
| `extenso` | 11 | 12 | 34 | 2.83 | core |
| `epoch-dia` | 6 | 12 | 38 | 3.17 | core+pol |
| `compacto` | 8 | 12 | 45 | 3.75 | core+pol |
| `iso` | 10 | 12 | 47 | 3.92 | core+pol |
| `us` | 10 | 12 | 56 | 4.67 | core |

### n = 120

| formato | len | k | bytes | bytes/valor | rota |
|---|---:|---:|---:|---:|---|
| `ano` | 4 | 1 | 18 | 0.15 | core |
| `epoch-dia` | 6 | 120 | 22 | 0.18 | core |
| `ano-mes` | 7 | 4 | 46 | 0.38 | core+pol |
| `compacto` | 8 | 120 | 89 | 0.74 | core+pol |
| `us` | 10 | 120 | 93 | 0.78 | core+pol |
| `extenso` | 11 | 120 | 94 | 0.78 | core+pol |
| `br` | 10 | 120 | 96 | 0.80 | core+pol |
| `ponto` | 10 | 120 | 96 | 0.80 | core+pol |
| `iso-invertido` | 10 | 120 | 96 | 0.80 | core+pol |
| `iso` | 10 | 120 | 97 | 0.81 | core+pol |

### n = 1200

| formato | len | k | bytes | bytes/valor | rota |
|---|---:|---:|---:|---:|---|
| `epoch-dia` | 6 | 1200 | 23 | 0.02 | core |
| `ano` | 4 | 4 | 47 | 0.04 | core |
| `ano-mes` | 7 | 40 | 426 | 0.35 | core |
| `compacto` | 8 | 1200 | 629 | 0.52 | core+pol |
| `extenso` | 11 | 1200 | 814 | 0.68 | core+pol |
| `iso` | 10 | 1200 | 829 | 0.69 | core+pol |
| `us` | 10 | 1200 | 849 | 0.71 | core+pol |
| `br` | 10 | 1200 | 852 | 0.71 | core+pol |
| `ponto` | 10 | 1200 | 852 | 0.71 | core+pol |
| `iso-invertido` | 10 | 1200 | 852 | 0.71 | core+pol |

## Eixo PRECISÃO — campo a campo, sobre o mesmo instante

### n = 12

| precisão | len | k | bytes | bytes/valor | Δ vs anterior | rota |
|---|---:|---:|---:|---:|---:|---|
| `P1-ano` | 4 | 1 | 17 | 1.42 | — | core |
| `P2-ano-mes` | 7 | 1 | 21 | 1.75 | +4 | core |
| `P3-data` | 10 | 1 | 24 | 2.00 | +3 | core+pol |
| `P4-data-hora` | 16 | 12 | 79 | 6.58 | +55 | core+pol |
| `P5-data-hora-seg` | 19 | 12 | 115 | 9.58 | +36 | core+pol |
| `P6-milissegundo` | 23 | 12 | 153 | 12.75 | +38 | core+pol |
| `P7-tz-Z` | 20 | 12 | 127 | 10.58 | -26 | core+pol |
| `P8-tz-offset` | 25 | 12 | 155 | 12.92 | +28 | core+pol |

### n = 120

| precisão | len | k | bytes | bytes/valor | Δ vs anterior | rota |
|---|---:|---:|---:|---:|---:|---|
| `P1-ano` | 4 | 1 | 18 | 0.15 | — | core |
| `P2-ano-mes` | 7 | 1 | 22 | 0.18 | +4 | core |
| `P3-data` | 10 | 1 | 25 | 0.21 | +3 | core+pol |
| `P4-data-hora` | 16 | 120 | 725 | 6.04 | +700 | core+pol |
| `P5-data-hora-seg` | 19 | 120 | 1322 | 11.02 | +597 | core+pol |
| `P6-milissegundo` | 23 | 120 | 1802 | 15.02 | +480 | core+pol |
| `P7-tz-Z` | 20 | 120 | 1442 | 12.02 | -360 | core+pol |
| `P8-tz-offset` | 25 | 120 | 1686 | 14.05 | +244 | core+pol |

### n = 1200

| precisão | len | k | bytes | bytes/valor | Δ vs anterior | rota |
|---|---:|---:|---:|---:|---:|---|
| `P1-ano` | 4 | 1 | 19 | 0.02 | — | core |
| `P2-ano-mes` | 7 | 1 | 23 | 0.02 | +4 | core |
| `P3-data` | 10 | 2 | 35 | 0.03 | +12 | core+pol |
| `P4-data-hora` | 16 | 1200 | 8612 | 7.18 | +8577 | core+pol |
| `P5-data-hora-seg` | 19 | 1200 | 15579 | 12.98 | +6967 | core+pol |
| `P6-milissegundo` | 23 | 1200 | 17770 | 14.81 | +2191 | core+pol |
| `P7-tz-Z` | 20 | 1200 | 16779 | 13.98 | -991 | core+pol |
| `P8-tz-offset` | 25 | 1200 | 19183 | 15.99 | +2404 | core+pol |

## Eixo REGIME — como os valores se distribuem

As três últimas colunas são **hipóteses naive**, não wire: o piso que um
tratamento por natureza teria de bater.

### n = 12 — datas (ISO)

| regime | k | bytes | bytes/valor | rota | H-split | H-delta | H-epoch | melhor |
|---|---:|---:|---:|---|---:|---:|---:|---|
| `R1-diario` | 12 | 47 | 3.92 | core+pol | 49 | 34 | 38 | **delta** |
| `R2-semanal` | 12 | 69 | 5.75 | core+pol | 75 | 34 | 28 | **epoch** |
| `R3-mensal` | 12 | 119 | 9.92 | core+pol | 99 | 35 | 42 | **delta** |
| `R4-repetido-k5` | 5 | 69 | 5.75 | bN | 84 | 44 | 40 | **epoch** |
| `R5-agrupado` | 2 | 32 | 2.67 | core+pol | 54 | 39 | 28 | **epoch** |
| `R6-espalhado` | 12 | 149 | 12.42 | core+pol | 147 | 81 | 94 | **delta** |
| `R7-espalhado-ordenado` | 12 | 153 | 12.75 | core+pol | 144 | 70 | 95 | **delta** |
| `R8-descendente` | 12 | 47 | 3.92 | core+pol | 49 | 35 | 43 | **delta** |

### n = 12 — timestamps

| regime | len | k | bytes | bytes/valor | rota |
|---|---:|---:|---:|---:|---|
| `T1-log-mesmo-dia` | 19 | 12 | 56 | 4.67 | core+pol |
| `T2-log-esparso` | 19 | 12 | 163 | 13.58 | core+pol |
| `T3-varios-dias` | 19 | 12 | 55 | 4.58 | core+pol |
| `T4-hora-redonda` | 19 | 12 | 55 | 4.58 | core+pol |

### n = 120 — datas (ISO)

| regime | k | bytes | bytes/valor | rota | H-split | H-delta | H-epoch | melhor |
|---|---:|---:|---:|---|---:|---:|---:|---|
| `R1-diario` | 120 | 97 | 0.81 | core+pol | 177 | 35 | 22 | **epoch** |
| `R2-semanal` | 120 | 544 | 4.53 | core+pol | 312 | 35 | 22 | **epoch** |
| `R3-mensal` | 120 | 1051 | 8.76 | core+pol | 328 | 36 | 23 | **epoch** |
| `R4-repetido-k5` | 5 | 123 | 1.02 | bN | 176 | 62 | 94 | **delta** |
| `R5-agrupado` | 12 | 63 | 0.53 | core+pol | 55 | 60 | 73 | **split** |
| `R6-espalhado` | 119 | 1124 | 9.37 | core+pol | 519 | 610 | 869 | **split** |
| `R7-espalhado-ordenado` | 119 | 1199 | 9.99 | core+pol | 462 | 405 | 774 | **delta** |
| `R8-descendente` | 120 | 405 | 3.38 | core+pol | 194 | 36 | 22 | **epoch** |

### n = 120 — timestamps

| regime | len | k | bytes | bytes/valor | rota |
|---|---:|---:|---:|---:|---|
| `T1-log-mesmo-dia` | 19 | 120 | 76 | 0.63 | core+pol |
| `T2-log-esparso` | 19 | 120 | 1452 | 12.10 | core+pol |
| `T3-varios-dias` | 19 | 120 | 148 | 1.23 | core+pol |
| `T4-hora-redonda` | 19 | 120 | 148 | 1.23 | core+pol |

### n = 1200 — datas (ISO)

| regime | k | bytes | bytes/valor | rota | H-split | H-delta | H-epoch | melhor |
|---|---:|---:|---:|---|---:|---:|---:|---|
| `R1-diario` | 1200 | 829 | 0.69 | core+pol | 1365 | 36 | 23 | **epoch** |
| `R2-semanal` | 1200 | 5504 | 4.59 | core+pol | 2040 | 36 | 23 | **epoch** |
| `R3-mensal` | 1200 | 14871 | 12.39 | core+pol | 2455 | 37 | 24 | **epoch** |
| `R4-repetido-k5` | 5 | 664 | 0.55 | bN | 1079 | 243 | 635 | **delta** |
| `R5-agrupado` | 120 | 980 | 0.82 | core | 766 | 241 | 529 | **delta** |
| `R6-espalhado` | 1026 | 11052 | 9.21 | core+pol | 2866 | 5975 | 8232 | **split** |
| `R7-espalhado-ordenado` | 1026 | 10221 | 8.52 | core+pol | 2060 | 1117 | 6494 | **delta** |
| `R8-descendente` | 1200 | 892 | 0.74 | core+pol | 1376 | 37 | 23 | **epoch** |

### n = 1200 — timestamps

| regime | len | k | bytes | bytes/valor | rota |
|---|---:|---:|---:|---:|---|
| `T1-log-mesmo-dia` | 19 | 1200 | 372 | 0.31 | core+pol |
| `T2-log-esparso` | 19 | 1191 | 14010 | 11.68 | core+pol |
| `T3-varios-dias` | 19 | 1200 | 1151 | 0.96 | core+pol |
| `T4-hora-redonda` | 19 | 1200 | 1151 | 0.96 | core+pol |


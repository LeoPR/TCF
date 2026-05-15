# EXP-008 — Compressao comparada (relatorio)

**Data execucao**: 2026-05-15T03:41:51.079880+00:00
**TCF source**: `src/tcf`
**Datasets**: 15
**Compressores**: gzip, brotli, zstd, lzma, bz2 (niveis maximos)
**Reps**: tcf=20, compressores=100

## Sumario global

- **Raw total**: 4812 bytes em 15 datasets
- **TCF total**: 3131 bytes (65.1% raw)
- **RT TCF**: 15/15 OK

Compressores aplicados a raw e a tcf:

| compressor | total raw | total tcf | tcf vs raw |
|---|---:|---:|---:|
| gzip | 1942 | 2383 | 1.23x |
| brotli | 1669 | 2141 | 1.28x |
| zstd | 1809 | 2228 | 1.23x |
| lzma | 2636 | 3276 | 1.24x |
| bz2 | 2266 | 2632 | 1.16x |

## Bytes por dataset

| dataset | raw | tcf | gzip/raw | gzip/tcf | brotli/raw | brotli/tcf | zstd/raw | zstd/tcf | lzma/raw | lzma/tcf | bz2/raw | bz2/tcf |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| D1-emails-simples | 191 | 118 | 89 | 117 | 71 | 97 | 87 | 104 | 132 | 172 | 107 | 132 |
| D2-emails-quote-id | 247 | 166 | 118 | 150 | 103 | 141 | 109 | 138 | 164 | 208 | 136 | 162 |
| D3-stress-substring | 344 | 177 | 114 | 150 | 87 | 131 | 104 | 140 | 152 | 212 | 132 | 169 |
| D4-caos-mix | 156 | 113 | 73 | 108 | 65 | 95 | 71 | 95 | 112 | 160 | 87 | 119 |
| D5-padroes-multiplos | 418 | 281 | 139 | 170 | 111 | 152 | 130 | 160 | 188 | 232 | 181 | 210 |
| D6-poucos-em-ruido | 533 | 287 | 188 | 217 | 164 | 195 | 181 | 209 | 240 | 284 | 230 | 228 |
| D7-aninhamento | 337 | 215 | 112 | 149 | 88 | 131 | 108 | 141 | 156 | 204 | 118 | 159 |
| D8-cabeca-cauda | 384 | 100 | 96 | 93 | 64 | 66 | 87 | 86 | 132 | 124 | 107 | 102 |
| D9-frequencia-alta | 371 | 158 | 96 | 114 | 68 | 95 | 84 | 102 | 136 | 160 | 111 | 124 |
| D10-datas-mundiais | 173 | 191 | 113 | 150 | 105 | 140 | 103 | 137 | 160 | 212 | 115 | 156 |
| D11-datetime-precisao | 300 | 209 | 114 | 148 | 100 | 134 | 104 | 137 | 160 | 224 | 135 | 172 |
| D12-datetime-timezone | 381 | 235 | 151 | 191 | 134 | 173 | 142 | 177 | 196 | 248 | 169 | 210 |
| D13-cpf-variados | 207 | 206 | 115 | 143 | 101 | 130 | 112 | 138 | 172 | 212 | 126 | 152 |
| D14-uuid-variados | 451 | 422 | 202 | 252 | 185 | 240 | 186 | 245 | 260 | 332 | 248 | 279 |
| D15-base64-variados | 319 | 253 | 222 | 231 | 223 | 221 | 201 | 219 | 276 | 292 | 264 | 258 |
| **TOTAL** | **4812** | **3131** | **1942** | **2383** | **1669** | **2141** | **1809** | **2228** | **2636** | **3276** | **2266** | **2632** |

## Ratio versus raw

`tcf/raw` e `C(*)/raw` — quanto cada saida ocupa em relacao ao raw original do dataset.

| dataset | tcf | gzip(raw) | gzip(tcf) | brotli(raw) | brotli(tcf) | zstd(raw) | zstd(tcf) | lzma(raw) | lzma(tcf) | bz2(raw) | bz2(tcf) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| D1-emails-simples | 62% | 47% | 61% | 37% | 51% | 46% | 54% | 69% | 90% | 56% | 69% |
| D2-emails-quote-id | 67% | 48% | 61% | 42% | 57% | 44% | 56% | 66% | 84% | 55% | 66% |
| D3-stress-substring | 51% | 33% | 44% | 25% | 38% | 30% | 41% | 44% | 62% | 38% | 49% |
| D4-caos-mix | 72% | 47% | 69% | 42% | 61% | 46% | 61% | 72% | 103% | 56% | 76% |
| D5-padroes-multiplos | 67% | 33% | 41% | 27% | 36% | 31% | 38% | 45% | 56% | 43% | 50% |
| D6-poucos-em-ruido | 54% | 35% | 41% | 31% | 37% | 34% | 39% | 45% | 53% | 43% | 43% |
| D7-aninhamento | 64% | 33% | 44% | 26% | 39% | 32% | 42% | 46% | 61% | 35% | 47% |
| D8-cabeca-cauda | 26% | 25% | 24% | 17% | 17% | 23% | 22% | 34% | 32% | 28% | 27% |
| D9-frequencia-alta | 43% | 26% | 31% | 18% | 26% | 23% | 27% | 37% | 43% | 30% | 33% |
| D10-datas-mundiais | 110% | 65% | 87% | 61% | 81% | 60% | 79% | 92% | 123% | 66% | 90% |
| D11-datetime-precisao | 70% | 38% | 49% | 33% | 45% | 35% | 46% | 53% | 75% | 45% | 57% |
| D12-datetime-timezone | 62% | 40% | 50% | 35% | 45% | 37% | 46% | 51% | 65% | 44% | 55% |
| D13-cpf-variados | 100% | 56% | 69% | 49% | 63% | 54% | 67% | 83% | 102% | 61% | 73% |
| D14-uuid-variados | 94% | 45% | 56% | 41% | 53% | 41% | 54% | 58% | 74% | 55% | 62% |
| D15-base64-variados | 79% | 70% | 72% | 70% | 69% | 63% | 69% | 87% | 92% | 83% | 81% |

## TCF como pre-tx: C(tcf) / C(raw)

Valor **<1** = TCF reduz tamanho final do pipeline. **~1** = ortogonal. **>1** = TCF aumenta tamanho final (redundancia ja' explorada pelo compressor, ou overhead TCF supera a reducao).

| dataset | gzip | brotli | zstd | lzma | bz2 |
|---|---|---|---|---|---|
| D1-emails-simples | 1.31 | 1.37 | 1.20 | 1.30 | 1.23 |
| D2-emails-quote-id | 1.27 | 1.37 | 1.27 | 1.27 | 1.19 |
| D3-stress-substring | 1.32 | 1.51 | 1.35 | 1.39 | 1.28 |
| D4-caos-mix | 1.48 | 1.46 | 1.34 | 1.43 | 1.37 |
| D5-padroes-multiplos | 1.22 | 1.37 | 1.23 | 1.23 | 1.16 |
| D6-poucos-em-ruido | 1.15 | 1.19 | 1.15 | 1.18 | 0.99 |
| D7-aninhamento | 1.33 | 1.49 | 1.31 | 1.31 | 1.35 |
| D8-cabeca-cauda | 0.97 | 1.03 | 0.99 | 0.94 | 0.95 |
| D9-frequencia-alta | 1.19 | 1.40 | 1.21 | 1.18 | 1.12 |
| D10-datas-mundiais | 1.33 | 1.33 | 1.33 | 1.32 | 1.36 |
| D11-datetime-precisao | 1.30 | 1.34 | 1.32 | 1.40 | 1.27 |
| D12-datetime-timezone | 1.26 | 1.29 | 1.25 | 1.27 | 1.24 |
| D13-cpf-variados | 1.24 | 1.29 | 1.23 | 1.23 | 1.21 |
| D14-uuid-variados | 1.25 | 1.30 | 1.32 | 1.28 | 1.12 |
| D15-base64-variados | 1.04 | 0.99 | 1.09 | 1.06 | 0.98 |

## Menor bytes por dataset (campeao global)

| dataset | raw | menor | metodo | reducao |
|---|---:|---:|---|---:|
| D1-emails-simples | 191 | 71 | brotli(raw) | 37% |
| D2-emails-quote-id | 247 | 103 | brotli(raw) | 42% |
| D3-stress-substring | 344 | 87 | brotli(raw) | 25% |
| D4-caos-mix | 156 | 65 | brotli(raw) | 42% |
| D5-padroes-multiplos | 418 | 111 | brotli(raw) | 27% |
| D6-poucos-em-ruido | 533 | 164 | brotli(raw) | 31% |
| D7-aninhamento | 337 | 88 | brotli(raw) | 26% |
| D8-cabeca-cauda | 384 | 64 | brotli(raw) | 17% |
| D9-frequencia-alta | 371 | 68 | brotli(raw) | 18% |
| D10-datas-mundiais | 173 | 103 | zstd(raw) | 60% |
| D11-datetime-precisao | 300 | 100 | brotli(raw) | 33% |
| D12-datetime-timezone | 381 | 134 | brotli(raw) | 35% |
| D13-cpf-variados | 207 | 101 | brotli(raw) | 49% |
| D14-uuid-variados | 451 | 185 | brotli(raw) | 41% |
| D15-base64-variados | 319 | 201 | zstd(raw) | 63% |

## Roundtrip

- **RT TCF**: `decode(encode(D)) == D`
- **RT full**: `decode(C.decompress(C.compress(encode(D)))).decode == D` (stack completo)

RT TCF: 15/15
RT full (todos compressores × todos datasets): OK

## Tempo (mediana, microssegundos)

Compressao em nivel maximo. Medianas sobre 20 reps (TCF) e 100 reps (compressores). Resolucao do clock = ~100ns no Windows; operacoes <10us tem ruido significativo.

### TCF encode/decode

| dataset | encode | decode |
|---|---:|---:|
| D1-emails-simples | 2648.4 | 72.8 |
| D2-emails-quote-id | 1220.2 | 67.0 |
| D3-stress-substring | 2735.1 | 80.8 |
| D4-caos-mix | 1793.6 | 52.5 |
| D5-padroes-multiplos | 829.1 | 85.0 |
| D6-poucos-em-ruido | 1008.4 | 86.9 |
| D7-aninhamento | 1311.9 | 108.8 |
| D8-cabeca-cauda | 908.8 | 104.2 |
| D9-frequencia-alta | 2142.9 | 78.5 |
| D10-datas-mundiais | 1639.3 | 141.4 |
| D11-datetime-precisao | 2171.8 | 151.7 |
| D12-datetime-timezone | 2106.7 | 167.6 |
| D13-cpf-variados | 1023.8 | 67.8 |
| D14-uuid-variados | 1030.0 | 144.7 |
| D15-base64-variados | 684.0 | 149.3 |

### Compressor sobre raw

| dataset | gzip | brotli | zstd | lzma | bz2 |
|---|---|---|---|---|---|
| D1-emails-simples | 40.5 | 1178.8 | 55.8 | 55419.8 | 140.1 |
| D2-emails-quote-id | 14.1 | 1290.8 | 66.8 | 55420.1 | 156.1 |
| D3-stress-substring | 41.9 | 1560.8 | 126.6 | 56161.1 | 152.6 |
| D4-caos-mix | 12.9 | 1330.2 | 41.2 | 55755.8 | 116.0 |
| D5-padroes-multiplos | 16.0 | 1675.5 | 147.2 | 54996.7 | 160.7 |
| D6-poucos-em-ruido | 17.0 | 1778.3 | 168.6 | 55051.4 | 189.4 |
| D7-aninhamento | 35.1 | 1323.8 | 117.0 | 55321.7 | 140.4 |
| D8-cabeca-cauda | 28.0 | 1328.8 | 129.9 | 54641.0 | 133.9 |
| D9-frequencia-alta | 35.2 | 1542.8 | 114.3 | 54649.9 | 130.8 |
| D10-datas-mundiais | 35.0 | 1232.8 | 40.7 | 53869.7 | 117.0 |
| D11-datetime-precisao | 36.2 | 1175.8 | 85.1 | 54597.9 | 146.2 |
| D12-datetime-timezone | 24.2 | 1592.0 | 114.8 | 54968.2 | 158.2 |
| D13-cpf-variados | 15.1 | 987.7 | 48.4 | 55060.9 | 120.8 |
| D14-uuid-variados | 24.2 | 1628.8 | 120.9 | 54622.3 | 183.8 |
| D15-base64-variados | 40.1 | 1691.2 | 64.1 | 54422.9 | 177.9 |

### Compressor sobre tcf

| dataset | gzip | brotli | zstd | lzma | bz2 |
|---|---|---|---|---|---|
| D1-emails-simples | 44.3 | 1263.1 | 24.7 | 54732.7 | 135.8 |
| D2-emails-quote-id | 23.7 | 1269.1 | 27.5 | 55904.0 | 146.9 |
| D3-stress-substring | 40.8 | 1376.3 | 31.5 | 56167.9 | 129.1 |
| D4-caos-mix | 13.5 | 1322.5 | 23.9 | 54812.2 | 123.7 |
| D5-padroes-multiplos | 16.2 | 1649.3 | 64.7 | 55315.5 | 158.5 |
| D6-poucos-em-ruido | 17.5 | 1579.7 | 46.9 | 54915.8 | 154.9 |
| D7-aninhamento | 34.5 | 1404.7 | 42.7 | 54405.6 | 124.9 |
| D8-cabeca-cauda | 26.0 | 1147.4 | 21.9 | 54737.6 | 113.7 |
| D9-frequencia-alta | 33.9 | 1532.0 | 32.9 | 54461.5 | 121.3 |
| D10-datas-mundiais | 30.7 | 1372.4 | 37.5 | 54660.0 | 120.5 |
| D11-datetime-precisao | 35.6 | 1143.7 | 41.2 | 55014.7 | 129.0 |
| D12-datetime-timezone | 16.6 | 1590.8 | 41.3 | 54907.3 | 144.2 |
| D13-cpf-variados | 15.2 | 1007.5 | 41.0 | 55266.6 | 119.8 |
| D14-uuid-variados | 19.5 | 1734.7 | 82.8 | 55034.1 | 179.5 |
| D15-base64-variados | 40.8 | 1664.4 | 36.3 | 54323.2 | 150.7 |

## Observacoes (computadas)

- **TCF stand-alone reduz bytes**: 14/15 datasets. Melhor caso: `D8-cabeca-cauda` = 26% raw. Pior caso: `D10-datas-mundiais` = 110% raw.
- **TCF como pre-tx (C(tcf) < C(raw))**: gzip=1/15, brotli=1/15, zstd=1/15, lzma=1/15, bz2=3/15.
- **Campeao bytes por dataset**: brotli(raw)=13, zstd(raw)=2.
- **Soma dos melhores por dataset**: 1645 bytes (34.2% do raw total). Limite inferior empirico sobre esse conjunto de compressores.
- **Latencia media (us)**: tcf encode=1550, tcf decode=104; compressores=gzip=28us, zstd=96us, bz2=148us, brotli=1421us, lzma=54997us.

## Notas metodologicas

- **D10-D15** sao variety datasets (poucas repeticoes por tipo); TCF-CORE atual nao tem type encoders (Estrategia 1.A do roadmap), entao baixa redundancia interna. Comportamento esperado: compressores gerais relativamente melhores.
- **Escala**: raw 100-500 bytes/dataset. Overhead fixo de gzip/brotli/zstd (~20-40 bytes header) e' significativo aqui. Inversoes de tendencia podem ocorrer em escalas maiores.
- **Niveis maximos**: gzip=9, brotli=11, zstd=22, lzma preset=9, bz2=9. Foco em bytes; latencia caracterizada como custo associado, nao otimizada.
- **gzip ≠ TCF** (ver feedback `gzip_e_compressao_externa`): comparacao e' qualitativa, nao criterio de descarte/aprovacao.

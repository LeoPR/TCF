# 03 — Latencia (microssegundos)

Compressao nos niveis maximos. Medianas de 20 reps (serialize/parse) e 30 reps (compress/decompress). Resolucao do clock ≈ 100ns em Windows; operacoes <10us tem ruido relevante.

## Serialize / parse por formato

Mediana **entre datasets** (us).

| formato | serialize | parse |
|---|---:|---:|
| csv | **0.6** | **1.4** |
| jsonl | 66.8 | 40.1 |
| json | _8.0_ | _4.4_ |
| tcf | 1361.8 | 132.3 |

## Compress por compressor

Mediana **entre todos os pares (formato × dataset)** (us).

| compressor | compress (us) | decompress (us) |
|---|---:|---:|
| gzip | **21.4** | 9.3 |
| brotli | 1580.2 | _9.2_ |
| zstd | _106.5_ | **3.7** |
| lzma | 55252.9 | 1052.7 |
| bz2 | 153.2 | 59.2 |

## Ranking (mediana global)

Ordenados por **soma de mediana compress + decompress** (ida e volta, menor = mais rapido).

| pos | compressor | compress + decompress (us) |
|---:|---|---:|
| 1 | `gzip` | 30.8 |
| 2 | `zstd` | 110.2 |
| 3 | `bz2` | 212.4 |
| 4 | `brotli` | 1589.5 |
| 5 | `lzma` | 56305.5 |

## Detalhe por dataset (compress sobre tcf)

| dataset | gzip | brotli | zstd | lzma | bz2 |
|---|---:|---:|---:|---:|---:|
| D1-emails-simples | **21.0** | 1168.8 | _25.1_ | 54611.4 | 120.3 |
| D2-emails-quote-id | **21.7** | 1374.8 | _27.7_ | 55130.3 | 120.9 |
| D3-stress-substring | _76.0_ | 1325.9 | **30.6** | 55631.5 | 132.2 |
| D4-caos-mix | **20.4** | 1238.5 | _23.8_ | 55660.2 | 121.7 |
| D5-padroes-multiplos | **23.6** | 1588.7 | _66.3_ | 54507.2 | 160.6 |
| D6-poucos-em-ruido | **18.0** | 1471.1 | _47.6_ | 55402.3 | 158.7 |
| D7-aninhamento | **16.4** | 1446.2 | _42.2_ | 55398.5 | 136.2 |
| D8-cabeca-cauda | _75.4_ | 1112.2 | **21.8** | 55276.8 | 114.8 |
| D9-frequencia-alta | **20.1** | 1195.0 | _22.6_ | 55561.0 | 114.7 |
| D10-datas-mundiais | **15.1** | 1416.8 | _37.1_ | 54928.8 | 121.3 |
| D11-datetime-precisao | **15.2** | 1178.4 | _40.7_ | 55373.4 | 129.1 |
| D12-datetime-timezone | _82.0_ | 1602.9 | **40.9** | 55198.1 | 154.4 |
| D13-cpf-variados | **16.0** | 1086.0 | _39.5_ | 54636.1 | 126.5 |
| D14-uuid-variados | **19.8** | 1769.7 | _80.1_ | 54897.4 | 177.8 |
| D15-base64-variados | **18.7** | 1674.5 | _36.8_ | 55483.6 | 159.2 |
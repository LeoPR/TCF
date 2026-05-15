# 03 — Latencia (microssegundos)

Compressao nos niveis maximos. Medianas de 20 reps (serialize/parse) e 30 reps (compress/decompress). Resolucao do clock ≈ 100ns em Windows; operacoes <10us tem ruido relevante.

## Serialize / parse por formato

Mediana **entre datasets** (us).

| formato | serialize | parse |
|---|---:|---:|
| csv | **0.6** | **1.5** |
| jsonl | 64.5 | 38.0 |
| json | _6.8_ | _3.6_ |
| tcf | 1528.2 | 105.1 |

## Compress por compressor

Mediana **entre todos os pares (formato × dataset)** (us).

| compressor | compress (us) | decompress (us) |
|---|---:|---:|
| gzip | **32.4** | 12.7 |
| brotli | 1583.8 | _8.1_ |
| zstd | _104.8_ | **3.6** |
| lzma | 55103.9 | 1066.2 |
| bz2 | 162.4 | 85.2 |

## Ranking (mediana global)

Ordenados por **soma de mediana compress + decompress** (ida e volta, menor = mais rapido).

| pos | compressor | compress + decompress (us) |
|---:|---|---:|
| 1 | `gzip` | 45.0 |
| 2 | `zstd` | 108.4 |
| 3 | `bz2` | 247.6 |
| 4 | `brotli` | 1591.8 |
| 5 | `lzma` | 56170.0 |

## Detalhe por dataset (compress sobre tcf)

| dataset | gzip | brotli | zstd | lzma | bz2 |
|---|---:|---:|---:|---:|---:|
| D1-emails-simples | _36.5_ | 1274.4 | **24.9** | 54932.1 | 138.3 |
| D2-emails-quote-id | _34.7_ | 1476.8 | **27.6** | 60559.9 | 144.4 |
| D3-stress-substring | _35.7_ | 1330.7 | **30.4** | 54505.5 | 144.2 |
| D4-caos-mix | _27.0_ | 1220.9 | **23.5** | 58086.4 | 137.1 |
| D5-padroes-multiplos | **30.5** | 1684.4 | _65.0_ | 56637.8 | 179.8 |
| D6-poucos-em-ruido | **32.0** | 1608.2 | _46.5_ | 56172.3 | 169.6 |
| D7-aninhamento | **29.6** | 1407.1 | _42.3_ | 54723.4 | 125.6 |
| D8-cabeca-cauda | _33.5_ | 1195.7 | **21.3** | 54777.2 | 136.6 |
| D9-frequencia-alta | _35.7_ | 1391.5 | **32.6** | 54459.0 | 119.9 |
| D10-datas-mundiais | **36.1** | 1358.0 | _36.8_ | 55349.0 | 125.4 |
| D11-datetime-precisao | **34.7** | 1078.0 | _40.6_ | 56473.8 | 131.5 |
| D12-datetime-timezone | **31.1** | 1721.8 | _40.7_ | 55015.4 | 172.2 |
| D13-cpf-variados | **34.9** | 1152.2 | _40.0_ | 54816.7 | 147.6 |
| D14-uuid-variados | **45.5** | 1871.8 | _79.5_ | 54573.9 | 199.9 |
| D15-base64-variados | _38.4_ | 1518.3 | **35.7** | 53706.1 | 157.9 |
# 05 — Campeao por dataset

Para cada dataset, qual (formato, compressor) produz **menor** bytes. Inclui tambem ranking dos 3 menores por dataset.

## Top-3 menor por dataset

| dataset | raw csv | 1o (menor) | 2o | 3o | reducao 1o |
|---|---:|---|---|---|---:|
| D1-emails-simples | 195 | **csv/brotli** = 73 | _json/brotli_ = 80 | csv/zstd = 89 | 37% |
| D2-emails-quote-id | 251 | **csv/brotli** = 110 | _csv/zstd_ = 111 | json/brotli = 111 | 44% |
| D3-stress-substring | 348 | **csv/brotli** = 90 | _json/brotli_ = 93 | jsonl/brotli = 100 | 26% |
| D4-caos-mix | 160 | **csv/brotli** = 65 | _csv/zstd_ = 67 | jsonl/brotli = 71 | 41% |
| D5-padroes-multiplos | 422 | **csv/brotli** = 114 | _json/brotli_ = 124 | csv/zstd = 132 | 27% |
| D6-poucos-em-ruido | 537 | **csv/brotli** = 169 | _json/brotli_ = 172 | csv/zstd = 183 | 31% |
| D7-aninhamento | 341 | **json/brotli** = 88 | _csv/brotli_ = 94 | jsonl/brotli = 109 | 26% |
| D8-cabeca-cauda | 388 | **tcf/brotli** = 66 | _csv/brotli_ = 68 | json/brotli = 71 | 17% |
| D9-frequencia-alta | 375 | **tcf/zstd** = 69 | _tcf/brotli_ = 70 | csv/brotli = 74 | 18% |
| D10-datas-mundiais | 177 | **csv/zstd** = 106 | _csv/brotli_ = 110 | json/zstd = 112 | 60% |
| D11-datetime-precisao | 304 | **csv/brotli** = 109 | _csv/zstd_ = 109 | json/brotli = 109 | 36% |
| D12-datetime-timezone | 385 | **json/brotli** = 137 | _csv/brotli_ = 142 | csv/zstd = 144 | 36% |
| D13-cpf-variados | 211 | **csv/brotli** = 112 | _json/brotli_ = 115 | csv/zstd = 117 | 53% |
| D14-uuid-variados | 455 | **csv/brotli** = 184 | _csv/zstd_ = 189 | json/brotli = 191 | 40% |
| D15-base64-variados | 323 | **csv/zstd** = 203 | _json/zstd_ = 215 | tcf/zstd = 219 | 63% |

## Frequencia do campeao

Quantas vezes cada combinacao `(formato, compressor)` foi a melhor.

| combinacao | vitorias |
|---|---:|
| `csv/brotli` | 9/15 |
| `json/brotli` | 2/15 |
| `csv/zstd` | 2/15 |
| `tcf/brotli` | 1/15 |
| `tcf/zstd` | 1/15 |

## Soma global do menor por dataset

- **Raw CSV total**: 4872 bytes
- **Soma do menor por dataset**: 1695 bytes (34.8% do raw CSV).
- Limite inferior empirico **sobre o conjunto medido** — compressores adicionais (snappy, lz4, parquet com diferentes engines) podem mover esse limite.
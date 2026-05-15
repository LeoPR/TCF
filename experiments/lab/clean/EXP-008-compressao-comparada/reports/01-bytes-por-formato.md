# 01 — Bytes por dataset × formato (sem compressao)

Quanto cada formato textual ocupa por dataset, antes de qualquer compressao externa. **Bold** = menor por linha. _Italico_ = segundo menor.

## Tabela

| dataset | linhas | csv | jsonl | json | tcf |
|---|---:|---:|---:|---:|---:|
| D1-emails-simples | 12 | _195_ | 323 | 227 | **118** |
| D2-emails-quote-id | 12 | _251_ | 379 | 283 | **166** |
| D3-stress-substring | 12 | _348_ | 476 | 380 | **177** |
| D4-caos-mix | 12 | _160_ | 288 | 192 | **113** |
| D5-padroes-multiplos | 12 | _422_ | 550 | 454 | **281** |
| D6-poucos-em-ruido | 12 | _537_ | 665 | 569 | **287** |
| D7-aninhamento | 12 | _341_ | 469 | 373 | **215** |
| D8-cabeca-cauda | 12 | _388_ | 516 | 420 | **100** |
| D9-frequencia-alta | 20 | _375_ | 591 | 431 | **158** |
| D10-datas-mundiais | 15 | **177** | 338 | 218 | _191_ |
| D11-datetime-precisao | 13 | _304_ | 443 | 339 | **209** |
| D12-datetime-timezone | 14 | _385_ | 535 | 423 | **235** |
| D13-cpf-variados | 15 | _211_ | 372 | 252 | **206** |
| D14-uuid-variados | 12 | _455_ | 583 | 487 | **422** |
| D15-base64-variados | 14 | _323_ | 473 | 361 | **253** |
| **TOTAL** | **199** | **_4872_** | **7001** | **5409** | **3131** |

## Observacoes

- **Formato mais compacto por dataset**: `csv`=1, `tcf`=14.
- **TCF / CSV total**: 3131 / 4872 = 64.3%.
- **JSON array / CSV total**: 5409 / 4872 = 111.0%.
- **JSONL / CSV total**: 7001 / 4872 = 143.7%.

TCF, JSON e JSONL sao avaliados como **contra-prova de formato**: se TCF reduzir vs CSV, e JSON tambem reduzir, entao o ganho do TCF nao e' apenas escape de delimitador — e' compactacao de redundancia.
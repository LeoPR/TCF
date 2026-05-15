# 04 — Roundtrip

Verificacao de identidade nas N combinacoes formato × compressor × dataset.

## RT formato

`parse(serialize(linhas)) == linhas` — **60/60** OK.

## RT compressor (bytes)

`decompress(compress(bytes)) == bytes` — **300/300** OK.

## RT full (cadeia inteira)

`parse(decompress(compress(serialize(linhas)))) == linhas` — **300/300** OK.

## Matriz por dataset × formato (todos compressores)

Cada celula = OK se TODAS as decompressoes (5 compressores) recuperam os dados originais.

| dataset | csv | jsonl | json | tcf |
|---|---|---|---|---|
| D1-emails-simples | **OK** | **OK** | **OK** | **OK** |
| D2-emails-quote-id | **OK** | **OK** | **OK** | **OK** |
| D3-stress-substring | **OK** | **OK** | **OK** | **OK** |
| D4-caos-mix | **OK** | **OK** | **OK** | **OK** |
| D5-padroes-multiplos | **OK** | **OK** | **OK** | **OK** |
| D6-poucos-em-ruido | **OK** | **OK** | **OK** | **OK** |
| D7-aninhamento | **OK** | **OK** | **OK** | **OK** |
| D8-cabeca-cauda | **OK** | **OK** | **OK** | **OK** |
| D9-frequencia-alta | **OK** | **OK** | **OK** | **OK** |
| D10-datas-mundiais | **OK** | **OK** | **OK** | **OK** |
| D11-datetime-precisao | **OK** | **OK** | **OK** | **OK** |
| D12-datetime-timezone | **OK** | **OK** | **OK** | **OK** |
| D13-cpf-variados | **OK** | **OK** | **OK** | **OK** |
| D14-uuid-variados | **OK** | **OK** | **OK** | **OK** |
| D15-base64-variados | **OK** | **OK** | **OK** | **OK** |
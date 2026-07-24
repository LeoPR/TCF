# Resultado — weld FAIL-LOUD no corpo core (2026-07-24-2010)

## A. BYTE-NEUTRO + roundtrip

| id | n | wire (B) | RT | cabecalho |
|---|---:|---:|---|---|
| A-repetidos | 6 | 35 | OK | `'#TCF.8'` |
| B-run | 43 | 23 | OK | `'#TCF.8'` |
| C-prefixo | 30 | 56 | OK | `'#TCF.8'` |
| D-bool | 24 | 15 | OK | `'#TCF.8b118'` |
| E-bordas | 5 | 19 | OK | `'#TCF.8'` |

RT: **5/5** ok.
Gates byte-canonicos (pinados ANTES do weld): **PASSOU** — `31 passed in 3.00s`

## B. FAIL-LOUD sob corrupcao

- mutacoes deterministicas: **501**
- `ValueError` (fail-loud): **306**
- decodou p/ outro dado: **193** — esperado, o formato nao tem checksum
- desviadas p/ classe AMPLIFICACAO: **2** (parte D)
- **excecao CRUA: 0** <- a metrica do weld (alvo: 0)

## C. Aceite-calado (`^N` fora de faixa)

| decl | ^N | veredito | detalhe |
|---:|---:|---|---|
| 1 | -1 | fail-loud | referencia de linha fora de faixa: '^-1' (de |
| 1 | 0 | fail-loud | referencia de linha fora de faixa: '^0' (dec |
| 1 | 2 | fail-loud | referencia de linha fora de faixa: '^2' (dec |
| 1 | 10 | fail-loud | referencia de linha fora de faixa: '^10' (de |
| 1 | 999 | fail-loud | referencia de linha fora de faixa: '^999' (d |
| 2 | -1 | fail-loud | referencia de linha fora de faixa: '^-1' (de |
| 2 | 0 | fail-loud | referencia de linha fora de faixa: '^0' (dec |
| 2 | 3 | fail-loud | referencia de linha fora de faixa: '^3' (dec |
| 2 | 11 | fail-loud | referencia de linha fora de faixa: '^11' (de |
| 2 | 999 | fail-loud | referencia de linha fora de faixa: '^999' (d |
| 5 | -1 | fail-loud | referencia de linha fora de faixa: '^-1' (de |
| 5 | 0 | fail-loud | referencia de linha fora de faixa: '^0' (dec |
| 5 | 6 | fail-loud | referencia de linha fora de faixa: '^6' (dec |
| 5 | 14 | fail-loud | referencia de linha fora de faixa: '^14' (de |
| 5 | 999 | fail-loud | referencia de linha fora de faixa: '^999' (d |

Falhas: **0** (inclui controle positivo da faixa valida).

## D. Amplificacao do contador RLE (achado NOVO, NAO soldado)

| wire (B) | elementos | amplificacao | tempo |
|---:|---:|---:|---:|
| 9 | 1,000 | 222x | 0.00s |
| 11 | 100,000 | 18,181x | 0.00s |
| 13 | 10,000,000 | 1,538,461x | 0.08s |

`*N|` nao tem teto: um wire minusculo materializa lista arbitraria (`saida.extend([no] * count)`). **Sem weld aqui de proposito** — o teto e' decisao de POLITICA (wire legitimo tambem tem count alto), nao correcao obvia. Fora do escopo deste weld (que e' so' fail-loud).

## Veredito

**APROVADO** — A=0 falhas, gates=ok, B=0 cruas, C=0 falhas.

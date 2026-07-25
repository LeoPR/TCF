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
Gates byte-canonicos (pinados ANTES do weld): **PASSOU** — `31 passed in 3.02s`

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

## D. Amplificacao do contador RLE — FECHADO pelo weld `max_length`

| wire (B) | elementos (sem teto) | amplificacao | tempo | teto default |
|---:|---:|---:|---:|---|
| 9 | 1,000 | 222x | 0.00s | passa |
| 11 | 100,000 | 18,181x | 0.00s | passa |
| 13 | 10,000,000 | 1,538,461x | 0.08s | passa |
| 15 | 1,000,000,000 | 133,333,333x | 8.04s | **barrado** |

A coluna 'sem teto' e' a medicao ORIGINAL (`max_length=0`), preservada como evidencia do problema; a ultima coluna e' o veredito do teto default. Nome `max_length` e a convencao `0 == sem teto` vem do zlib/bz2/lzma — nada reinventado. Unidade = ELEMENTOS (e' o que a bomba aloca), por coluna, no funil unico `_decode_column` (protege single/multi/view/hierarquico).

## Veredito

**APROVADO** — A=0 falhas, gates=ok, B=0 cruas, C=0 falhas.

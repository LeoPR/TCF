# Resultado — null no slot 0 SOLDADO (2026-07-25-0030)

`antes` = rota `.8H` (o que a coluna com null produzia até o weld) · `depois` = `encode()` atual, medido no produto REAL.

| id | n | nulls | antes `.8H` | depois | Δ | Δ% | RT |
|---|---:|---:|---:|---:|---:|---:|---|
| A-exemplo-owner | 7 | 2 | 57 | 31 | -26 | -46% | OK |
| B-n7-1null | 7 | 1 | 58 | 37 | -21 | -36% | OK |
| C-todos-null | 12 | 12 | 30 | 13 | -17 | -57% | OK |
| D-null-bordas | 5 | 2 | 40 | 17 | -23 | -58% | OK |
| E-sem-null | 4 | 0 | 29 | 29 | +0 | +0% | OK |
| R-n10-p1 | 10 | 0 | 59 | 59 | +0 | +0% | OK |
| R-n10-p10 | 10 | 0 | 59 | 59 | +0 | +0% | OK |
| R-n10-p50 | 10 | 6 | 75 | 47 | -28 | -37% | OK |
| R-n10-p90 | 10 | 9 | 43 | 22 | -21 | -49% | OK |
| R-n100-p1 | 100 | 1 | 360 | 328 | -32 | -9% | OK |
| R-n100-p10 | 100 | 13 | 395 | 312 | -83 | -21% | OK |
| R-n100-p50 | 100 | 60 | 361 | 232 | -129 | -36% | OK |
| R-n100-p90 | 100 | 95 | 117 | 79 | -38 | -32% | OK |
| R-n1000-p1 | 1000 | 12 | 3141 | 3017 | -124 | -4% | OK |
| R-n1000-p10 | 1000 | 103 | 3611 | 2928 | -683 | -19% | OK |
| R-n1000-p50 | 1000 | 508 | 3770 | 2398 | -1372 | -36% | OK |
| R-n1000-p90 | 1000 | 900 | 1189 | 798 | -391 | -33% | OK |

RT: **17/17**

- colunas **com** null (14): Δ mediano **-36%**, pior caso -4%, melhor -58%
- colunas **sem** null (3): Δ **+0%** — byte-idênticas, como tem que ser (o slot 0 era espaço morto)

## Byte-neutralidade — D1-D9 (datasets reais do gate)

| dataset | bytes | pino ADR-0034 | ok |
|---|---:|---:|---|
| D1-emails-simples | 125 | 125 | OK |
| D2-emails-quote-id | 173 | 173 | OK |
| D3-stress-substring | 184 | 184 | OK |
| D4-caos-mix | 120 | 120 | OK |
| D5-padroes-multiplos | 288 | 288 | OK |
| D6-poucos-em-ruido | 294 | 294 | OK |
| D7-aninhamento | 222 | 222 | OK |
| D8-cabeca-cauda | 107 | 107 | OK |
| D9-frequencia-alta | 73 | 73 | OK |

Byte-neutro em coluna sem null: **SIM** — o slot 0 era espaço morto, então não roubou endereço de dado.

## Sob gzip (sinal qualitativo, não critério)

| id | antes gz | depois gz | Δ% |
|---|---:|---:|---:|
| A-exemplo-owner | 77 | 50 | -35% |
| B-n7-1null | 75 | 54 | -28% |
| C-todos-null | 50 | 33 | -34% |
| D-null-bordas | 60 | 35 | -42% |
| E-sem-null | 49 | 49 | +0% |

gzip **não é o TCF** — entra só como sinal de que o ganho não é artefato de redundância textual que um entropy-coder colapsaria.

## Veredito

**APROVADO** — RT 17/17, byte-neutro=sim, Δ mediano -33%.

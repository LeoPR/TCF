# Resultado — null no slot 0 SOLDADO (2026-07-25-1630)

`JSON` = JSON equivalente **compacto** (`separators=(',',':')`, sem `\uXXXX`) — referência de escala. `antes` = rota `.8H` (o que a coluna com null produzia até o weld). `depois` = `encode()` atual, produto REAL.

| id | n | nulls | JSON | `.8H` | vs JSON | depois | vs JSON | Δ do weld | RT |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| A-exemplo-owner | 7 | 2 | 41 | 57 | +39% | 31 | **-24%** | -46% | OK |
| B-n7-1null | 7 | 1 | 61 | 58 | -5% | 37 | **-39%** | -36% | OK |
| C-todos-null | 12 | 12 | 61 | 30 | -51% | 13 | **-79%** | -57% | OK |
| D-null-bordas | 5 | 2 | 23 | 40 | +74% | 17 | **-26%** | -58% | OK |
| E-sem-null | 4 | 0 | 38 | 29 | -24% | 29 | **-24%** | +0% | OK |
| R-n10-p1 | 10 | 0 | 103 | 59 | -43% | 59 | **-43%** | +0% | OK |
| R-n10-p10 | 10 | 0 | 103 | 59 | -43% | 59 | **-43%** | +0% | OK |
| R-n10-p50 | 10 | 6 | 72 | 75 | +4% | 47 | **-35%** | -37% | OK |
| R-n10-p90 | 10 | 9 | 56 | 43 | -23% | 22 | **-61%** | -49% | OK |
| R-n100-p1 | 100 | 1 | 1016 | 360 | -65% | 328 | **-68%** | -9% | OK |
| R-n100-p10 | 100 | 13 | 949 | 395 | -58% | 312 | **-67%** | -21% | OK |
| R-n100-p50 | 100 | 60 | 708 | 361 | -49% | 232 | **-67%** | -36% | OK |
| R-n100-p90 | 100 | 95 | 530 | 117 | -78% | 79 | **-85%** | -32% | OK |
| R-n1000-p1 | 1000 | 12 | 10142 | 3141 | -69% | 3017 | **-70%** | -4% | OK |
| R-n1000-p10 | 1000 | 103 | 9660 | 3611 | -63% | 2928 | **-70%** | -19% | OK |
| R-n1000-p50 | 1000 | 508 | 7536 | 3770 | -50% | 2398 | **-68%** | -36% | OK |
| R-n1000-p90 | 1000 | 900 | 5534 | 1189 | -79% | 798 | **-86%** | -33% | OK |

RT: **17/17**

- **vs JSON compacto** — mediana **-67%** (pior -24%, melhor -86%); só as colunas com null: **-67%**
- vs `.8H`, colunas **com** null (14): Δ mediano **-36%**, pior -4%, melhor -58%
- vs `.8H`, colunas **sem** null (3): Δ **+0%** — byte-idênticas, como tem que ser (o slot 0 era espaço morto)

### O achado: o `.8H` era MAIOR que o JSON em payload pequeno

Antes do weld, uma coluna minúscula com null saía **maior como TCF do que como JSON** — o envelope hierárquico custava mais que os bytes que economizava. Isso contradizia frontalmente o foco declarado (cada byte conta em payload minúsculo).

| id | JSON | `.8H` | era | virou |
|---|---:|---:|---:|---:|
| A-exemplo-owner | 41 | 57 | **+39%** | **-24%** |
| D-null-bordas | 23 | 40 | **+74%** | **-26%** |
| R-n10-p50 | 72 | 75 | **+4%** | **-35%** |

**3 de 14 colunas com null** estavam nessa situação; todas viraram ganho.

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

| id | JSON gz | `.8H` gz | TCF gz | vs JSON gz |
|---|---:|---:|---:|---:|
| A-exemplo-owner | 50 | 77 | 50 | +0% |
| B-n7-1null | 52 | 75 | 54 | +4% |
| C-todos-null | 29 | 50 | 33 | +14% |
| D-null-bordas | 39 | 60 | 35 | -10% |
| E-sem-null | 45 | 49 | 49 | +9% |

gzip **não é o TCF** — entra só como sinal de que o ganho não é artefato de redundância textual que um entropy-coder colapsaria.

## Veredito

**APROVADO** — RT 17/17, byte-neutro=sim, Δ mediano -33%.

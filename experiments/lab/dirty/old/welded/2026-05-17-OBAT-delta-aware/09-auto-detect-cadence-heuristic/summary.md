# Resumo — Sub-exp 09 (auto-detect cadence)

Pipelines:
- **baseline** = OBAT canon + HCC canon
- **always-on (ao)** = OBAT fork shape-preserve + HCC fork
- **auto** = Pre heuristica decide; OBAT canon OU fork; + HCC fork

Datasets onde heuristica detectou cadencia: 11/20
RT always-on: 20/20
RT auto:      20/20

## Totais

- baseline:  2770 B
- always-on: 2619 B (-151, -5.5%)
- auto:      2272 B (-498, -18.0%)

## Tabela

| Dataset | det? | baseline | always-on | auto | ao-bl | au-bl | au-ao |
|---|---|---:|---:|---:|---:|---:|---:|
| [D1-emails-simples](D1-emails-simples/stats.txt) | no | 118 | 104 | 118 | -14 | +0 | +14 |
| [D2-emails-quote-id](D2-emails-quote-id/stats.txt) | no | 166 | 169 | 166 | +3 | +0 | -3 |
| [D3-stress-substring](D3-stress-substring/stats.txt) | no | 177 | 185 | 177 | +8 | +0 | -8 |
| [D4-caos-mix](D4-caos-mix/stats.txt) | no | 113 | 113 | 113 | +0 | +0 | +0 |
| [D5-padroes-multiplos](D5-padroes-multiplos/stats.txt) | no | 281 | 484 | 281 | +203 | +0 | -203 |
| [D6-poucos-em-ruido](D6-poucos-em-ruido/stats.txt) | no | 287 | 354 | 287 | +67 | +0 | -67 |
| [D7-aninhamento](D7-aninhamento/stats.txt) | no | 215 | 315 | 215 | +100 | +0 | -100 |
| [D8-cabeca-cauda](D8-cabeca-cauda/stats.txt) | yes | 100 | 100 | 100 | +0 | +0 | +0 |
| [D9-frequencia-alta](D9-frequencia-alta/stats.txt) | yes | 158 | 66 | 66 | -92 | -92 | +0 |
| [D11a-datas-dia](D11a-datas-dia/stats.txt) | yes | 87 | 71 | 71 | -16 | -16 | +0 |
| [D11b-datas-borda](D11b-datas-borda/stats.txt) | no | 173 | 153 | 173 | -20 | +0 | +20 |
| [D11c-datas-mensal](D11c-datas-mensal/stats.txt) | yes | 109 | 72 | 72 | -37 | -37 | +0 |
| [D11d-datetime-min](D11d-datetime-min/stats.txt) | yes | 110 | 61 | 61 | -49 | -49 | +0 |
| [D11e-datetime-mensal](D11e-datetime-mensal/stats.txt) | yes | 121 | 84 | 84 | -37 | -37 | +0 |
| [D11f-datetime-ms](D11f-datetime-ms/stats.txt) | yes | 115 | 66 | 66 | -49 | -49 | +0 |
| [D11g-datetime-us](D11g-datetime-us/stats.txt) | yes | 120 | 71 | 71 | -49 | -49 | +0 |
| [D11h-datetime-ns](D11h-datetime-ns/stats.txt) | yes | 123 | 74 | 74 | -49 | -49 | +0 |
| [D16a-ids-3digits](D16a-ids-3digits/stats.txt) | no | 65 | 11 | 11 | -54 | -54 | +0 |
| [D16b-ids-4digits](D16b-ids-4digits/stats.txt) | yes | 62 | 28 | 28 | -34 | -34 | +0 |
| [D16c-ids-prefixados](D16c-ids-prefixados/stats.txt) | yes | 70 | 38 | 38 | -32 | -32 | +0 |


# Medições — alvo DELTA (bytes de wire; D1 +12 B e D2 +10 B de header hipotético)

D2 = seq-RLE periódico ESTRITO (>=2 ciclos completos). D2L = a forma degenerada
descoberta no lab: 1 ciclo só = LISTA literal de deltas no marcador.

| caso | n | C0 sem spec | C1 com spec | D1 delta-col | D2 período | D2L lista | floor | vence |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| diario-controle | 600 | 414 | 32 | 35 | 32 | 32 | 32 | C1 |
| semanal-controle | 600 | 2744 | 32 | 35 | 32 | 32 | 32 | C1 |
| uteis | 600 | 2471 | 1590 | 239 | 41 | 41 | 41 | D2 |
| uteis-feriado-mensal | 600 | 2878 | 1889 | 345 | 649 | 904 | 345 | D1 |
| mensal-dia1 | 600 | 1085 | 1085 | 349 | 664 | 1098 | 349 | D1 |
| quinzenal | 600 | 7628 | 3951 | 349 | 600 | 600 | 349 | D1 |
| espalhado-ordenado | 600 | 6398 | 4059 | 644 | 3766 | 1825 | 644 | D1 |
| espalhado-desordenado | 600 | 6104 | 4737 | 3167 | 4212 | 3301 | 3167 | D1 |
| uteis-ruido-1pct | 600 | 2710 | 1644 | 350 | 209 | 184 | 184 | D2L |
| uteis-ruido-5pct | 600 | 3016 | 3016 | 353 | 764 | 699 | 353 | D1 |
| ids-turno-nao-data | 600 | 1959 | — | 241 | 33 | 33 | 33 | D2 |
| uteis-n6000 | 6000 | 26595 | 15630 | 2040 | 42 | 42 | 42 | D2 |

Detalhe D2 por caso:

- `diario-controle`: {"rota": "#TCF.8", "ajuste": 10, "estrito": {"bytes": 32, "ganhou_no_corpo": false, "runs": 0, "periodos": []}, "lista": {"bytes": 32, "ganhou_no_corpo": false, "runs": 0, "periodos": []}}
- `semanal-controle`: {"rota": "#TCF.8", "ajuste": 10, "estrito": {"bytes": 32, "ganhou_no_corpo": false, "runs": 0, "periodos": []}, "lista": {"bytes": 32, "ganhou_no_corpo": false, "runs": 0, "periodos": []}}
- `uteis`: {"rota": "#TCF.8!!", "ajuste": 10, "estrito": {"bytes": 41, "ganhou_no_corpo": true, "runs": 1, "periodos": [5]}, "lista": {"bytes": 41, "ganhou_no_corpo": true, "runs": 1, "periodos": [5]}}
- `uteis-feriado-mensal`: {"rota": "#TCF.8!!", "ajuste": 10, "estrito": {"bytes": 649, "ganhou_no_corpo": true, "runs": 30, "periodos": [5]}, "lista": {"bytes": 904, "ganhou_no_corpo": true, "runs": 15, "periodos": [24]}}
- `mensal-dia1`: {"rota": "#TCF.8!!", "ajuste": 10, "estrito": {"bytes": 664, "ganhou_no_corpo": true, "runs": 14, "periodos": [2, 5, 12]}, "lista": {"bytes": 1098, "ganhou_no_corpo": true, "runs": 13, "periodos": [24]}}
- `quinzenal`: {"rota": "#TCF.8!!", "ajuste": 10, "estrito": {"bytes": 600, "ganhou_no_corpo": true, "runs": 7, "periodos": [24]}, "lista": {"bytes": 600, "ganhou_no_corpo": true, "runs": 7, "periodos": [24]}}
- `espalhado-ordenado`: {"rota": "#TCF.8!!", "ajuste": 10, "estrito": {"bytes": 3766, "ganhou_no_corpo": false, "runs": 0, "periodos": []}, "lista": {"bytes": 1825, "ganhou_no_corpo": true, "runs": 24, "periodos": [20, 24]}}
- `espalhado-desordenado`: {"rota": "#TCF.8!!", "ajuste": 10, "estrito": {"bytes": 4212, "ganhou_no_corpo": true, "runs": 0, "periodos": []}, "lista": {"bytes": 3301, "ganhou_no_corpo": true, "runs": 24, "periodos": [24]}}
- `uteis-ruido-1pct`: {"rota": "#TCF.8!!", "ajuste": 10, "estrito": {"bytes": 209, "ganhou_no_corpo": true, "runs": 4, "periodos": [5]}, "lista": {"bytes": 184, "ganhou_no_corpo": true, "runs": 6, "periodos": [5]}}
- `uteis-ruido-5pct`: {"rota": "#TCF.8!! (construido)", "ajuste": 10, "estrito": {"bytes": 764, "ganhou_no_corpo": true, "runs": 15, "periodos": [5]}, "lista": {"bytes": 699, "ganhou_no_corpo": true, "runs": 24, "periodos": [2, 3, 4, 5]}}
- `ids-turno-nao-data`: {"rota": "#TCF.8!!", "ajuste": 0, "estrito": {"bytes": 33, "ganhou_no_corpo": true, "runs": 1, "periodos": [4]}, "lista": {"bytes": 33, "ganhou_no_corpo": true, "runs": 1, "periodos": [4]}}
- `uteis-n6000`: {"rota": "#TCF.8!!", "ajuste": 10, "estrito": {"bytes": 42, "ganhou_no_corpo": true, "runs": 1, "periodos": [5]}, "lista": {"bytes": 42, "ganhou_no_corpo": true, "runs": 1, "periodos": [5]}}

Rotas D1 (o delta-coluna muda a ROTA do core — k baixo cai no bN):

- `diario-controle`: `#TCF.8`
- `semanal-controle`: `#TCF.8`
- `uteis`: `#TCF.8B2258`
- `uteis-feriado-mensal`: `#TCF.8B3258`
- `mensal-dia1`: `#TCF.8B3258`
- `quinzenal`: `#TCF.8B3258`
- `espalhado-ordenado`: `#TCF.8B5258`
- `espalhado-desordenado`: `#TCF.8!!`
- `uteis-ruido-1pct`: `#TCF.8B3258`
- `uteis-ruido-5pct`: `#TCF.8B3258`
- `ids-turno-nao-data`: `#TCF.8B2258`
- `uteis-n6000`: `#TCF.8B21770`

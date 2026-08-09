# Medições — alvos mensais (bytes; alvos novos pagam +11 B de header)

| caso | n | C0 sem spec | A1 ordinal dia | A2-mes-epoca-d01 | A2f-mes-epoca-FIM | A3-YYYYMM-d01 | A4-mes31-dia | YM-grafia-propria | vence |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| mensal-dia1 | 600 | 1085 | 679 | 31 | 3746 | 55 | 33 | — | **A2-mes-epoca-d01** |
| mensal-dia15 | 600 | 1085 | 679 | 3746 | 3746 | 3746 | 33 | — | **A4-mes31-dia** |
| mensal-fim-do-mes | 600 | 6455 | 655 | 5821 | 31 | 5821 | 745 | — | **A2f-mes-epoca-FIM** |
| trimestral-dia1 | 600 | 6377 | 139 | 31 | 7414 | 39 | 33 | — | **A2-mes-epoca-d01** |
| mensal-com-faltas | 600 | 2799 | 2799 | 41 | 4862 | 1731 | 48 | — | **A2-mes-epoca-d01** |
| yyyy-mm-puro | 600 | 826 | 826 | — | — | — | — | 31 | **YM-grafia-propria** |
| diario-CONTROLE | 600 | 414 | 32 | 2214 | 589 | 2234 | 136 | — | **A1_ordinal_dia** |
| misto-d01-d15 | 600 | 7628 | 629 | 5461 | 7336 | 5761 | 36 | — | **A4-mes31-dia** |

Rotas dos alvos por caso:

- `mensal-dia1`: {"A2-mes-epoca-d01": {"rota": "#TCF.8", "validos": 600}, "A2f-mes-epoca-FIM": {"rota": "#TCF.8!", "validos": 0}, "A3-YYYYMM-d01": {"rota": "#TCF.8", "validos": 600}, "A4-mes31-dia": {"rota": "#TCF.8", "validos": 600}}
- `mensal-dia15`: {"A2-mes-epoca-d01": {"rota": "#TCF.8!", "validos": 0}, "A2f-mes-epoca-FIM": {"rota": "#TCF.8!", "validos": 0}, "A3-YYYYMM-d01": {"rota": "#TCF.8!", "validos": 0}, "A4-mes31-dia": {"rota": "#TCF.8", "validos": 600}}
- `mensal-fim-do-mes`: {"A2-mes-epoca-d01": {"rota": "#TCF.8!", "validos": 0}, "A2f-mes-epoca-FIM": {"rota": "#TCF.8", "validos": 600}, "A3-YYYYMM-d01": {"rota": "#TCF.8!", "validos": 0}, "A4-mes31-dia": {"rota": "#TCF.8!!", "validos": 600}}
- `trimestral-dia1`: {"A2-mes-epoca-d01": {"rota": "#TCF.8", "validos": 600}, "A2f-mes-epoca-FIM": {"rota": "#TCF.8!!", "validos": 0}, "A3-YYYYMM-d01": {"rota": "#TCF.8", "validos": 600}, "A4-mes31-dia": {"rota": "#TCF.8", "validos": 600}}
- `mensal-com-faltas`: {"A2-mes-epoca-d01": {"rota": "#TCF.8", "validos": 600}, "A2f-mes-epoca-FIM": {"rota": "#TCF.8!", "validos": 0}, "A3-YYYYMM-d01": {"rota": "#TCF.8!!", "validos": 600}, "A4-mes31-dia": {"rota": "#TCF.8", "validos": 600}}
- `yyyy-mm-puro`: {"YM-grafia-propria": {"rota": "#TCF.8", "validos": 600}}
- `diario-CONTROLE`: {"A2-mes-epoca-d01": {"rota": "#TCF.8!", "validos": 20}, "A2f-mes-epoca-FIM": {"rota": "#TCF.8!!", "validos": 19}, "A3-YYYYMM-d01": {"rota": "#TCF.8!", "validos": 20}, "A4-mes31-dia": {"rota": "#TCF.8!!", "validos": 600}}
- `misto-d01-d15`: {"A2-mes-epoca-d01": {"rota": "#TCF.8!!", "validos": 300}, "A2f-mes-epoca-FIM": {"rota": "#TCF.8!", "validos": 0}, "A3-YYYYMM-d01": {"rota": "#TCF.8!!", "validos": 300}, "A4-mes31-dia": {"rota": "#TCF.8", "validos": 600}}

# Proveniência das entradas

Sintéticas, material de FORMA (mecanismo + custo), não medida de ganho — viés declarado.

- `inputs/01-coluna-nullable.json` — coluna ilustrativa **construída para vistoriar as 4 vias**:
  `null` real (posições 1,6), a string `"null"` (pos 3), a string `""` (pos 4), mais valores comuns.
  É o caso-assinatura que o mecanismo tem que distinguir.
- `study.py` — gera as tabelas multi-coluna (16×200) e as colunas de cardinalidade nas fronteiras
  9/99/999 com seed fixa (`random.Random(20260715)` / `Random(7)`), regimes declarados no output.

Sem dado real neste estudo (é estudo de MECANISMO). A validação real (coluna nullable de receita-cnpj,
etc.) fica pro lab de integração ao L1 real, se o owner ratificar o framework — mesma esteira do P1
(fuzz + real-world + gate byte-canônico).

# Dataset estendido — 30 linhas × 5 colunas

Coluna nova: `data` (data da compra). Distribuída em 4 padrões para
estresse-test do delta encoding.

---

## Dataset completo

```
nome,     produto,    quantidade, valor_unitario, data
Helena,   Lápis,      20,         0.50,           2026-01-05
Beto,     Caneta,     10,         1.50,           2026-01-06
Diana,    Mochila,    1,          50.00,          2026-01-07
Ana,      Caderno,    3,          3.00,           2026-01-08
Carlos,   Caneta,     12,         2.00,           2026-01-09
Eduardo,  Régua,      5,          2.00,           2026-01-10
Beto,     Caderno,    5,          3.00,           2026-01-11
Fernanda, Marcador,   2,          4.50,           2026-01-15
Gabriel,  Caneta,     10,         1.50,           2026-01-15
Helena,   Borracha,   4,          0.75,           2026-01-15
Ana,      Lápis,      30,         0.50,           2026-01-15
Diana,    Apontador,  8,          1.00,           2026-01-15
Carlos,   Caderno,    1,          5.00,           2026-01-15
Eduardo,  Caneta,     10,         1.50,           2026-01-22
Beto,     Lápis,      15,         0.50,           2026-01-23
Helena,   Régua,      5,          2.00,           2026-01-23
Fernanda, Caneta,     20,         1.50,           2026-02-01
Ana,      Marcador,   3,          4.00,           2026-02-01
Gabriel,  Borracha,   4,          0.75,           2026-02-02
Diana,    Caderno,    5,          3.00,           2026-02-15
Carlos,   Régua,      5,          2.00,           2026-02-15
Eduardo,  Lápis,      25,         0.50,           2026-02-16
Helena,   Caneta,     12,         2.00,           2026-03-03
Beto,     Apontador,  8,          1.00,           2026-03-10
Fernanda, Caderno,    3,          3.00,           2026-03-12
Gabriel,  Régua,      5,          2.00,           2026-03-20
Ana,      Caneta,     10,         1.50,           2026-03-25
Diana,    Borracha,   4,          0.75,           2026-04-01
Carlos,   Lápis,      20,         0.50,           2026-04-05
Eduardo,  Mochila,    1,          50.00,          2026-04-15
```

---

## Padrões da coluna `data`

| Padrão | Linhas | Datas | Comportamento |
|---|---|---|---|
| **A — Sequencial denso** | 1–7 | 01-05 a 01-11 | 1 venda/dia, 7 dias consecutivos |
| **B — Mesmo dia** | 8–13 | 01-15 (×6) | 6 vendas no mesmo dia |
| **C — Mistura** | 14–22 | 01-22 a 02-16 | rajadas curtas + gaps + mesmo-dia |
| **D — Esparso** | 23–30 | 03-03 a 04-15 | 8 datas únicas espalhadas |

---

## Estatísticas

### Cardinalidade da coluna `data`

22 datas distintas:
- 7 datas únicas no padrão A
- 1 data com 6 ocorrências (padrão B)
- Padrão C: 01-22 (×1), 01-23 (×2), 02-01 (×2), 02-02 (×1), 02-15 (×2), 02-16 (×1) → 6 distintas, 9 ocorrências
- 8 datas únicas no padrão D

Total: 7 + 1 + 6 + 8 = 22 distintas em 30 linhas.

### Repetições

| Data | Ocorrências |
|---|---|
| 2026-01-15 | 6 |
| 2026-01-23, 2026-02-01, 2026-02-15 | 2 cada |
| Demais 18 datas | 1 cada |

### Distribuição de "deltas em dias" (em ordem cronológica)

29 transições de uma data à seguinte:
```
+1, +1, +1, +1, +1, +1, +4,
0, 0, 0, 0, 0,
+7, +1, 0, +9, 0, +1, +13, 0, +1,
+15, +7, +2, +8, +5, +7, +4, +10
```

Cardinalidade dos deltas: 11 valores distintos (`0, +1, +2, +4, +5, +7, +8, +9, +10, +13, +15`).

Frequência:
- `+1`: 9× (mais frequente)
- `0`: 8× (mesmo dia)
- `+7`: 3×
- `+4`: 2×
- demais 7 deltas: 1× cada

→ Os deltas são **muito mais repetitivos** que as datas. RLE+dict aplicado
sobre deltas vai capturar mais.

---

## Cenários de sort relevantes para a mesa

| Cenário | Coluna primária do sort | Ordem da `data` |
|---|---|---|
| **Cron** | data | já em ordem cronológica (== ordem original) |
| **Nome** | nome | datas espalhadas (mas dentro de cada nome, cronológico por linha) |
| **Produto** | produto | datas espalhadas dentro de cada produto |
| **Sem sort** | nenhuma | mesma ordem original (== Cron neste dataset) |

Vou rodar a comparação no cenário **Cron** (melhor caso pra delta) e no
**Nome** (cenário onde delta vai sofrer mais — datas espalhadas).

---

## Bytes-âncora (sem delta, para comparação)

Coluna `data` em ordem cronológica, codificações sem transformação
delta:

| Codificação | Bytes (aprox) | Comentário |
|---|---|---|
| Literal puro | 30 × 11 = 330 | cada `2026-MM-DD\n` = 11 B |
| RLE local | 280–290 | RLE no `01-15` (×6) + 3 pares ×2; resto único |
| Unified rule (RLE + dict refs) | ~250 | dict pega 4 datas que reaparecem |
| **Delta + unified** | **?** (calcular em `03`) | esperado: <100 |

Header da coluna: `data:\n` = 6 B em todos os casos.

→ A mesa avalia agora: vale o delta?

# Resultado — null como índice 0 numa coluna de string (2026-07-24-2210)

`hoje` = `src/tcf` REAL (rota `.8H`, máscara). `proto` = flat `#TCF.8` + índice 0.

| id | n | nulls | hoje (B) | proto (B) | Δ | Δ% | RT |
|---|---:|---:|---:|---:|---:|---:|---|
| A-exemplo-owner | 7 | 2 | 57 | 32 | -25 | -44% | OK |
| B-n7-1null | 7 | 1 | 58 | 37 | -21 | -36% | OK |
| C-todos-null | 12 | 12 | 30 | 13 | -17 | -57% | OK |
| D-null-bordas | 5 | 2 | 40 | 18 | -22 | -55% | OK |
| E-sem-null | 4 | 0 | 29 | 29 | +0 | +0% | OK |
| R-n10-p1 | 10 | 0 | 59 | 59 | +0 | +0% | OK |
| R-n10-p10 | 10 | 0 | 59 | 59 | +0 | +0% | OK |
| R-n10-p50 | 10 | 6 | 75 | 49 | -26 | -35% | OK |
| R-n10-p90 | 10 | 9 | 43 | 23 | -20 | -47% | OK |
| R-n100-p1 | 100 | 1 | 360 | 328 | -32 | -9% | OK |
| R-n100-p10 | 100 | 13 | 395 | 319 | -76 | -19% | OK |
| R-n100-p50 | 100 | 60 | 361 | 252 | -109 | -30% | OK |
| R-n100-p90 | 100 | 95 | 117 | 84 | -33 | -28% | OK |
| R-n1000-p1 | 1000 | 12 | 3141 | 3028 | -113 | -4% | OK |
| R-n1000-p10 | 1000 | 103 | 3611 | 3019 | -592 | -16% | OK |
| R-n1000-p50 | 1000 | 508 | 3770 | 2646 | -1124 | -30% | OK |
| R-n1000-p90 | 1000 | 900 | 1189 | 890 | -299 | -25% | OK |

RT: **17/17** ok (hoje E protótipo, os dois validados).
CONTROLE sem-null byte-idêntico ao flat: **SIM** — o protótipo não cobra de quem não tem null.
Δ mediano: **-28%**

## Decomposição — de onde vem o ganho

- **(a) hoje** = `.8H` + máscara (real)
- **(b) flat+literal** = flat com null → literal `"0"` — **NÃO-lossless** (colide com a string real `"0"`)
- **(c) protótipo** = flat + índice 0 reservado — lossless

| caso | (a) | (b) | (c) | envelope (a−b) | índice (b−c) |
|---|---:|---:|---:|---:|---:|
| A-exemplo-owner | 57 | 33 | 32 | +24 | +1 |
| B-n7-1null | 58 | 38 | 37 | +20 | +1 |
| C-todos-null | 30 | 14 | 13 | +16 | +1 |
| D-null-bordas | 40 | 19 | 18 | +21 | +1 |
| R-n10-p50 | 75 | 50 | 49 | +25 | +1 |
| R-n10-p90 | 43 | 24 | 23 | +19 | +1 |
| R-n100-p1 | 360 | 329 | 328 | +31 | +1 |
| R-n100-p10 | 395 | 320 | 319 | +75 | +1 |
| R-n100-p50 | 361 | 253 | 252 | +108 | +1 |
| R-n100-p90 | 117 | 85 | 84 | +32 | +1 |
| R-n1000-p1 | 3141 | 3029 | 3028 | +112 | +1 |
| R-n1000-p10 | 3611 | 3020 | 3019 | +591 | +1 |
| R-n1000-p50 | 3770 | 2647 | 2646 | +1123 | +1 |
| R-n1000-p90 | 1189 | 891 | 890 | +298 | +1 |
| **TOTAL** | | | | **+2495** | **+14** |

Do ganho total de 2509 B: **envelope = 99%**, **índice = 1%** (exatamente +1 B por coluna — o `\0`→`0` da linha de declaração).

**O valor do índice reservado NÃO é o 1 byte.** É que a forma (b), que captura os 99%, é **inviável**: um literal colide com a string real. O índice 0 é o que torna ficar no flat **lossless** — ele não gera o ganho, ele o VIABILIZA.

## Wire lado a lado — exemplo do owner

```
coluna : [None, '', 'true', 'false', 'oi', None, 'null']
hoje   : '#TCF.8H#V\\z#:3?:14[\n\\7\n\\0\n*4|.\n^1\n^2\n\ntrue\nfalse\noi\nnull\n'
proto  : '#TCF.8\n0\n\ntrue\nfalse\noi\n^1\nnull\n'
```


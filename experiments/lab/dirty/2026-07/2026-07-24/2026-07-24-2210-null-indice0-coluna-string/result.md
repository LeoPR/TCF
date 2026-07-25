# Resultado — null como índice 0 numa coluna de string (2026-07-24-2210)

`hoje` = `src/tcf` REAL (rota `.8H`, máscara). `proto` = flat `#TCF.8` + índice 0.

| id | n | nulls | hoje (B) | proto (B) | Δ | Δ% | RT |
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

RT: **17/17** ok (hoje E protótipo, os dois validados).
CONTROLE sem-null byte-idêntico ao flat: **SIM** — o protótipo não cobra de quem não tem null.
Δ mediano: **-33%**

## Decomposição — de onde vem o ganho

- **(a) hoje** = `.8H` + máscara (real)
- **(b) flat+literal** = flat com null → literal `"0"` — **NÃO-lossless** (colide com a string real `"0"`)
- **(c) protótipo** = flat + índice 0 reservado — lossless

| caso | (a) | (b) | (c) | envelope (a−b) | índice (b−c) |
|---|---:|---:|---:|---:|---:|
| A-exemplo-owner | 57 | 33 | 31 | +24 | +2 |
| B-n7-1null | 58 | 38 | 37 | +20 | +1 |
| C-todos-null | 30 | 14 | 13 | +16 | +1 |
| D-null-bordas | 40 | 19 | 17 | +21 | +2 |
| R-n10-p50 | 75 | 50 | 47 | +25 | +3 |
| R-n10-p90 | 43 | 24 | 22 | +19 | +2 |
| R-n100-p1 | 360 | 329 | 328 | +31 | +1 |
| R-n100-p10 | 395 | 320 | 312 | +75 | +8 |
| R-n100-p50 | 361 | 253 | 232 | +108 | +21 |
| R-n100-p90 | 117 | 85 | 79 | +32 | +6 |
| R-n1000-p1 | 3141 | 3029 | 3017 | +112 | +12 |
| R-n1000-p10 | 3611 | 3020 | 2928 | +591 | +92 |
| R-n1000-p50 | 3770 | 2647 | 2398 | +1123 | +249 |
| R-n1000-p90 | 1189 | 891 | 798 | +298 | +93 |
| **TOTAL** | | | | **+2495** | **+493** |

Do ganho total de 2988 B: **envelope = 84%**, **índice = 16%**.

A parcela do índice cresceu com a grafia decidida pelo owner (`0` como endereço reservado que NÃO declara nó): **todo** null vira 1 char, contra 2 do literal `\0` e 2+ do `^k` que a grafia anterior gerava nas repetições. Por isso ela escala com a densidade de null (+249 B em `R-n1000-p50`).

**Mas o valor estrutural do índice não é essa parcela.** A forma (b), que sozinha captura a maior parte, é **inviável**: um literal colide com a string real `"0"` — foi exatamente a refutação do lab `2026-07-13-1921`. O índice reservado é o que torna ficar no flat **lossless**; ele não só gera ganho, ele **VIABILIZA** o resto.

## Wire lado a lado — exemplo do owner

```
coluna : [None, '', 'true', 'false', 'oi', None, 'null']
hoje   : '#TCF.8H#V\\z#:3?:14[\n\\7\n\\0\n*4|.\n^1\n^2\n\ntrue\nfalse\noi\nnull\n'
proto  : '#TCF.8\n0\n\ntrue\nfalse\noi\n0\nnull\n'
```


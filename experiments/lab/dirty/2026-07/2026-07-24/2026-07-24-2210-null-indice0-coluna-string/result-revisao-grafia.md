# Revisão de grafia — `0` (dígito nu) vs `^0` (referência de linha)

| id | nulls | A `0` (B) | B `^0` (B) | Δ | RT |
|---|---:|---:|---:|---:|---|
| A-exemplo-owner | 2 | 32 | 33 | +1 | OK |
| B-n7-1null | 1 | 37 | 38 | +1 | OK |
| C-todos-null | 12 | 13 | 14 | +1 | OK |
| D-null-bordas | 2 | 18 | 19 | +1 | OK |
| E-sem-null | 0 | 29 | 29 | +0 | OK |
| R-n10-p1 | 0 | 59 | 59 | +0 | OK |
| R-n10-p10 | 0 | 59 | 59 | +0 | OK |
| R-n10-p50 | 6 | 49 | 50 | +1 | OK |
| R-n10-p90 | 9 | 23 | 24 | +1 | OK |
| R-n100-p1 | 1 | 328 | 329 | +1 | OK |
| R-n100-p10 | 13 | 319 | 320 | +1 | OK |
| R-n100-p50 | 60 | 252 | 253 | +1 | OK |
| R-n100-p90 | 95 | 84 | 85 | +1 | OK |
| R-n1000-p1 | 12 | 3028 | 3029 | +1 | OK |
| R-n1000-p10 | 103 | 3019 | 3020 | +1 | OK |
| R-n1000-p50 | 508 | 2646 | 2647 | +1 | OK |
| R-n1000-p90 | 900 | 890 | 891 | +1 | OK |

RT: **34/34** (A e B).
Δ total de B sobre A: **+14 B** em 17 casos.

## Exemplo do owner

```
coluna : [None, '', 'true', 'false', 'oi', None, 'null']
A `0`  : '#TCF.8\n0\n\ntrue\nfalse\noi\n^1\nnull\n'
B `^0` : '#TCF.8\n^0\n\ntrue\nfalse\noi\n^0\nnull\n'
```

```
# B, legível:
#TCF.8
^0

true
false
oi
^0
null

```

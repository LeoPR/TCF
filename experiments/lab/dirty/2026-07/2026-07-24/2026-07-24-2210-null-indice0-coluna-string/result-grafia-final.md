# Grafia final + caça a colisões — `0` cru como null

## 1. Caça a colisões (o gate da decisão)

Colunas testadas com o encoder REAL: **1179** — vocabulário adversarial (`"0"`, `"00"`, `"01"`, `"10"`, `"-0"`, `"0.0"`, `"000"`, `"^0"`, `"\\0"`, `"*2|0"`, `"0~0"`, vazia…) em singleton, pares, trios, repetição (RLE) e intercalado.

**Linhas `0` emitidas pelo encoder: 0** · RT quebrado: 0

**Zero colisões.** A string `"0"` é sempre escapada como `\0` pelo core, e a tabela de fragmentos é 1-based — então uma linha cujo conteúdo inteiro é `0` nunca é emitida por dado. O slot está livre.

## 2. As três grafias

- **A** `0` DECLARA nó → 1º null = `0`, demais = `^k` (grafia inconsistente)
- **B** `^0` reservado, não declara → todo null = `^0`
- **C** `0` reservado, não declara → todo null = `0` (**grafia do owner + semântica do `^0`**)

| id | nulls | A | B | C | C−A | C−B | RT |
|---|---:|---:|---:|---:|---:|---:|---|
| A-exemplo-owner | 2 | 32 | 33 | 31 | -1 | -2 | OK |
| B-n7-1null | 1 | 37 | 38 | 37 | +0 | -1 | OK |
| C-todos-null | 12 | 13 | 14 | 13 | +0 | -1 | OK |
| D-null-bordas | 2 | 18 | 19 | 17 | -1 | -2 | OK |
| E-sem-null | 0 | 29 | 29 | 29 | +0 | +0 | OK |
| R-n10-p1 | 0 | 59 | 59 | 59 | +0 | +0 | OK |
| R-n10-p10 | 0 | 59 | 59 | 59 | +0 | +0 | OK |
| R-n10-p50 | 6 | 49 | 50 | 47 | -2 | -3 | OK |
| R-n10-p90 | 9 | 23 | 24 | 22 | -1 | -2 | OK |
| R-n100-p1 | 1 | 328 | 329 | 328 | +0 | -1 | OK |
| R-n100-p10 | 13 | 319 | 320 | 312 | -7 | -8 | OK |
| R-n100-p50 | 60 | 252 | 253 | 232 | -20 | -21 | OK |
| R-n100-p90 | 95 | 84 | 85 | 79 | -5 | -6 | OK |
| R-n1000-p1 | 12 | 3028 | 3029 | 3017 | -11 | -12 | OK |
| R-n1000-p10 | 103 | 3019 | 3020 | 2928 | -91 | -92 | OK |
| R-n1000-p50 | 508 | 2646 | 2647 | 2398 | -248 | -249 | OK |
| R-n1000-p90 | 900 | 890 | 891 | 798 | -92 | -93 | OK |

RT: **51/51** (as três grafias).
Total: C é **-479 B** vs A e **-493 B** vs B em 17 casos.

## 3. Exemplo do owner

```
coluna : [None, '', 'true', 'false', 'oi', None, 'null']
A      : '#TCF.8\n0\n\ntrue\nfalse\noi\n^1\nnull\n'
B      : '#TCF.8\n^0\n\ntrue\nfalse\noi\n^0\nnull\n'
C      : '#TCF.8\n0\n\ntrue\nfalse\noi\n0\nnull\n'
```

## 4. Regra de desambiguação

**Posicional** (mesma classe do char de modo no índice 7): a **linha inteira** igual a `0` é o especial. Um `0` DENTRO de composição (`1~0`, `0..3`) permanece no espaço de FRAGMENTO e não vira null — logo a classe absurda "compor uma string com null" continua **inexprimível**, que era a única objeção real ao dígito nu.


# Inteiros — ordem, cardinalidade, null e magnitude (2026-07-25-2036)

Métrica: **bytes**, decompostos em `cabeçalho` + `corpo`. Porcentagem fica fora de propósito — em payload pequeno ela mede o header, não o mecanismo. `B/elem` = corpo ÷ n.

`JSON` = equivalente compacto, em bytes, só como régua de ordem de grandeza.

## 1. ORDEM (mesma multiset, ordem diferente)

| id | n | nulls | cab | corpo | total | B/elem | JSON | RT |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| `O-seq-n10` | 10 | 0 | 8 | 9 | **17** | 0.90 | 21 | OK |
| `O-seq-n100` | 100 | 0 | 8 | 19 | **27** | 0.19 | 291 | OK |
| `O-seq-n1000` | 1000 | 0 | 8 | 31 | **39** | 0.03 | 3891 | OK |
| `O-desord-n10` | 10 | 0 | 8 | 40 | **48** | 4.00 | 21 | OK |
| `O-desord-n100` | 100 | 0 | 8 | 460 | **468** | 4.60 | 291 | OK |
| `O-desord-n1000` | 1000 | 0 | 8 | 5676 | **5684** | 5.68 | 3891 | OK |
| `O-decresc-n10` | 10 | 0 | 8 | 9 | **17** | 0.90 | 21 | OK |
| `O-decresc-n100` | 100 | 0 | 8 | 19 | **27** | 0.19 | 291 | OK |

## 2. PASSO (cadência regular, mas não unitária)

| id | n | nulls | cab | corpo | total | B/elem | JSON | RT |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| `P-passo5-n100` | 100 | 0 | 8 | 29 | **37** | 0.29 | 379 | OK |
| `P-passo100-n100` | 100 | 0 | 8 | 29 | **37** | 0.29 | 489 | OK |
| `P-ids-n100` | 100 | 0 | 8 | 13 | **21** | 0.13 | 501 | OK |
| `P-ts-n100` | 100 | 0 | 8 | 54 | **62** | 0.54 | 1101 | OK |
| `P-negativos-n100` | 100 | 0 | 8 | 39 | **47** | 0.39 | 332 | OK |

## 3. CARDINALIDADE (poucos valores distintos)

| id | n | nulls | cab | corpo | total | B/elem | JSON | RT |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| `C-k1-n100` | 100 | 0 | 8 | 8 | **16** | 0.08 | 201 | OK |
| `C-k2-n100` | 100 | 0 | 8 | 302 | **310** | 3.02 | 201 | OK |
| `C-k5-n100` | 100 | 0 | 8 | 294 | **302** | 2.94 | 201 | OK |
| `C-k20-n100` | 100 | 0 | 8 | 350 | **358** | 3.50 | 249 | OK |
| `C-ruido-n100` | 100 | 0 | 8 | 867 | **875** | 8.67 | 694 | OK |

## 4. NULL (sobre a sequência e sobre o ruído)

| id | n | nulls | cab | corpo | total | B/elem | JSON | RT |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| `N-seq-p1-n100` | 100 | 2 | 8 | 32 | **40** | 0.32 | 296 | OK |
| `N-seq-p10-n100` | 100 | 10 | 8 | 107 | **115** | 1.07 | 315 | OK |
| `N-seq-p50-n100` | 100 | 36 | 8 | 253 | **261** | 2.53 | 368 | OK |
| `N-seq-p90-n100` | 100 | 80 | 8 | 164 | **172** | 1.64 | 460 | OK |
| `N-desord-p10-n100` | 100 | 10 | 8 | 431 | **439** | 4.31 | 312 | OK |
| `N-desord-p50-n100` | 100 | 36 | 8 | 365 | **373** | 3.65 | 368 | OK |
| `N-todos-n20` | 20 | 20 | 7 | 6 | **13** | 0.30 | 101 | OK |

## 5. MAGNITUDE (largura do literal)

| id | n | nulls | cab | corpo | total | B/elem | JSON | RT |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| `M-1digito-n100` | 100 | 0 | 8 | 316 | **324** | 3.16 | 201 | OK |
| `M-6digitos-n100` | 100 | 0 | 8 | 329 | **337** | 3.29 | 701 | OK |
| `M-20digitos-n100` | 100 | 0 | 8 | 344 | **352** | 3.44 | 2201 | OK |
| `M-float-n100` | 100 | 0 | 8 | 588 | **596** | 5.88 | 601 | OK |

## Wires — o mecanismo visível

```
O-seq-n10        '#TCF.8n\n*10+1|\\0\n'
O-desord-n10     '#TCF.8n\n*2+4|\\4\n*2-2|\\9\n*2-1|\\1\n*2-3|\\5\n*2+3|\\3\n'
O-decresc-n10    '#TCF.8n\n*10-1|\\9\n'
P-passo5-n100    '#TCF.8n\n*2+5|\\0\n*18+5|\\10\n*80+5|\\100\n'
C-k1-n100        '#TCF.8n\n*100|\\0\n'
C-k2-n100        '#TCF.8n\n*2+1|\\0\n^1\n^2\n^1\n^2\n^1\n^2\n^1\n^2\n^1\n^2\n^1\n^2\n^1\n^2\n^1\n^2\n' …
N-seq-p10-n100   '#TCF.8n\n*2|0\n*3+1|\\2\n0\n\\6\n0\n*2+1|\\8\n*2+1|\\10\n0\n*23+1|\\13\n0\n*5+1|' …
N-todos-n20      '#TCF.8\n*20|0\n'
```

## Efeito da ORDEM (mesma multiset)

| n | crescente | embaralhado | custo da desordem |
|---:|---:|---:|---:|
| 10 | 17 | 48 | **+31 B** |
| 100 | 27 | 468 | **+441 B** |
| 1000 | 39 | 5684 | **+5645 B** |

## Efeito do NULL sobre uma sequência

| coluna | corpo | B/elem |
|---|---:|---:|
| `O-seq-n100` (0 nulls) | 19 | 0.19 |
| `N-seq-p1-n100` (2 nulls) | 32 | 0.32 |
| `N-seq-p10-n100` (10 nulls) | 107 | 1.07 |
| `N-seq-p50-n100` (36 nulls) | 253 | 2.53 |
| `N-seq-p90-n100` (80 nulls) | 164 | 1.64 |

O null **não é caro em si** (é 1 char, `0`) — ele **fragmenta a cadência**. Uma sequência limpa vira um marcador só (`*100+1|\0`); com 10% de null ela vira ~10 trechos, cada um com seu marcador. Por isso 19 B → 107 B. Em coluna já desordenada o efeito some (não havia cadência a quebrar).

## Baixa cardinalidade — a lacuna que este lab expõe

Mesma estrutura (`k=2` alternado, `n=100`), tipos diferentes:

| tipo | total | B/elem | por quê |
|---|---:|---:|---|
| bool | 31 | 0.23 | modo **denso** (bit-pack, 1 bit/elem) |
| int | 310 | 3.02 | só o core — `^N` custa 3 B por elemento |
| str | 305 | 2.97 | idem |

O piso do mecanismo de referência no corpo é **`^N` + LF = 3 B por elemento**. O bool escapa disso porque tem um segundo candidato de modo; int e string não têm.

Custo do `k` no int (n=100, valores sorteados por LCG):

| k | total | B/elem |
|---:|---:|---:|
| 1 | 16 | 0.08 |
| 2 | 310 | 3.02 |
| 3 | 269 | 2.61 |
| 5 | 302 | 2.94 |
| 10 | 324 | 3.16 |
| 20 | 358 | 3.50 |
| 50 | 402 | 3.94 |
| 100 | 430 | 4.22 |

`k=1` é o único barato (**0.08 B/elem**): vira um `*100|` só. De `k=2` em diante o corpo satura em ~3 B/elem e **quase não depende de `k`** — o que confirma que o gargalo é o `^N`, não o dicionário.

**A generalização do modo denso para além do bool é a próxima peça** — é o que a coluna de baixa cardinalidade está esperando, e o registry já reserva as larguras `b2`/`b4`/`b8`.

## RT: **29/29**


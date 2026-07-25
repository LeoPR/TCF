# 2026-07-25-2036 — Inteiros: ordem, cardinalidade, null e magnitude

Mesmo estilo do trabalho com `true`/`false`, agora para a tag `n`. **29 casos, RT 29/29.**

## Métrica: bytes, não porcentagem

Decisão do owner nesta rodada: reportar **bytes decompostos em `cabeçalho` + `corpo`**. Em
payload minúsculo a porcentagem mede o header, não o mecanismo — 7 B de cabeçalho contra 2 B
de JSON viram "+250%" e isso não informa nada. Porcentagem volta quando houver dado realista
em escala.

`B/elem` = corpo ÷ n. É o que mostra o mecanismo trabalhando conforme `n` cresce.

## Achado 1 — a ordem domina tudo

Mesma **multiset**, ordem diferente:

| n | crescente | embaralhado | custo da desordem |
|---:|---:|---:|---:|
| 10 | 17 | 48 | +31 B |
| 100 | 27 | 468 | +441 B |
| 1000 | **39** | **5684** | **+5645 B** |

`0..999` crescente cabe em 39 B (`*1000+1|\0` — um marcador só). Os mesmos mil números
embaralhados custam **146×** mais. Decrescente é idêntico ao crescente (`*10-1|\9`): o
seq-RLE lê passo negativo.

O passo não precisa ser unitário: `0,5,10,…` e `0,100,200,…` custam os mesmos 37 B, e uma
faixa de ids (`1000..1099`) custa 21 B.

## Achado 2 — null não é caro; ele fragmenta a cadência

| coluna | corpo | B/elem |
|---|---:|---:|
| sequência limpa | 19 | 0.19 |
| 10% null | 107 | 1.07 |
| 50% null | 253 | 2.53 |

O `0` do slot custa 1 char. O que pesa é que **cada null corta a corrida**: uma sequência
limpa é um marcador só; com 10% de null vira ~10 trechos, cada um com o seu. Em coluna já
desordenada o efeito some — não havia cadência a quebrar.

## Achado 3 — a lacuna: baixa cardinalidade sem modo denso

Mesma estrutura (`k=2` alternado, `n=100`), tipos diferentes:

| tipo | total | B/elem | por quê |
|---|---:|---:|---|
| bool | **31** | 0.23 | modo **denso** (bit-pack) |
| int | **310** | 3.02 | só o core — `^N` custa 3 B/elem |
| str | **305** | 2.97 | idem |

**10× de diferença pela ausência de um segundo candidato de modo.** O piso do mecanismo de
referência é `^N` + LF = 3 B por elemento, e de `k=2` a `k=100` o custo mal se move
(3.02 → 4.22 B/elem) — o gargalo é o `^N`, não o dicionário.

`k=1` é a exceção (0.08 B/elem): vira um `*100|` só.

## Achado 4 — a magnitude do número quase não importa

| literal | total |
|---|---:|
| 1 dígito | 324 |
| 6 dígitos | 337 |
| 21 dígitos | 352 |

100 elementos, `k=10` nos três. Vinte dígitos a mais custam 28 B **no total**, não por
elemento — porque o literal viaja uma vez e o resto são referências. Float é o caso caro
(588 B de corpo): mais dígitos distintos, menos repetição.

## Leitura

O mecanismo de números hoje é **excelente em cadência** (39 B para mil inteiros) e **fraco em
baixa cardinalidade** (310 B para dois valores alternados). São os dois extremos do mesmo
core: quando há corrida, o seq-RLE resolve; quando não há, sobra o `^N` a 3 B/elem.

A generalização do modo denso para além do bool é o que fecha o segundo caso — o registry já
reserva `b2`/`b4`/`b8`.

## Rodar

```
python run.py     # 29 casos; regenera evidências + result.md
```

`inputs/` · `intermediates/` · `outputs/*-wire.tcf` (REAL) + `*-equivalente.json` +
`*.roundtrip.json`. **Não toca `src/tcf`.**

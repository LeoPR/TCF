# Exemplos explícitos — como ficam os dados em cada caso

Mostro o conteúdo completo do arquivo TCF para 4 estratégias-chave da mesa.
Em cada caso: dataset reordenado (CSV compacto, só para ver a ordem) + as 4
colunas codificadas conforme a heurística C11-híbrida escolheu.

> Sintaxe usada nos blocos:
> - `N*valor` = RLE (N ocorrências contíguas)
> - linha sem prefixo = literal (declaração ou valor sem dict)
> - número solo = referência a índice de dict implícito (1ª aparição decide o idx)
> - O dict é construído pela ordem de 1ª aparição no próprio corpo

---

## CASO A — Sort `(valor, produto, qty)` — vencedor (348 B)

### Dataset reordenado (30 linhas)

```
nome,        produto,    qty,  valor
Beto,        Lápis,      15,   0.50
Helena,      Lápis,      20,   0.50
Carlos,      Lápis,      20,   0.50
Eduardo,     Lápis,      25,   0.50
Ana,         Lápis,      30,   0.50
Helena,      Borracha,   4,    0.75
Gabriel,     Borracha,   4,    0.75
Diana,       Borracha,   4,    0.75
Diana,       Apontador,  8,    1.00
Beto,        Apontador,  8,    1.00
Beto,        Caneta,     10,   1.50
Gabriel,     Caneta,     10,   1.50
Eduardo,     Caneta,     10,   1.50
Ana,         Caneta,     10,   1.50
Fernanda,    Caneta,     20,   1.50
Carlos,      Caneta,     12,   2.00     ← Caneta×5 (1.50) + Caneta×2 (2.00) colam
Helena,      Caneta,     12,   2.00
Eduardo,     Régua,      5,    2.00
Helena,      Régua,      5,    2.00
Carlos,      Régua,      5,    2.00
Gabriel,     Régua,      5,    2.00
Ana,         Caderno,    3,    3.00
Fernanda,    Caderno,    3,    3.00
Beto,        Caderno,    5,    3.00
Diana,       Caderno,    5,    3.00
Ana,         Marcador,   3,    4.00     ← Marcador×2 (4.00 + 4.50) colam
Fernanda,    Marcador,   2,    4.50
Carlos,      Caderno,    1,    5.00     ← Caderno fragmentado (4 antes, 1 aqui)
Diana,       Mochila,    1,    50.00
Eduardo,     Mochila,    1,    50.00
```

### nome → dict-bare implícito (98 B)

Estratégia escolhida porque não há runs longos contíguos suficientes
(só `Diana,Diana` e `Beto,Beto`, runs ≤ 2). Dict pega repetição espalhada.

Dict construído por 1ª aparição: Beto=1, Helena=2, Carlos=3, Eduardo=4,
Ana=5, Gabriel=6, Diana=7, Fernanda=8.

```
nome:
Beto         ← idx 1
Helena       ← idx 2
Carlos       ← idx 3
Eduardo      ← idx 4
Ana          ← idx 5
2            ← Helena
Gabriel      ← idx 6
Diana        ← idx 7
7            ← Diana
1            ← Beto
1            ← Beto
6            ← Gabriel
4            ← Eduardo
5            ← Ana
Fernanda     ← idx 8
3            ← Carlos
2            ← Helena
4            ← Eduardo
2            ← Helena
3            ← Carlos
6            ← Gabriel
5            ← Ana
8            ← Fernanda
1            ← Beto
7            ← Diana
5            ← Ana
8            ← Fernanda
3            ← Carlos
7            ← Diana
4            ← Eduardo
```

### produto → RLE puro (87 B)

8 produtos viram 9 runs (Caderno fragmenta em 2 blocos).

```
produto:
5*Lápis
3*Borracha
2*Apontador
7*Caneta        ← fusão chave: 5 do bloco 1.50 + 2 do bloco 2.00
4*Régua
4*Caderno       ← 4 do bloco 3.00
2*Marcador      ← fusão: 4.00 + 4.50
Caderno         ← solitário, do bloco 5.00
2*Mochila
```

### quantidade → RLE local (55 B)

Inteiros puros, dict colidiria. Tem runs locais bons. RLE-local vence.

```
quantidade:
15
2*20
25
30
3*4
2*8
4*10
20
2*12
4*5
2*3
2*5
3
2
3*1
```

### valor_unitario → RLE puro (65 B)

10 únicos viram 10 runs perfeitos (sort-primário por valor).

```
valor_unitario:
5*0.50
3*0.75
2*1.00
5*1.50
6*2.00
4*3.00
4.00
4.50
5.00
2*50.00
```

### Arquivo TCF completo (sem header de enc/sort, decoder infere)

```
nome:
Beto
Helena
Carlos
Eduardo
Ana
2
Gabriel
Diana
7
1
1
6
4
5
Fernanda
3
2
4
2
3
6
5
8
1
7
5
8
3
7
4
produto:
5*Lápis
3*Borracha
2*Apontador
7*Caneta
4*Régua
4*Caderno
2*Marcador
Caderno
2*Mochila
quantidade:
15
2*20
25
30
3*4
2*8
4*10
20
2*12
4*5
2*3
2*5
3
2
3*1
valor_unitario:
5*0.50
3*0.75
2*1.00
5*1.50
6*2.00
4*3.00
4.00
4.50
5.00
2*50.00
```

**Total ≈ 348 B** (43 cabeçalhos de coluna + 98 + 87 + 55 + 65)

---

## CASO B — Sort `(produto, valor)` (353 B)

Diferença para o caso A: produto é primário, então fica perfeitamente
agrupado (8 runs limpos), mas o `valor=2.00` fragmenta entre Caneta e Régua.

### produto → RLE puro (79 B) — perfeito

```
produto:
2*Apontador
3*Borracha
5*Caderno
7*Caneta
5*Lápis
2*Marcador
2*Mochila
4*Régua
```

### valor → RLE puro (72 B) — `2.00` quebra em dois lugares

```
valor_unitario:
2*1.00
3*0.75
4*3.00
5.00
5*1.50
2*2.00         ← parte 1 (dentro de Caneta)
5*0.50
4.00
4.50
2*50.00
4*2.00         ← parte 2 (dentro de Régua)
```

→ `2.00` aparece 6× total mas em 2 runs separados. Custo extra: ~3 B.

### nome (98 B), quantidade (61 B) seguem mesma escolha do caso A.

---

## CASO C — Sort `(valor, produto)` (352 B)

Como o caso A mas sem o desempate por qty. produto fica como em A (87 B).
quantidade perde 4 B (RLE-local rende 59 em vez de 55).

### produto → RLE (87 B)

```
produto:
5*Lápis
3*Borracha
2*Apontador
7*Caneta        ← fusão Caneta×5 + ×2
4*Régua
4*Caderno
2*Marcador      ← fusão 4.00 + 4.50
Caderno
2*Mochila
```

### quantidade → RLE local (59 B)

Sem o desempate por qty, a ordem dentro de cada bloco (valor, produto) é
estável por linha original — produz menos runs longos.

```
quantidade:
20
30
15
25
20
3*4
2*8
3*10        ← 3 em vez de 4 (sem sub-sort por qty, o 20 fica no meio)
20
10
2*12
4*5
3
2*5
2*3
2
3*1
```

---

## CASO D — Sort `(nome, produto)` — placebo (387 B)

Sub-sort por produto dentro de cada nome **não cria runs em produto** porque
cada pessoa compra produtos diferentes. RLE em produto saves 0 → encoder
escolhe dict-bare igual ao unordered.

### nome → RLE puro (70 B) — perfeito

```
nome:
4*Ana
4*Beto
4*Carlos
4*Diana
4*Eduardo
3*Fernanda
3*Gabriel
4*Helena
```

### produto → dict-bare (109 B) — segue espalhado

Dentro de cada nome, produtos são únicos, então mesmo sortidos
alfabeticamente não há runs.

Dict por 1ª aparição: Caderno=1, Caneta=2, Lápis=3, Marcador=4, Apontador=5,
Régua=6, Mochila=7, Borracha=8.

```
produto:
Caderno     ← idx 1 (Ana/Caderno)
Caneta      ← idx 2 (Ana/Caneta)
Lápis       ← idx 3 (Ana/Lápis)
Marcador    ← idx 4 (Ana/Marcador)
Apontador   ← idx 5 (Beto/Apontador)
1           ← Caderno (Beto/Caderno)
2           ← Caneta (Beto/Caneta)
3           ← Lápis (Beto/Lápis)
1           ← Caderno (Carlos/Caderno)
2           ← Caneta (Carlos/Caneta)
3           ← Lápis (Carlos/Lápis)
Régua       ← idx 6 (Carlos/Régua)
5           ← Apontador (Diana/Apontador)
8 (?)       ← na verdade Borracha vem antes de Caderno alfabeticamente, idx 8
... (continua o padrão)
```

(Rascunho — o detalhe do dict depende da ordem exata; o ponto é: como
produto não vira contíguo dentro de cada nome, RLE não rende.)

### quantidade, valor → mantém-se igual ao unordered

quantidade = literal 72 B, valor = dict-bare 93 B.

### Total: 70 + 109 + 72 + 93 + 43 = **387 B**

Idêntico ao sort-nome solo. Sub-sort foi placebo. Confirma a regra:
**chave secundária só ajuda se correlaciona com primária**.

---

## Comparação visual lado a lado da coluna `produto`

Mesmas 30 linhas, 4 estratégias diferentes:

```
sort (produto, valor):       sort (valor, produto):     sort (valor, produto, qty):    sort (nome, produto):
2*Apontador                  5*Lápis                    5*Lápis                        Caderno
3*Borracha                   3*Borracha                 3*Borracha                     Caneta
5*Caderno                    2*Apontador                2*Apontador                    Lápis
7*Caneta                     7*Caneta                   7*Caneta                       Marcador
5*Lápis                      4*Régua                    4*Régua                        Apontador
2*Marcador                   4*Caderno                  4*Caderno                      1
2*Mochila                    2*Marcador                 2*Marcador                     2
4*Régua                      Caderno                    Caderno                        3
                             2*Mochila                  2*Mochila                      1
                                                                                       2
                                                                                       3
                                                                                       Régua
                                                                                       ... (sem RLE)

8 runs perfeitos             9 runs (Caderno frag.)     9 runs (Caderno frag.)         dict de 8, 22 refs
79 B                         87 B                       87 B                           109 B
```

---

## Comparação visual lado a lado da coluna `valor_unitario`

```
sort (valor, produto, qty):  sort (produto, valor):
5*0.50                       2*1.00
3*0.75                       3*0.75
2*1.00                       4*3.00
5*1.50                       5.00
6*2.00                       5*1.50
4*3.00                       2*2.00      ← parte 1
4.00                         5*0.50
4.50                         4.00
5.00                         4.50
2*50.00                      2*50.00
                             4*2.00      ← parte 2

10 runs                      11 runs (2.00 fragmentado)
65 B                         72 B
```

---

## Caso E — Adicionando o cabeçalho `# enc:`

Mesmo conteúdo do caso A, com header explícito declarando estratégia por
coluna. Decoder não precisa inferir.

```
# TCF v0.5
# sort: valor, produto, quantidade
# enc:  D, R, R, R         ← nome=dict, produto=RLE, qty=RLE-local, valor=RLE
nome:
Beto
Helena
... (idem caso A)
```

Header agrega ~50 B → total ≈ 398 B.

Trade: +14% bytes em troca de:
- decoder simples (sem inferir)
- ordem de sort declarada (cliente sabe se precisa re-sortar)
- validação semântica (decoder verifica que `produto` só tem RLE válido)

Em arquivo de 30 linhas, overhead chama atenção. Em arquivo de 30000 linhas,
mesmo header relativo é 0.05% — desprezível.

---

## Observações finais sobre a representação

1. **A heurística do encoder é local** — cada coluna decide sozinha. Não
   precisa look-ahead pelo arquivo todo, basta uma passada de stats.

2. **O dict-bare aparece "natural"** — primeiras ocorrências dos nomes
   estão lá em texto puro, e o decoder vai construindo o map enquanto lê.
   Não precisa "pular" para um bloco de dict, nem reconstituir no fim.

3. **O RLE só vence quando o sort fez sua parte** — nas colunas onde o sort
   não conseguiu agrupar, o encoder cai elegantemente para dict (ou literal,
   no caso de quantidade quando nem dict ajuda).

4. **As fronteiras de bloco contam** — Caneta×5 + Caneta×2 fundindo na
   transição valor 1.50→2.00 é literalmente o que tira o sort-(valor, produto)
   em 1B do sort-(produto, valor). Em datasets maiores essas colagens são
   mais frequentes e o ganho cresce.

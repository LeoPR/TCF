# Regra unificada aplicada — sort `(valor, produto, qty)`

Mesma ordem do vencedor da mesa anterior. Aplicar a regra unificada a cada
coluna, comparando com o C11-híbrido (que escolhia 1 modo por coluna).

---

## Coluna `nome` — modo bare (não-numérico, sem colisão)

Sequência ordenada (30 posições):

```
Beto, Helena, Carlos, Eduardo, Ana, Helena, Gabriel, Diana, Diana, Beto, Beto,
Gabriel, Eduardo, Ana, Fernanda, Carlos, Helena, Eduardo, Helena, Carlos,
Gabriel, Ana, Fernanda, Beto, Diana, Ana, Fernanda, Carlos, Diana, Eduardo
```

Encoder unificado, decisão por linha (R = run length contígua):

| Pos | Valor | Run | Decl/Ref | Escolha | Bytes |
|---|---|---|---|---|---|
| 1 | Beto | 1 | declara idx 1 | `Beto` | 5 |
| 2 | Helena | 1 | declara idx 2 | `Helena` | 7 |
| 3 | Carlos | 1 | declara idx 3 | `Carlos` | 7 |
| 4 | Eduardo | 1 | declara idx 4 | `Eduardo` | 8 |
| 5 | Ana | 1 | declara idx 5 | `Ana` | 4 |
| 6 | Helena | 1 | ref idx 2 | `2` | 2 |
| 7 | Gabriel | 1 | declara idx 6 | `Gabriel` | 8 |
| 8-9 | Diana | 2 | declara idx 7 + 1 ref OU declaração RLE? | `2*Diana` ou `Diana\n7` (ambos 8 B) | 8 |
| 10-11 | Beto | 2 | ref RLE | `2*1` | 4 |
| 12 | Gabriel | 1 | ref | `6` | 2 |
| 13 | Eduardo | 1 | ref | `4` | 2 |
| 14 | Ana | 1 | ref | `5` | 2 |
| 15 | Fernanda | 1 | declara idx 8 | `Fernanda` | 9 |
| 16 | Carlos | 1 | ref | `3` | 2 |
| 17 | Helena | 1 | ref | `2` | 2 |
| 18 | Eduardo | 1 | ref | `4` | 2 |
| 19 | Helena | 1 | ref | `2` | 2 |
| 20 | Carlos | 1 | ref | `3` | 2 |
| 21 | Gabriel | 1 | ref | `6` | 2 |
| 22 | Ana | 1 | ref | `5` | 2 |
| 23 | Fernanda | 1 | ref | `8` | 2 |
| 24 | Beto | 1 | ref | `1` | 2 |
| 25 | Diana | 1 | ref | `7` | 2 |
| 26 | Ana | 1 | ref | `5` | 2 |
| 27 | Fernanda | 1 | ref | `8` | 2 |
| 28 | Carlos | 1 | ref | `3` | 2 |
| 29 | Diana | 1 | ref | `7` | 2 |
| 30 | Eduardo | 1 | ref | `4` | 2 |
| **Total** | | | | | **98** |

**Codificação final:**

```
nome:
Beto
Helena
Carlos
Eduardo
Ana
2
Gabriel
2*Diana
2*1
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
```

**Empata com C11-híbrido (98 B).** Ganho zero porque os pares contíguos
(Diana-Diana, Beto-Beto) têm mesmo custo em RLE de literal/ref ou em
declaração+ref separados.

---

## Coluna `produto` — modo bare (não-numérico, sem colisão)

Sequência:

```
5*Lápis, 3*Borracha, 2*Apontador, 7*Caneta, 4*Régua, 4*Caderno (3.00),
2*Marcador, Caderno (5.00, ALONE), 2*Mochila
```

Encoder unificado:

| Pos | Run | Valor | Decl? | Escolha | Bytes |
|---|---|---|---|---|---|
| 1-5 | 5 | Lápis | declara idx 1 | `5*Lápis` | 8 |
| 6-8 | 3 | Borracha | declara idx 2 | `3*Borracha` | 11 |
| 9-10 | 2 | Apontador | declara idx 3 | `2*Apontador` | 11 |
| 11-17 | 7 | Caneta | declara idx 4 | `7*Caneta` | 9 |
| 18-21 | 4 | Régua | declara idx 5 | `4*Régua` | 9 |
| 22-25 | 4 | Caderno | declara idx 6 | `4*Caderno` | 10 |
| 26-27 | 2 | Marcador | declara idx 7 | `2*Marcador` | 11 |
| 28 | 1 | Caderno | já declarado | **ref `6`** vs literal `Caderno` (8) | **2** ← ganho! |
| 29-30 | 2 | Mochila | declara idx 8 | `2*Mochila` | 10 |
| **Total** | | | | | **81** |

**Codificação final:**

```
produto:
5*Lápis
3*Borracha
2*Apontador
7*Caneta
4*Régua
4*Caderno
2*Marcador
6
2*Mochila
```

**Ganho de 6 B** sobre C11-híbrido (87 B → 81 B). A 2ª aparição de Caderno
vira ref `6` (2 B) em vez de literal `Caderno` (8 B).

---

## Coluna `quantidade` — modo marcado (inteiro puro, colisão)

Sequência:

```
15, 2*20, 25, 30, 3*4, 2*8, 4*10, 20, 2*12, 4*5, 2*3, 2*5, 3, 2, 3*1
```

(Já com RLE local aplicado.)

Encoder unificado: para cada linha, decide entre literal e ref `:k`:

| Pos | Run | Valor | Caso | Bytes |
|---|---|---|---|---|
| 1 | 1 | 15 | declara idx 1 → `15` | 3 |
| 2-3 | 2 | 20 | declara idx 2 → `2*20` | 5 |
| 4 | 1 | 25 | declara idx 3 → `25` | 3 |
| 5 | 1 | 30 | declara idx 4 → `30` | 3 |
| 6-8 | 3 | 4 | declara idx 5 → `3*4` | 4 |
| 9-10 | 2 | 8 | declara idx 6 → `2*8` | 4 |
| 11-14 | 4 | 10 | declara idx 7 → `4*10` | 5 |
| 15 | 1 | 20 | já declarado, idx=2: literal `20` (3 B) vs ref `:2` (3 B) — **tie** | 3 |
| 16-17 | 2 | 12 | declara idx 8 → `2*12` | 5 |
| 18-21 | 4 | 5 | declara idx 9 → `4*5` | 4 |
| 22-23 | 2 | 3 | declara idx 10 → `2*3` | 4 |
| 24-25 | 2 | 5 | já declarado, idx=9: `2*5` (4 B) vs `2*:9` (5 B) — **literal vence** | 4 |
| 26 | 1 | 3 | já declarado, idx=10: `3` (2 B) vs `:10` (4 B) — **literal vence** | 2 |
| 27 | 1 | 2 | declara idx 11 → `2` | 2 |
| 28-30 | 3 | 1 | declara idx 12 → `3*1` | 4 |
| **Total** | | | | **55** |

**Codificação final:**

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

**Empata com RLE-local C11-híbrido (55 B).** Onde o encoder podia ter usado
ref, decidiu pelo literal porque o marcador `:` adiciona overhead que
supera economia. Para coluna de inteiros curtos com cardinalidade alta,
literal é melhor mesmo.

---

## Coluna `valor_unitario` — modo bare (decimal, sem colisão)

Sequência (já em runs perfeitos por sort primário):

```
5*0.50, 3*0.75, 2*1.00, 5*1.50, 6*2.00, 4*3.00, 4.00, 4.50, 5.00, 2*50.00
```

Cada valor aparece em UM bloco contíguo (sort primário). Sem fragmentação,
nenhuma ref disponível.

Codificação = idêntica a RLE puro:

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

**Total: 65 B** (igual a C11-híbrido).

---

## Total da regra unificada para sort `(valor, produto, qty)`

| Coluna | C11-híbrido | Regra unificada | Δ |
|---|---|---|---|
| nome | 98 | 98 | 0 |
| produto | 87 | **81** | **-6** |
| quantidade | 55 | 55 | 0 |
| valor_unitario | 65 | 65 | 0 |
| headers | 43 | 43 | 0 |
| **total** | **348** | **342** | **-6** |

**Ganho de 6 B** vem todo da coluna `produto` — único caso de fragmentação
(Caderno em 2 blocos por causa do sort secundário valor 3.00 vs 5.00 com
Marcador entre eles).

---

## Arquivo TCF completo (sem header)

```
nome:
Beto
Helena
Carlos
Eduardo
Ana
2
Gabriel
2*Diana
2*1
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
6
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

≈ **342 B** (-55% vs CSV original 762 B)

---

## Observação sobre o sort primário

A predição da hipótese se confirma para `valor_unitario` (sort primário):
**zero refs**, só RLE puro. As 4 colunas mostram comportamentos distintos:

| Coluna | Posição no sort | Tem refs? | Modo dominante |
|---|---|---|---|
| valor_unitario | **primária** | não | RLE puro |
| produto | secundária | sim (1 ref de Caderno) | RLE + 1 ref |
| quantidade | terciária | não (literal vence) | RLE-local com literais |
| nome | não-sortida | sim (muitas refs) | mix RLE + refs |

A regra é a **mesma** nas 4 colunas. O resultado visual diverge porque o
encoder, por linha, escolhe o que é mais curto.

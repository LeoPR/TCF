# Aplicado ao dataset — sort `(valor, produto, qty)`

Recompute a regra unificada com diferentes escolhas de alfabeto. Cardinalidades
das colunas:

- nome: 8 únicos
- produto: 8 únicos
- quantidade: 12 únicos
- valor_unitario: 10 únicos

**Todas ≤ 16, então hex/letras/base64 todos cabem em 1 char.**

---

## Coluna `nome` (cardinalidade 8) — alfabética

Decimal já dá 1 char/idx (8 ≤ 9). Não há colisão (nomes começam com letra).

| Alfabeto | chars/idx | Bytes total nome | Comentário |
|---|---|---|---|
| **Decimal** | 1 | **98** | atual, sem mudança |
| Hex | 1 | 98 | empate |
| Letras | 1 | 98 | empate; mas RISCO de colisão se houver valor de 1 letra |
| Base64 | 1 | 98 | empate |

→ Decimal continua o melhor (mais legível, sem colisão, empate em bytes).

---

## Coluna `produto` (cardinalidade 8) — alfabética

Mesma análise que nome. Decimal vence.

| Alfabeto | chars/idx | Bytes total produto |
|---|---|---|
| **Decimal** | 1 | **81** | (regra unificada já)
| Outros | 1 | 81 | empate |

---

## Coluna `quantidade` (cardinalidade 12) — numérica

Aqui tem colisão. Decimal exige marcador `:`. Letras eliminam.

Cardinalidade 12 ⇒ todos alfabetos não-decimais cabem em 1 char.

### Sequência ordenada

```
15, 2*20, 25, 30, 3*4, 2*8, 4*10, 20, 2*12, 4*5, 2*3, 2*5, 3, 2, 3*1
```

Após dict implícito (encoder decide por linha):
- pos 1-14: tudo declaração (1ª aparição de cada valor)
- pos 15: `20` reaparece — pode ser literal `20` (3B) ou ref
- pos 24-25: `2*5` reaparece — literal RLE (`2*5` = 4B) ou ref RLE
- pos 26: `3` reaparece — literal `3` (2B) ou ref

### Bytes com decimal + marcador

- pos 15 ref: `:2\n` = 3B vs `20\n` = 3B → **empate**, encoder pode usar literal
- pos 24-25 ref RLE: `2*:9\n` = 5B vs `2*5\n` = 4B → **literal vence**
- pos 26 ref: `:10\n` = 4B vs `3\n` = 2B → **literal vence**

Total decimal: 55B (todos literais quando ref perde)

### Bytes com letras (a, b, c, ..., l)

- pos 15 ref: `b\n` = 2B vs `20\n` = 3B → **letra vence** (-1B)
- pos 24-25 ref RLE: `2*i\n` = 4B vs `2*5\n` = 4B → empate
- pos 26 ref: `j\n` = 2B vs `3\n` = 2B → empate

Total letras: **54B** (1B economizado em pos 15)

### Bytes com hex (1, 2, ..., a, b, c)

Mesmo problema: `a` (idx 10) = 1B na ref. Mas `a` colide com nada
(coluna numérica, sem letra como valor). Letra hex equivale a letras
para fins práticos.

Total hex = 54B (mesmo das letras).

### Comparativo da coluna quantidade

| Alfabeto | Bytes | Δ vs decimal |
|---|---|---|
| Decimal (com marcador) | 55 | — |
| **Letras (a-z)** | **54** | **-1** |
| Hex | 54 | -1 |
| Base64 | 54 | -1 |

Ganho modesto (1B nesse dataset). Mas escala: para cardinalidade média
(20-50) com mais ocorrências, esse +1B/ref se acumula em dezenas a
centenas de B em datasets reais.

---

## Coluna `valor_unitario` (cardinalidade 10) — numérica com decimal

Cardinalidade 10. Decimal tem idx `1`–`10` (algumas 2 chars). Colisão é
ZERO porque valores têm decimal (`0.50`, `1.50`) e índices são inteiros
puros.

| Alfabeto | chars/idx | Bytes |
|---|---|---|
| Decimal | 1 (idx 1-9) ou 2 (idx 10) | 65 (atual) |
| **Letras / hex / base64** | 1 sempre | 65 (mesmo, pois sort primária = sem refs) |

Para `valor_unitario` no sort `(valor, produto, qty)`, valor é a coluna
**primária**, então tem 0 refs. Alfabeto não muda os bytes.

Mas se valor fosse não-primária (ex: sort `(produto, valor)`, valor é
secundária):
- Decimal: idx 10 dá 2 chars (idx para `4.00`, `4.50`, `5.00`, `50.00`
  pode ser 10 dependendo da ordem de 1ª aparição)
- Letras: 1 char sempre (cardinalidade 10 ≤ 26)

→ Em sort não-primário sobre valor, letras economizariam ~1B/ref para
valores que recebem idx ≥ 10.

---

## Total do dataset com alfabeto otimizado

Para sort `(valor, produto, qty)`:

| Coluna | Decimal | Letras (otimizado) |
|---|---|---|
| nome | 98 | 98 |
| produto | 81 | 81 |
| quantidade | 55 | **54** |
| valor | 65 | 65 |
| headers | 43 | 43 |
| **total** | **342** | **341** |

Ganho: 1B (~0.3%). **Praticamente nulo neste dataset** — porque as
cardinalidades são baixas (≤ 12) e a regra unificada já encontrou
literais melhores que refs em vários casos.

---

## Onde o ganho seria maior

Cenário hipotético: dataset de 100 linhas, coluna numérica com 50 valores
únicos, frequência média ~2 ocorrências por valor.

Refs estimadas: ~50 (50 declarações + 50 refs).

| Alfabeto | chars/ref | Bytes/ref | Total refs |
|---|---|---|---|
| Decimal com marcador | `:50` = 3B | 3 | 150 B |
| Letras (a-z A-X) | `a` a `X` = 1 char | 2 (com \n) | 100 B |
| **Diferença** | | | **-50 B** |

Em datasets de cardinalidade média (10-94), o ganho cresce
proporcionalmente ao número de refs. Em coluna com 1000 refs,
economizaria 1000B (1KB) só na coluna.

---

## Conclusão da aplicação

A escolha de alfabeto:
- **Não muda nada** para colunas alfabéticas com cardinalidade ≤ 9
- **Economiza 1B/ref** para colunas numéricas (eliminando marcador `:`)
- **Economiza ~1 char/ref** para cardinalidades 10-94 onde decimal exige 2 chars

Para o nosso dataset (mini, cardinalidades baixas), o ganho é desprezível
(1B). Para datasets reais (TPC-H, logs, etc.) com cardinalidades médias,
pode ser significativo.

A próxima questão é: vale o custo (legibilidade, complexidade)?
Discussão em `03-tradeoffs.md`.

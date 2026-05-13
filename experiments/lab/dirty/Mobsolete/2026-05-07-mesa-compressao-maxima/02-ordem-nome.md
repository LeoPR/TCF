# Compressão com SORT POR NOME

Linhas reordenadas alfabeticamente por nome (estável dentro do mesmo nome).

---

## Sequência resultante por coluna

```
nome:           Ana×4 | Beto×4 | Carlos×4 | Diana×4 | Eduardo×4 | Fernanda×3 | Gabriel×3 | Helena×4
produto:        Caderno, Lápis, Marcador, Caneta, Caneta, Caderno, Lápis, Apontador,
                Caneta, Caderno, Régua, Lápis, Mochila, Apontador, Caderno, Borracha,
                Régua, Caneta, Lápis, Mochila, Marcador, Caneta, Caderno, Caneta,
                Borracha, Régua, Lápis, Borracha, Régua, Caneta
quantidade:     3, 30, 3, 10, 10, 5, 15, 8, 12, 1, 5, 20, 1, 8, 5, 4, 5, 10, 25, 1,
                2, 20, 3, 12, 4, 5, 10, 4, 5, 1
valor:          3.00, 0.50, 4.00, 1.50, 1.50, 3.00, 0.50, 1.00, 1.50, 5.00, 2.00,
                0.50, 50.00, 1.00, 3.00, 0.75, 2.00, 1.50, 0.50, 50.00, 4.50, 1.50,
                3.00, 2.00, 0.75, 2.00, 0.50, 0.75, 2.00, 2.00
```

A coluna nome ficou perfeitamente agrupada (8 runs limpos).
As outras 3 colunas ficaram **embaralhadas** — sort por nome não preserva
nenhum padrão nelas.

---

## Estratégias aplicadas

### nome — RLE perfeito

```
4*Ana
4*Beto
4*Carlos
4*Diana
4*Eduardo
3*Fernanda
3*Gabriel
4*Helena
```

≈ **70 B** (vs 199 literal, vs 98 dict-bare)
**RLE vence pesado** — sort em coluna correlacionada consigo mesma é o caso
ótimo do RLE.

### produto — sem ganho de RLE (segue scrambleado)

RLE local: 1 par de Caneta-Caneta na fronteira Ana/Beto (coincidência), savings ~0.

Dict-bare: 8 declarações + 22 refs = ≈ **109 B**

Encoder escolhe **dict-bare**.

### quantidade — só 1 par adjacente (`10,10`), RLE não rende

Literal = 72B; RLE-local saves ~0; dict colide → literal vence.

≈ **72 B**

### valor — 2 pares adjacentes (savings 6B); dict-bare ainda vence

RLE-local: 157 - 6 = 151 B
Dict-bare: ≈ 93 B

Dict vence.

### Total

| Coluna | Estratégia | Bytes |
|---|---|---|
| nome | **RLE** (8 runs) | 70 |
| produto | dict-bare | 109 |
| quantidade | literal | 72 |
| valor | dict-bare | 93 |
| headers | — | 43 |
| **total** | | **≈ 387 B** |

---

## Comparação com unordered (415 B)

Ganho de ordenar por nome: **~28 B** (-7% vs unordered).

Pequeno. Por quê? Porque sort por nome **só ajuda a coluna nome**. As outras
três continuam exatamente igual ao caso unordered (dict-bare sobre o mesmo
conjunto de valores, em ordem irrelevante).

→ **Lição:** sortear por uma coluna que não correlaciona com as outras é
quase um desperdício se o dict implícito já está disponível.

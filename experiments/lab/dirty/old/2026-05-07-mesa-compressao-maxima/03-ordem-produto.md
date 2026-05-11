# Compressão com SORT POR PRODUTO

Linhas reordenadas alfabeticamente por produto (estável).

---

## Sequência resultante por coluna

```
produto:    Apontador×2 | Borracha×3 | Caderno×5 | Caneta×7 | Lápis×5 | Marcador×2 | Mochila×2 | Régua×4
nome:       Diana, Beto, Helena, Gabriel, Diana, Ana, Beto, Carlos, Diana, Fernanda,
            Beto, Carlos, Gabriel, Eduardo, Fernanda, Helena, Ana, Helena, Ana, Beto,
            Eduardo, Carlos, Fernanda, Ana, Diana, Eduardo, Eduardo, Helena, Carlos, Gabriel
quantidade: 8, 8, 4, 4, 4, 3, 5, 1, 5, 3, 10, 12, 10, 10, 20, 12, 10, 20, 30, 15,
            25, 20, 2, 3, 1, 1, 5, 5, 5, 5
valor:      1.00, 1.00, 0.75, 0.75, 0.75, 3.00, 3.00, 5.00, 3.00, 3.00, 1.50, 2.00,
            1.50, 1.50, 1.50, 2.00, 1.50, 0.50, 0.50, 0.50, 0.50, 0.50, 4.50, 4.00,
            50.00, 50.00, 2.00, 2.00, 2.00, 2.00
```

Produto: 8 runs perfeitos.
Quantidade e valor: **parcialmente agrupados** porque correlação produto↔qty/valor
existe mas não é perfeita (Caneta tem qtd 10, 12 ou 20; valor 1.50 ou 2.00).

---

## Estratégias aplicadas

### produto — RLE perfeito

```
2*Apontador
3*Borracha
5*Caderno
7*Caneta
5*Lápis
2*Marcador
2*Mochila
4*Régua
```

≈ **79 B** (vs 233 literal, vs 109 dict-bare)
RLE vence forte.

### nome — não muda (segue embaralhada)

1 par adjacente (Eduardo, Eduardo) → RLE saves 6B, dá 193B.
Dict-bare: ≈ **98 B** (mesma economia que unordered).

Dict vence.

### quantidade — RLE local agora rende algo

Runs: `2*8`, `3*4`, `2*10`, `2*1`, `4*5` (parciais, dentro de blocos de produto).

Bytes salvos:
- `8,8`: 0
- `4,4,4`: save 2
- `10,10`: save 1
- `1,1`: save 0
- `5,5,5,5`: save 4

Total saved: ~7B → quantidade ≈ **65 B** (vs 72 literal, vs 85 dict).

RLE-local vence agora — sort por produto criou agrupamento parcial.

### valor — RLE local também rende, mas dict ainda compete

Runs adjacentes: `1.00,1.00`, `3*0.75`, vários grupos de `3.00`, `1.50`,
`5*0.50`, `2*50.00`, `4*2.00`, etc. Total saved: ~60B.

valor com RLE-local: 157 - 60 = **97 B**
valor com dict-bare: **94 B**

Dict ganha por 3B (margem fina).

### Total

| Coluna | Estratégia | Bytes |
|---|---|---|
| nome | dict-bare | 98 |
| produto | **RLE** (8 runs) | 79 |
| quantidade | **RLE-local** (parcial) | 65 |
| valor | dict-bare | 94 |
| headers | — | 43 |
| **total** | | **≈ 379 B** |

---

## Comparação

| | Bytes | vs unordered |
|---|---|---|
| Unordered | 415 | — |
| Sort-nome | 387 | -28 |
| **Sort-produto** | **379** | **-36** |

Sort por produto **vence sort por nome** porque produto está parcialmente
correlacionado com quantidade (e fracamente com valor). Sort puxa essas duas
para um estado parcialmente comprimível também.

→ **Lição:** sort vence quando a chave **arrasta outras colunas junto**.

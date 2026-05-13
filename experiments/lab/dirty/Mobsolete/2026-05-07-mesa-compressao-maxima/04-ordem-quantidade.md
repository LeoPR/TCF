# Compressão com SORT POR QUANTIDADE

Sort numérico (não lexicográfico) por quantidade. Ascendente.

> **Palpite inicial do usuário:** "esse parece inútil". Vamos verificar.

---

## Sequência resultante por coluna

```
quantidade: 1×3 | 2 | 3×3 | 4×3 | 5×6 | 8×2 | 10×4 | 12×2 | 15 | 20×3 | 25 | 30
nome:       Diana, Carlos, Eduardo, Fernanda, Ana, Ana, Fernanda, Helena, Gabriel,
            Diana, Eduardo, Beto, Helena, Diana, Carlos, Gabriel, Diana, Beto, Beto,
            Gabriel, Eduardo, Ana, Carlos, Helena, Beto, Helena, Fernanda, Carlos,
            Eduardo, Ana
produto:    Mochila, Caderno, Mochila, Marcador, Caderno, Marcador, Caderno,
            Borracha, Borracha, Borracha, Régua, Caderno, Régua, Caderno, Régua,
            Régua, Apontador, Apontador, Caneta, Caneta, Caneta, Caneta, Caneta,
            Caneta, Lápis, Lápis, Caneta, Lápis, Lápis, Lápis
valor:      50.00, 5.00, 50.00, 4.50, 3.00, 4.00, 3.00, 0.75, 0.75, 0.75, 2.00,
            3.00, 2.00, 3.00, 2.00, 2.00, 1.00, 1.00, 1.50, 1.50, 1.50, 1.50, 2.00,
            2.00, 0.50, 0.50, 1.50, 0.50, 0.50, 0.50
```

Quantidade: 12 runs (alguns de 1).
Produto: **muito agrupado** porque cada quantidade tende a ir junto com poucos
produtos (qtd 5 → Régua/Caderno; qtd 10 → Caneta; qtd 4 → Borracha).
Valor: parcialmente agrupado pelo mesmo motivo.

---

## Estratégias aplicadas

### quantidade — RLE perfeito

```
3*1
2
3*3
3*4
6*5
2*8
4*10
2*12
15
3*20
25
30
```

≈ **46 B** (vs 72 literal — saved 26B)

### produto — RLE local agora rende MUITO

Runs: `3*Borracha`, `2*Régua`, `2*Apontador`, `6*Caneta`, `2*Lápis`, `Caneta`(solo),
`3*Lápis`. Savings: ~82B.

produto RLE-local: 233 - 82 = **151 B**
produto dict-bare: **109 B**

Dict ainda vence (109 < 151) — RLE captura runs longos mas há fragmentação:
Caneta aparece em 2 blocos (×6 + ×1) e Lápis idem (×2 + ×3). Dict não se
importa com fragmentação.

### nome — segue embaralhada

Sem runs adjacentes úteis. Dict-bare ≈ **98 B**.

### valor — alguns runs decentes mas dict vence

Runs: `3*0.75`, `2*1.00`, `4*1.50`, alguns pares de `2.00` e `0.50`, `2*50.00`.
Savings: ~41B.

valor RLE-local: 157 - 41 = **116 B**
valor dict-bare: **93 B**

Dict vence.

### Total

| Coluna | Estratégia | Bytes |
|---|---|---|
| nome | dict-bare | 98 |
| produto | dict-bare | 109 |
| quantidade | **RLE** (12 runs) | 46 |
| valor | dict-bare | 93 |
| headers | — | 43 |
| **total** | | **≈ 389 B** |

---

## Comparação

| | Bytes |
|---|---|
| Sort-produto | 379 |
| **Sort-quantidade** | **389** |
| Sort-nome | 387 |
| Unordered | 415 |

Sort-quantidade **NÃO É INÚTIL** — fica empatado com sort-nome e perde por
apenas 10B para sort-produto. **Comprimiu mais a coluna alvo** (46B vs 79B
do produto), mas as outras colunas ganham menos por correlação.

### Por que sort-produto vence sort-quantidade

Produto correlaciona melhor com **duas** outras colunas (qty parcial + valor
parcial), então o sort arrasta dois passageiros. Quantidade só arrasta produto
parcialmente — valor só fragmentadamente.

### Quando sort-quantidade venceria

Em dataset onde qty determina o resto. Exemplo: lojas vendem em "embalagens
fixas" (5 = pacote, 10 = caixa, 20 = caixa grande), e cada embalagem tem
preço fixo. Então qty → valor é determinístico. Aí sort-qty empata com
sort-valor para fins de RLE de várias colunas.

→ Conclusão preliminar: **não há sort universalmente inútil**. Cada um vira
ótimo em algum tipo de dataset.

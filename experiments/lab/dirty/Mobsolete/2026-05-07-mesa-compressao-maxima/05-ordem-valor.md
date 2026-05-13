# Compressão com SORT POR VALOR_UNITARIO

Sort numérico ascendente por valor.

> **Palpite inicial:** "esse parece inútil". Vamos ver.

---

## Sequência resultante por coluna

```
valor:      0.50×5 | 0.75×3 | 1.00×2 | 1.50×5 | 2.00×6 | 3.00×4 | 4.00 | 4.50 | 5.00 | 50.00×2
produto:    Lápis×5 | Borracha×3 | Apontador×2 | Caneta×5 | Caneta, Régua×3, Caneta, Régua |
            Caderno×4 | Marcador | Marcador | Caderno | Mochila×2
nome:       Helena, Ana, Beto, Eduardo, Carlos, Helena, Gabriel, Diana, Diana, Beto,
            Beto, Gabriel, Eduardo, Fernanda, Ana, Carlos, Eduardo, Helena, Carlos,
            Gabriel, Ana, Beto, Helena, Diana, Fernanda, Ana, Ana, Carlos, Diana, Eduardo
quantidade: 20, 30, 15, 25, 20, 4, 4, 4, 8, 8, 10, 10, 10, 20, 10, 12, 5, 5, 5, 12,
            5, 3, 5, 5, 3, 3, 2, 1, 1, 1
```

**Surpresa pesada na coluna produto:** sort por valor agrupou produtos quase
perfeitamente, porque vários produtos têm valor único (Lápis sempre 0.50,
Borracha sempre 0.75, Apontador sempre 1.00, etc.). A "bagunça" só aparece
no grupo de valor 2.00 (Caneta e Régua misturados) e 3.00 (Caderno).

---

## Estratégias aplicadas

### valor — RLE perfeito

```
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

≈ **65 B** (vs 157 literal, vs 93 dict-bare)
RLE vence forte — 6 runs longos.

### produto — RLE local rende mais que sort-by-produto NÃO renderia em valor

Runs após sort-by-valor:
`5*Lápis`, `3*Borracha`, `2*Apontador`, `6*Caneta` (5 do 1.50 + 1 do 2.00),
`3*Régua`, `Caneta` (solo), `Régua` (solo), `4*Caderno`, `2*Marcador`
(4.00 + 4.50), `Caderno` (solo do 5.00), `2*Mochila`.

Bytes: ≈ **101 B** (savings ~132B vs literal)

produto dict-bare: 109 B.

**RLE vence dict por 8B aqui** — porque os runs que aparecem são longos
(>=3 em vários casos), e RLE pena pouco com fragmentação dos blocos
solitários (Caneta solo, Régua solo, Caderno solo).

### quantidade — RLE local rende moderadamente

Runs: `3*4`, `2*8`, `3*10`, `3*5`, `2*5`, `2*3`, `3*1`. Savings ~10B.

quantidade RLE-local: 72 - 10 = **62 B** (vs literal 72, vs dict 85)
RLE-local vence.

### nome — segue embaralhada

Sem runs úteis. Dict-bare ≈ **98 B**.

### Total

| Coluna | Estratégia | Bytes |
|---|---|---|
| nome | dict-bare | 98 |
| produto | **RLE** (11 runs, alguns longos) | 101 |
| quantidade | **RLE-local** (parcial) | 62 |
| valor | **RLE** (10 runs) | 65 |
| headers | — | 43 |
| **total** | | **≈ 369 B** |

---

## Comparação geral

| Ordenação | Bytes | Δ vs unordered |
|---|---|---|
| **Sort-valor** | **369** | **-46** |
| Sort-produto | 379 | -36 |
| Sort-nome | 387 | -28 |
| Sort-quantidade | 389 | -26 |
| Unordered | 415 | — |

### Por que sort-valor é o vencedor neste dataset?

Três motivos combinados:
1. **valor tem alta repetição própria** (10 únicos × 30 linhas, máximo 6 ocorrências).
2. **valor está fortemente correlacionado com produto** (alguns produtos têm
   valor único). Sort-valor arrasta produto junto.
3. **valor está fracamente correlacionado com quantidade**, mas mesmo assim
   produz alguns runs locais úteis.

→ O sort venceu porque a chave **ordenou três passageiros junto** (valor,
produto, parte de quantidade), enquanto sort-produto só arrastou dois.

### Refutação do palpite "sort-valor é inútil"

**Errado.** Em datasets onde valor tem cardinalidade ~igual à de produto e
correlaciona com produto (preço por SKU é regra na vida real), sort-valor
pode ser tão bom ou melhor que sort-produto.

A "inutilidade" só aparece se:
- valor for praticamente único por linha (cardinalidade ≈ N), ou
- valor for completamente independente das outras colunas.

Nenhum dos dois é o caso comum.

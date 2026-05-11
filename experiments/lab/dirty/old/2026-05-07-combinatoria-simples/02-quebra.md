# Hipóteses de QUEBRA (aplicadas DEPOIS de escolher a compressão)

Cada hipótese assume que uma compressão de `01-compressao.md` já foi aplicada.
A quebra é a próxima decisão: como fatiar o resultado em pedaços entregáveis.

Sem cabeçalho ainda. Sem manifest. Só o efeito físico de partir o conteúdo.

---

## B1 — Monolítico

Sem quebra. Um arquivo só, do início ao fim.

```
(preencher — é o resultado da compressão escolhida sem nenhuma divisão)
```

**Bytes totais:** _____  
**Bytes até primeira resposta útil:** _____  (igual ao total, sem quebra)  
**Comentário:** _____

---

## B2 — Por blocos de N linhas

Quebra a cada N linhas (ex: N=4 → 3 chunks). Útil em row-major, estranho em
column-major (cada chunk teria pedaço de cada coluna).

```
chunk 1:
(linhas 1-4)
---
chunk 2:
(linhas 5-8)
---
chunk 3:
(linhas 9-12)
```

**Bytes por chunk:** _____ / _____ / _____  
**RLE sobrevive entre chunks?** _____  
**Comentário:** _____

---

## B3 — Por coluna (cada coluna = 1 chunk)

Cada coluna vira um chunk independente.

```
chunk-nome:
(coluna nome inteira)
---
chunk-produto:
(coluna produto inteira)
---
chunk-quantidade:
(...)
---
chunk-valor:
(...)
```

**Bytes por chunk:** _____ / _____ / _____ / _____  
**Cliente pode renderizar cedo?** _____  
**Comentário:** _____

---

## B4 — Por grupo (chunk por valor de coluna escolhida — ex: por nome)

Cada chunk contém TODAS as linhas de uma pessoa.

```
chunk-João:
(linhas onde nome=João, em formato column-major local)
---
chunk-Maria:
(linhas onde nome=Maria)
---
chunk-Ana:
(...)
---
chunk-Carlos:
(...)
```

**Bytes por chunk:** _____  
**RLE intra-chunk eficaz?** _____  
**Cada chunk é "unidade de resposta" pronta?** _____  
**Comentário:** _____

---

## B5 — Por tier (colunas-chave em chunk 0, resto depois)

Tier 1 = só `nome` (ou `nome` + algum agregado pré-calculado tipo `total_gasto`).
Tier 2+ = restante das colunas.

```
chunk-tier1:
(colunas mínimas para resposta inicial)
---
chunk-tier2:
(detalhes — produto, quantidade, valor)
```

**Bytes por chunk:** _____  
**Tier 1 é suficiente para alguma UI parcial?** _____  
**Comentário:** _____

---

## B6 — Híbrido: tier 1 (resumo) + tiers 2+ por grupo (detalhe)

Combina B5 e B4. Primeiro chunk traz nomes (e totais agregados, se desejável).
Próximos chunks vêm um por pessoa, com todos os detalhes.

```
chunk-0 (tier1, resumo):
nomes: João, Maria, Ana, Carlos
(opcional: totais)
---
chunk-1 (tier2, grupo=João):
(produtos/quantidades/valores do João)
---
chunk-2 (tier2, grupo=Maria):
(...)
---
... etc
```

**Bytes por chunk:** _____  
**T_first (tempo até render dos nomes):** _____  
**T_total:** _____  
**Comentário:** _____

---

## Notas livres

- Em qual quebra a soma dos pedaços fica bem maior que B1 (overhead crítico)?
- Em qual quebra cada pedaço sozinho já é "útil" (decodificável + renderizável)?
- Quebras que dependem de ordem específica vs quebras paralelizáveis?

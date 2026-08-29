---
title: "T-DOC-TIPOS-MISTOS: elaborar a documentação do comportamento de tipos mistos (hoje em post-it)"
status: open
priority: P3
created: 2026-08-29
updated: 2026-08-29
target: "pré-1.0, didático; o comportamento já está soldado e medido, falta a redação"
blocked-by: []
related:
  - docs/reference/api.md
  - docs/reference/lazy-view.pt-BR.md
  - docs/how-to/mimetizar-pandas-sql-polars.md
  - docs/adr/0039-lazytype-bool-cabeca-congelada-extras.md
---

# T-DOC-TIPOS-MISTOS

**[registro]** O comportamento do TCF diante de coluna de tipos mistos está **soldado e
medido** (commit `b80da8a5`), e documentado em três lugares em forma de **post-it**: o
suficiente para não se perder, longe do suficiente para ensinar. Este ticket é o rastro
para a passada didática.

## Onde estão os post-its

| lugar | o que já diz | o que falta |
|---|---|---|
| [`api.md`](../docs/reference/api.md), seção *Coluna de tipos mistos* | a tabela do que cada família faz, e por que a união bool+str tem rota e as outras não | o porquê contado como raciocínio, não como tabela |
| [`lazy-view.pt-BR.md`](../docs/reference/lazy-view.pt-BR.md) e `.en.md`, seção *A coluna de UNIÃO* | os quatro modos de perguntar, com o resultado de cada um | um exemplo que mostre para que serve cada modo, e não só o que devolve |
| [`mimetizar-pandas-sql-polars.md`](../docs/how-to/mimetizar-pandas-sql-polars.md), seção *Uma coluna que mistura booleano e texto* | as receitas TCF, verificadas por execução, e a linha de limpeza | **a coluna comparativa com pandas, polars e SQL** |

## O que trava a parte comparativa

Este ambiente não tem `pandas`, `polars`, `pyarrow` nem `numpy` instalados, e a página não
afirma o que não mediu. Fechar essa lacuna exige um ambiente com as bibliotecas, e o
resultado de cada uma conferido por execução, como as receitas TCF já são.

## Critérios de aceite

- [ ] A coluna comparativa da página de mímica preenchida, com cada resultado obtido por
      execução da ferramenta de origem, não de memória.
- [ ] As três seções reescritas com intenção didática: hoje elas registram, não ensinam.
- [ ] Um exemplo por modo de consulta que mostre a **pergunta** que aquele modo responde.
- [ ] Nenhuma das três referencia o dirty lab: o lab é histórico, a documentação carrega o
      presente.

## Um resto que apareceu junto

[`mimetizar-pandas-sql-polars.md`](../docs/how-to/mimetizar-pandas-sql-polars.md), na seção
*Verificação*, aponta as receitas da página para um script do dirty lab. A verificação
pertence a um teste, que é o que sobrevive a uma limpeza do lab. Trocar quando esta página
for reescrita.

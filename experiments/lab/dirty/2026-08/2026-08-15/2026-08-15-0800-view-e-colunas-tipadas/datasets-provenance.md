# Procedência dos dados — e os vieses declarados

## Sintético, determinístico, sem `Z:`

Uma tabela só, gerada em `run.py::tabela()` com `random.Random(11)` — sem `random` global,
reprodutível. 5000 linhas × 5 colunas, **retangular e sem nulls**:

| coluna | forma | por que está aqui |
|---|---|---|
| `data` | ISO `YYYY-MM-DD`, 2015→2026 | a coluna do filtro; é o tipo mais medido do projeto |
| `cliente` | `cliente-NNN`, 400 distintos | baixa cardinalidade → modo dict |
| `produto` | `SKU-NNNN`, 900 distintos | cardinalidade média |
| `qtd` | inteiro 1..99 | a coluna que **vira `int` nativo** na variante tipada |
| `preco` | decimal 2 casas | a coluna que **vira `float` nativo** na variante tipada |

## As três variantes, e a CONSTANTE

O ponto do lab é que as três carregam **exatamente os mesmos valores**. Muda só a forma de
chamada e o tipo Python:

| variante | chamada | rota |
|---|---|---|
| todo string (dict) | `encode(COLS)` | `.8M` |
| todo string (list[dict]) | `encode([dict(...), ...])` | `.8H` |
| 2 colunas tipadas | `encode({**COLS, "qtd": [int], "preco": [float]})` | `.8H` |

A segunda existe **só** para isolar o envelope da tipagem. Sem ela, +101% seria atribuído à
tipagem — que é o oposto do que a medição mostra.

## Viés 1 — uma tabela, e ela é o caso favorável ao `.8M`

Retangular, sem nulls, sem aninhamento. É **exatamente** o caso em que `.8M` e `.8H` competem,
e por isso é onde a comparação tem sentido. **Não é uma amostra de tabelas reais** — é o caso
que isola a pergunta.

Tabela com aninhamento real usaria o `.8H` por necessidade e não haveria comparação a fazer;
os +101,7% **não se transferem** para lá.

## Viés 2 — n=5000, e as razões de tempo são dev-run

Máquina não quiescente. O Bloco 3 reporta **razões** (1,8× e 5,3×), não milissegundos como
verdade. O `min()` de 5 repetições com aquecimento reduz, não elimina.

## Viés 3 — 10 formas de wire, não todas as formas

As 10 cobrem os discriminadores que o `encode` emite hoje por caminho normal. Não cobrem wire
escrito à mão nem formas de terceiros; a `#TCF.8C` (bN domínio-por-último) não aparece porque
não consegui produzi-la por chamada normal nesta tabela.

## O que NÃO foi medido

- **`.8H` com aninhamento** — onde o envelope se justifica.
- **O `view` sobre single-col**, que o `T-LAZY-BYPASS-ARITMETICO` já prototipou.
- **O custo de implementar** qualquer das duas saídas do §7 do `result.md`.

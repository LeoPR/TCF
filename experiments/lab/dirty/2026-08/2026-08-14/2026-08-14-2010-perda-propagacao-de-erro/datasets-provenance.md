# Procedência dos dados — e o viés declarado

## Fonte

`Z:/tcf-data/interim/online-retail.db` (SQLite, read-only), tabela `online_retail`, colunas
**`UnitPrice` e `Quantity`** — filtro `UnitPrice > 0 AND Quantity > 0`.

**Não versionado**; este lab **exige** `Z:` e não roda sem ele.

**Amostragem**: passo espalhado (`linhas[::176]`), alvo 3000. Nunca `LIMIT` puro — `LIMIT`
degenera a amostra e neste projeto já inverteu uma conclusão (o mesmo `online-retail` com
`LIMIT 600` devolveu 1 data distinta).

## Por que esta fonte

É a **única** do corpus com preço e quantidade na mesma linha. Isso permite medir a propagação
num **produto derivado real** (`receita = preço × quantidade`) em vez de num produto sintético
— que mediria a aritmética, não o dado.

## Derivado sintético, declarado

A coluna `custo` **não existe no dataset**: é `venda × 0,97`, construída aqui para produzir um
par de valores **próximos**, que é o regime do cancelamento catastrófico. O `0,97` é arbitrário
e escolhido para dar margem estreita — **é o pior caso de propósito**, não uma margem de varejo
observada. As 500 linhas usadas são as primeiras da amostra já espalhada.

Sem esse par sintético não haveria como exibir a lente que quebra, porque o corpus não tem duas
colunas monetárias próximas na mesma tabela.

## Viés, declarado

- **Uma fonte só, e é varejo britânico** (`online-retail`, UCI). Os números de erro relativo
  dependem da distribuição de preços — aqui concentrada em valores baixos, com cauda até ~800.
  Um catálogo de preços altos e uniformes daria erros relativos menores a mesmo `d`.
- **`UnitPrice` já tem ≤2 casas**, então `d=4,3,2` são no-op. A escada real tem só dois degraus
  (`d=1` e `d=0`), e `d=0` é semanticamente absurdo para preço — está na tabela como **limite**,
  não como opção.
- **O erro máximo por valor é dominado pelos preços mínimos** (0,12 e similares): arredondar
  0,12 para 0,1 já dá 16,7%, e um item de 0,03 daria 100%. A métrica "erro máximo" é por
  construção um retrato da cauda inferior, não do típico.
- **Nada aqui é gate real-world.** São 2 colunas de 1 fonte; o gate para qualquer weld lossy
  exige N≥5 fontes mais decisão explícita do owner.

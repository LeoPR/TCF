# Proveniência dos dados

## Bordas (12 casos, `borda-*`)

Construídas à mão em `run.py` — não são amostra, são **casos-limite** escolhidos para
exercitar o que o IEEE-754 e o JSON tornam especial: `-0.0`, o maior float representável
(`1.7976931348623157e308`), o menor subnormal (`5e-324`), notação científica nas duas
direções, precisão suja (`0.1+0.2`), união `int|float` na mesma coluna, slot nulo, e os três
que **devem** ser recusados (NaN, +Inf, −Inf).

Sintético é o correto aqui: borda não se amostra, se constrói.

## Colunas reais (5, `real-*`)

Lidas de `Z:/tcf-data/interim/*.db` em tempo de execução — nada baixado, nada congelado
(o lab roda sem `Z:`, pulando esta parte).

| coluna | origem | por que está aqui |
|---|---|---|
| `wine.density` | wine-quality | precisão fixa de instrumento (3–5 casas) |
| `wine.alcohol` | wine-quality | **a precisão suja** (13–14 casas em 6 valores) |
| `tpch.l_discount` | TPC-H sf001 | entre 0 e 1, cardinalidade baixa (k=11) |
| `tpch.l_quantity` | TPC-H sf001 | **int em roupa de float** (`17.0`, 2000/2000 com 1 casa) |
| `retail.UnitPrice` | online-retail | moeda, casas variadas (1 e 2) |

Cinco colunas, quatro origens — escolhidas para cobrir as variações que o owner listou, cada
uma sendo o caso mais nítido da sua variação.

**CONSTANTE na comparação**: cada coluna passa pelos mesmos 5 eixos; o RT é sempre
`igual_float` (tipo + valor + sinal do zero).

Nenhum dado pessoal: são medidas químicas, preços e quantidades.

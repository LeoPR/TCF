# Proveniência dos dados

## Sintéticos (8 casos, prefixo `sint-`)

Gerados por `casos.py`, seed fixa 20260814, **materializados** em
`inputs/<caso>.entrada.json`. Cada um isola um regime, e quatro deles existem para provar
que o spec **recusa** onde deve: largura já uniforme, baixa cardinalidade, aleatório sem
progressão, e negativos.

## Reais (10 casos, prefixo `real-`)

Colunas congeladas em `inputs/fontes/`, vindas do lab dirty
`2026-08-14-0112-gatilhos-int-em-corpus-real`, que as extraiu de `Z:/tcf-data/interim/*.db`
por **descoberta automática** (varre os bancos, pega toda coluna numérica com dados
suficientes). Nada foi baixado; o hub é a fonte, como manda a regra do projeto.

Congelar aqui é deliberado: o `run.py` roda **sem `Z:` montado**, e a evidência é
reproduzível por quem clonar o repositório.

| caso | origem | por que está aqui |
|---|---|---|
| `real-tpch-orderkey` | TPC-H sf001, `orders.o_orderkey` | o maior ganho medido (2,80×) |
| `real-tpch-partkey` | TPC-H sf001, `part.p_partkey` | ganho típico (1,79×) |
| `real-tpch-custkey` | TPC-H sf001, `customer.c_custkey` | ganho típico (1,75×) |
| `real-tpch-lineitem-orderkey` | TPC-H sf001, `lineitem.l_orderkey` | **chave repetida**: o pad perde |
| `real-tpch-linenumber` | TPC-H sf001 | k=7, largura 1, o bN domina |
| `real-wine-quality` | wine-quality | nota 3..9, k=7 |
| `real-retail-quantity` | online-retail | tem **negativos**: o spec recusa |
| `real-ibge-municipio-id` | IBGE | 7 dígitos uniformes, sem progressão |
| `real-tpch-availqty` | TPC-H sf001, `partsupp` | largura varia, sem progressão |
| `real-tpch-nationkey` | TPC-H sf001 | k=25, baixa cardinalidade |

**Seis dos dez casos reais são de recusa.** Um lab que só mostra o caso favorável não prova
nunca-pior, que é a invariante que sustenta todo mecanismo novo do projeto.

## ⚠ Viés declarado

Sete dos dez reais vêm de **TPC-H**, um gerador sintético de benchmark com muitas chaves
sequenciais densas, exatamente o regime que **favorece o PAD**. Os independentes são três
(IBGE, retail, wine).

O que este lab sustenta com firmeza: que o spec **ganha onde o gatilho dispara** e **recusa
onde não**, com round-trip e nunca-pior provados. O que ele **não** sustenta: que 1,79× de
mediana seja previsão para dado de produção genérico, para isso o corpus precisaria de
origens mais variadas, e o lab dirty de origem declara o mesmo.

## CONSTANTE na comparação

Os **mesmos valores** no baseline e no candidato; só varia a presença do spec. A largura é
**dimensionada pela coluna** (o que um auto-detector faria), nunca escolhida à mão. Nenhum
dado pessoal: são chaves, quantidades, notas e ids numéricos.

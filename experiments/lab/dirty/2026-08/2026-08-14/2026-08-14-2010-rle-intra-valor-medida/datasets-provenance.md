# Procedência dos dados — e o viés declarado

## Sintéticos (blocos 1–3)

Gerados em `run.py`, sem seed (literais e concatenação determinística). Gravados em
`inputs/<caso>.entrada.json` com `<caso>.fonte.json` ao lado.

**Bloco 1** é um **par de contra-prova**: `b1-com-run` e `b1-sem-run` têm o **mesmo
comprimento (19) e o mesmo alfabeto** (dígitos e `.`); a única variável é a repetição. Sem esse
par, uma diferença de bytes não poderia ser atribuída ao run.

**Bloco 2** varia só `N`, mantendo as bordas (`a`…`b`) constantes. Viés declarado: um run de
zeros puros é o **melhor caso possível** para qualquer RLE — a curva medida ali é um limite
superior de quanto o mecanismo teria a ganhar, não uma expectativa.

**Bloco 3** não tem dado de entrada no sentido usual: os arquivos em
`inputs/f*.wire-de-entrada.tcf` são **wires escritos à mão**, que o encoder canônico nunca
produz. São sondas do decoder, não amostras.

## Reais (bloco 4)

Corpus local `Z:/tcf-data/interim/*.db` (SQLite, read-only). **Não versionado**; o lab roda sem
ele, pulando este bloco.

| coluna | por que está aqui | n |
|---|---|---|
| `wine-quality.wine.alcohol` | a **única** coluna do corpus com run no **meio** do valor (40 valores `n/30`, exportados com `%.15g`) | 6497 (tabela inteira) |
| `tpch-sf001.orders.o_clerk` | padding de ID — o run é **prefixo compartilhado**; 1000 clerks distintos | 15000 |
| `tpch-sf001.customer.c_name` | padding de ID em **progressão aritmética perfeita** — é onde o run é *load-bearing* | 1500 |

**Viés, declarado, e é forte:**

- **Duas das três são TPC-H**, que é dado **gerado**, e as duas são a *mesma família* de padrão
  (`Nome#000000NNN`). Não representam frequência no mundo.
- **`wine.alcohol` tem n=1 no corpus** — é a única instância da família "run no meio". Qualquer
  conclusão sobre essa família repousa numa coluna de um dataset.
- A varredura que precedeu este lab achou **11 de 186 colunas** com run ≥6, e 99% delas são da
  família padding-de-ID. O corpus **não tem** o regime onde o mecanismo brilharia (runs longos,
  não-load-bearing) — o Bloco 2 sintetiza esse regime justamente porque ele não existe aqui.

**Amostragem**: `wine` e `customer` são lidas **inteiras**; `orders` é truncada nas primeiras
15000 linhas. Truncar por posição é aceitável aqui porque a métrica é a **presença de run na
grafia**, que é uniforme por construção do gerador TPC-H — não é uma métrica sensível a
distribuição. Onde a distribuição importasse, o passo espalhado seria obrigatório.

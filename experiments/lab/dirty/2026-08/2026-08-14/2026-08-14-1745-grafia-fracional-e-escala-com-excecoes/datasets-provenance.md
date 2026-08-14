# Procedência dos dados — e o viés declarado

## Sintéticos (7 casos + 8 bordas)

Gerados em `casos.py`, sem seed (são listas literais ou aritmética exata). Gravados em
`inputs/<caso>.entrada.json` com `<caso>.fonte.json` ao lado.

**Viés, declarado**: são **viesados por construção** — escolhidos para ver *comportamento*,
não para vencer benchmark. `dizima-variada` existe justamente porque é o regime onde a fração
teria folga; ele **não é evidência de frequência no mundo**. Por isso cada sintético que faz
uma afirmação vem com o **par de contra-prova**:

| caso | par | o que o par isola |
|---|---|---|
| `owner-sujo-no-meio` | `owner-sem-o-sujo` | quanto **um** valor sujo custa hoje |
| `dizima-variada` | `dizima-uniforme` | quanto do ganho é do mecanismo e quanto o RLE já fazia |
| `money-com-terco` | `money-2casas` | o que 1 dízima em 20 faz com a escala pura |

`money-2casas` foi escrito **fora de progressão** de propósito: uma progressão aritmética
viraria seq-RLE depois da escala e eu estaria medindo o núcleo, não o mecanismo.

As 8 bordas são as mesmas do fechamento do float
([`…-1616`](../2026-08-14-1616-fechamento-float/)), reapontadas — lá se perguntava do núcleo,
aqui se pergunta dos mecanismos.

## Reais (5 colunas)

Corpus local `Z:/tcf-data/interim/*.db` (SQLite, read-only). **Não versionado**; o lab roda
sem ele, pulando estas linhas.

| coluna | por que está aqui | n |
|---|---|---|
| `wine-quality.wine.alcohol` | **o caso que quebrou a escala** no fechamento do float — valores de 13–14 casas (médias sujas do dataset) derrubavam a coluna inteira | 2000 |
| `wine-quality.wine.density` | 3–5 casas; é a coluna do PoC de junho (M4) | 2000 |
| `online-retail.online_retail.UnitPrice` | money-like real, onde uma **soma** tem sentido semântico | 2000 |
| `tpch-sf001.lineitem.l_discount` | 2 casas, faixa 0.00–0.10 — escala pura fácil | 2000 |
| `tpch-sf001.lineitem.l_extendedprice` | money-like de maior magnitude | 2000 |

**Amostragem**: passo espalhado (`vals[::passo]`), nunca `LIMIT` puro — `LIMIT` degenera a
amostra e neste projeto já inverteu uma conclusão (o `online-retail` com `LIMIT 600` devolveu
1 data distinta).

**Viés, declarado**: 2 das 5 colunas são TPC-H (dado **gerado**, não observado), e 2 são do
mesmo dataset (`wine`). São **cinco colunas**, escolhidas por já terem papel em avaliações
anteriores — não é uma amostra do mundo, e nenhum número daqui deve ser lido como
frequência esperada. Cobrir os regimes que faltam é exatamente o "depois expandimos".

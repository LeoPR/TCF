# Resultado — RLE intra-valor, primeira medição da H-INTRA

4 blocos, 0 falhas de RT. Linguagem de dirty lab: **orienta**, não fecha.

## 1. O núcleo não aproveita run intra-valor — zero

Par de contra-prova, **mesmo comprimento e mesmo alfabeto**, só muda se há repetição:

| caso | corpo emitido | bytes |
|---|---|---|
| `b1-com-run` | `\0.\30000000000000004` | **29** |
| `b1-sem-run` | `\0.\31415926535894704` | **29** |

**Diferença: 0 B.** Os 14 zeros custam exatamente o mesmo que 14 dígitos sem padrão.

## 2. A curva é linear, com coeficiente exato

`"a" + N×"0" + "b"`:

| N | 1 valor | 20 distintos |
|---:|---:|---:|
| 4 | 15 | 149 |
| 32 | 43 | 709 |
| 128 | 139 | 2629 |
| 256 | 267 | 5189 |

`d(bytes)/d(N)` = **exatamente 1,0** (1 valor) e **exatamente 20,0** (20 valores distintos),
sem resíduo, em todos os pares consecutivos até N=256. **Um byte por caractere repetido, por
linha. Zero amortização** — nem dentro do valor, nem entre valores.

## 3. O `*0|` — o "RLE fantasma" já existe, sem guarda

**O fluxo deste bloco é invertido**: os wires são escritos à mão (`inputs/*.wire-de-entrada.tcf`)
e a saída é o JSON. A pergunta é se o **decoder** aceita.

| wire | decodifica para | aceito? |
|---|---|---|
| `#TCF.8\n*0\|abc\ndef\n^1\n` | `['def', 'abc']` | **sim** |
| `#TCF.8\n*0\|abc\n` | `[]` | **sim** |
| `#TCF.8\n*-1\|abc\ndef\n` | `['def']` | **sim** |
| `#TCF.8\n*0\|zzz\nx\ny\n` | `['x', 'y']` | **sim** |

No primeiro, `abc` é **declarado, nunca emitido, e depois referenciado** por `^1` — que é
exatamente a construção proposta. O terceiro aceita **count negativo**.

E o encoder canônico **nunca emite isso**: testado em 9 formas de entrada (vazio, singleton,
repetidos, nulos, 50 iguais, 10 distintos), zero ocorrências.

**Wire aceito-em-silêncio.** E o mesmo padrão é **fail-loud no bN**
([dominio_bn.py:288-292](../../../../../../src/tcf/composicional/dominio_bn.py#L288-L292)):
slot de domínio não referenciado levanta `ValueError`. Ticket: `T-RLE-COUNT-ZERO`.

## 4. Dado real — e a contra-prova apareceu em outro lugar

Teto idealizado: cada run vira 5 chars de **1 byte**, escolhido por **complemento** da coluna
(a ideia da `H-REF-03`). É limite **superior** — nenhum mecanismo real é de graça.

| coluna | n | % com run | hoje | teto (5ch) | delta |
|---|---:|---:|---:|---:|---:|
| `wine.alcohol` | 6497 | 0,62% | 8676 B | 8512 B | **−1,89%** |
| `tpch.o_clerk` | 15000 | 100% | 75522 B | 74241 B | −1,70% |
| `tpch.c_name` | 1500 | 100% | **87 B** | 93 B | **+6,90% — CUSTA** |

**A contra-prova é o `c_name`**, e o mecanismo dela é instrutivo: 1500 valores
(`Customer#000000001`…) são uma **progressão aritmética perfeita**, que o seq-RLE esmaga para
**87 bytes**. Colapsar os runs **destrói a progressão** e o wire incha. Ou seja: o run ali não é
redundância sobrando — é o que **sustenta** outro mecanismo.

## Duas correções ao levantamento que precedeu este lab

O lab existe justamente porque medição em scratchpad não é evidência. Duas coisas mudaram:

1. **A contra-prova do `o_clerk` NÃO reproduziu.** O levantamento reportou que colapsar seus
   runs custaria **1.744 B (−2,31%)**; medido aqui, ele **ganha 1.281 B (−1,70%)**. O número
   publicado antes deste lab está errado; vale o desta tabela. A contra-prova real é o `c_name`.
2. **Defeito meu, pego na 1ª rodada**: eu colapsava o run usando `¤`, que são **2 bytes em
   UTF-8** — o "teto de 5 chars" custava 10 B e saía pessimista. Trocado por um char ASCII
   ausente da coluna. Isso mudou `wine.alcohol` de −0,45% para **−1,89%**.

## O que isto orienta

- O mecanismo **não existe** hoje, e a curva mostra que a sobra é real onde há run longo.
- Mas em dado real ele **ganha pouco onde ganha** (−1,89% na melhor coluna) e **custa onde o
  run é load-bearing** — e a segunda situação é o regime comum no corpus (`Customer#`,
  `Clerk#`, `Supplier#` são 99% das colunas com run).
- Um mecanismo cego perde. Um mecanismo com FLOOR (nunca-pior) não perderia, mas então o ganho
  fica confinado ao nicho de −1,89%.
- E **os mesmos valores de `wine.alcohol` já são atacados pela grafia fracional** — são `n/30`,
  então o run é o sintoma e a divisão é a causa.
- O `T-RLE-COUNT-ZERO` é independente disto tudo e vale por si.

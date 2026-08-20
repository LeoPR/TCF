# 2026-08-17-1500 — o `split` explicado com dado de controle

Lab didático, pedido pelo owner. Seis casos mínimos, cada um isolando **uma lição**.

## A ideia em uma frase

**O `split` não comprime. Ele descola** valores estruturados para que a redundância que
**já existia** — mas estava colada — fique alcançável pelo `dict`.

```
"12.50"   a repetição de ".50" entre linhas EXISTE, mas está presa ao "12".
          Nenhum mecanismo a enxerga: cada valor parece único.

split ->  c0 = ["12", "45", "7", …]     c1 = ["00", "50", "99"]
          agora o c1 tem 3 valores possíveis, e o `dict` esmaga.
```

## O caso canônico — `c1-decimal`

```
coluna: ['12.00', '12.50', '12.99', '45.00', '45.50', '45.99', …]   24 valores

template (as partes NÃO-dígito):  []  ['.']  []
  campo c0: ['12','12','12','45','45','45', …]   ->  6 distintos de 24
  campo c1: ['00','50','99','00','50','99', …]   ->  3 distintos de 24
  sub-tabela: #TCF.8M@34=c0,@c1        <- os DOIS campos viraram dict (@)

A REDUNDÂNCIA QUE ESTAVA ESCONDIDA:
  coluna inteira    18 distintos de 24  (75%)
  campo c0          6                   (25%)
  campo c1          3                   (12%)

candidatos:  split 118  |  tcf 137  |  raw 146  |  dict 147     -> split vence
```

**Repare no que aconteceu**: a coluna tem 75% de valores distintos — parece incompressível
por dicionário, e de fato o `dict` sozinho é o **pior** candidato (147 B). Descolada, cada
campo cai para 25% e 12%, e aí o `dict` (que agora roda *dentro* do slot) ganha.

**A redundância não foi criada pelo split — ela sempre esteve lá.** O que faltava era acesso.

## Quando o ano é quase-constante — `c2-data-iso`

```
template:  []  ['-']  ['-']  []
  c0 (ano)  = ['2026', …]   ->  1 distinto   ( 4%)
  c1 (mês)  = ['01','02',…] ->  3 distintos  (12%)
  c2 (dia)  = ['05','12',…] ->  4 distintos  (17%)
  sub-tabela: #TCF.8Ma=c0,1e=c1,@c2

candidatos:  split 110  |  dict 125  |  tcf 137  |  raw 263     -> split vence
```

O `c0` tem **um** distinto em 24 — e no wire ele aparece como `*24|\2026`, uma corrida RLE.
Um campo constante custa quase nada depois de descolado; colado na data, ele reaparecia
inteiro em cada linha.

## Quando o split **aplica mas não paga** — `c3-alta-card`

```
coluna: ['339563.993908', '158176.414002', …]   24 valores, 24 distintos

  c0 -> 24 distintos de 24  (100%)
  c1 -> 24 distintos de 24  (100%)

candidatos:  raw 335  |  split 361  |  tcf 384     -> raw vence
             (o split existe mas PERDE por +8%)
```

**O gate passou** (template uniforme, 2 campos, variação real) — mas **não havia redundância
para expor**. O split pagou moldura (template + sub-header) sem colher nada. O `min()` o
descarta, e é exatamente para isso que o `min()` existe: zero-regressão por construção.

## Quando o gate **recusa** — `c4` e `c5`

```
c4  ['12.50', '7.99', '1.234,56', '88.10', '3.00', 'R$ 45']
    separadores e nº de campos VARIAM -> sem template comum, não há como descolar.

c5  ['553', '120', '584', …]
    sem separador -> um número puro já é um campo só. O gate exige >=2.
```

O gate é **rígido de propósito**: template 100% uniforme, ≥2 campos, algum campo não-constante.
Sem mecanismo de exceção — o refinamento do ADR-0026 mediu **1 near-miss em 80 colunas reais**
e concluiu que a complexidade não se pagava.

## O caso misto — `c6-telefone`

```
template:  ['(']  [') ']  ['-']  []
  c0 (DDD)     ->  2 distintos de 24   ( 8%)   -> vira o campo barato
  c1 (prefixo) -> 24 distintos          (100%)
  c2 (sufixo)  -> 24 distintos          (100%)
  sub-tabela: #TCF.8Me=c0,!8f=c1,!c2    <- c0 comprime, c1 e c2 vão RAW

candidatos:  split 314  |  tcf 365  |  raw 383     -> split vence
```

A coluna é **100% distinta** e mesmo assim o split ganha — porque **basta um campo** ter
cardinalidade baixa. Aqui é o DDD. Os outros dois vão `raw` e não atrapalham.

## A regra, destilada

> **O `split` paga quando ALGUM campo, isolado, tem cardinalidade muito menor que a coluna
> inteira** — porque é essa diferença que o `dict` colhe.

| caso | distintos | vence | campos (distintos) |
|---|--:|---|---|
| `c1-decimal` | 18/24 | **split** | [6, 3] |
| `c2-data-iso` | 12/24 | **split** | [1, 3, 4] |
| `c3-alta-card` | 24/24 | raw | [24, 24] |
| `c4-gate-recusa` | 6/6 | raw | — gate recusou |
| `c5-um-campo` | 23/24 | raw | — gate recusou |
| `c6-telefone` | 24/24 | **split** | [2, 24, 24] |

**Compare `c3` e `c6`**: as duas colunas são 100% distintas, mas `c6` ganha e `c3` perde. A
diferença não é a coluna — é se **algum campo** desaba quando descolado.

## O slot, formalmente (ADR-0026)

```
%<size>=<nome>                          no meta da coluna
slot = <ntmpl>\n<template><subtabela>

<template>  = (<bytelen>:<bytes>) por parte NÃO-dígito, big-endian
<subtabela> = multi-col aninhado com c0, c1, …  (cada campo volta ao min(tcf,raw,dict))
```

O `%` no índice 7 do meta é o que sinaliza. O sub-table aninhado é **por design** — é ele que
faz o `dict` alcançar cada campo. (Sobre a redundância do `#TCF.8M` desse sub-table, ver
[a nota de 1400](../../../notas/2026-08/2026-08-17-1400-split-teoria-e-o-magic-aninhado.md).)

## Evidência

`inputs/<caso>.json` + `outputs/<caso>.tcf` + `outputs/<caso>.roundtrip.json`, 6 de cada.
Round-trip validado em todos. `src/tcf` intocado.

## Conexões

- [ADR-0026](../../../../../docs/adr/0026-structural-split-weld.md) (split) ·
  [ADR-0025](../../../../../docs/adr/0025-v2b-dictionary-categorical-weld.md) (o `dict`, que é o motor)
- Nota da teoria e do magic aninhado:
  [`1400`](../../../notas/2026-08/2026-08-17-1400-split-teoria-e-o-magic-aninhado.md)
- Onde isto apareceu em dado real: [`1200` (CEP)](../2026-08-17-1200-cep-real-receita/) — o `D6`
  é este mesmo mecanismo aplicado à mão

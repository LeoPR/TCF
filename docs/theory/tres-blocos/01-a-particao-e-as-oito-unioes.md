---
title: "A partição em três blocos, e as oito uniões"
type: explanation
parent: tres-blocos
subsystem: presenca-nulo-ausencia
---

# A partição em três blocos, e as oito uniões

**A tese, em uma frase**: o wire do TCF distingue três estados por célula, esses três
estados formam uma partição das linhas, e toda pergunta sobre presença é uma união de
blocos dessa partição.

## Os três blocos

Para cada coluna `k` de uma tabela de `n` linhas:

| bloco | definição | símbolo no wire |
|---|---|---|
| `V` | a chave existe e o valor não é nulo | `.` |
| `N` | a chave existe e o valor é nulo | `\0` |
| `A` | a chave não existe naquele registro | `-` |

```
[n] = V ⊔ N ⊔ A          disjuntos, e cobrem todas as linhas
```

Isso não é convenção da biblioteca: é o que o wire grava. A máscara de uma coluna **é** a
função classificadora `c : [n] → {., 0, -}`, e as fibras de uma função particionam o
domínio, que é teorema padrão. Cada bloco é uma fibra.

Uma precisão sobre a grafia: os três símbolos convivem na máscara de **campo opcional**
(`?:`), que é a forma que admite ausência. Na coluna densa com nulos (`?0:`, grafia de
2026-08-28) a máscara tem dois estados, porque ali `A` é vazio por construção e gravar um
símbolo para ele seria pagar por um caso que não ocorre. A partição é a mesma nas duas: o
que muda é quantos blocos podem ser não vazios.

Medido sobre a tabela de referência (lab `0500`), com a coluna `b` de
`[{a:1,b:10}, {a:2,b:None}, {a:3}, {a:4,b:40}, {a:5,b:None}, {a:6}]`:

```
máscara no wire:  ['.', '\0', '-']
classificação:    ['.', '0', '-', '.', '0', '-']

fibra('.')  tem valor    = [0, 3]
fibra('0')  é nulo       = [1, 4]
fibra('-')  não existe   = [2, 5]
disjuntas e cobrem [n]?  True
```

## As oito uniões

Três blocos geram `2³ = 8` uniões. Todas as perguntas úteis sobre presença estão nesta
tabela, e não há uma nona:

| V N A | linhas do exemplo | a pergunta |
|---|---|---|
| 0 0 0 | `[]` | o conjunto vazio, que não se pergunta |
| 1 0 0 | `[0, 3]` | tem valor |
| 0 1 0 | `[1, 4]` | existe **e** é nulo |
| 0 0 1 | `[2, 5]` | não existe |
| 1 1 0 | `[0, 1, 3, 4]` | existe (o domínio de definição) |
| 1 0 1 | `[0, 2, 3, 5]` | tem valor ou não existe |
| 0 1 1 | `[1, 2, 4, 5]` | nulo ou ausente |
| 1 1 1 | todas | não é filtro, é `count()` |

## Três nomes bastam

Com complemento em relação a `[n]`, os três primitivos geram as oito:

```
V           tem valor
N           existe e é nulo
A           não existe

~A = V ∪ N  existe
~V = N ∪ A  nulo ou ausente
~N = V ∪ A  tem valor ou não existe
V | N | A   todas as linhas
```

Isso importa por dois motivos. O primeiro é economia: cinco nomes cobririam cinco uniões,
e três nomes com complemento cobrem oito. O segundo é que `N ∪ A` **não tem nome firmado**
em nenhuma matemática e em nenhum framework, e descrever pela operação é mais honesto que
cunhar uma palavra (ver [02](02-os-termos-firmados.md) e
[03](03-o-que-nao-serve.md)).

## O complemento é em relação a `[n]`

Sempre. `~V` é `N ∪ A`, e não `N`. A razão é que os três blocos particionam as **linhas da
tabela**, não o domínio da coluna: se o complemento fosse tomado dentro de `dom(c)`, o
bloco `A` ficaria fora do universo e as oito uniões viravam quatro. Complementar em `[n]`
é o que mantém a álgebra fechada.

## O que a `view` responde hoje

A `view` abre single-col, multi-col e hierárquico **denso**, inclusive com nulos. Ela
**recusa** no header o hierárquico com campo opcional, com um erro que manda usar
`decode()`. Consequência prática, e ela é medida, não estimada:

```
[{'a':1}, {'a':None}]        -> #TCF.8R5N=a            a view ABRE
[{'a':1,'b':2}, {'a':3}]     -> #TCF.8Ha:6n,b?:4:3n    a view RECUSA (ragged)
```

A primeira entrada é retangular e plana, e desde o
[ADR-0049](../../adr/0049-marcador-r-a-forma-da-entrada-e-metadado.md) sai pelo `.8R`, um wire
multi com o discriminador trocado. O hierárquico denso continua no `.8H`, e a `view` o abre
igual.

Em todo blob que a `view` abre hoje, `A` é vazio, e as respostas sobre `A` são as do caso
total: `A = ∅` e `~A = [n]`. Isso é a resposta certa para uma coluna sem buraco, e é o
mesmo que o Arrow faz ao **omitir** o buffer de validade quando não há nulo, continuando a
responder que toda posição é válida. Os blocos do lado da ausência ganham conteúdo quando
a `view` passar a abrir ragged, sem que a álgebra mude.

## Fonte

Labs de 2026-08-30, `0100` a `0500`, em `experiments/lab/dirty/2026-08/2026-08-30/`. A
tabela das oito uniões é gerada pelo `run.py` do lab `0400`, com a evidência em disco.

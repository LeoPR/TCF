---
title: "O lift duplo: por que nulo e ausente não colapsam"
type: explanation
parent: tres-blocos
subsystem: presenca-nulo-ausencia
---

# O lift duplo

Esta é a justificativa de fundo da distinção inteira. Ela responde a pergunta que sempre
volta: por que não basta um estado de "sem valor"?

## Um lift dá uma distinção

O lifting de Scott **totaliza** uma função parcial. Uma `f : X ⇀ Y` vira `f : X → Y⊥`, onde
`Y⊥ = Y ⊔ {⊥}` e `⊥ ∉ Y`. O ponto adjunto fica ordenado abaixo de todos os outros e carrega
informação zero: ele é o "ainda não sei", não um valor do domínio original.

Um lift, portanto, separa duas coisas: tem valor, ou não tem.

## O TCF precisa de duas distinções

A célula de uma tabela pode estar em três situações, e duas delas são "sem valor útil" por
motivos diferentes. Formalmente, a coluna é o lift **duplo**:

```
c_k : [n]  →  ( Vals ⊎ {null} )⊥       =   X ⊔ 1 ⊔ 1
```

O primeiro ponto adjunto é o `null`, que é o valor que o dado carrega. O segundo é a
ausência, que é a posição não estar no domínio.

## Por que os dois não se fundem

Por um fato elementar de tipos algébricos:

```
1 + (1 + X)   ≇   1 + X            Maybe não é idempotente
```

Aplicar `Maybe` duas vezes dá um tipo com **dois** pontos a mais, não um. `Just Nothing` e
`Nothing` são habitantes distintos, e é exatamente essa distinção que o wire grava com dois
símbolos diferentes.

Em uma frase: **`null` é um valor, `ausente` não é.**

## O `null` do TCF não é o `⊥`

Vale registrar, porque a confusão é natural. No lift, o `⊥` é o elemento adjunto: ele existe
no contradomínio estendido, mas não pertence a `Y` e não carrega informação. O `null` do TCF
é elemento **ordinário** do contradomínio: ele tem símbolo próprio no wire, sobrevive ao
round-trip e é observável em contagem.

Quem faz o papel de `⊥` no TCF é a **ausência**, e ela nem chega a ter célula gravada: o
wire marca a posição na máscara e não escreve nada no corpo.

## A consequência para a API

Isso decide uma coisa prática. Um predicado sobre o valor, `pred: Callable[[str], bool]`,
alcança `V` e alcança `N`, porque nos dois casos existe uma célula para passar ao predicado.
Ele **nunca** alcança `A`, porque não existe valor `x` para passar: a ausência é propriedade
da posição, não do valor.

Por isso o bloco `A` precisa de forma própria de ser pedido, e não é açúcar sobre um filtro
que já se poderia escrever. Os outros dois blocos são fibras do valor; o terceiro é fibra da
presença.

## Fontes

- Maybe monad e lifting: <https://ncatlab.org/nlab/show/maybe+monad> · <https://ncatlab.org/nlab/show/partial+function>
- Domain theory, lifting de Scott: <https://en.wikipedia.org/wiki/Domain_theory>

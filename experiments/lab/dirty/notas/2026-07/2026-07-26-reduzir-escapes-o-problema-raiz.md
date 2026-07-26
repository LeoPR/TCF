---
title: Como reduzir escapes — o problema raiz (o flip era só uma resposta)
type: analise
status: aberta
created: 2026-07-26
related:
  - experiments/lab/dirty/2026-07/2026-07-25/2026-07-25-2337-polaridade-escape-vs-referencia/
  - experiments/lab/dirty/2026-07/2026-07-26/2026-07-26-0038-delimitador-do-flip-opcoes/
  - experiments/lab/dirty/notas/2026-07/2026-07-26-min-len-ganho-dinamico-e-custo.md
---

# Como reduzir escapes — o problema raiz

Reenquadramento do owner (2026-07-26):

> *"o problema aqui, a rigor, não é fazer flip — flip é uma das formas que podem resolver o
> problema. O problema raiz é que temos muitos escapes. A pergunta é: como reduzir os
> escapes? Como deixá-los mais genéricos e mais compactos? Como declarar o que quero sem
> colidir?"*

Está certo, e a medição confirma que a pergunta é ainda mais estreita do que parecia.

## Fato 1 — 100% dos escapes são de dígito

Medido no corpo real, separando escape de dígito (`\123`) de escape estrutural (`\*`, `\~`,
`\\`):

| coluna | corpo | escape dígito | escape estrutural | % do corpo |
|---|---:|---:|---:|---:|
| hex | 5711 | 1211 | **0** | 21,2% |
| pessoas-sample | 1900 | 400 | **0** | 21,1% |
| empresas-sample | 2195 | 440 | **0** | 20,0% |
| moeda | 6226 | 1036 | **0** | 16,6% |
| telefone | 8244 | 1272 | **0** | 15,4% |
| int-ruído | 3922 | 500 | **0** | 12,7% |
| beijing-pm25 | 23 | 3 | **0** | 13,0% |
| adult-sample | 382 | 42 | **0** | 11,0% |
| email | 5743 | 367 | **0** | 6,4% |
| texto puro | 1807 | 0 | 0 | 0,0% |

Os escapes estruturais são **zero em todas**. O orçamento inteiro é **uma colisão só**:
referências são escritas em dígitos decimais, e o dado também tem dígitos.

**11–21% do corpo em dado real.** Não é caso de borda.

## Fato 2 — nas colunas que mais sofrem, as letras estão livres

Composição do dado por classe de caractere:

| coluna | dígito | minúscula | MAIÚSCULA | escape hoje |
|---|---:|---:|---:|---:|
| adult-sample | 100% | 0% | 0% | 11% |
| beijing-pm25 | 100% | 0% | 0% | 13% |
| pessoas-sample | 78,6% | **0%** | **0%** | **21%** |
| empresas-sample | 77,8% | **0%** | **0%** | **20%** |
| telefone | 73,3% | 0% | 0% | 15% |
| hex | 67% | 33% | 0% | 21% |
| email | 32,8% | 53,7% | 0% | 6% |

MAIÚSCULA é 0% em **8 de 9**. Minúscula é 0% em 6 de 9. As colunas que pagam mais escape são
justamente as que não têm letra nenhuma.

## O espaço de soluções, reordenado

A pergunta certa não é "marcar literal ou marcar referência", e sim **qual classe de
caractere carrega a referência**:

| # | mecanismo | custo | observação |
|---|---|---|---|
| 1 | marcar o **literal** (hoje) | 1 B por corrida de dígito no dado | o que medimos: 11–21% |
| 2 | marcar a **referência** (flip) | 1 B por referência + delimitador | tem 3 bloqueadores estruturais |
| 3 | **referência em outra classe** (ex.: letras) | 0 B de escape onde a classe é livre | ver abaixo |
| 4 | **comprimento explícito** | dígitos do comprimento + separador | nunca escapa, mas paga sempre |
| 5 | escopo declarado (por coluna/linha) | o flag no header | é o eixo do (2) e do (3), não um mecanismo à parte |

O **(3) é o que a medição aponta**, e ele tem uma propriedade que o flip não tem:

> **Letras auto-delimitam contra dígitos.** `a1` é referência `a` seguida do literal `1`, sem
> ambiguidade nenhuma. Toda a discussão de delimitador — qual char, onde aplicar, quanto custa
> — **desaparece**, porque ela só existia por referência e literal disputarem o mesmo alfabeto.

E as referências ficam **mais curtas**: base-26 contra base-10.

## Estimativa (rotulada como tal)

| coluna | corpo | escapes que somem | Δ ref (dec→b26) | saldo |
|---|---:|---:|---:|---:|
| empresas-sample | 2195 | 440 | −16 | **−456 B (−21%)** |
| pessoas-sample | 1900 | 400 | 0 | **−400 B (−21%)** |
| adult-sample | 382 | 42 | 0 | −42 B (−11%) |

> **Isto é estimativa, não medição.** Nesta mesma linha de trabalho, duas estimativas já
> precisaram ser materializadas antes de valerem — e a segunda revelou três bloqueadores
> estruturais que nenhuma contagem mostrava. **Não tratar como resultado.**

## Os três bloqueadores do flip, reexaminados sob o (3)

| bloqueador | sob o flip | sob referência-em-letras |
|---|---|---|
| adjacência ref↔literal | precisa de delimitador | **dissolve** (classes distintas se auto-delimitam) |
| linha `0` = grafia do null | colide | endereço do null passa a ser uma **letra** — some a colisão |
| seq-RLE acha dígitos pelo escape | quebra (some ou muda de token) | as corridas de dígito **são** os literais — a regra fica mais simples |

Os três **parecem** dissolver. Isso é raciocínio, não evidência — e é exatamente o tipo de
raciocínio que a última rodada mostrou ser insuficiente.

## O que custa

- **Colunas com letras no dado pagam.** `email` (53,7% minúscula) e `hex` (33%) precisariam de
  escape de letra. É a mesma troca do flip, com um corte diferente — e por isso continua sendo
  decisão **por coluna**, com `min()`.
- **Declarar no header** qual classe carrega referência: 1–2 B, no char de modo (que exige
  tag; ver o custo já medido no lab `0038`).
- **Reescrever o parser de declaração** — é mais invasivo que o flip, que era uma troca de
  polaridade sobre a mesma gramática.

## Próximo passo

**Materializar** o (3) como o `0038` materializou o flip: corpo real, wire com cabeçalho, e —
a lição que custou caro — **decodificar a forma proposta com um leitor independente**, não
`de_X(para_X())`.

Antes disso, uma pergunta de escopo para o owner: o alfabeto da referência seria **fixo**
(sempre letras) ou **declarado por coluna** (o encoder escolhe a classe mais livre)? O
declarado é mais geral e responde melhor ao *"declarar o que quero sem colidir"*, mas custa
header e complexidade de parser.

---
title: "Os termos firmados: domain of definition, antidomain, fibra, classificador"
type: explanation
parent: tres-blocos
subsystem: presenca-nulo-ausencia
---

# Os termos firmados

Critério deste levantamento: preferir termo **firmado pela matemática**, em inglês, com
definição literal e fonte. Termo genérico de programação só entra se a matemática não tiver
palavra. Onde não existe termo, está escrito que não existe.

## A tabela

| bloco | termo | definição literal | quão firmado |
|---|---|---|---|
| `V ∪ N` | **domain of definition**, `dom(c)` | o subconjunto onde a função parcial está definida. Em computabilidade, `W_e = dom(φ_e) = {x : φ_e(x)↓}` | **firme e universal** |
| `A` | **antidomain**, `A(c)` | `A(f) = {(x,x) ∈ X² : x ∈ X \ dom(f)}`. Relacional: `ad(R) = {(x,x) : ∀y.(x,y) ∉ R}` | **firme**, porém jargão de uma comunidade (álgebra de funções parciais, Kleene algebra with domain) |
| `N` | **fiber over null**, `c⁻¹(null)` | pré-imagem de um ponto. Vocabulário universal, sem ambiguidade | **firme** |
| `V` | a fibra complementar, `dom(c) \ c⁻¹(null)` | descrito pela operação | ver a ressalva em [03](03-o-que-nao-serve.md) |
| `N ∪ A` | *(não existe termo)* | o complemento de `V` em `[n]` | **nenhuma fonte**, em matemática ou em framework |

Mais dois termos que descrevem o objeto e não dependem de nenhuma hipótese algébrica:

- **classifier**: a máscara da coluna é a função `[n] → {., 0, -}`;
- **block**: cada parte de uma partição. Os três blocos são as fibras do classificador.

Esse par é o vocabulário mais barato de defender, porque descreve o que o wire já grava.

## Uma desambiguação obrigatória: `domain`

No TCF, a palavra `domain` **já está ocupada**, e do outro lado da seta. O ADR-0036 chama de
domínio o conjunto de **valores distintos** de uma coluna, que é um subconjunto do
contradomínio, e o discriminador `B`/`C` é glosado como *domain bN* em
`docs/algorithms/TCF-format.en.md`.

O termo desta nota é um conjunto de **linhas**. Por isso ele se escreve sempre por extenso,
**domain of definition**, e nunca abreviado para `domain` na prosa. A entrada
correspondente do [`vocabulary.md`](../../vocabulary.md) registra as duas.

## A notação de Kleene, com uma ressalva de uso

`f(x)↓` e `f(x)↑` são padrão em computabilidade: *"We write φ(n) ↓, and say that φ(n)
converges, if n ∈ dom(φ); otherwise φ(n) diverges, written φ(n)↑"*.

A ressalva é de leitura. A glosa canônica é **converges/diverges**, que é operacional e fala
de terminação. Para uma tabela estática, a leitura honesta é **defined/undefined**: dizer que
uma linha de CSV "diverge" seria erro de categoria.

## Fontes

- Partial function e domain of definition: <https://en.wikipedia.org/wiki/Partial_function> · <https://encyclopediaofmath.org/wiki/Domain_of_definition>
- Antidomain: Hirsch & McLean, <https://arxiv.org/pdf/2307.09620> · *Domain Semirings United*, <https://arxiv.org/pdf/2011.04704> · Desharnais, Jipsen & Struth, *Domain and Antidomain Semigroups*, RelMiCS/AKA 2009
- Fibra e pré-imagem: <https://ncatlab.org/nlab/show/fiber>
- Kleene arrows: R. Miller, *Computable Fields and Galois Theory*, AMS Notices 2008

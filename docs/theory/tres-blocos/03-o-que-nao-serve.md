---
title: "O que não serve: support refutado, missing como falso cognato"
type: explanation
parent: tres-blocos
subsystem: presenca-nulo-ausencia
---

# O que não serve, e por quê

Esta nota registra as escolhas **descartadas**. Ela existe porque a hipótese inicial deste
estudo era outra, e ela caiu pela metade na verificação: registrar só o que sobreviveu
esconderia o argumento que interessa.

## `support` não serve para `V`

A hipótese era gerar os cinco conjuntos com dois termos, `domain` e `support`. O primeiro
sustenta. O segundo não.

`supp(f) = {x : f(x) ≠ 0}` exige um **elemento distinguido no contradomínio**, o zero. A
pergunta que decide é: `null` é o zero de quê?

- em aritmética escalar SQL, `x + NULL = NULL`. Isso é comportamento de elemento
  **absorvente**, o oposto do neutro, que por definição deixa os outros inalterados;
- o `SUM` ignorar nulo é regra do **agregado**, não identidade aditiva;
- e `COUNT(*)` contra `COUNT(col)` mostra que o nulo é **observável**, enquanto o ponto do
  support é justamente que o basepoint é o default invisível.

Então `support` só seria honesto como termo **declarado** ("nesta biblioteca, o basepoint de
uma coluna é null"), nunca como termo herdado com significado pronto. Para `V`, o nome sem
ressalva é a fibra, ou o complemento de `N ∪ A`.

## `missing` é falso cognato, e não deve ser usado

A mesma palavra significa coisas opostas em produção:

| sistema | o que `missing` quer dizer | bloco |
|---|---|---|
| MongoDB | `$type` devolve `"missing"` para campo que **não existe** | `A` |
| pandas, polars, R | "missing data" é o **nulo** | `N` |

Um vocabulário que usasse `missing` faria o usuário de Mongo e o usuário de pandas pedirem
conjuntos diferentes com a mesma palavra. A entrada correspondente do
[`vocabulary.md`](../../vocabulary.md) registra `missing` como forma a não usar.

O mesmo argumento derruba a sigla composta `NuA`: em R, `NA` é o `N` sozinho, e `N ∪ A`
inclui a ausência. É por isso que a grafia adotada usa complemento (`~V`) em vez de sigla
composta.

## Os outros candidatos

| termo | por que não |
|---|---|
| `carrier` | ocupado: em álgebra universal é o conjunto-suporte da estrutura, e colidiria com "a coluna" |
| `cosupport` | jargão de uma comunidade só (categorias trianguladas), e **não** é o complemento do support |
| `essential support` | medida-teórico, definido a menos de conjuntos de medida **nula**: colisão de palavra |
| `level set` | caso particular de fibra, e só se usa para função real |
| `valid` | jargão de uma linhagem só (Arrow, *validity bitmap*), e ali significa apenas não nulo, cego à ausência |
| `partiality monad` | ambíguo: em teoria de tipos construtiva é o delay monad de Capretta quocientado, mônada diferente de `1 + A` |

## A letra `V`, e a ressalva que ela carrega

Das três letras, `N` puxa `null` e `A` puxa `antidomain`. A letra `V` **não tem palavra
inglesa firme por trás**, porque `support` caiu e `valid` tem lastro fraco. Ela é mnemônica
de *value*, e a descrição honesta é operacional: as linhas onde a coluna tem valor.

Isso é o motivo de `V` ser o bloco que o filtro tradicional já alcança sem declarar nada:
`where(k, 10)` está contido em `V` por construção. Ele fica documentado para o padrão
fechar, não porque a API precise dele.

## Fontes

- Support: <https://en.wikipedia.org/wiki/Support_(mathematics)>
- MongoDB `$type` e `$exists`: <https://www.mongodb.com/docs/manual/reference/operator/query/type/> · <https://www.mongodb.com/docs/manual/reference/operator/query/exists/>
- polars missing data: <https://docs.pola.rs/user-guide/expressions/missing-data/>
- Arrow validity bitmap: <https://arrow.apache.org/docs/format/Columnar.html>

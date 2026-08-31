---
title: "Mimetismo: o que cada framework faz, e o que nenhum deles nomeia"
type: explanation
parent: tres-blocos
subsystem: presenca-nulo-ausencia
---

# Mimetismo, e a bibliografia

O critério de projeto é usar o default de quem já resolveu, aproveitando a documentação e a
experiência acumulada. Esta nota levanta o que cada sistema faz, para que os defaults do TCF
sejam herdados e não inventados.

## A tabela cruzada

| conceito TCF | termo de framework | quão firmado |
|---|---|---|
| `V ∪ N` (existe) | **exists** | **o único com lastro real**: Mongo `$exists` *"matches the documents that contain the field, including documents where the field value is null"*; PostgreSQL chama `?` de *existence operator*. Duas comunidades independentes, mesma definição, ambas cegas ao valor ser nulo |
| `N` (existe e é nulo) | **null** | firmado como palavra, ambíguo como conceito: só Mongo e Postgres conseguem dizer "existe **e** é nulo" |
| `A` (não existe) | ~~missing~~ | **falso cognato**: ver [03](03-o-que-nao-serve.md) |
| `V` (tem valor) | **valid** | Arrow, *validity bitmap*. Ali significa apenas não nulo |
| `N ∪ A` | *(sem nome)* | o Mongo tem o comportamento (`{k: null}` casa os dois) e não o batiza |

**Nenhum framework tem nome para `A` separado de `N`.** Esse é o achado que justifica ir
buscar o vocabulário na matemática: não há de quem copiar o nome, embora haja de quem copiar
o comportamento.

## O precedente mais próximo, e onde ele para

O **R** separa os dois eixos na própria linguagem: `NA` é o valor faltando, `NULL` é o objeto
ausente. É a distinção que o TCF faz. Mas o R **colapsa no armazenamento**: atribuir `NULL` a
um componente de lista deleta o componente, então a distinção não sobrevive à estrutura.

O **Arrow** oferece o precedente que mais importa para os defaults. A especificação permite
**omitir** o buffer de validade quando a coluna não tem nulo nenhum, e mesmo assim
`is_valid(i)` continua respondendo verdadeiro para toda posição. Ou seja: a ausência da
estrutura é lida como o caso total, e não como erro nem como resposta indefinida. É
exatamente a situação do TCF quando `A` é vazio.

## Como cada sistema responde a pergunta que não tem linha

O caso que decide o default do TCF: perguntar por ausência onde não há nenhuma.

| sistema | a pergunta | a resposta |
|---|---|---|
| pandas | `.isna()` numa coluna sem NaN | série toda `False`, sem aviso |
| polars | `is_null()` / `null_count()` | máscara toda falsa, contagem zero |
| MongoDB | `$exists: false` em campo sempre presente | conjunto vazio |
| PostgreSQL | `WHERE col IS NULL` em coluna `NOT NULL` | vazio, e o planejador chega a otimizar |
| Arrow | `is_valid(i)` sem buffer de validade | verdadeiro para todo `i` |

Cinco sistemas, o mesmo comportamento: **resposta vazia, em silêncio**. Nenhum trata a
pergunta como erro, e nenhum avisa. É o default que o TCF herda.

## Bibliografia

- Partial function, domain of definition: <https://en.wikipedia.org/wiki/Partial_function> · <https://encyclopediaofmath.org/wiki/Domain_of_definition>
- Antidomain: Hirsch & McLean, <https://arxiv.org/pdf/2307.09620> · *Domain Semirings United*, <https://arxiv.org/pdf/2011.04704> · Desharnais, Jipsen & Struth, *Domain and Antidomain Semigroups*, RelMiCS/AKA 2009
- Support: <https://en.wikipedia.org/wiki/Support_(mathematics)>
- Maybe e lifting: <https://ncatlab.org/nlab/show/maybe+monad> · <https://ncatlab.org/nlab/show/partial+function>
- Kleene arrows: R. Miller, *Computable Fields and Galois Theory*, AMS Notices 2008
- MongoDB `$exists` e `$type`: <https://www.mongodb.com/docs/manual/reference/operator/query/exists/> · <https://www.mongodb.com/docs/manual/reference/operator/query/type/>
- PostgreSQL JSON operators: <https://www.postgresql.org/docs/current/functions-json.html>
- Arrow columnar format, validity bitmap: <https://arrow.apache.org/docs/format/Columnar.html>
- polars missing data: <https://docs.pola.rs/user-guide/expressions/missing-data/>
- R: *Advanced R*, capítulo de vetores (NA contra NULL)

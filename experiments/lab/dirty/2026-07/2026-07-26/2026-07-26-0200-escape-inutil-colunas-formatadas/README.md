# 2026-07-26-0200 — Escape inútil em colunas formatadas

Você olhou `A-cpf-like-n200` e notou: CPFs quase todos únicos, **nenhuma referência gerada**,
e mesmo assim escape em todo dígito.

> *"a ideia era gastar o mínimo possível de indicação pra que o CPF não tenha escape em nada.
> mas obviamente precisamos fazer por alguma regra que se aplique de forma dinâmica e não se
> misture."*

A regra testada é a mais barata possível: **se o corpo não emite referência de fragmento, o
cabeçalho declara isso e todo dígito na declaração é literal**. Binário por coluna, decidido
pelo encoder — não se mistura com nada.

## Resultado: a regra quase não pega — e o motivo é o achado

**1 de 12** formas formatadas. Só `ip`, com −256 B.

| forma | corpo | escapes | refs | seq-RLE quebra | modo vale? |
|---|---:|---:|---:|---:|---|
| `ip` | 2851 | 256 | 0 | 0 | **sim** (−256) |
| `coord` | 6495 | 986 | **0** | **7** | não |
| `cep` | 5990 | 997 | 3 | 1 | não |
| `cartao` | 11960 | 2000 | 19 | 0 | não |
| `cpf-mascara` | 9383 | 1950 | 30 | 0 | não |
| `placa` | 4908 | 920 | 47 | 0 | não |
| `moeda` | 6234 | 1036 | 136 | 0 | não |
| `hora` | 5135 | 978 | 340 | 0 | não |
| `telefone` | 8244 | 1272 | 508 | 0 | não |
| `isbn` | 9224 | 1660 | 736 | 0 | não |
| `data-iso` | 5513 | 677 | 765 | 0 | não |
| `cnpj-mascara` | 9774 | 1714 | 774 | 0 | não |

Duas razões distintas para recusar, e a segunda importa mais:

1. **a coluna usa referência** — aí o escape está fazendo o trabalho dele, e a regra
   corretamente recusa. É o caso de 10 das 12.
2. **a coluna tem marcador seq-RLE** — e tirar o escape o quebra **em silêncio**, porque ele
   localiza os dígitos incrementáveis *pelo escape*. É o caso de `coord`, que tinha 0
   referências e mesmo assim não pode.

## O obstáculo é comum, não do flip

A razão (2) é **exatamente o bloqueador #3 que derrubou o flip** no lab `0038`. Ele não é
específico daquele esquema:

> **Qualquer** mecanismo que remova o escape de dígito quebra o seq-RLE, porque o marcador
> `*N±d|` usa o escape como *marcação de onde incrementar*.

Isso converge duas investigações independentes no mesmo ponto. E indica a ordem certa:
**enquanto o seq-RLE deduzir a posição pelo escape, nenhum esquema de redução de escape
fecha** — nem flip, nem sem-escape, nem referência-em-letras.

## A regra binária é frágil por natureza

| forma | n | únicos | refs | modo vale? |
|---|---:|---:|---:|---|
| cep | 20 | 20 | 1 | não |
| cep | **100** | 100 | **0** | **sim** |
| cep | 500 | 500 | 3 | não |
| cep | 2000 | 2000 | 40 | não |
| telefone | 20 | 20 | 3 | não |
| telefone | 2000 | 2000 | 3048 | não |

O mesmo formato de dado muda de lado conforme `n`. **Não é propriedade do tipo, é do
conteúdo** — o HCC acha composição quando há volume suficiente. Por isso tem de ser decidido
pelo encoder a cada coluna, e por isso um "modo CPF" declarado por tipo não funcionaria.

Note `cep`: **997 escapes para 3 referências**. Abrir mão de 3 referências destravaria o modo
— o que aponta para uma regra melhor que a binária: **`min()` entre "usar as referências" e
"abrir mão delas para não pagar escape"**. Não medi essa variante.

## Validação

O corpo sem-escape é lido por um **leitor independente** (`le_sem_escape`), que reimplementa a
semântica direto — não pela inversa da transformação. Foi a lição do lab `0038`, onde
`de_X(para_X(c)) == c` deu 36/36 e escondia 2 wires corrompidos.

O leitor **desiste** (devolve `None`) quando encontra seq-RLE, e foi assim que `coord`
apareceu: ele não conseguiu validar, e a investigação achou os 7 marcadores quebrados.

## Limites

- **1 de 12 é resultado negativo** para a regra binária. Não é fracasso da ideia do owner — é
  a medição mostrando que a formulação mais simples não cobre o caso que a motivou (o CPF
  tem 30 referências em n=500, então não se aplica).
- Formas **sintéticas com máscara fixa**, geradas por LCG. Dado real de documento tem
  distribuição diferente de dígitos e provavelmente mais composição.
- Não testei a variante `min()` (abrir mão de poucas referências).
- Nada soldado.

## Rodar

```
python run.py
```
`semescape.py` tem a transformação, o detector de aplicabilidade e o leitor independente.

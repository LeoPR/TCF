# Marcador virtual + alfabeto da coluna (2026-07-26-1913)

Reavaliação do lab `1853` a partir de dois erros apontados: o char foi **chutado**, e a decisão era uma **esteira serializada** rodando depois do núcleo.

## A reformulação

O marcador é **virtual** — um sentinela na representação intermediária, não um char. Não pode colidir porque **não é texto**. É o movimento do OBAT (nós, não strings) e do HCC (composição, não grafia).

```
tokens = [('R','56'), FLIP, ('L','033'), ('txt','-'), ...]   <- FLIP é objeto
grafia = resolve(tokens, char, inicial)                      <- char NO FIM
```

E não se pergunta *qual char usar*, se pergunta **onde existe conflito**: o alfabeto que a coluna realmente usa. O complemento tem **conflito zero por construção**.

## A — sempre existe char livre?

Faixa considerada: ASCII imprimível menos a gramática do corpo (`* ~ ^ , | \`) = **88 chars**.

| coluna | n | chars usados | chars LIVRES | escolhido |
|---|---:|---:|---:|:-:|
| `cpf` | 200 | 2 | **86** | `!` |
| `cartao` | 500 | 12 | **77** | `!` |
| `ip` | 500 | 1 | **87** | `!` |
| `cep` | 500 | 7 | **82** | `!` |
| `telefone` | 500 | 17 | **75** | `!` |
| `data-iso` | 500 | 15 | **76** | `!` |
| `email` | 500 | 23 | **68** | `—` |
| `texto` | 500 | 28 | **61** | `—` |
| `data-br` | 500 | 15 | **76** | `!` |
| `cnpj-mascara` | 500 | 16 | **75** | `!` |
| **`retail-description`** (real) | 2000 | 57 | **35** | `—` |
| **`retail-stockcode`** (real) | 2000 | 31 | **60** | `!` |
| **`lineitem-comment`** (real) | 2000 | 47 | **45** | `—` |

Mínimo de chars livres em qualquer coluna medida: **35**. Onde há char livre, o custo de ocorrência do delimitador é **0 por construção** — a lista de candidatos do `1853` era desnecessária.

Colunas de texto livre real usam poucas dezenas de chars num alfabeto de 88. **Não é sorte das formas sintéticas.**

## B — quantas varreduras a decisão custa?

| | varreduras sobre o corpo | quando |
|---|---:|---|
| lab `1853` | **8** (6 candidatos × ocorrências + 2 polaridades) | depois do núcleo terminar |
| aqui | **1** | fundida na que já existe |

A varredura única acumula três coisas no mesmo passo por char, dentro do laço que `_escape_lit` (`src/tcf/composicional/syntax.py:173-193`) **já roda** — é o único laço char-a-char do emit, e é exatamente onde o escape de dígito é decidido (linha 181):

```
presentes   set/bitmap do alfabeto   (1 add por char)
trocas_R    contador                  (1 comparação por corrida)
trocas_L    contador                  (a outra polaridade, no mesmo passo)
```

A decisão é depois uma leitura de **3 acumuladores**, sem tocar no dado. É o que o owner descreveu: marcar durante a avaliação, decidir no fim.

## C — os bytes mudam em relação ao `1853`?

`recusa` = a regra escolhe o inline de hoje porque as transições não compensam.

| coluna | corpo | escapes hoje | trans. R | trans. L | decisão | trans. `1853` | igual? | Δ corpo |
|---|---:|---:|---:|---:|---|---:|:-:|---:|
| `cpf` | 3800 | 800 | 200 | 0 | 0 | 0 | sim | -800 |
| `cartao` | 11960 | 2000 | 513 | 25 | 25 | 25 | sim | -1975 |
| `ip` | 2851 | 256 | 64 | 0 | 0 | 0 | sim | -256 |
| `cep` | 5990 | 997 | 500 | 5 | 5 | 5 | sim | -992 |
| `telefone` | 8244 | 1272 | 504 | 824 | 504 | 504 | sim | -768 |
| `data-iso` | 5513 | 677 | 458 | 689 | 458 | 458 | sim | -219 |
| `email` | 5743 | 367 | 472 | 788 | recusa (367 escapes) | 472 | sim | +0 |
| `texto` | 1807 | 0 | 0 | 25 | recusa (0 escapes) | 0 | sim | +0 |
| `data-br` | 4905 | 726 | 457 | 681 | 457 | 457 | sim | -269 |
| `cnpj-mascara` | 9774 | 1714 | 975 | 515 | 515 | 515 | sim | -1199 |
| **retail-description** | 27581 | 105 | 134 | 814 | recusa (105 escapes) | — | — | +0 |
| **retail-stockcode** | 11437 | 1098 | 890 | 1185 | 890 | — | — | -208 |
| **lineitem-comment** | 50598 | 0 | 0 | 1448 | recusa (0 escapes) | — | — | +0 |

- divergências contra o `1853`: **0** (mesmos bytes, decididos em 1 varredura em vez de 8)
- ganho somado (sintéticas + reais): **-6686 B**
- reconstrução byte-exata do corpo canônico **e** RT pelo `decode` REAL: **26/26**

## O que isto destrava — e o que continua aberto

O mapa do núcleo mostrou que existe representação estruturada até a fase B (`pieces_per_line`, tagged-union, `syntax.py:263-278`) e que ela **some no `_emit_body`**: dali em diante é `list[str]`. É por isso que o seq-RLE precisa **re-parsear texto** (`find_escape_digit_runs`, `hcc_seqrle.py:56`) para achar o dígito incrementável.

Um marcador virtual na saída é exatamente a camada que falta ali. Com ela o seq-RLE leria o token em vez de reencontrar o `\` no texto — o que dissolveria o bloqueador de todos os labs anteriores em vez de contorná-lo.

**Não medido**: essa mudança no `_emit_body`. É a próxima pergunta, não uma conclusão deste lab.

**Aberto**: coluna sem nenhum char livre. Aqui não ocorreu (mínimo 35), mas existe — e aí a saída é o `min` com custo de escape do delimitador, como no `1853`. A regra recusa e cai no comportamento de hoje.


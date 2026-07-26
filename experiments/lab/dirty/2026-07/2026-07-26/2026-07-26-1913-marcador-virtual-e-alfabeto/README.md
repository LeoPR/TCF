# 2026-07-26-1913 — Marcador virtual + alfabeto da coluna

Reavaliação do lab `1853`. Você apontou dois erros, e os dois eram reais.

## Erro 1 — eu perguntei "qual char?" em vez de "onde há conflito?"

Chutei uma lista `/ ! ? & % #`. A pergunta certa é qual alfabeto a coluna **realmente usa** —
o complemento tem **conflito zero por construção**, sem lista, sem chute.

O mapa do núcleo confirmou que essa informação **não existe hoje**:
[column_features.py:55-88](src/tcf/column_features.py#L55-L88) coleta `n_unicas`, `avg_len`,
`cardinality`, `is_numeric` — nenhuma estatística de caractere.

| coluna | n | chars usados | chars **LIVRES** (de 88) |
|---|---:|---:|---:|
| `ip` | 500 | 1 | 87 |
| `cpf` | 200 | 2 | 86 |
| `cartao` | 500 | 12 | 77 |
| `telefone` | 500 | 17 | 75 |
| `texto` | 500 | 28 | 61 |
| **`retail-stockcode`** (real) | 2000 | 31 | 60 |
| **`lineitem-comment`** (real) | 2000 | 47 | 45 |
| **`retail-description`** (real) | 2000 | 57 | **35** |

**Mínimo em qualquer coluna medida: 35 chars livres** — e o pior caso é uma coluna de texto
livre real, não uma forma sintética favorável. As três `real` são as fixtures do gate
`test_real_world_snapshots.py`.

## Erro 2 — era uma esteira serializada

`plano()` varria o corpo **8 vezes** (6 candidatos × ocorrências + 2 polaridades), *depois* do
núcleo terminar. Faz-uma-coisa, para, analisa.

| | varreduras | quando |
|---|---:|---|
| lab `1853` | **8** | depois do núcleo |
| aqui | **1** | fundida na que já existe |

O marcador é **virtual** — um sentinela na representação intermediária, não um char. Não pode
colidir porque **não é texto**. É o movimento do OBAT (nós, não strings) e do HCC (composição,
não grafia):

```
tokens = [('R','56'), FLIP, ('L','033'), ('txt','-'), ...]   <- FLIP é objeto
grafia = resolve(tokens, char, inicial)                      <- char decidido NO FIM
```

Dentro do laço que [syntax.py:173-193](src/tcf/composicional/syntax.py#L173-L193) `_escape_lit`
**já roda** — o único laço char-a-char do emit, e exatamente onde o escape de dígito é decidido
([linha 181](src/tcf/composicional/syntax.py#L181)) — acumulam-se três coisas sem laço novo:

```
presentes   alfabeto da coluna   (1 add por char)
trocas_R    contador             (1 comparação por corrida)
trocas_L    contador             (a outra polaridade, no mesmo passo)
```

A decisão vira uma leitura de **3 acumuladores**. Exatamente o que você descreveu: marcar
durante a avaliação, decidir no fim.

## Os bytes não mudam — só o custo de decidir

| coluna | corpo | escapes hoje | trans. R | trans. L | decisão | Δ corpo |
|---|---:|---:|---:|---:|---|---:|
| `cpf` | 3800 | 800 | 200 | **0** | 0 | **−800** |
| `cartao` | 11960 | 2000 | 513 | 25 | 25 | **−1975** |
| `cnpj-mascara` | 9774 | 1714 | 975 | 515 | 515 | **−1199** |
| `cep` | 5990 | 997 | 500 | 5 | 5 | **−992** |
| `telefone` | 8244 | 1272 | 504 | 824 | 504 | **−768** |
| `data-br` | 4905 | 726 | 457 | 681 | 457 | **−269** |
| `ip` | 2851 | 256 | 64 | **0** | 0 | **−256** |
| `data-iso` | 5513 | 677 | 458 | 689 | 458 | **−219** |
| `email` | 5743 | 367 | 472 | 788 | recusa | 0 |
| **`retail-stockcode`** | 11437 | 1098 | 890 | 1185 | 890 | **−208** |
| **`retail-description`** | 27581 | 105 | 134 | 814 | recusa | 0 |
| **`lineitem-comment`** | 50598 | 0 | 0 | 1448 | recusa | 0 |

- divergências contra o `1853`: **0** — mesmos bytes, decididos em 1 varredura em vez de 8
- ganho somado: **−6686 B** · reconstrução byte-exata **e** RT pelo `decode` REAL: **26/26**

**As colunas reais de texto livre não ganham nada** (2 das 3 recusam, e a regra recusa
sozinha). O ganho está nas colunas formatadas. Isso é honesto declarar: o mecanismo é geral,
o benefício não é uniforme.

## O que isto destrava

O mapa mostrou que existe representação estruturada até a fase B (`pieces_per_line`,
tagged-union, [syntax.py:263-278](src/tcf/composicional/syntax.py#L263-L278)) e que ela
**some no `_emit_body`**: dali em diante é `list[str]`. É por isso que o seq-RLE precisa
**re-parsear texto** ([hcc_seqrle.py:56](src/tcf/composicional/hcc_seqrle.py#L56)
`find_escape_digit_runs`) para achar o dígito incrementável.

Um marcador virtual na saída é **exatamente a camada que falta ali**. Com ela o seq-RLE leria
o token em vez de reencontrar o `\` no texto — o que **dissolveria** o bloqueador de todos os
labs desta sequência em vez de contorná-lo.

## Limites

- **Nada soldado.** `src/tcf` intocado. `virtual.py` **simula** o que moraria em
  `_escape_lit`, percorrendo o corpo canônico uma vez; o ponto medido é *quantas varreduras a
  decisão custa* e *se sempre há char livre*, não a solda.
- **Não medido**: a mudança no `_emit_body`. É a próxima pergunta.
- **Aberto**: coluna sem nenhum char livre. Não ocorreu aqui (mínimo 35), mas existe — e aí a
  saída é o `min` com custo de escape, como no `1853`.
- A faixa é ASCII imprimível menos a gramática (`* ~ ^ , | \`). Não considerei chars fora de
  ASCII, que custariam mais de 1 byte em UTF-8.
- Estado da polaridade reseta por linha (mantém a linha auto-contida).

## Rodar

```
python run.py
```
`virtual.py` tem o marcador `FLIP`, a varredura única e as duas direções.

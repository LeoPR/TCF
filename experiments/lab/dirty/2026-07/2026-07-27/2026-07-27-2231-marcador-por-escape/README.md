# 2026-07-27-2231 — O marcador de fronteira pelo ESCAPE que já existe

Eu tinha travado no `=` literal e concluído que "o marcador colide com dado". A pergunta certa
era a sua:

> *"o `=` foi meramente um exemplo ilustrativo (…) teoricamente qualquer um que dê escape — a
> gente já trabalhou com escape, não tem como usar o mesmo ou um escape diferente?"*

Serve. E não por sorte — **por construção da gramática**.

## O que o core nunca consegue emitir

Varrendo os 95 imprimíveis como valor de coluna, os únicos chars que aparecem depois de um `\`
num corpo canônico são:

```
* 0 1 2 3 4 5 6 7 8 9 \ ^ ~
```

`_escape_lit` escapa corrida de dígito, `*`, `\` e `~`; o `^`-líder à parte. **Mais nada.**
Logo `\` + qualquer outro char é uma sequência **impossível** de o core produzir.

| valor de dado | vira no corpo | contém `\|`? |
|---|---|:-:|
| `a\|b` | `a\|b` | não |
| `=SOMA(A1)` | `=SOMA(A\1)` | não |
| `\temp` | `\\temp` | não |
| **`\|`** (o próprio marcador) | **`\\\|`** | não |

O último é o caso bonito: um valor de dado que **é** o marcador vira dois backslashes, porque
o core escapa o próprio `\`. O marcador continua inalcançável.

## O veneno que derrubou o `=`, agora

| coluna | `=` cru (F2) | `\|` (F5) |
|---|:-:|:-:|
| começa com `=` | **FALHA** | **OK** |
| contém `\` | OK | **OK** |
| contém `\|` | OK | **OK** |
| **é o próprio marcador** | OK | **OK** |
| só dígitos | OK | **OK** |
| com `~` e `*` | OK | **OK** |

```
#TCF.8B278          →  ["\\|", "normal", "outro", …]
\\|
normal
outro
\|GGGG…
```

## O eixo que só aparece pensando em stream dos dois lados

| | leitor streama? | **escritor** streama? | colide com dado? |
|---|:-:|:-:|:-:|
| **F1** contagem de linhas | sim | **não** — precisa contar antes de escrever o cabeçalho | não |
| **F2** `=` cru | sim | sim | **SIM** |
| **F3** b64 primeiro | **não** | sim | não |
| **F5** marcador `\|` | **sim** | **sim** | **não, por construção** |

O `F1` tem um custo que o eixo de bytes escondia: o encoder precisa **terminar o bloco do
domínio** para contar as linhas antes de escrever o cabeçalho — ou bufferiza tudo, ou volta
atrás para preencher o campo. Com o marcador ele escreve cabeçalho → domínio → marcador →
bits, sem voltar.

## E ainda é 1-2 B mais barato

| coluna | n | k | F1 | F5 | Δ |
|---|---:|---:|---:|---:|---:|
| `adult-sex` | 100 | 2 | 44 | 42 | **−2** |
| `pm25-cbwd` | 100 | 4 | 61 | 59 | **−2** |
| `adult-workclass` | 93 | 6 | 120 | 119 | **−1** |
| `cnpj-uf` | 2000 | 28 | 1767 | 1765 | **−2** |
| `str-k7` | 200 | 7 | 168 | 168 | 0 |

O marcador custa 2 B, mas o padding `=` do base64 (deduzível de `n` e `w`) é dropado — os dois
se cancelam e ainda sobra.

## O marcador não precisa ser `\|`

| marcador | válido? |
|---|:-:|
| `\|` · `\=` · `\!` · `\` + espaço | **sim** |
| `\*` · `\7` · `\\` · `\~` | não — o core emite essas |

Nenhum dos válidos colide. `\|` foi escolhido só por lembrar visualmente o `*N|` que já separa
prefixo de declaração.

## Um bug meu no caminho — 4ª aparição da mesma assimetria

Na primeira rodada, `contém \` e `é o próprio marcador` **falharam**. Não era o marcador: meu
`_le_grafia` tirava **qualquer** `\` inicial, quando `_grafa` só escapa o valor `"0"`. Um dado
`\temp` era mutilado para `temp`.

É a mesma classe dos três anteriores (weld do slot nulo, lab `2126`, lab `1608`): **quem grafa
valores ao lado do slot nulo tem de desfazer exatamente o que fez, nem mais**. O core faz o
próprio escape e o desfaz sozinho antes de chegar ao meu helper.

## O que muda na recomendação do lab anterior

O lab `2211` recomendou `F1` como default **porque o marcador colidia**. Com o marcador por
escape essa objeção some, e o `F5` passa a ser melhor em tudo: streama nos dois sentidos, é
imune a colisão por construção, e custa 1-2 B a menos.

Fica:

- **F5 como default** — domínio primeiro, marcador `\<char>`, padding dropado.
- **F3 como modo extra** — b64 primeiro, lote fechado. Continua ganhando ~1 B e continua sem
  streamar.

## Limites

- **Nada soldado**; `src/tcf` intocado.
- A garantia do marcador vale para o **corpo canônico de hoje**. Se `_escape_lit` passar a
  escapar char novo, o conjunto `SEGUEM_ESCAPE` muda — merece um teste que trave isso, não um
  comentário.
- A varredura foi sobre os 95 imprimíveis ASCII; não varri não-ASCII.
- Métrica de prefixo é **analítica**, não cronometrada.

## Rodar

```
python run.py
```
`marcador.py` tem a montagem, o **leitor independente** (acha a fronteira pelo marcador, sem
receber `k` nem contagem) e o validador de marcador.

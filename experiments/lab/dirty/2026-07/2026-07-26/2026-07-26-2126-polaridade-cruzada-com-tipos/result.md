# Polaridade × tipos — bool, binário, null (2026-07-26-2126)

Escala pequena de propósito: **50 linhas por coluna**, **18 sintéticas** + **15 reais**. Não é benchmark — é observação de comportamento e caça a bug.

`RT` compara **valor E tipo**, elemento a elemento: um `"0"` virando `None` (ou o contrário) passaria num RT frouxo.

## Sintéticas

| coluna | n | tag | nulls | corpo | escapes | tR | tL | decisão | Δ | RT |
|---|---:|:-:|---:|---:|---:|---:|---:|---|---:|:-:|
| `bool-puro` | 50 | `b132` | 0 | 12 | — | — | — | **N/A** (base64) | — | — |
| `bool-constante` | 50 | `b` | 0 | 9 | 0 | 0 | 0 | recusa (0 esc) | +0 | OK |
| `bool-null` | 50 | `b` | 10 | 145 | 0 | 0 | 10 | recusa (0 esc) | +0 | OK |
| `bool-null-maioria` | 50 | `b` | 33 | 138 | 0 | 0 | 17 | recusa (0 esc) | +0 | OK |
| `binario-01` | 50 | `(nenhuma)` | 0 | 150 | 2 | 2 | 0 | recusa (2 esc) | +0 | OK |
| `binario-01-null` | 50 | `(nenhuma)` | 13 | 137 | 2 | 2 | 13 | recusa (2 esc) | +0 | OK |
| `binario-sn` | 50 | `(nenhuma)` | 0 | 148 | 0 | 0 | 0 | recusa (0 esc) | +0 | OK |
| `null-puro` | 50 | `(nenhuma)` | 50 | 6 | 0 | 0 | 1 | recusa (0 esc) | +0 | OK |
| `null-quase-tudo` | 50 | `(nenhuma)` | 49 | 8 | 0 | 0 | 1 | recusa (0 esc) | +0 | OK |
| `null-esparso` | 50 | `(nenhuma)` | 1 | 291 | 49 | 49 | 1 | delim `!`L | -46 | OK |
| `int-null` | 50 | `n` | 9 | 303 | 41 | 41 | 9 | delim `!`L | -30 | OK |
| `int-ordenado-null` | 50 | `n` | 6 | 80 | 7 | 7 | 6 | recusa (7 esc) | +0 | OK |
| `int-negativo-null` | 50 | `n` | 7 | 241 | 43 | 43 | 7 | delim `!`L | -34 | OK |
| `float-null` | 50 | `n` | 8 | 339 | 78 | 39 | 8 | delim `!`L | -68 | OK |
| `str-zero-e-null` | 50 | `(nenhuma)` | 17 | 133 | 1 | 1 | 17 | recusa (1 esc) | +0 | OK |
| `str-zero-misto` | 50 | `(nenhuma)` | 13 | 148 | 12 | 12 | 13 | recusa (12 esc) | +0 | OK |
| `cpf-mascara-null` | 50 | `(nenhuma)` | 5 | 864 | 164 | 68 | 30 | delim `!`L | -132 | OK |
| `cartao-null` | 50 | `(nenhuma)` | 5 | 1090 | 181 | 48 | 8 | delim `!`L | -171 | OK |

## Reais (fixtures do repo, 50 linhas)

| coluna | n | tag | nulls | corpo | escapes | tR | tL | decisão | Δ | RT |
|---|---:|:-:|---:|---:|---:|---:|---:|---|---:|:-:|
| `real-adult-sex-bool` | 50 | `b132` | 0 | 12 | — | — | — | **N/A** (base64) | — | — |
| `real-adult-class-bool` | 50 | `b132` | 0 | 12 | — | — | — | **N/A** (base64) | — | — |
| `real-adult-age-int` | 50 | `n` | 0 | 192 | 30 | 30 | 0 | delim `!`L | -28 | OK |
| `real-adult-capgain-int` | 50 | `n` | 0 | 86 | 6 | 6 | 0 | delim `!`L | -4 | OK |
| `real-pm25-com-NA` | 50 | `(nenhuma)` | 24 | 127 | 21 | 21 | 1 | delim `!`L | -18 | OK |
| `real-pm25-Iws-float` | 50 | `n` | 0 | 344 | 82 | 41 | 0 | delim `!`L | -80 | OK |
| `real-cnpj-matriz-bin` | 50 | `(nenhuma)` | 0 | 29 | 2 | 2 | 0 | recusa (2 esc) | +0 | OK |
| `real-cnpj-fantasia-null` | 50 | `(nenhuma)` | 42 | 190 | 0 | 0 | 8 | recusa (0 esc) | +0 | OK |
| `real-cnpj-doc` | 50 | `(nenhuma)` | 0 | 805 | 147 | 61 | 101 | delim `!`R | -85 | OK |
| `real-pessoas-cpf` | 50 | `(nenhuma)` | 0 | 949 | 192 | 58 | 10 | delim `!`L | -180 | OK |
| `real-pessoas-email-null` | 50 | `(nenhuma)` | 5 | 913 | 0 | 0 | 48 | recusa (0 esc) | +0 | OK |
| `real-ibge-id` | 50 | `n` | 0 | 235 | 24 | 21 | 40 | delim `!`R | -2 | OK |
| `real-retail-stockcode` | 50 | `(nenhuma)` | 0 | 344 | 59 | 46 | 54 | delim `!`R | -12 | OK |
| `real-tpch-phone` | 20 | `(nenhuma)` | 0 | 393 | 78 | 21 | 11 | delim `!`L | -65 | OK |
| `real-tpch-acctbal` | 20 | `n` | 0 | 191 | 40 | 20 | 0 | delim `!`L | -38 | OK |

## Resultado

- colunas medidas: **33** (18 sintéticas + 15 reais)
- **N/A** (corpo não é declaração): **3** — `bool-puro` (`b132`), `real-adult-sex-bool` (`b132`), `real-adult-class-bool` (`b132`)
- delimitador ativa: **16 de 30** aplicáveis
- RT estrito (valor **e** tipo): **30/30**
- divergência de TIPO: **0** (nenhuma)
- Δ somado: **-993 B**

## O `0` do null: dígito que não é dado

O slot nulo é escrito como `0` cru — grafia otimizada de `^0`. Ele é **dígito** no corpo, mas é **referência**, não dado. Se o mecanismo o tratasse como corrida literal, a reconstrução emitiria `\0` = a string `"0"`, e um RT frouxo não veria: o tamanho bate, o tipo da lista bate.

Este lab trata a linha `0` como **opaca** (junto de `^N` e da linha vazia) e compara tipo elemento a elemento. As colunas que exercem isso:

| coluna | nulls | tem `"0"` como dado? | RT |
|---|---:|:-:|:-:|
| `bool-null` | 10 | não | OK |
| `bool-null-maioria` | 33 | não | OK |
| `binario-01-null` | 13 | sim | OK |
| `null-puro` | 50 | não | OK |
| `null-quase-tudo` | 49 | não | OK |
| `null-esparso` | 1 | não | OK |
| `int-null` | 9 | não | OK |
| `int-ordenado-null` | 6 | não | OK |
| `int-negativo-null` | 7 | não | OK |
| `float-null` | 8 | não | OK |
| `str-zero-e-null` | 17 | sim | OK |
| `str-zero-misto` | 13 | sim | OK |
| `cpf-mascara-null` | 5 | não | OK |
| `cartao-null` | 5 | não | OK |
| `real-pm25-com-NA` | 24 | não | OK |
| `real-cnpj-fantasia-null` | 42 | não | OK |
| `real-pessoas-email-null` | 5 | não | OK |

`str-zero-e-null` e `binario-01-null` são o par crítico: o mesmo char `0` aparece como **dado** e como **slot nulo** na mesma coluna.


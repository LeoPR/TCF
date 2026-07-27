# Polaridade × tipos — bool, binário, null (2026-07-26-2126)

Escala pequena de propósito: **até 50 linhas por coluna** (2 fixtures reais têm menos — a coluna `n` da tabela diz o real), **19 sintéticas** + **15 reais**. Não é benchmark — é observação de comportamento e caça a bug.

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
| `zero-null-ATIVO` | 50 | `(nenhuma)` | 9 | 666 | 124 | 48 | 23 | delim `!`L | -99 | OK |
| `cpf-mascara-null` | 50 | `(nenhuma)` | 5 | 853 | 156 | 69 | 37 | delim `!`L | -117 | OK |
| `cartao-null` | 50 | `(nenhuma)` | 5 | 1094 | 183 | 46 | 10 | delim `!`L | -171 | OK |

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

- colunas medidas: **34** (19 sintéticas + 15 reais)
- **N/A** (corpo não é declaração): **3** — `bool-puro` (`b132`), `real-adult-sex-bool` (`b132`), `real-adult-class-bool` (`b132`)
- delimitador ativa: **17 de 31** aplicáveis
- **RT com transformação real** (a regra ativou, o corpo foi para o delimitador e voltou): **17/17**
- RT das colunas que **recusaram** — é IDENTIDADE, não prova do mecanismo: **14**
- divergência de TIPO: **0** (nenhuma)
- Δ somado: **-1077 B**

**O decoder REAL nunca recebe a grafia da proposta.** Ele recebe o corpo canônico *reconstruído* — que é o desenho (camada de borda), mas precisa ser dito: o que está provado é a **reconstrução**, não que um `.tcfp` seja um wire válido. Alimentar o `.tcfp` direto ao `decode` **falha alto** (`ValueError`), graças ao fail-loud soldado antes nesta sessão — não corrompe em silêncio.

## O `0` do null: dígito que não é dado

O slot nulo é escrito como `0` cru — grafia otimizada de `^0`. Ele é **dígito** no corpo, mas é **referência**, não dado. Se o mecanismo o tratasse como corrida literal, a reconstrução emitiria `\0` = a string `"0"`, e um RT frouxo não veria: o tamanho bate, o tipo da lista bate.

A correção foi **tirar** a regra especial: o null é referência ao slot 0, e a máquina de polaridade classifica dígito nu como `R` = referência. Ela acerta sozinha.

A coluna que importa é a que tem `"0"` como **dado**, `null` na mesma coluna, **e** a regra ATIVADA — sem as três coisas juntas o RT é identidade e não prova nada. Foi um achado da auditoria: as 4 primeiras abaixo **recusam**.

| coluna | nulls | `"0"` como dado? | regra ativou? | RT |
|---|---:|:-:|:-:|:-:|
| `bool-null` | 10 | não | não (identidade) | OK |
| `bool-null-maioria` | 33 | não | não (identidade) | OK |
| `binario-01-null` | 13 | sim | não (identidade) | OK |
| `null-puro` | 50 | não | não (identidade) | OK |
| `null-quase-tudo` | 49 | não | não (identidade) | OK |
| `null-esparso` | 1 | não | **sim** | OK |
| `int-null` | 9 | não | **sim** | OK |
| `int-ordenado-null` | 6 | não | não (identidade) | OK |
| `int-negativo-null` | 7 | não | **sim** | OK |
| `float-null` | 8 | não | **sim** | OK |
| `str-zero-e-null` | 17 | sim | não (identidade) | OK |
| `str-zero-misto` | 13 | sim | não (identidade) | OK |
| `zero-null-ATIVO` | 9 | sim | **sim** | OK |
| `cpf-mascara-null` | 5 | não | **sim** | OK |
| `cartao-null` | 5 | não | **sim** | OK |
| `real-pm25-com-NA` | 24 | não | **sim** | OK |
| `real-cnpj-fantasia-null` | 42 | não | não (identidade) | OK |
| `real-pessoas-email-null` | 5 | não | não (identidade) | OK |

`zero-null-ATIVO` foi construída depois da auditoria exatamente para fechar esse buraco: `"0"` como dado, `null`, e corridas de dígito suficientes para o FLOOR ativar. Ela ativa (`-99 B`) e o RT passa.

## A FAIXA encolheu — ainda sobra char?

A auditoria adversarial reproduziu dois bugs de eleição: **dígito** eleito funde com a corrida vizinha (`1\\22.\\33` → `1022.33`, e a volta deixa de ser exata), e **letra** eleita colide com o slot do discriminador — uma coluna de STRING emitia `#TCF.8b`, byte-idêntico ao cabeçalho canônico de uma coluna bool. A correção exclui por **classe**, não por lista: só pontuação.

```
FAIXA = !"#$%&'()+-./:;<=>?@[]_`{}
26 chars (era 88 — caiu 70%)
```

Isso encolhe muito o espaço, então a pergunta vira empírica:

| coluna | usados da FAIXA | livres | eleito |
|---|---:|---:|:-:|
| `bool-constante` | 0 | 26 | `!` |
| `bool-null` | 0 | 26 | `!` |
| `bool-null-maioria` | 0 | 26 | `!` |
| `binario-01` | 0 | 26 | `!` |
| `binario-01-null` | 0 | 26 | `!` |
| `binario-sn` | 0 | 26 | `!` |
| `null-puro` | 0 | 26 | `!` |
| `null-quase-tudo` | 0 | 26 | `!` |
| `null-esparso` | 0 | 26 | `!` |
| `int-null` | 0 | 26 | `!` |
| `int-ordenado-null` | 0 | 26 | `!` |
| `int-negativo-null` | 1 | 25 | `!` |
| `float-null` | 1 | 25 | `!` |
| `str-zero-e-null` | 0 | 26 | `!` |
| `str-zero-misto` | 0 | 26 | `!` |
| `zero-null-ATIVO` | 2 | 24 | `!` |
| `cpf-mascara-null` | 2 | 24 | `!` |
| `cartao-null` | 1 | 25 | `!` |
| `real-adult-age-int` | 0 | 26 | `!` |
| `real-adult-capgain-int` | 0 | 26 | `!` |
| `real-pm25-com-NA` | 0 | 26 | `!` |
| `real-pm25-Iws-float` | 1 | 25 | `!` |
| `real-cnpj-matriz-bin` | 0 | 26 | `!` |
| `real-cnpj-fantasia-null` | 1 | 25 | `!` |
| `real-cnpj-doc` | 3 | 23 | `!` |
| `real-pessoas-cpf` | 2 | 24 | `!` |
| `real-pessoas-email-null` | 2 | 24 | `!` |
| `real-ibge-id` | 1 | 25 | `!` |
| `real-retail-stockcode` | 0 | 26 | `!` |
| `real-tpch-phone` | 1 | 25 | `!` |
| `real-tpch-acctbal` | 2 | 24 | `!` |

Mínimo de chars livres: **23 de 26** (em `real-cnpj-doc`). Nenhuma coluna ficou sem opção nesta amostra — mas a margem caiu, e é uma amostra pequena.


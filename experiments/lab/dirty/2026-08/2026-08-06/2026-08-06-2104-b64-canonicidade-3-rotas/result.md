# Canonicidade de payload b64 — as três rotas (2026-08-06-2104)

Refaz o lab `2026-08-06-2006` corrigindo **uma classificação** e convergindo para **uma** proposta.

## Correção 1 — o lazy `bB` não é padrão-ouro

O lab anterior deu a ele **48/48 fail-loud**. Ele valida, mas **não confere tamanho**, e aceita payload estendido com **bytes zero**:

| rota | cabeçalho | payload + `AAAA` (bytes zero) |
|---|---|---|
| `bn-B` | `#TCF.8B2c8` | **SILENCIOSO-IGUAL** |
| `bn-C` | `#TCF.8C2c8` | FAIL-LOUD TCF |
| `denso-b1` | `#TCF.8b1c8` | FAIL-LOUD TCF |
| `denso-b2` | `#TCF.8b2c8` | FAIL-LOUD TCF |
| `lazy-bB` | `#TCF.8bB3c8` | **SILENCIOSO-IGUAL** |

A sonda do lab anterior não separava os dois porque a extensão que ela usava caía na checagem de bits-de-padding do `unpack_w` (que exige padding zerado). Estender com bytes que **são** zero atravessa essa checagem.

**Consequência: a correção vai em duas rotas, não em uma.**

## Correção 2 — `tamanho exato` não é variante opcional

O lab anterior a chamou de "recomendação". Medindo **qual checagem pega o quê** (payload de 25 bytes, convenção sem padding):

| adulteração | `validate` | re-codifica | tamanho |
|---|:-:|:-:|:-:|
| char inválido `!` | **PEGA** | — | — |
| espaço | **PEGA** | — | — |
| padding `==` a mais | passa | **PEGA** | passa |
| caixa trocada | passa | **PEGA** | passa |
| extensão zero `+AA` | passa | passa | **PEGA** |
| extensão zero `+AAAA` | passa | passa | **PEGA** |
| truncado −4 | passa | **PEGA** | **PEGA** |

**Nenhuma subsome a outra.** A re-codificação não pega extensão com bytes zero; o tamanho não pega char inválido. As três juntas são o mínimo — e são exatamente o que o denso (`_decode_denso`) já faz.

## Correção 3 — o padding não é decisão nova

Re-codificar-e-comparar é a **mesma técnica** que o cabeçalho já usa para o hex (`f"{n:x}" != nhex`, ADR-0036). A regra de canonicidade já existe no formato; ela só não tinha sido aplicada ao payload. Cada rota declara a sua forma canônica (o denso emite **com** `=`; bN e lazy **sem**) e a checagem é sempre "bate com a canônica desta rota".

## A matriz — 9 sondas × 5 rotas, hoje × proposto

Cada célula tem wire em `outputs/sondas/<rota>-<sonda>.tcf`, relido do disco antes do decode.

| sonda | `bn-B` | `bn-C` | `denso-b1` | `denso-b2` | `lazy-bB` |
|---|:-:|:-:|:-:|:-:|:-:|
| `s1-char-invalido` | **cru**→OK | OK | OK | OK | OK |
| `s2-espaco` | **cru**→OK | OK | OK | OK | OK |
| `s3-quatro-invalidos` | **mudo**→OK | OK | OK | OK | OK |
| `s4-padding-extra` | **mudo**→OK | OK | OK | OK | OK |
| `s5-truncado-2` | **cru**→OK | **cru**→OK | OK | OK | OK |
| `s6-truncado-4` | OK | **cru**→OK | OK | OK | OK |
| `s7-extensao-zero-AA` | **cru**→OK | OK | OK | OK | **mudo**→OK |
| `s8-extensao-zero-AAAA` | **mudo**→OK | OK | OK | OK | **mudo**→OK |
| `s9-caixa-trocada` | **CORROMPE**→OK | **CORROMPE**→OK | OK | OK | **CORROMPE** |

`OK` = fail-loud TCF · `cru` = vaza `binascii` · `mudo` = aceita o wire adulterado calado · `→OK` = a proposta fecha.

| | fail-loud TCF | binascii cru | silencioso | corrompe |
|---|:-:|:-:|:-:|:-:|
| **hoje** | 31 | **6** | **5** | 3 |
| **proposto** | 44 | 0 | 0 | 1 |

Total de células: **45**. Matriz completa em `outputs/matriz-sondas.csv`.

## Byte-neutralidade — a proposta só toca caminho de erro

| rota | wire | bytes | RT byte-idêntico |
|---|---|---:|:-:|
| `bn-B` | `#TCF.8B2c8` | 88 | OK |
| `bn-C` | `#TCF.8C2c8` | 87 | OK |
| `denso-b1` | `#TCF.8b1c8` | 47 | OK |
| `denso-b2` | `#TCF.8b2c8` | 79 | OK |
| `lazy-bB` | `#TCF.8bB3c8` | 122 | OK |

Os wires válidos das 5 rotas **passam** pela proposta, e o roundtrip é byte-idêntico ao consumido: **todos OK**. A mudança só toca caminho de erro — byte-neutra por construção.

## O `s9` separa duas coisas que o lab anterior juntou

Trocar a **caixa do último char** do payload dá resultados diferentes conforme o comprimento — e a diferença **não é acaso**:

| rota | bits | último char tem bits mortos? | s9 |
|---|---|:-:|---|
| `bn-B` | n=200, w=2 → 50 B | **sim** | a re-codificação **pega** |
| `bn-C` | n=200, w=2 → 50 B | **sim** | a re-codificação **pega** |
| `denso-b1` | n=200, w=1 → 25 B | **sim** | a re-codificação **pega** |
| `denso-b2` | n=200, w=2 → 50 B | **sim** | a re-codificação **pega** |
| `lazy-bB` | n=200, w=3 → 75 B | não | nenhuma checagem pega |

Quando o payload **não** fecha em grupo de 3 bytes, o último char carrega bits que não significam nada — e trocá-lo produz uma grafia **não-canônica dos mesmos bytes**. Isso é sintaxe, e a re-codificação pega.

Quando o payload fecha exato (o caso do `lazy-bB`: 200×3 bits = 75 B = 100 chars), **todos** os bits significam, e a troca é mudança de **conteúdo** — nenhuma validação sintática pode pegar.

O lab anterior reportou **0 corrupção**; havia 3 células, das quais 2 são sintáticas (fechadas pela proposta) e 1 é de conteúdo (fora de escopo). A diferença entre elas é o que faltava.

## O que a proposta NÃO resolve

**Char válido trocado por outro char válido, em payload sem bits mortos** — é integridade de *conteúdo*, não de sintaxe. Nenhuma validação sintática pega; só checksum resolveria, e é outro ticket.

## Consequência para o weld

| onde | mudança |
|---|---|
| `dominio_bn.decode_bn` | as 3 checagens (hoje não tem nenhuma) |
| `decoder._decode_lazy_bool` | acrescentar re-codificação + tamanho exato |
| `decoder._decode_denso` | **nada** — já é o padrão |

Os `outputs/sondas/*.tcf` viram casos de teste diretos.


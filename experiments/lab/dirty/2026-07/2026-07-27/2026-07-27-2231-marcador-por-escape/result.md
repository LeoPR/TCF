# O marcador de fronteira pelo ESCAPE (2026-07-27-2231)

Eu tinha travado no `=` literal e concluído que "o marcador colide com dado". A pergunta certa era a sua: **o escape que a gente já tem não serve?**

Serve — e não por sorte, por **construção da gramática**.

## A — o que pode seguir um `\` num corpo canônico

Varrendo os 95 imprimíveis, um por vez, como valor de coluna:

```
chars que seguem um `\`:  *0123456789\^~
```

`_escape_lit` escapa corrida de dígito, `*`, `\` e `~`; o `^`-líder é escapado à parte. **Mais nada.** Então:

| valor de dado | vira | contém `\|`? |
|---|---|:-:|
| `'\\x'` | `'\\\\x'` | não |
| `'a*b'` | `'a\\*b'` | não |
| `'a~b'` | `'a\\~b'` | não |
| `'^topo'` | `'\\^topo'` | não |
| `'a|b'` | `'a|b'` | não |
| `'=SOMA(A1)'` | `'=SOMA(A\\1)'` | não |
| `'123'` | `'\\123'` | não |
| `'\\|'` | `'\\\\|'` | **SIM** |
| `'\\\\|'` | `'\\\\\\\\|'` | **SIM** |

O conjunto medido está contido no declarado (`SEGUEM_ESCAPE`): **sim**.

Repare no caso `'\\|'`: o valor de dado que **é** o marcador vira `\\\\|` (dois backslashes) no corpo. O core escapa o próprio `\`, então o marcador continua inalcançável.

## B — o veneno que derrubou o `=`

| coluna | `=` cru (F2) | `\|` (F5) |
|---|:-:|:-:|
| `comeca-com-igual` | **FALHA** | OK |
| `contem-backslash` | OK | OK |
| `contem-pipe` | OK | OK |
| `e-o-proprio-marcador` | OK | OK |
| `so-digitos` | OK | OK |
| `com-til-e-asterisco` | OK | OK |

## C — bytes e prefixo, contra as variantes anteriores

`F1` = contagem de linhas no cabeçalho · `F5` = marcador `\|` + padding dropado

| coluna | n | k | F1 | F5 | Δ | prefixo F5 | RT |
|---|---:|---:|---:|---:|---:|---:|:-:|
| `str-k2` | 200 | 2 | 59 | 57 | **-2** | 27 | OK |
| `str-k4` | 200 | 4 | 110 | 109 | **-1** | 46 | OK |
| `str-k7` | 200 | 7 | 168 | 168 | **+0** | 72 | OK |
| `str-k4-null` | 200 | 5 | 146 | 146 | **+0** | 50 | OK |
| `adult-sex` | 100 | 2 | 44 | 42 | **-2** | 28 | OK |
| `adult-workclass` | 93 | 6 | 120 | 119 | **-1** | 76 | OK |
| `cnpj-uf` | 2000 | 28 | 1767 | 1765 | **-2** | 102 | OK |
| `pm25-cbwd` | 100 | 4 | 61 | 59 | **-2** | 29 | OK |

## D — o eixo que só aparece pensando em stream dos DOIS lados

O `F1` (contagem de linhas) é robusto, mas tem um custo que o eixo de bytes não mostra: **o encoder precisa terminar o bloco do domínio para contar as linhas antes de escrever o cabeçalho**. Ou ele bufferiza o domínio inteiro, ou volta atrás para preencher o campo.

| | leitor streama? | escritor streama? | colide com dado? |
|---|:-:|:-:|:-:|
| **F1** contagem de linhas | sim | **não** (precisa contar antes) | não |
| **F2** `=` cru | sim | sim | **SIM** |
| **F3** b64 primeiro | **não** | sim | não |
| **F5** marcador `\|` | sim | **sim** | **não, por construção** |

O `F5` é o único que fecha as três colunas — e não precisou de char novo, eleição, nem escape adicional. Só usou a gramática que já existia.

### Qualquer `\<char>` fora do conjunto serve

| marcador | válido? |
|---|:-:|
| `'\\|'` | **sim** |
| `'\\='` | **sim** |
| `'\\!'` | **sim** |
| `'\\ '` | **sim** |
| `'\\*'` | não |
| `'\\7'` | não |
| `'\\\\'` | não |
| `'\\~'` | não |
| `'|\\'` | não |
| `'=='` | não |

A escolha entre eles é estética — nenhum colide. `\|` foi escolhido só por lembrar visualmente o `*N|` que já separa prefixo de declaração.

## O que muda na recomendação anterior

O lab `2211` recomendou `F1` como default porque o marcador `=` colidia. **Com o marcador por escape, essa objeção some**, e o `F5` passa a ser o melhor dos dois mundos: streama nos dois sentidos, é imune a colisão por construção, e custa o mesmo que o `F1`.

RT pelo leitor independente: **todos OK**


# Domínio primeiro — o eixo de streaming (2026-07-27-2211)

O lab `1647` escolheu **b64 primeiro** porque custa 0 B de declaração. Media o eixo errado sozinho: **com o domínio no fim, nenhum valor sai antes do payload inteiro chegar**. Aqui os dois eixos andam juntos.

| | bytes | prefixo até o 1º valor |
|---|---|---|
| **F1** contagem de linhas | +1-2 B | cabeçalho + domínio + 4 |
| **F2** marcador `=`, padding dropado | +1 B / −0-2 B | cabeçalho + domínio + 4 |
| **F3** b64 primeiro | **+0 B** | **o wire inteiro** |
| **F4** tamanho em bytes | +2-4 B | cabeçalho + domínio + 4 |

## O `=` é deduzível — e por isso pode virar marcador de abertura

O padding do base64 sai do número de bytes, que sai de `n` e `w` — ambos no cabeçalho. Dropar e recolocar reconstrói byte a byte.

| n | w | b64 com `=` | sem `=` | economia |
|---:|---:|---:|---:|---:|
| 100 | 1 | 20 | 18 | **-2** |
| 200 | 1 | 36 | 34 | **-2** |
| 200 | 2 | 68 | 67 | **-1** |
| 200 | 3 | 100 | 100 | **+0** |
| 93 | 3 | 48 | 47 | **-1** |
| 2000 | 5 | 1668 | 1667 | **-1** |

Foi a sua observação: o `=` como **terminador** é dispensável, e liberá-lo para **abrir** o bloco resolve a delimitação sem gastar declaração.

## As quatro, medidas (n=200)

`prefixo` = bytes que o leitor precisa bufferizar antes de emitir o **1º valor**.

| coluna | k | F1 | F2 | F3 | F4 | prefixo F1/F2/F4 | prefixo F3 |
|---|---:|---:|---:|---:|---:|---:|---:|
| `str-k2` | 2 | 59 | 56 | 57 | 59 | 27 | **57** |
| `str-k2-null` | 3 | 95 | 93 | 93 | 95 | 31 | **93** |
| `str-k3` | 3 | 100 | 98 | 98 | 101 | 36 | **98** |
| `str-k3-null` | 4 | 104 | 102 | 102 | 105 | 40 | **102** |
| `str-k4` | 4 | 110 | 108 | 108 | 111 | 46 | **108** |
| `str-k4-null` | 5 | 146 | 145 | 144 | 147 | 50 | **144** |
| `str-k7` | 7 | 168 | 167 | 166 | 169 | 72 | **166** |
| `str-k7-null` | 8 | 172 | 171 | 170 | 173 | 76 | **170** |
| `num-k4` | 4 | 91 | 89 | 89 | 91 | 27 | **89** |

## Reais

| coluna | n | k | F1 | F2 | F3 | F4 | prefixo F2 | prefixo F3 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| **`adult-sex`** | 100 | 2 | 44 | 41 | 42 | 44 | 26 | **42** |
| **`adult-workclass`** | 93 | 6 | 120 | 118 | 118 | 121 | 74 | **118** |
| **`cnpj-situacao`** | 2000 | 2 | 358 | 355 | 356 | 358 | 24 | **356** |
| **`cnpj-uf`** | 2000 | 28 | 1767 | 1764 | 1764 | 1767 | 100 | **1764** |
| **`pm25-cbwd`** | 100 | 4 | 61 | 58 | 59 | 61 | 27 | **59** |

## O que os dois eixos dizem juntos

Em bytes as quatro ficam **dentro de 3 B uma da outra** — ruído em qualquer coluna de tamanho real. Em prefixo a diferença é de **ordem de grandeza**: F3 precisa do wire inteiro, as outras precisam só do domínio.

`cnpj-uf` (n=2000, k=28) é o caso que mostra: **F2 bufferiza ~100 B, F3 bufferiza ~1760 B** — 17× — para a mesma informação e 1 byte de diferença.

Ou seja: **ter as duas é a resposta certa**, e a escolha não é de bytes, é de modo de transporte:

| | quando |
|---|---|
| **domínio primeiro** (F1/F2/F4) | default — stream, pipe, resposta HTTP, qualquer consumo incremental |
| **b64 primeiro** (F3) | lote fechado, arquivo em disco, quando 1-3 B importam e ninguém vai ler incrementalmente |

Entre as três de domínio-primeiro, **F2 é a mais barata** (o `=` que abre o bloco se paga dropando o padding) e é a que você propôs. **F1 é a mais robusta**: a contagem de linhas não depende de nenhum char ser reservado.

### O risco do F2, declarado

O marcador `=` abre o bloco de bits. Se um **valor do domínio** começar com `=`, o leitor corta no lugar errado. Não é hipotético — `=` é char comum em dado (fórmula, base64 embutido, query string). F1 não tem esse risco.

| domínio com valor começando em `=` | F1 | F2 |
|---|:-:|:-:|
| `['=SOMA(A1)','normal','outro']` | OK | **FALHOU** |

Medido, não suposto. Se o `=` for o marcador, ele precisa ser escapado no domínio — e aí some a economia que o justificava.

## Recomendação

- **F1 como default**: domínio primeiro, contagem de linhas no cabeçalho. Custa 1-2 B, streama, e não reserva char nenhum.
- **F3 como modo extra**: b64 primeiro, para lote fechado. Ganha 1-3 B e é o que você chamou de "formato de compressão extra".
- **F2 fica registrado**: a ideia do `=` é boa e a economia do padding é real, mas o marcador colide com dado. Vale se o `=` for escapado — o que consome de volta o que ele economiza.

RT pelos leitores independentes: **todos OK**


# Domínio comprimido + alinhamento (2026-07-27-1647)

Refino da escada bN (`2026-07-27-1608`) a partir de duas observações suas sobre `adult-sex-bn.tcfp`.

## A — o alinhamento fecha? (varredura exaustiva)

`n*w` quase nunca é múltiplo de 8, e o base64 ainda arredonda para múltiplos de 3 bytes. Os bits do rabo são **lixo**. A pergunta é se o leitor para no lugar certo.

Varrendo **todo** `n` de 1 a 40 × **todo** `w` de 1 a 6, nas duas montagens, com e sem compressão do domínio:

- combinações testadas: **936**
- reconstruíram os dados originais: **936/936**

O rabo **não estraga** porque `n` viaja no cabeçalho e o leitor para nele. Mas isso é uma **obrigação do leitor**, não uma propriedade do formato: um leitor que desempacotasse até o fim do buffer devolveria valores fantasma.

Quanto o rabo custa, em bits desperdiçados:

| n | w=1 | w=2 | w=3 | w=4 | w=5 | w=6 |
|---:|---:|---:|---:|---:|---:|---:|
| 3 | 21 | 18 | 15 | 12 | 9 | 6 |
| 5 | 19 | 14 | 9 | 4 | 23 | 18 |
| 7 | 17 | 10 | 3 | 20 | 13 | 6 |
| 10 | 14 | 4 | 18 | 8 | 22 | 12 |
| 100 | 20 | 16 | 12 | 8 | 4 | 0 |
| 200 | 16 | 8 | 0 | 16 | 8 | 0 |

O desperdício é **constante em ordem de grandeza** (≤ 40 bits = 5 B), vindo do arredondamento do base64 para múltiplos de 4 chars. Em `n` grande é ruído; em `n` minúsculo é parte do porquê a proposta não se paga abaixo de ~5 linhas.

## B — onde o domínio termina? (o seq-RLE colapsa linhas)

Este é o achado que a sua pergunta destravou. **"Leia k linhas" não funciona**, porque o core pode colapsar o domínio inteiro:

| domínio | k | linhas emitidas | corpo |
|---|---:|---:|---|
| `['Male', 'Female']` | 2 | **2** | `'M*ale\nFem2'` |
| `['100', '101', '102', '103']` | 4 | **1** | `'*4+1|\\100'` |
| `['A1', 'A2', 'A3', 'A4', 'A5']` | 5 | **1** | `'*5+1|A\\1'` |
| `['ativo', 'inativo', 'suspenso']` | 3 | **3** | `'ativo\nin1\nsuspenso'` |

Quatro valores viram **uma** linha (`*4+1|\100`). Duas saídas:

| variante | como | custo de declaração |
|---|---|---|
| **V-len** | tamanho do domínio no cabeçalho (`:<hex>`) | 2-4 B |
| **V-b64** | b64 **primeiro**; o resto é domínio | **0 B** |

O comprimento do b64 é `4*ceil(ceil(n*w/8)/3)` — **deduzível de `n` e `w`, que já estão no cabeçalho**. É materialização mínima: deduz em vez de declarar.

| coluna | V-len | V-b64 | Δ |
|---|---:|---:|---:|
| `sex-100` | 44 | 42 | **-2** |
| `status-4-200` | 102 | 99 | **-3** |
| `num-4-200` | 91 | 89 | **-2** |

## C — comprimir o domínio com o core

O domínio é uma mini-coluna. `_encode_column(dom)` — **zero código novo**, reusa OBAT, HCC e seq-RLE, que é exatamente o "aproveitando os índices inter tipos" que você viu.

| domínio | cru | pelo core | Δ | grafia |
|---|---:|---:|---:|---|
| 2 valores, `Male`… | 11 | 10 | **-1** | `'M*ale\nFem2'` |
| 2 valores, `S`… | 3 | 3 | **+0** | `'S\nN'` |
| 4 valores, `ativo`… | 32 | 28 | **-4** | `'ativo\nin1\nsuspenso\ncancelado'` |
| 6 valores, `Private`… | 69 | 58 | **-11** | `'Private\nSelf-emp-*not-*inc\nLoc*al*'` |
| 3 valores, `2020-01-01`… | 32 | 23 | **-9** | `'\\2020-\\01-\\0*\\1\n1\\2\n1\\3'` |
| 8 valores, `AC`… | 23 | 23 | **+0** | `'AC\nAL\nAM\nAP\nBA\nCE\nDF\nES'` |

Rende pouco em `k` pequeno e valor curto (é onde a escada já ganhava fácil), e rende **mais** justamente onde a escada perdia: `k` grande com valor longo, porque lá o domínio é que dominava o custo.

## D — o foco: bool + 3 a 7 tipos

Você perguntou se **7 seria o limite**. Com o `null` no slot 0, **7 valores de dado + null = 8 = 2³** — a fronteira natural é o `w` fechar em 3 bits.

| k | w | usa o w inteiro? | sobra |
|---:|---:|:-:|---:|
| 2 | 1 | **sim** | 0 |
| 3 | 2 | não | 1 |
| 4 | 2 | **sim** | 0 |
| 5 | 3 | não | 3 |
| 6 | 3 | não | 2 |
| 7 | 3 | não | 1 |
| 8 | 3 | **sim** | 0 |
| 9 | 4 | não | 7 |

`k=3` e `k=5,6,7` **desperdiçam slots** (o `w` arredonda para cima). Isso não é bug — é o preço de largura fixa. `k` = potência de 2 é o caso justo.

Medição, n=200, com e sem null, domínio cru × comprimido (variante V-b64):

| coluna | k | w | hoje | bN cru | bN core | melhor Δ | RT |
|---|---:|---:|---:|---:|---:|---:|:-:|
| `str-k2` | 2 | 1 | 611 | 61 | 57 | **-554** | OK |
| `str-k2-null` | 3 | 2 | 589 | 95 | 93 | **-496** | OK |
| `str-k3` | 3 | 2 | 617 | 102 | 98 | **-519** | OK |
| `str-k3-null` | 4 | 2 | 595 | 104 | 102 | **-493** | OK |
| `str-k4` | 4 | 2 | 624 | 112 | 108 | **-516** | OK |
| `str-k4-null` | 5 | 3 | 602 | 146 | 144 | **-458** | OK |
| `str-k5` | 5 | 3 | 629 | 152 | 148 | **-481** | OK |
| `str-k5-null` | 6 | 3 | 607 | 154 | 152 | **-455** | OK |
| `str-k6` | 6 | 3 | 635 | 162 | 157 | **-478** | OK |
| `str-k6-null` | 7 | 3 | 613 | 164 | 161 | **-452** | OK |
| `str-k7` | 7 | 3 | 641 | 171 | 166 | **-475** | OK |
| `str-k7-null` | 8 | 3 | 619 | 173 | 170 | **-449** | OK |
| `bool` | 2 | 1 | 612 | 58 | 58 | **-554** | OK |
| `bool-null` | 3 | 2 | 589 | 92 | 93 | **-497** | OK |

## Reais, no mesmo recorte

| coluna | n | k | w | hoje | bN cru | bN core | melhor Δ | RT |
|---|---:|---:|---:|---:|---:|---:|---:|:-:|
| **`adult-sex`** | 100 | 2 | 1 | 205 | 43 | 42 | **-163** | OK |
| **`adult-race`** | 100 | 5 | 3 | 157 | 119 | 119 | **-38** | OK |
| **`adult-workclass`** | 93 | 6 | 3 | 234 | 129 | 118 | **-116** | OK |
| **`cnpj-situacao`** | 2000 | 2 | 1 | 425 | 354 | 356 | **-71** | OK |
| **`cnpj-uf`** | 2000 | 28 | 5 | 6378 | 1764 | 1764 | **-4614** | OK |
| **`pm25-cbwd`** | 100 | 4 | 2 | 61 | 59 | 59 | **-2** | OK |

RT pelos leitores independentes: **todos OK**

## O que fica

1. **O alinhamento fecha**, mas por obrigação do leitor (parar em `n`), não por propriedade do formato. Merece um teste, não um comentário.
2. **A delimitação do domínio era um buraco real** — o seq-RLE colapsa linhas. A saída `V-b64` custa **0 B** porque o tamanho do b64 é deduzível.
3. **Comprimir o domínio pelo core não precisa de código novo** e rende mais justamente onde a escada perdia.
4. **`k` potência de 2 é o caso justo**; 3, 5, 6, 7 desperdiçam slots — o preço de largura fixa. Largura variável fica pra outra conversa.


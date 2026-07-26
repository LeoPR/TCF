# Dedução do delimitador — 30 variações (2026-07-26-1954)

**Eleição** (encoder): o menor char da FAIXA que a coluna não usa.  
**Dedução** (decoder): o menor char da FAIXA presente no corpo.

A dedução só fecha quando o eleito é menor que todo char de FAIXA do dado — o que equivale a **`!` não estar no dado**. Medido, não assumido.

## Formatadas

| coluna | corpo | escapes | livres | eleito | deduzido | dedução | decisão | Δ corpo |
|---|---:|---:|---:|:-:|:-:|:-:|---|---:|
| `cpf` | 5700 | 1200 | 76 | `!` | `-` | **FALHA** | 0 | -1200 |
| `cnpj` | 5880 | 1059 | 75 | `!` | `!` | **bate** | 285 | -774 |
| `cartao` | 7186 | 1200 | 77 | `!` | `!` | **bate** | 8 | -1192 |
| `cep` | 3596 | 598 | 77 | `!` | `!` | **bate** | 2 | -596 |
| `telefone` | 5035 | 801 | 75 | `!` | `!` | **bate** | 301 | -500 |
| `ip` | 2078 | 256 | 77 | `!` | `.` | **FALHA** | 0 | -256 |
| `mac` | 978 | 18 | 71 | `!` | `0` | **FALHA** | 0 | -18 |
| `uuid` | 51 | 9 | 71 | `!` | `-` | **FALHA** | 0 | -9 |
| `data-iso` | 3478 | 487 | 76 | `!` | `!` | **bate** | 311 | -176 |
| `data-br` | 3176 | 514 | 76 | `!` | `!` | **bate** | 308 | -206 |
| `hora` | 3220 | 672 | 76 | `!` | `!` | **bate** | 189 | -483 |
| `timestamp` | 6628 | 1170 | 73 | `!` | `!` | **bate** | 360 | -810 |
| `moeda` | 3764 | 619 | 76 | `!` | `!` | **bate** | 90 | -529 |
| `coord` | 3895 | 588 | 76 | `!` | `-` | **FALHA** | 0 | -588 |
| `isbn` | 5538 | 1006 | 76 | `!` | `!` | **bate** | 305 | -701 |
| `placa` | 2978 | 583 | 52 | `!` | `!` | **bate** | 13 | -570 |
| `semver` | 2824 | 472 | 77 | `!` | `!` | **bate** | 315 | -157 |
| `sku` | 2996 | 299 | 51 | `!` | `!` | **bate** | 1 | -298 |
| `matricula` | 3503 | 150 | 78 | `!` | `0` | **bate** | 0 | -150 |

## Numéricas

| coluna | corpo | escapes | livres | eleito | deduzido | dedução | decisão | Δ corpo |
|---|---:|---:|---:|:-:|:-:|:-:|---|---:|
| `int-ordenado` | 12 | 1 | 86 | `!` | `0` | **bate** | 0 | -1 |
| `int-aleatorio` | 2659 | 300 | 78 | `!` | `0` | **bate** | 0 | -300 |
| `int-negativo` | 1590 | 276 | 77 | `!` | `-` | **FALHA** | 0 | -276 |
| `float` | 2953 | 594 | 77 | `!` | `.` | **FALHA** | 0 | -594 |
| `com-null` | 1595 | 254 | 78 | `!` | `!` | **bate** | 43 | -211 |

## Texto

| coluna | corpo | escapes | livres | eleito | deduzido | dedução | decisão | Δ corpo |
|---|---:|---:|---:|:-:|:-:|:-:|---|---:|
| `texto` | 1082 | 0 | 61 | `!` | `—` | — | recusa (0 esc) | +0 |
| `nomes` | 3300 | 0 | 36 | `!` | `—` | — | recusa (0 esc) | +0 |
| `email` | 3576 | 305 | 68 | `!` | `—` | — | recusa (305 esc) | +0 |
| `url` | 3326 | 424 | 67 | `!` | `!` | **bate** | 298 | -126 |
| `frase` | 9000 | 0 | 62 | `!` | `—` | — | recusa (0 esc) | +0 |

## Adversariais

| coluna | corpo | escapes | livres | eleito | deduzido | dedução | decisão | Δ corpo |
|---|---:|---:|---:|:-:|:-:|:-:|---|---:|
| `adv-usa-bang` | 3562 | 594 | 76 | `"` | `!` | **FALHA** | 23 | -571 |
| `adv-alfabeto-total` | 1827 | 261 | 0 | `—` | `—` | — | recusa (261 esc) | +0 |
| `adv-so-digitos` | 3000 | 300 | 78 | `!` | `0` | **FALHA** | 0 | -300 |
| `adv-sem-digitos` | 2700 | 0 | 62 | `!` | `—` | — | recusa (0 esc) | +0 |
| `adv-um-valor` | 12 | 1 | 83 | `!` | `1` | **FALHA** | 0 | -1 |
| `adv-unicode` | 3367 | 139 | 73 | `!` | `-` | **FALHA** | 0 | -139 |

## O que a dedução aguenta

- colunas em que a regra ATIVA o delimitador: **29 de 35**
- dedução do char recupera o eleito: **18 de 29** — falha em ['cpf', 'ip', 'mac', 'uuid', 'coord', 'int-negativo', 'float', 'adv-usa-bang', 'adv-so-digitos', 'adv-um-valor', 'adv-unicode']
- colunas sem nenhum char livre: **1** — ['adv-alfabeto-total']
- reconstrução byte-exata **e** RT pelo `decode` REAL: **70/70**

A condição exata (`!` ausente do dado) falha em **2** das 35 colunas: ['adv-usa-bang', 'adv-alfabeto-total'].

É por isso que a dedução **não pode ser a regra sozinha**: ela é uma otimização condicional, não um invariante. O caminho seguro é o marcador virtual decidir e a materialização escolher entre declarar e deduzir.

## V3 — o **caractere inicial**, que foi o que você propôs

O corpo **começa com o char eleito**. Ele se auto-declara pela posição — o mesmo idioma que o formato já usa (char de modo no índice 7, `0` cru para o slot nulo). O decoder lê o byte 0 e pronto: **nada no cabeçalho**.

```
#TCF.8!!               <- `!!` no fim do cabecalho: char + polaridade `L`
000.000.000-00
001.007.013-01
```

O prefixo **não precisa de linha própria** — cabe no fim da linha de cabeçalho, que já existe. Custo: **1 B** com polaridade `R`, **2 B** com `L` (char repetido). E, ao contrário da dedução por menor-char, ela **não depende do dado**:

- V3 reconstrói o corpo canônico lendo só o prefixo: **29 de 29** (todas)
- dedução por menor-char: **18 de 29**

A dedução por menor-char falha em casos onde V3 passa, e por dois motivos distintos que a tabela separa: o dado usa `!` (`adv-usa-bang`), **ou** o delimitador nunca é emitido no corpo (`cpf`, `ip`, `mac`, `uuid`, `coord`, `float`…) — e aí não há o que deduzir, e o decoder acabaria tratando um char de dado como troca. **Esse segundo motivo eu não tinha previsto**; era a maioria das falhas.

## As quatro materializações

| | cabeçalho | corpo | funciona sempre? |
|---|---:|---|---|
| **V0** `d<char><pol>` | 2 B | — | sim |
| **V1** `<pol>`, char por menor-char | 1 B | — | não (ver acima) |
| **V2** polaridade no 1º byte | 0 B | +1 B se pol=`L` | não (mesma dedução) |
| **V3** char inicial auto-declarante | **0 B** | +1 B (`R`) / +2 B (`L`) | **sim** |

| coluna | corpo+V0 | corpo+V1 | corpo+V3 | melhor |
|---|---:|---:|---:|:-:|
| `cpf` | 4502 | — | 4502 | **V0** |
| `cnpj` | 5108 | 5107 | 5108 | **V1** |
| `cartao` | 5996 | 5995 | 5996 | **V1** |
| `cep` | 3002 | 3001 | 3002 | **V1** |
| `telefone` | 4537 | 4536 | 4536 | **V1** |
| `ip` | 1824 | — | 1824 | **V0** |
| `mac` | 962 | — | 962 | **V0** |
| `uuid` | 44 | — | 44 | **V0** |
| `data-iso` | 3304 | 3303 | 3303 | **V1** |
| `data-br` | 2972 | 2971 | 2971 | **V1** |
| `hora` | 2739 | 2738 | 2739 | **V1** |
| `timestamp` | 5820 | 5819 | 5819 | **V1** |
| `moeda` | 3237 | 3236 | 3237 | **V1** |
| `coord` | 3309 | — | 3309 | **V0** |
| `isbn` | 4839 | 4838 | 4838 | **V1** |
| `placa` | 2410 | 2409 | 2410 | **V1** |
| `semver` | 2669 | 2668 | 2668 | **V1** |
| `sku` | 2700 | 2699 | 2700 | **V1** |
| `matricula` | 3355 | 3354 | 3355 | **V1** |
| `int-ordenado` | 13 | 12 | 13 | **V1** |
| `int-aleatorio` | 2361 | 2360 | 2361 | **V1** |
| `int-negativo` | 1316 | — | 1316 | **V0** |
| `float` | 2361 | — | 2361 | **V0** |
| `com-null` | 1386 | 1385 | 1386 | **V1** |
| `texto` | 1082 | 1082 | 1082 | hoje |
| `nomes` | 3300 | 3300 | 3300 | hoje |
| `email` | 3576 | 3576 | 3576 | hoje |
| `url` | 3202 | 3201 | 3201 | **V1** |
| `frase` | 9000 | 9000 | 9000 | hoje |
| `adv-usa-bang` | 2993 | — | 2993 | **V0** |
| `adv-alfabeto-total` | 1827 | 1827 | 1827 | hoje |
| `adv-so-digitos` | 2702 | — | 2702 | **V0** |
| `adv-sem-digitos` | 2700 | 2700 | 2700 | hoje |
| `adv-um-valor` | 13 | — | 13 | **V0** |
| `adv-unicode` | 3230 | — | 3230 | **V0** |

Ganho somado com V0 (2 B de cabeçalho): **-11674 B**  
Ganho somado com V3 (auto-declarante): **-11681 B**  
— em 35 colunas de 300 linhas.

A diferença entre V0 e V3 é de **0-1 byte por coluna**. Numa coluna de 300 linhas isso é ruído; num payload minúsculo de poucas linhas, não é. A escolha entre elas é a mesma conta de sempre, não uma preferência — e o marcador virtual é justamente o que permite trocar de materialização sem mexer em nada antes dela.

## O que a estrutura diz

```
varredura unica ->  tokens virtuais  +  alfabeto  +  trocas_R  +  trocas_L
                         |                |            |           |
decisao         ->       |          char eleito    <-- min(...) -->
materializacao  ->  resolve(tokens, char, pol)   <- unica fase que ve o char
```

O marcador virtual permite adiar a decisão até o fim **e** trocar a materialização sem tocar em nada antes dela. A dedução vira uma escolha de materialização, não uma propriedade do formato — que era o ponto.


# Polaridade do escape — literal x referência (2026-07-25-2337)

`NORMAL` = hoje (`\168116` literal · `1` referência). `FLIP` = invertido (`168116` literal · `\1` referência).

A troca **deveria** ser uma involução (`normal → flip → normal` = identidade). Onde não é, o flip é **inexpressável** — ver a seção de adjacência.

| id | corpo NORMAL | corpo FLIP | Δ | adjacências ambíguas | flip é seguro? |
|---|---:|---:|---:|---:|---|
| `A-ruido1e6-n1000` | 7854 | 6856 | **-998** | 0 | sim |
| `A-ruido1e6-n100` | 793 | 693 | **-100** | 0 | sim |
| `A-cpf-like-n200` | 3800 | 3000 | **-800** | 0 | sim |
| `A-uuid-hex-n200` | 2663 | 2200 | **-463** | 0 | sim |
| `A-precos-n200` | 1175 | 1027 | **-148** | 0 | sim |
| `B-datas-n200` | 1110 | 1131 | **+21** | 74 | **NAO** |
| `C-emails-n200` | 2095 | 2316 | **+221** | 0 | sim |
| `C-texto-n200` | 718 | 743 | **+25** | 0 | sim |
| `D-seq-n1000` | 31 | 28 | **-3** | 0 | sim |
| `D-ruido0a9-n1000` | 3104 | 3094 | **-10** | 0 | sim |

## Leitura

- **7 de 10** colunas ficam menores com o FLIP; **2** ficam maiores.
- ganho somado onde ganha: **2522 B** · perda somada onde perde: **-246 B**
- **1 coluna(s) NÃO podem ser flipadas** com este esquema (adjacência ambígua, abaixo)

As colunas que **perdem** (emails, texto sem dígito) são a razão de isto não poder virar default novo — tem que ser **decisão por coluna**, um `min()` como os outros. É exatamente o que o owner descreveu: *o que tiver mais, troca*.

## Parte 2 — o guia no cabeçalho basta sozinho?

Hipótese testada: *as colunas onde o flip ganha talvez não tenham a adjacência ambígua*. Se valesse, o flag no header resolveria tudo.

**REFUTADA.** Varredura de 15 formas × 3 tamanhos:

| forma | n | ganho bruto | adjac. | ganho c/ delimitador | decisão |
|---|---:|---:|---:|---:|---|
| int-ruido | 50 | +50 | 0 | **+50** | FLIP |
| int-ruido | 200 | +200 | 0 | **+200** | FLIP |
| int-ruido | 1000 | +998 | 0 | **+998** | FLIP |
| int-pequeno | 50 | +40 | 0 | **+40** | FLIP |
| int-pequeno | 200 | +85 | 0 | **+85** | FLIP |
| int-pequeno | 1000 | +100 | 0 | **+100** | FLIP |
| seq | 50 | +2 | 0 | **+2** | FLIP |
| seq | 200 | +3 | 0 | **+3** | FLIP |
| seq | 1000 | +3 | 0 | **+3** | FLIP |
| data-iso | 200 | +85 | 117 | **-32** | normal |
| data-br | 50 | +24 | 14 | **+10** | FLIP |
| data-br | 200 | +154 | 105 | **+49** | FLIP |
| ip | 50 | +200 | 0 | **+200** | FLIP |
| ip | 200 | +256 | 0 | **+256** | FLIP |
| ip | 1000 | +256 | 0 | **+256** | FLIP |
| telefone | 50 | +135 | 13 | **+122** | FLIP |
| telefone | 200 | +422 | 119 | **+303** | FLIP |
| telefone | 1000 | +1247 | 910 | **+337** | FLIP |
| moeda | 50 | +8 | 47 | **-39** | normal |
| moeda | 200 | +381 | 18 | **+363** | FLIP |
| moeda | 1000 | +1582 | 363 | **+1219** | FLIP |
| sku | 200 | +76 | 78 | **-2** | normal |
| hex | 50 | +120 | 0 | **+120** | FLIP |
| hex | 200 | +485 | 0 | **+485** | FLIP |
| hex | 1000 | +2398 | 0 | **+2398** | FLIP |
| ts | 50 | +26 | 1 | **+25** | FLIP |
| ts | 200 | +100 | 0 | **+100** | FLIP |
| ts | 1000 | +500 | 0 | **+500** | FLIP |
| versao | 50 | +66 | 21 | **+45** | FLIP |
| versao | 200 | +229 | 66 | **+163** | FLIP |
| coord | 50 | +94 | 0 | **+94** | FLIP |
| coord | 200 | +390 | 0 | **+390** | FLIP |
| coord | 1000 | +1966 | 0 | **+1966** | FLIP |

**33 colunas ganhariam** com o flip puro, e **13 delas têm adjacência ambígua** — o header sozinho não fecha.

Com um **delimitador de 1 B** em cada posição ambígua: **30 ainda ganham**, 3 deixam de ganhar. E essas 3 o `min()` rejeita sozinho, materializando as duas polaridades e emitindo a menor — o mesmo padrão do FLOOR do seq-RLE.

Ou seja: **existe esquema não-ambíguo** (guia no header + delimitador na adjacência) e ele **sobrevive economicamente** — os ganhos grandes (hex, coord, moeda, telefone) atravessam o custo do delimitador.

## Lado a lado — as duas polaridades

```
A-ruido1e6-n100
  normal: '\\168116' …
  flip  : '168116' …
C-texto-n200
  normal: 'palavra*a' …
  flip  : 'palavra*a' …
```


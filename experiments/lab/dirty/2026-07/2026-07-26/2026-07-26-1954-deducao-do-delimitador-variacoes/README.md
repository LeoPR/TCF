# 2026-07-26-1954 — Dedução do delimitador, 35 variações

> *"se a gente eleger um caractere inicial para ligar com essa ambiguidade ela também não
> precisa ser declarada. ou seja a marcação existe em estrutura interna, a gente pode usar até
> isso como dedução pra saber onde tem ou não."*

A sua ideia funciona — **29 de 29**. A minha, de deduzir o char pelo menor da faixa, **não**:
18 de 29. E o motivo da maioria das falhas eu não tinha previsto.

## As duas regras testadas

| | como | resultado |
|---|---|---|
| **dedução por menor-char** | o delimitador é o menor char da FAIXA presente no corpo | **18/29** |
| **V3, caractere inicial** | o char fecha a linha de cabeçalho e se auto-declara pela posição | **29/29** |

```
#TCF.8d!L            V0 — declarado: `d` + char + polaridade      (2 B)
#TCF.8!!             V3 — auto-declarante: char, dobrado = pol L  (2 B)
#TCF.8!              V3 — polaridade R                            (1 B)
```
(`outputs/cpf-wire-V0-declarado.tcfp` × `outputs/cpf-wire-V3-autodeclarante.tcfp`)

O prefixo **não precisa de linha própria** — cabe no fim da linha de cabeçalho, que já existe.
É o idioma posicional que o formato já usa: char de modo no índice 7, `0` cru para o slot nulo.

## Por que a dedução por menor-char falha — e o motivo que eu não previa

Eu previa **um** modo de falha: o dado usar `!`. Isso acontece em **1** coluna
(`adv-usa-bang`, construída de propósito).

O outro modo, que era a **maioria** das falhas: quando o delimitador **nunca é emitido no
corpo** — polaridade escolhida certa, zero transições — **não há o que deduzir**, e o decoder
acabaria elegendo um char de dado (`-`, `.`, `0`) e tratando-o como troca. É o caso de `cpf`,
`ip`, `mac`, `uuid`, `coord`, `float`, `int-negativo`, `adv-so-digitos`, `adv-um-valor`,
`adv-unicode` — exatamente as colunas onde o ganho é **maior**.

V3 não tem esse problema porque não deduz do conteúdo: lê a posição.

## As 35 colunas

**Formatadas (19)** — cpf, cnpj, cartao, cep, telefone, ip, mac, uuid, data-iso, data-br,
hora, timestamp, moeda, coord, isbn, placa, semver, sku, matricula
**Numéricas (5)** — int-ordenado, int-aleatorio, int-negativo, float, com-null
**Texto (5)** — texto, nomes, email, url, frase
**Adversariais (6)** — usa-bang, alfabeto-total, so-digitos, sem-digitos, um-valor, unicode

| resultado | |
|---|---|
| colunas em que a regra ATIVA o delimitador | **29 de 35** |
| colunas sem nenhum char livre | **1** (`adv-alfabeto-total`, construída para isso) |
| reconstrução byte-exata **e** RT pelo `decode` REAL | **70/70** |
| ganho somado (V3) | **−11681 B** em 35 colunas de 300 linhas |

As 6 que não ativam recusam sozinhas e caem no comportamento de hoje: 4 por não ter dígito
literal a economizar (`texto`, `nomes`, `frase`, `adv-sem-digitos`), 1 por transições ≥
escapes (`email`), 1 por não ter char livre (`adv-alfabeto-total`).

## Onde os ganhos estão

| coluna | corpo | escapes | decisão | Δ |
|---|---:|---:|---|---:|
| `cpf` | 5700 | 1200 | 0 transições | **−1200** |
| `cartao` | 7186 | 1200 | 8 | **−1192** |
| `timestamp` | 6628 | 1170 | 360 | **−810** |
| `cnpj` | 5880 | 1059 | 285 | **−774** |
| `isbn` | 5538 | 1006 | 305 | **−701** |
| `coord` | 3895 | 588 | 0 | **−588** |
| `float` | 2953 | 594 | 0 | **−594** |
| `email` | 3576 | 305 | recusa | 0 |
| `frase` | 9000 | 0 | recusa | 0 |

## A diferença entre materializações é ruído — e isso importa

V0 (2 B), V1 (1 B, não confiável) e V3 (1-2 B, sempre válido) diferem em **0-1 byte por
coluna**. Numa coluna de 300 linhas é ruído; num payload minúsculo de poucas linhas, não é.

O ponto estrutural é outro: **o marcador virtual permite trocar de materialização sem tocar em
nada antes dela**. A dedução vira uma escolha de materialização, não uma propriedade do
formato.

```
varredura unica ->  tokens virtuais  +  alfabeto  +  trocas_R  +  trocas_L
decisao         ->             char eleito   <-- min(...) -->
materializacao  ->  resolve(tokens, char, pol)   <- unica fase que ve o char
```

## Limites

- **Nada soldado.** `src/tcf` intocado.
- Colunas **sintéticas** por LCG, 300 linhas cada. Ainda **falta a escala maior com
  variedade** que você pediu para depois — inclusive dado real (o lab `1913` já usou 3 colunas
  reais; aqui não).
- V3 assume que o cabeçalho tem um slot posicional para o char. A gramática desse slot não foi
  fechada; o `#TCF.8!` é notação do lab.
- `adv-alfabeto-total` prova que existe coluna sem char livre. A regra recusa, mas a saída
  alternativa (escapar o próprio delimitador) **não foi medida**.
- Estado da polaridade reseta por linha (mantém a linha auto-contida).
- Não medi o que acontece se o delimitador virar grafia **canônica** — o seq-RLE ainda
  localiza o dígito incrementável pelo escape. Continua aberto desde o lab `1913`.

## Rodar

```
python run.py
```
`deducao.py` tem o marcador virtual, a eleição, as duas deduções e as duas direções.

# Namespace do `<modo>` — larguras (funciona) + subtipos (preparado) [design / consolidação]

**Data**: 2026-07-24 03:22. Fecha a escolha do marcador (`~<modo>` vence o G2 marker-free do lab
`0253`) e **alinha** o modo tipado com dois designs JÁ registrados: o sub-namespace bN e o mecanismo de
índices especiais. Direção do owner: *"focar no que funciona e deixar apenas a parte que cuida disso
preparada pra mapear outros subtipos pra aproveitar espaço."*

## O `~` NÃO é necessário (correção 2026-07-24, pergunta do owner)

**Revisão da 1ª versão desta nota** (que dizia "`~<modo><n>` é a forma certa porque o namespace é
load-bearing"): o namespace É load-bearing, mas **não exige o `~`**. O disambiguador é o próprio
**char de `<modo>`, posicional no índice 7** (logo após a tag) — mesmo mecanismo do G2, generalizado:

```
#TCF.8b\n<corpo>            → índice 7 = '\n'  → CORE  (implícito, default)
#TCF.8b<modo><n>\n<base64>  → índice 7 = modo → DENSO (o char já diz QUAL modo)
```

O índice 7 é `\n` (core) OU um char de modo (denso) — **disjuntos por construção** (o encode sempre põe
`\n` ali no core; o namespace de `<modo>` exclui `\n`). O char de modo faz **duplo papel**: sinaliza
"denso" E carrega qual (largura `1/2/4/8` ou subtipo). **Nenhum separador dedicado é preciso.**

**O `~` compra só LEGIBILIDADE** (separador visual ao abrir num editor: `#TCF.8b~4123` vs `#TCF.8b4123`)
ao custo de +1 byte/denso. É decisão de gosto — **não função**. Ambos (com ou sem `~`) são gramática
válida; o namespace do `<modo>` (abaixo) independe dessa escolha.

**Decisão pendente do owner** (agora reduzida a legibilidade × 1 byte): manter `~` (legível, +1B) ou
colar `<modo>` na tag (mais denso). O default sensato pra payload minúsculo = **sem `~`** (colado).

## FECHADO — o `~` é FUNÇÃO INTERNA de detecção, não caractere de wire (owner 2026-07-24)

Insight do owner: um "caractere de desambiguação" é, na verdade, o **nome de uma etapa de validação
que o parser roda de qualquer forma**. Pra decodar `b333`, o parser JÁ tem que perguntar "o que vem
após a tag?" — e essa pergunta É a desambiguação. Logo o `~` não acrescenta nada ao wire: ele é
redundante com a validação posicional que já existe. **Vive só no código** (flag/conceito interno),
**nunca no arquivo** — a menos que ajude (legibilidade), o que pra payload minúsculo não vale.

**Condição de "formato forte" (quando o `~` pode ser interno-só)** — a dispatch posicional é inambígua
em TODOS os casos SOB 3 invariantes:
1. **tag = exatamente 1 char** (índice 6): `\n`→`[]` · `M`→multi · `H`→hier · ` `→spec · `b/n/s`→tipado.
2. **modo = exatamente 1 char** (índice 7, no tipado): `\n`→core · char-de-modo→denso.
3. **namespace de modo exclui `\n`**; `n`≥1 dígito termina no `\n`; base64 vem depois.

Sob os 3, `#TCF.8b4123\n<b64>` → tag=`b`, modo=`4`, n=`123` — inambíguo, sem separador. **Único
cenário que reabriria um char no wire**: subtipo futuro com código de modo MULTI-char (quebra a
invariante 2) → aí um delimitador/length-prefix volta, mas por escolha consciente. Enquanto modo = 1
char, o `~` é interno pra sempre.

**Portanto o wire canônico do #4 NÃO tem `~`**: `#TCF.8<tag><modo><n>\n<base64>` (denso) ·
`#TCF.8<tag>\n<corpo>` (core). O `~` fica como conceito de código/doc, não como byte.

## O namespace do `<modo>` (recall + consolidação)

Sub-namespace bN já registrado (registry de chars, owner 2026-07-08): `b1/b2/b4` = **largura física**
(1/2/4 bits, únicas que tile-de-byte) · `b3` = trio "b2+null" · `b5/b6/b7` = especiais reservados ·
`B` = bool+dict interno. Consolidando no `<modo>`:

| `<modo>` | significado | estado |
|---|---|---|
| `1` `2` `4` `8` | **LARGURA física** (bits/símbolo). É o bN puro. | **FUNCIONA — entra no weld** |
| (ausente) | core/text (default, sem `~`) | já é o default |
| letras / outros dígitos | **SUBTIPOS** mapeados (gênero M/F, enums internos, null, NaN, ±Inf) | **PREPARADO, não construído** |

O `<modo>` é 1 char extensível: hoje ele carrega largura; amanhã, uma letra aponta pra um **subtipo
registrado** sem rework de gramática.

## O hook de subtipos — mecanismo de ÍNDICES ESPECIAIS (recall)

O "mapear subtipos pra aproveitar espaço" JÁ tem mecanismo desenhado
([substituicao-indices-especiais-plano](substituicao-indices-especiais-plano.md), refutação de
"null=índice-stringificado" já corrigida):

- A tabela de refs da coluna **nasce PRÉ-SEMEADA** com especiais nos índices 0..k−1 (não é "if null
  desloca" — a tabela já começa preenchida; menos lógica, não mais).
- Um **byte combinatório no header** declara QUAIS especiais estão reservados → até 8 (null, ausência,
  NaN, ±Inf, + reservados) em ordem canônica.
- No corpo, um especial é **referência ao índice reservado** (sentinela NÃO-string → sem colisão com a
  string real `"null"`). decode: ref a índice reservado → materializa (0 → `None`).
- **null/true/false = a MESMA natureza** (Ciclo 2): índice → valor Python tipado (0→None, 1→True,
  2→False); a string SAI do arquivo e vive no dicionário da VERSÃO (freeze 1.0). É o que torna lossless.
- Sua lembrança confere: **índice 0 = null SE houver declaração de null no header** (o byte combinatório).

## Escopo do weld #4 (o que funciona) vs o que fica preparado

**Entra agora (funciona):**
- Header tipado `#TCF.8<tag>` + modo denso `~<modo><n>` com `<modo>` ∈ {1,2,4,8} = largura.
- Os dois algoritmos de corpo (core/RLE default, denso bN) competindo no FLOOR.

**Fica PREPARADO (estrutura extensível, não construída — evita lixo pra limpar depois):**
- O `<modo>` como **namespace de 1 char** — o parser lê o char e despacha; hoje só reconhece larguras,
  mas o ponto de despacho é o hook pros subtipos.
- O **stream de refs empacotável por bN** desacoplado do encoding físico (hook do `.9`, Ciclo 2).
- A **tabela de reservados extensível** (null primeiro; true/false/NaN depois, sem rework).
- O **byte combinatório de especiais no header** — projetado, weld só quando o subtipo for exercido.

**NÃO entra**: os subtipos em si (gênero, enums, NaN, ±Inf), o dicionário-de-versão, o preditor
estatístico do modo. Tudo com dono-de-decisão no `.9` (ticket
[T-TYPED-SINGLECOL-MODE-HEURISTIC](../../../../tickets/T-TYPED-SINGLECOL-MODE-HEURISTIC.md)).

## Princípio (owner, reafirmado 3×: 2026-07-15 e 2026-07-24)

**Fazer funcionar, deixar preparado, não otimizar prematuramente.** A parte que "cuida disso" = o
ponto de despacho do `<modo>` + os hooks acima; o resto é `.9`.

Relaciona: lab [`0253`](../../2026-07/2026-07-24/2026-07-24-0253-cicloB-gramatica-marcador-modo-inferivel/)
· [registry de chars](tcf8-header-char-registry.md) · [índices especiais](substituicao-indices-especiais-plano.md)
· [camada explícita↔implícita](2026-07-24-0100-camada-explicita-vs-implicita-fecha-cicloA.md) ·
plano `.8` §S3.

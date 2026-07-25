# 2026-07-24-2210 — null como índice 0 numa coluna de string

Escala do owner: **uma coluna de UM tipo**. `[null, "", "true", "false", "oi", null, "null"]`
é uma coluna de **string** onde null é um token válido — a falta do dado, não outro tipo.

| | hoje | protótipo |
|---|---|---|
| envelope | **expulsa pro `.8H`** (porque `None` não é `str`) | **fica no flat `#TCF.8`** |
| null | máscara def-level num canal `?` | referência ao **índice 0** (tabela pré-semeada) |

```
coluna : [None, '', 'true', 'false', 'oi', None, 'null']
hoje   : '#TCF.8H#V\z#:3?:14[\n\7\n\0\n*4|.\n^1\n^2\n\ntrue\nfalse\noi\nnull\n'   57 B
proto  : '#TCF.8\n0\n\ntrue\nfalse\noi\n0\nnull\n'                                  31 B
```

## Grafia (revisada pelo owner)

O `0` cru é a **representação otimizada de `^0`** — logo herda a semântica dele: **endereço
RESERVADO que NÃO declara nó**. Assim **todo** null é `0` (1 char). A 1ª rodada tinha o `0`
declarando um nó, o que fazia o 2º null virar `^1` — grafia inconsistente e mais cara. Medido:
**−479 B** em 17 casos contra a forma que declarava.

**Desambiguação POSICIONAL** (mesma classe do char de modo no índice 7): a **linha inteira**
igual a `0` é o especial. Um `0` DENTRO de composição (`1~0`, `0..3`) continua no espaço de
FRAGMENTO e não vira null — então a classe absurda "compor uma string com null" permanece
**inexprimível**, que era a única objeção real ao dígito nu.

**Caça a colisões**: **1179 colunas** com vocabulário adversarial (`"0"`, `"00"`, `"01"`,
`"10"`, `"-0"`, `"0.0"`, `"000"`, `"^0"`, `"\0"`, `"*2|0"`, `"0~0"`, vazia) em singleton,
pares, trios, repetição (RLE) e intercalado → **0 linhas `0` emitidas pelo encoder, 0 RT
quebrado**. A string `"0"` é sempre escapada como `\0` e a tabela de fragmentos é 1-based: o
slot está livre. Ver `colisao-e-grafia-final.py` / `result-grafia-final.md`.

## Resultado

**RT 17/17** (hoje E protótipo, os dois validados) · **Δ mediano −33%** · controle sem-null
**byte-idêntico** ao flat (quem não tem null não paga nada).

Ganho por regime: cresce com a densidade de null (−4% em 1%, −36% em 50%) e é maior em **n
pequeno** (−46% no exemplo do owner, 7 elementos) — o regime de payload minúsculo.

## O achado que importa (auto-adversarial)

Decompus o ganho: **84% vem do ENVELOPE, 16% do índice**. A parcela do índice cresce com a
densidade de null (a grafia `0` faz todo null custar 1 char) — +249 B em `R-n1000-p50`.

Mas a forma que captura a maior parte sem o índice — deixar null virar o **literal** `"0"` — é
**inviável**: colide com a string real `"0"`, não é lossless. Foi exatamente por isso que o
lab `2026-07-13-1921` refutou "null = índice" (ele **stringificava**).

> **O índice reservado não GERA o ganho — ele o VIABILIZA.** Ele é o que torna possível manter
> a coluna no flat sem perder a distinção `null` ≠ `"null"`.

Isso também reposiciona o alvo: o custo real do null hoje **não é a máscara** (ela é barata e
comprime bem — medido no levantamento: +3% em n=1000). É **a expulsão da coluna para o
`.8H`**, cujo envelope é projetado para estrutura aninhada e tipos mistos, generalidade que
uma coluna de string com nulls não usa.

## Índice 0 está livre — verificado

A string literal `"0"` é escapada pelo core como `\0`. Então um `0` puro no corpo **nunca é
literal — é sempre referência**, e a tabela de fragmentos começa em 1. O slot 0 está vago nos
dois espaços de referência.

## Arquitetura do protótipo

Segue o modelo do owner (camada explícita ↔ implícita): o decoder é um **pré-avaliador** que
expande `0` (implícito) para a forma explícita e delega ao **core REAL, intocado**. Por isso o
RT é fiel — não há reimplementação do compressor aqui.

O encode usa o mesmo truque ao contrário: passa a coluna pro `encode` real com null → `"0"`,
e troca a **declaração** `\0` por `0`. Isso preserva a numeração `^N` exatamente — o nó
continua sendo o mesmo nó (visível no exemplo: o 2º null virou `^1` sozinho).

## Limites desta medição (declarados)

1. **A restrição de colisão é do PROTÓTIPO, não do design.** Aqui a coluna não pode conter a
   string `"0"` (o placeholder é textual). O design real usa **sentinela não-string
   pré-semeada na tabela**, então não tem essa restrição — a reserva é posicional, não por valor.
2. **Parte do ganho de envelope é especialização.** O `.8H` também compra generalidade
   (aninhamento, tipos mistos) que esta coluna não usa. A conclusão honesta é "o `.8H` é
   exagero para uma coluna tipada com nulls", não "o `.8H` é ineficiente".
3. **`R-n10-p1` e `R-n10-p10` saíram com 0 nulls** — o LCG não produziu nenhum nessa
   densidade com n=10. As linhas continuam válidas (viraram controles extras de
   byte-identidade), mas não medem o que o rótulo sugere.
4. **Uma coluna só, tipo string.** Multi-coluna, tipos numéricos, NaN/±Inf e ausência (`-`)
   estão fora — ver o levantamento.

## Rodar / layout

```
python run.py     # 17 casos: hoje vs protótipo + decomposição envelope/índice
```
`inputs/*-fonte.json` · `intermediates/*-dataset-consumido.json` ·
`outputs/*-hoje.tcf` (REAL) + `*-proto.tcfp` (protótipo) + `*.roundtrip.json` · `result.md`.

**Não toca `src/tcf`.** Levantamento:
[`2026-07-24-2140-levantamento-null-e-tipos.md`](../../notas/2026-07/2026-07-24-2140-levantamento-null-e-tipos.md).

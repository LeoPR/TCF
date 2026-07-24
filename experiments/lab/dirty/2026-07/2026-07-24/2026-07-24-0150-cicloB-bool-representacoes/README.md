# 2026-07-24-0150 — Ciclo B: bool completo (cada representação + a combinação)

Primeiro ciclo de TIPO do [plano `.8`](../../../notas/2026-06/tcf8-estrutura-plano.md) §9 (Ciclo B),
começando pelos booleanos. Segue o fluxo de dados real (fonte→dataset→wire→roundtrip) e o
[modelo camada-explícita↔implícita](../../../notas/2026-07/2026-07-24-0100-camada-explicita-vs-implicita-fecha-cicloA.md).

**GATE do owner**: a tipagem tem que voltar — **bool volta bool**, não a string `"true"`. Economia é
de moldura, nunca de semântica. Toda representação é medida com **RT-tipado**.

## Representações (todas hipotéticas exceto `atual`)

- **atual** — `encode(dataset)` REAL: hoje bool[N] vira envelope `.8H` só pra preservar o tipo.
- **typed** — `#TCF.8b` + corpo do CORE (reusa o flat: seq-RLE p/ runs). = "typed **com RLE**".
- **bN** — modo denso: bit-pack (1 bit/elem) → base64.
- **misto** — modo misto: segmentação adaptativa RLE+denso (**a combinação**).
- **FLOOR** — `min(typed, bN, misto)`: nunca-pior por construção.

## Resultado (9 perfis · RT-tipado 9/9 ✅)

| perfil | atual | typed | bN | misto | **FLOOR** | vencedor |
|---|---:|---:|---:|---:|---:|:---:|
| all-true / all-false | 33–35 | 17–18 | 25 | 15 | **15** | misto (RLE 1 seg) |
| runs | 50 | 33 | 25 | 26 | **25** | bN |
| alt | 223 | 205 | 25 | 26 | **25** | bN |
| p10 / p50 / p90 | 77–181 | 60–163 | 25 | 26 | **25** | bN |
| n1 | 28 | 13 | 16 | 17 | **13** | typed |

**Cada representação tem seu regime**: `typed`/RLE esmaga runs e constantes; `bN` (denso, fixo 25 B) ganha
na alternância/ruído; `misto` só compensa em heterogêneo genuíno. O `atual` (.8H) perde para todos —
confirma a oportunidade do header tipado (#4). E o **FLOOR combina** sem precisar de limiar.

## Sob gzip — a escolha é ESTÁVEL (9/9)

O vencedor do FLOOR é o **mesmo raw e sob gzip** em todos os perfis. O `bN` é ~incompressível e o
`typed`/texto tem redundância que o gzip come, então o *gap* encolhe muito — mas a **decisão de modo
não inverte**. A decisão pré-transporte é robusta ao gzip pra bool (gzip = lente, não critério).

## Homógrafos — o tipo mantém distintos (§S2)

`[True,False]` (bool, `.8H` hoje) · `["true","false"]` (string, órfão) · `[1,0]` (number, `.8H`) —
mesma superfície textual, **3 datasets**, RT preserva o tipo. A forma `#TCF.8b` seria a marca que
distingue bool de string homógrafa num único char.

## O que este ciclo NÃO conclui

Não escolhe a gramática/modo final nem mede em N grande ou dados reais. As formas typed/bN/misto são
protótipos (o header `#TCF.8b`/modos `~d`/`~x` é hipótese — o #4 ainda não foi soldado). Faltam null,
canal de exceção e a paridade M/H. **Nada em `src/tcf`.**

## Rodar / layout

```
python run.py     # 9 perfis + gzip + homógrafos · RT-tipado 9/9
```
`inputs/*-fonte.json` · `intermediates/*-dataset-consumido.json` · `intermediates/*.tcfp` (hipóteses)
· `outputs/*-wire.tcf` (REAL) · `result.md`.

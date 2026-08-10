# Resultado — a bateria multi-vetor: um win-win, dois trades, um teto no caminho

**2026-08-09 · dirty · bytes × CPU (intercalado, mediana de 5) × memória (tracemalloc) ×
online-ness (estrutural) · RT verde em todos os candidatos de todos os casos.
Números em [`outputs/bateria.json`](outputs/bateria.json).**

Regra de decisão aplicada (do owner, agora em memória permanente): **win-win vira
default; trade-off vira UM default + a melhor versão de cada qualidade.** Nada aqui é
`.8`; a raiz (nós de proximidade no OBAT) está registrada como 2.0 com vontade de fazer
logo (`T-OBAT-NOS-PROXIMIDADE`).

## A tabela de decisão

| encaixe | bytes | CPU | memória | online | veredito |
|---|---|---|---|---|---|
| **SPEC mensal (A4)** | 679→**34** (20×) | **39,8→19,1 ms (2× mais RÁPIDO)** | igual | igual | **WIN-WIN-WIN → default por mérito** quando o weld vier |
| **E2 sem-dedup** | cíclicos **10×** (423→42; 321→30; 4024→43) | candidato custa **+84–93% do encode** | ~igual | igual (mesma gramática) | **trade → variante**, não default |
| **E1 split na flat** | mensal −35%; úteis −63% | **+47–54% sempre** | +285 KiB | **PERDE** (corpo por coluna-campo) | **trade duplo → variante/perfil** |

## O achado que muda a leitura: o spec mensal é o único win-win — e é win em CPU

O A4 (`mês×31+dia`) não só esmaga os bytes: **corta o encode pela metade** (39,8 → 19,1
ms). O motivo é estrutural — a coluna transformada colapsa para um marcador, então o
corpo, o FLOOR e os candidatos todos trabalham sobre quase nada. A semântica barata na
borda *economiza* o trabalho cego do núcleo.

Isso fecha a decisão do owner ("data ser spec mesmo") com o multi-vetor inteiro a favor:
o weld dos specs mensais não precisa de flag, perfil nem gate — é melhor em tudo.

## E2 — encoder-only, mas não é de graça

A sonda provou que o corpo sem-dedup **já decodifica hoje** (mesma gramática,
linha-a-linha): o E2 é weld de encoder, sem formato novo. Os bytes são 10× nos cíclicos —
mas o candidato custa quase **um encode inteiro a mais** (+84–93%), porque constrói e
compacta um segundo corpo. E o FLOOR já é 58% do encode.

Pela regra: **variante** (perfil `compacto`, ou flag de mecanismo do
`T-FORCAR-MECANISMO-PARAM`), com promoção a default condicionada ao `T-GATES-ANTES`
baratear o caminho. Gate natural quando virar variante: só tentar em coluna toda-dígito.

## E1 — dois motivos independentes para não ser default

1. **CPU**: +47–54% do encode, *sempre* (o candidato é materializado pra competir mesmo
   quando perde, como no diário).
2. **Online-ness**: o corpo do split é um **multi-col embutido** (`#TCF.8M` interno,
   blocos por coluna-campo) — a primeira linha completa exige ler até o bloco do último
   campo. Não streama por linha. É a classe do modo `C` do bN, e o precedente ADR-0036 já
   decidiu o que fazer com essa classe: **decodável, não emitido por default, opt-in de
   emissão**.

Pela regra: **variante/perfil** (`compacto`/`lote`). O ganho existe (−35%/−63% onde
vence) e fica disponível para quem declarar que não precisa de streaming.

## O teto que apareceu no caminho: `MAX_PERIODO = 24` barra o calendário

O `dia-ciclico-k28` só melhorou 2,3× (523→227) porque o período 28 **excede o teto 24**
do detector periódico — e 28/29/30/31 são exatamente os períodos naturais de calendário.
O ciclo completo daria ~70 B. Subir o teto para **31** custa +7 iterações no laço O(n·P)
e cobriria a família inteira. Registrado como `T-MAX-PERIODO-31` — weld de 1 linha,
**aguarda aprovação** (mexe em `src/tcf`).

## Controles (o floor segue protegendo)

- E2 no dígito-sem-ordem: perde (333→2369) e o atual fica. ✓
- E1 no diário: perde (414→821) e o atual fica. ✓
- Deltas negativos no periódico: `*600~1,…,1,-11|\01` decodifica hoje. ✓

## O que vai pro 1.0, em uma linha cada

1. **Specs mensais (A4+A2f+YM)**: weld candidato, default por mérito — win-win-win.
2. **E1 e E2**: variantes da família perfis (`T-PERFIS-MACRO`), não defaults.
3. **`T-MAX-PERIODO-31`**: 1 linha, aguarda OK.
4. **Nós de proximidade no OBAT**: 2.0, vontade registrada.

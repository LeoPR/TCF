---
title: T-TYPED-SINGLECOL-MODE-HEURISTIC — single-col tipado + modos de corpo (heurística p/ .9)
status: open
priority: P2
created: 2026-07-24
updated: 2026-07-24
blocked-by: []
related:
  - experiments/lab/dirty/notas/2026-07/2026-07-24-0100-camada-explicita-vs-implicita-fecha-cicloA.md
  - experiments/lab/dirty/2026-07/2026-07-24/2026-07-24-0150-cicloB-bool-representacoes/
  - experiments/lab/dirty/2026-07/2026-07-23/2026-07-23-1759-bn-lowcard-generaliza-e-compoe/
  - tickets/T-OPT-INFERENCE.md
---

# T-TYPED-SINGLECOL-MODE-HEURISTIC

**[dispositivo]** Header single-col tipado (`#TCF.8<tag>`, weld #4) com **dois algoritmos de corpo
preparados e postos pra funcionar**, escolhidos por uma **heurística razoável** (FLOOR/`min`), e o
refino da heurística **anotado pra o `.9`**.

## Direção do owner (2026-07-24)

> "O importante é ter os dois algoritmos preparados e uma heurística razoável pra aplicar. O mais
> importante é que ele tem POSSÍVEIS ganhos, não precisa ter todos — isso pode ser otimizado depois.
> É importante que TEM possibilidades, não que os ganhos sejam em 100% das vezes. Podemos deixar os
> algoritmos preparados e colocados pra funcionar; no `.9` deixamos anotado pra fazer uma verificação
> mais rigorosa, seja determinística ou com estatística mais robusta."

## O que entra AGORA (weld #4)

- **Header tipado** `#TCF.8<tag>` (whitelist fechada `{b,n,s}`), pré-avaliador na borda
  (implícito→explícito; core de coluna intocado).
- **Dois algoritmos de corpo**, ambos funcionando:
  - **A · core/text** — reusa `_encode_column` (traz seq-RLE/aliases de graça). Ganha em runs/constante.
  - **B · denso bN** — bit-pack (w=`ceil(log2 k)`) → base64. Ganha em alta entropia.
- **Heurística = FLOOR/`min`** (nunca-pior por construção). Compete os candidatos + o `.8H` atual;
  emite o menor. Não precisa acertar 100% — só nunca piorar e capturar os ganhos POSSÍVEIS.

## O que fica pro `.9` (este ticket)

- **Verificação rigorosa da heurística**: hoje é `min()` materializando os candidatos. No `.9`, avaliar:
  1. **preditor determinístico** — decidir o modo por fórmula barata (a partir de nº de runs / cardinalidade
     / N) SEM materializar todos os candidatos (ver labs 1533/1759: o tamanho é previsível).
  2. **preditor estatístico** — balancear, por perfil de coluna, qual modo é mais PROVÁVEL de vencer,
     escolhendo previamente (ex.: distribuição de runs → modo). Reduz custo de CPU do `min()`.
- **Medir custo de CPU/memória** de materializar N candidatos vs prever (o `min()` atual paga N encodes).
- **Pós-transporte**: o Ciclo B mostrou o FLOOR estável sob gzip pra bool; reconferir em tipos maiores.
- **Refino do limiar bN** (o cruzamento não é monotônico — base-94 esgota em k=95; ver lab 1857 v2).

## Gate

Nenhuma decisão de modo estabiliza sem: RT-tipado (o tipo volta), FLOOR nunca-pior verificado,
snapshots byte-canônicos verdes quando o código elegível for tocado, e o custo de CPU conhecido no
regime onde cada modo vence (plano `.8` §10).

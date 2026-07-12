---
title: T-FMT-TCF8H-HEADER — Decisões de formato do cabeçalho TCF.8H (hierárquico)
status: closed-decided (slot H reservado no .8, ADR-0031; codec -> trilho .9 via T-STUDY-HIERARCHICAL-TCF)
priority: P2
created: 2026-07-05
updated: 2026-07-10
closed: 2026-07-10
blocked-by: []
related:
  - experiments/lab/dirty/notas/tcf8h-header-checklist.md
  - experiments/lab/clean/EXP-015-tcf-hierarquico-csv-json/
  - experiments/lab/dirty/notas/tcf8h-proximas-ideias.md
  - experiments/lab/dirty/2026-07-01-header-minimal/result.md
  - tickets/T-STUDY-HIERARCHICAL-TCF.md
---

# T-FMT-TCF8H-HEADER — cabeçalho do TCF.8H

> **ENCERRADO (2026-07-10, T-REL-08-CLOSEOUT Passo 1e)**: a DECISÃO deste ticket foi executada —
> discriminador `H` REGISTRADO e reservado no `.8` com fail-loud (`a001fd3`, ADR-0031; testado);
> consagráveis (M-implícito, omit-closes, última-sem-size) já valem no `.8M`. O CODEC hierárquico
> (colchete-meta `{}[]`, reorder S2/S3 condicional) segue GATED no trilho `.9` —
> [T-STUDY-HIERARCHICAL-TCF](T-STUDY-HIERARCHICAL-TCF.md) (ABERTO) + EXP-015; o quoting das
> chaves cruza com [T-FMT-QUOTING-STUDY](T-FMT-QUOTING-STUDY.md). Corpo abaixo = a decisão da era.

**[dispositivo]** Consolida o que dá pra **consagrar** no cabeçalho hierárquico TCF.8H (protótipo EXP-015,
peças 1-9), separando o SETTLED do CONDICIONAL. Formato: `#TCF.8H<colchete-meta>\n<bodies>`; a árvore no
colchete (`{}`=objeto, `[]`=array); **M/N/cardinalidade DEDUZIDOS** (não escritos). Gate de welding em
`src/tcf`: `test_real_world_snapshots.py` + re-pin de baselines (ADR-0024); opt-in não muda default.

> **DECISÃO DISPOSITIVA (owner 2026-07-09) — discriminador `H` formalizado**: `H` é char de discriminador
> do `.8` = **multi-col hierárquico, especialização de `M`** (espaço=single · `M`=multi plano · `H`=`M`+
> hierarquia). Além de formalizar, dá dispatch **O(1)** no decode (roteia pro codec-árvore sem parsear o
> meta). **Sem-espaço** (herda de `M`): `#TCF.8H<meta>`, NÃO `#TCF.8H <meta>` — o protótipo EXP-015 usou
> espaço e deve alinhar no weld. Formalizado em **[ADR-0031](../docs/adr/0031-hierarchical-discriminator-H.md)**
> (accepted); registrado no [char-registry Eixo 1](../experiments/lab/dirty/notas/tcf8-header-char-registry.md).
> **Escopo do ADR-0031**: reserva o char + a semântica; o CODEC hierárquico (gramática do meta, omit-closes,
> etc.) segue research-track — welding = ticket próprio gated. `src/tcf` NÃO muda agora.

## CONSAGRAR (settled, RT-exato, medido)

- **`M` implícito**: o `H`/multi-col já implica ≥2 colunas → sem flag `M`. (medido EXP-015)
- **omit-closes**: o `\n` do cabeçalho fecha os grupos abertos → dropar a corrida final de `}`/`]`. O
  decoder auto-fecha no EOF. **Ganho limpo, RT-EXATO, sempre bom, custo zero.** ← consagrar.
- **última-folha-sem-size** (herdado ADR-0023) + **colchete p/ hierarquia** (P5). Nomes explícitos; tipos
  = extensão futura (`:tipo`).

## CONDICIONAL (config-dependente — a CONTA, não "quem vence")

Fórmula (EXP-015 `05-header-condicoes.txt`): escolher a última folha economiza
`SAVING(L) = digits(size(L)) + depth(L)` (última-sem-size dá digits; omit-closes dá depth).
- **reorder profundo-por-último** (order-free): vale **SSE** `argmax_L(digits+depth) ≠ natural-última`.
  **Não é só profundidade** — é digits+depth. Precisa de S2 (reorder-at-encode) ou S3 (telemetria) pra
  realizar (ver [T-FLOW-ENCODE-STRATEGIES-TELEMETRY](T-FLOW-ENCODE-STRATEGIES-TELEMETRY.md)).
- **base dos byte-sizes** (só a EXISTÊNCIA aqui): os sizes têm uma base (dec/hex). `len(hex(s)) ≤
  len(str(s))` sempre → hex é byte win-or-tie. **A decisão detalhada** (hex-default + dedução da base +
  decimal-por-comando) vive em **[T-OPT-INFERENCE](T-OPT-INFERENCE.md)** (otimização por inferência,
  separada). O header só reserva que o size pode vir em hex.

## Aberto / decidir

- ~~Discriminador `H`~~ **DECIDIDO 2026-07-09** (ADR-0031): `H` = multi hierárquico, especialização de `M`,
  sem-espaço. Char + semântica reservados.
- **Welding do codec TCF.8H** (arestas explícitas + resto deduzido) → **ticket próprio, gated** (gate
  real-world + aprovação src/tcf + re-pin baselines). NÃO coberto por este ticket nem pelo ADR-0031.
- base dos sizes (hex/dec): delegado a **T-OPT-INFERENCE** (hex-default é a direção do owner).
- tipos (`:tipo`) no colchete: estratégia **C-híbrida decidida** (Ciclo 1a/1b — deduz número/bool, tag só
  na colisão; H-TYPE-01), mas **ainda não no codec EXP-015**; entra no welding.

## Critério de aceite

- [x] omit-closes + M-implícito documentados como a forma canônica do TCF.8H (consagrado) — checklist C2/C3,
  EXP-015 RT-medido.
- [x] reorder marcado condicional (SSE argmax≠natural), delegado a T-FLOW (S2/S3).
- [x] hex decidido (base dos sizes): delegado a **T-OPT-INFERENCE**; tradeoff bytes×legibilidade registrado
  lá (hex win-or-tie; convenção-default) + no checklist C4.
- [x] **discriminador `H` formalizado** (ADR-0031, 2026-07-09) — especialização de `M`, sem-espaço, dispatch O(1).
- [ ] (se weldar) gate real-world verde + baselines re-pinados — **ticket de welding próprio, gated** (fora deste).

**Estado**: as decisões de FORMATO do header estão cravadas (`decided-weld-gated`). Resta só o welding do
codec em `src/tcf`, que é gated e vive num ticket separado — este ticket não fica mais "aberto por decidir".

---
title: T-FMT-TCF8H-HEADER — Decisões de formato do cabeçalho TCF.8H (hierárquico)
status: partial-consecrate
priority: P2
created: 2026-07-05
updated: 2026-07-05
blocked-by: []
related:
  - experiments/lab/dirty/notas/tcf8h-header-checklist.md
  - experiments/lab/clean/EXP-015-tcf-hierarquico-csv-json/
  - experiments/lab/dirty/notas/tcf8h-proximas-ideias.md
  - experiments/lab/dirty/2026-07-01-header-minimal/result.md
  - tickets/T-STUDY-HIERARCHICAL-TCF.md
---

# T-FMT-TCF8H-HEADER — cabeçalho do TCF.8H

**[dispositivo]** Consolida o que dá pra **consagrar** no cabeçalho hierárquico TCF.8H (protótipo EXP-015,
peças 1-9), separando o SETTLED do CONDICIONAL. Formato: `#TCF.8H <colchete-meta>\n<bodies>`; a árvore no
colchete (`{}`=objeto, `[]`=array); **M/N/cardinalidade DEDUZIDOS** (não escritos). Gate de welding em
`src/tcf`: `test_real_world_snapshots.py` + re-pin de baselines (ADR-0024); opt-in não muda default.

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

- Welding do TCF.8H (arestas explícitas + resto deduzido) → decisão de formato do owner.
- base dos sizes (hex/dec): delegado a **T-OPT-INFERENCE** (hex-default é a direção do owner).
- tipos (`:tipo`) no colchete.

## Critério de aceite

- [ ] omit-closes + M-implícito documentados como a forma canônica do TCF.8H (consagrado).
- [ ] reorder marcado condicional (SSE argmax≠natural), delegado a T-FLOW (S2/S3).
- [ ] hex decidido (base dos sizes) com o tradeoff bytes×legibilidade registrado.
- [ ] (se weldar) gate real-world verde + baselines re-pinados.

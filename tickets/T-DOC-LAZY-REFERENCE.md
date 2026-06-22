---
title: T-DOC-LAZY-REFERENCE — Reference Diátaxis da API tcf.view (A5 do plano 0.8)
status: open
priority: P1
created: 2026-06-21
updated: 2026-06-21
blocked-by: [T-CODE-LAZY-VIEW-PROMOTE]
related:
  - experiments/lab/dirty/notas/v08-plano-etapas.md
  - src/tcf/view.py
  - docs/reference/encode-knobs.md
---

# T-DOC-LAZY-REFERENCE (A5 do plano 0.8)

## Contexto / motivação

Com a view promovida pro core ([T-CODE-LAZY-VIEW-PROMOTE](T-CODE-LAZY-VIEW-PROMOTE.md),
A4 feito), a API de `tcf.view` precisa de **reference Diátaxis** própria. Hoje
`docs/reference/` só tem `encode-knobs.md`; a API do lazy só está documentada em
`scripts/tcf_lazy/README.md` (que virou shim).

## Plano

Escrever `docs/reference/lazy-view.md`:
- `view(blob) -> LazyTCF`; `LazyTCF` (count/sum/min/max/avg, where, group_count,
  group_ranges, agg_by, select, nrows, columns, `*_bytes`, report) + `Filtered`
  (encadeamento AND).
- **Semântica row-aligned por posição** (a i-ésima posição de cada coluna = linha `i`);
  contrato numérico (ignora vazios, erra em não-numérico).
- **Marcar estável vs experimental**: L1-L4 estáveis; `agg_by`/`group_ranges`/L5 podem
  evoluir no H-QUERY-04 (0.9) → marcar **experimental**.
- Cross-link de `encode-knobs.md` (`sort_by` habilita o layout L5) e how-to de inspeção.
- Adicionar a `MAP.md` (entrada nova de doc).

## Critério de aceite

- [ ] `docs/reference/lazy-view.md` criado, cobrindo a superfície de `tcf.view`.
- [ ] Estável vs experimental explícito por método.
- [ ] Exemplos rodáveis (`from tcf import encode, view`).
- [ ] Cross-link em MAP.md + encode-knobs.md.

## Riscos / notas

- Depende de A4 (caminho de import canônico fixado: `from tcf import view`).

## Updates

- **2026-06-21**: aberto após A4 fechar. Bloqueado só pela ordem (A4 já feito → pode iniciar).

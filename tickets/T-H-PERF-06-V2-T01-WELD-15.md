---
title: T-H-PERF-06-V2-T01 — Weld do candidato #15 (topK prune) em src/tcf
status: closed-done
priority: P1
created: 2026-05-31
closed: 2026-05-31
blocked-by: []
related:
  - docs/adr/0019-hcc-detect-compositions-topk-prune.md
  - tickets/T-REGRESSION-REAL-WORLD.md  (gate, pre-requisito — closed-done)
  - experiments/lab/dirty/old/welded/2026-05-27-h-perf-06-v2-fase-a/  (geracao do #15)
  - experiments/lab/dirty/2026-05-31-regression-real-world/  (gate + bench)
---

# T-H-PERF-06-V2-T01 — Weld #15

## Resumo

Port do candidato `#15 tier-scoring-02-topK-heap-with-safe-skip` (Fase A
de H-PERF-06-v2) para `src/tcf/composicional/syntax.py` `_detect_compositions`.
Otimizacao **interna** (sem mudanca de formato/API; output byte-identico).

Aprovado pelo owner em 2026-05-31 (toque explicito em src/tcf autorizado).

## O que mudou

Duas mudancas contidas no loop de candidatos de `_detect_compositions`:
1. Cheap upper-bound prune antes de `_estimate_baseline_chars` (descarta
   subs que nem o upper-bound conservador bate o best corrente).
2. Running-max inline (funde build+pick num loop; tie-break first-wins
   preservado via `net > best_net` estrito).

Prova de safety byte-canonical (ub_net >= net sempre) em ADR-0019.

## Gate (criterio de aceite)

- [x] Pre-requisito: T-REGRESSION-REAL-WORLD fechado (gate real-world existe)
- [x] Diff vs variant #15: so' as 2 hunks intencionais (verificado)
- [x] Suite completa verde: **269 passed, 2 xfailed**
- [x] Byte-canonical: D1-D9=1523B, D17a=322B, real-world 3 fixtures inalteradas
- [x] Prune ativo: `_estimate_baseline_chars` 87.4% menos chamadas (72.121 -> 9.093)
- [x] Speedup confirmado: 1.22x (coluna isolada 8k) / 1.354x (encode completo Fase A)
- [x] ADR-0019 escrito + CLAUDE.md gate + h-perf-06-exploration.md status
- [x] src/tcf tocado SOMENTE com aprovacao explicita

## Nao incluido (backlog)

- 16 candidatos marginais (~1%) da Fase A: nao weldados (overhead nao
  compensa). Bundle possivel se Fase B abrir revisao integral.
- Fase B (Cython): ticket separado quando priorizado. Teto puro-Python
  ~1.8x (Amdahl); >2x exige codigo compilado.

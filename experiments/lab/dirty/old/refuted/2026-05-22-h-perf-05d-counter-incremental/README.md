# Lab dirty — H-PERF-05d counter incremental (2026-05-22)

**Ticket**: [T-EXP-H-PERF-05d](../../../../tickets/T-EXP-H-PERF-05d.md)

**Origem**: H-PERF-05d era candidata futura em META-PERF-PHASE2
(closed-parcial 2026-05-20). Agora reaberta apos completar ciclo
H-DA-* categoria B.

## Sub-exps

1. **`01-profile/`** — profile granular de `_detect_compositions`
   em lineitem 5k pra identificar % tempo em Counter rebuild
2. **`02-prototype/`** — (se Fase 1 go) prototype incremental
3. **`03-validacao/`** — (se Fase 2 OK) byte-canonical + speedup

## Decision gate

Fase 1 e' go/no-go: se Counter rebuild < 30% do tempo de
_detect_compositions, encerrar lab (counter incremental nao vale).

## Conexoes

- [Ticket](../../../../tickets/T-EXP-H-PERF-05d.md)
- [HCC perf anterior (closed-adiado)](../2026-05-20-hcc-perf-optimization/)
- [Roadmap](../notas/roadmap-hipoteses.md)

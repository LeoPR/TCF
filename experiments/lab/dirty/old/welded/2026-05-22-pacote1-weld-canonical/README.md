# Lab dirty — Welding Pacote 1 canonical (2026-05-22)

**Ticket**: [T-CODE-PACOTE1-WELD-CANONICAL](../../../../tickets/T-CODE-PACOTE1-WELD-CANONICAL.md)

**Origem**: aprovacao explicita do owner pra weldar Pacote 1 inteiro
(delta-aware completo) em src/tcf canonical apos H-DA-11 + H-DA-11c.

**Consequencia esperada**: M9 baseline (1615B em D1-D9) muda pra M10
baseline (~1300B esperado, requer medicao). Pipeline canonical passa
a ser delta-aware completo.

## Sub-exps

1. **`01-validacao-multi-camada/`** — medir novo baseline M10 + ganho
   real-world + RT 100%

## Conexoes

- [Ticket](../../../../tickets/T-CODE-PACOTE1-WELD-CANONICAL.md)
- [EXP-010 prototype (origem)](../../clean/EXP-010-tcf-delta-aware-prototype/)
- [ADR-0008](../../../../docs/adr/0008-detect-cadence-numeric-rule.md)
- [ADR-0010](../../../../docs/adr/0010-auto-detect-min-len.md)

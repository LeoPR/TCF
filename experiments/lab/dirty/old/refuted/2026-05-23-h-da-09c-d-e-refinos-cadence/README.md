# Lab dirty — H-DA-09c/d/e refinos detect_cadence (2026-05-23)

**Ticket**: [T-EXP-H-DA-09c-d-e](../../../../tickets/T-EXP-H-DA-09c-d-e.md)

## Sub-exps

1. **`01-h-da-09c-threshold/`** — varrer threshold {0.5, 0.6, 0.7, 0.8}
2. (condicional) `02-h-da-09d-multivariada/`
3. (condicional) `03-h-da-09e-adaptativo/`

## Decision gate

Sub-exp 01 é go/no-go: se algum threshold der >= 2% weighted real-world
gain sem regressao em D1-D9, vale considerar refino.

## Conexoes

- [Ticket](../../../../tickets/T-EXP-H-DA-09c-d-e.md)
- [ADR-0008](../../../../docs/adr/0008-detect-cadence-numeric-rule.md)
- [ADR-0011](../../../../docs/adr/0011-pacote1-weld-canonical.md)

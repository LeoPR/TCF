# Lab dirty — Naturezas raras exploracao (2026-05-23)

**Ticket**: [T-EXP-NATUREZAS-RARAS-EXPLORACAO](../../../../tickets/T-EXP-NATUREZAS-RARAS-EXPLORACAO.md)

## Sub-exps

1. **`01-caracterizacao-observacional/`** — detectar padroes #5 (range
   narrow) e #8 (arredondamento) em Adult+TPC-H + D1-D9 controle.
   Estimar ganho potencial vs M10.

## Decision gate

Se padroes nao-cobertos por M10 mostram ganho >= 5% weighted em
colunas afetadas: GO sub-exp 02. Caso contrario: NO-GO documentado.

## Conexoes

- [Ticket](../../../../tickets/T-EXP-NATUREZAS-RARAS-EXPLORACAO.md)
- [Reflexao naturezas](../notas/naturezas-numericas-2026-05-23.md)
- [Pacote 5 NO-GO (precedente)](../2026-05-23-pacote5-t03-enumerated/)

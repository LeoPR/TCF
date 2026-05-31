# Lab dirty — H-DA-11c features unificadas (2026-05-22)

**Ticket**: [T-CODE-H-DA-11c-features-unificadas](../../../../tickets/T-CODE-H-DA-11c-features-unificadas.md)

**Origem**: decorrente de T-EXP-H-DA-11 (canonical welded). Reduz
duplicacao entre `detect_cadence` (ADR-0008, EXP-010) e
`detect_min_len` (ADR-0010, src/tcf canonical).

## Sub-exps

1. **`01-implementacao/`** — design ColumnFeatures + analyze_column +
   refactor auto_min_len.py + encoder.py
2. **`02-validacao-zero-risk/`** — verificar output IDENTICO ao
   pre-refactor (D1-D9 1615B, real-world 908,502B, RT 100%)

## Criterio

Refactor zero-risk. Sem mudanca de bytes nem RT.

## Conexoes

- [Ticket](../../../../tickets/T-CODE-H-DA-11c-features-unificadas.md)
- [ADR-0010](../../../../docs/adr/0010-auto-detect-min-len.md)
- [ADR-0008](../../../../docs/adr/0008-detect-cadence-numeric-rule.md)
- [Roadmap](../notas/roadmap-hipoteses.md)

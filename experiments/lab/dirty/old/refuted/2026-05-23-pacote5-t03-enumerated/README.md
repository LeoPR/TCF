# Lab dirty — Pacote 5 T03 enumerated (2026-05-23)

**Ticket**: [T-EXP-PACOTE5-T03-ENUMERATED](../../../../tickets/T-EXP-PACOTE5-T03-ENUMERATED.md)

**Origem**: reflexao 2026-05-23 sobre naturezas numericas identificou
natureza #7 (enumerated) como candidato Pacote 5. META-TYPE-ENCODERS T03.

## Sub-exps

1. **`01-caracterizacao/`** — identificar low-card cols em Adult+TPC-H,
   medir bytes atual M10 vs estimativa enumerated, decidir go/no-go

## Decision gate

Fase 1 e' go/no-go: se ganho weighted real-world < 5% sobre colunas
low-card, encerrar lab.

## Conexoes

- [Ticket](../../../../tickets/T-EXP-PACOTE5-T03-ENUMERATED.md)
- [Reflexao naturezas](../notas/naturezas-numericas-2026-05-23.md)
- [META-TYPE-ENCODERS T03](../../../../tickets/META-TYPE-ENCODERS.md)

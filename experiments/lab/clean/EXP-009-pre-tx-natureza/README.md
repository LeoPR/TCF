# EXP-009 — Pre-tx por natureza dos dados (meta-pasta)

**Status**: planejado (sub-experimentos abrem conforme macros dirty fecham com hipotese confirmada)
**Plano-mestre**: [`tickets/META-TYPE-ENCODERS.md`](../../../../tickets/META-TYPE-ENCODERS.md)
**Origem**: gap do [EXP-008](../EXP-008-compressao-comparada/) — D10-D15 + variety datasets sem ferramenta no TCF v0.6 atual.

## Estrutura

Cada sub-experimento e' **auto-contido**, segue template
**comparativo** ([META-EXP-FORMAT](../../../../tickets/META-EXP-FORMAT.md)):

```
EXP-009.1-incremental/        # base + delta (datas, timestamps)
EXP-009.2-templated/          # layout extract (CPF, UUID, email)
EXP-009.3-enumerated/         # dicionario (dominios, status)
EXP-009.4-checked/            # elide check digits (CPF)
EXP-009.5-composite/          # split sub-valores (datetime)
EXP-009.6-hierarchical/       # shared prefix tree (URL, path)
EXP-009.7-high-entropy/       # passthrough (UUID random, hash, base64 random)
```

Sub-experimento abre quando **macro dirty correspondente fecha**
com hipotese confirmada. Vide
[`experiments/lab/dirty/2026-05-15-naturezas-e-camada/`](../../dirty/2026-05-15-naturezas-e-camada/).

## Status por sub-experimento

| ID | Nature | Dirty | Clean | Welding | Notas |
|---|---|---|---|---|---|
| EXP-009.1 | Incremental | T01 (planejado) | — | — | Onda 1 |
| EXP-009.2 | Templated | T02 (planejado) | — | — | Onda 1 |
| EXP-009.3 | Enumerated | T03 (planejado) | — | — | Onda 2 |
| EXP-009.4 | Checked | T04 (planejado) | — | — | Onda 2 |
| EXP-009.5 | Composite | T05 (planejado) | — | — | Onda 2 |
| EXP-009.6 | Hierarchical | T06 (planejado) | — | — | Onda 3 |
| EXP-009.7 | High-entropy | T07 (planejado) | — | — | Onda 3 |

## Pergunta cientifica (consolidada)

Pra cada nature `N`, dado o dataset `D` correspondente, qual a
**reducao em bytes** do pipeline `pretx_N → tcf → C` vs `tcf → C`
e vs `csv → C` (baseline EXP-008)?

Cada sub-experimento responde essa pergunta no escopo da sua nature.

## Conexoes

- [META-TYPE-ENCODERS](../../../../tickets/META-TYPE-ENCODERS.md) — plano-mestre
- [META-EXP-FORMAT](../../../../tickets/META-EXP-FORMAT.md) — template comparativo aplicado
- [EXP-008](../EXP-008-compressao-comparada/) — baseline e motivacao
- [Dirty lab T-series](../../dirty/2026-05-15-naturezas-e-camada/) — exploracao precedente
- [Roadmap perspectiva-triplice](../../../../docs/theory/perspectiva-triplice-e-pre-tx.md)

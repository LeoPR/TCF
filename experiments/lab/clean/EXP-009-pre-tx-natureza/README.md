# EXP-009 — Pre-tx por natureza dos dados (meta-pasta — stub)

**Status**: stub (vazio — abre quando primeira natureza fechar no dirty)
**Plano-mestre**: [`tickets/META-TYPE-ENCODERS.md`](../../../../tickets/META-TYPE-ENCODERS.md)
**Origem**: gap do [EXP-008](../EXP-008-compressao-comparada/) — D10-D15 + variety datasets sem ferramenta no TCF v0.6 atual.

## Escopo realinhado (2026-05-15)

Pasta criada como **placeholder**. Sub-experimentos `EXP-009.N`
abrem **apenas quando macro dirty correspondente fechar com
hipotese confirmada**. Hoje, **nenhum sub-experimento ativo**.

Trabalho atual e' inteiramente no dirty lab. Vide
[`experiments/lab/dirty/2026-05-15-naturezas-e-camada/pre-tx/T01-incremental-base-delta/`](../../dirty/2026-05-15-naturezas-e-camada/pre-tx/T01-incremental-base-delta/).

## Status (mapping potencial, sem compromisso)

| ID (futuro) | Nature | Dirty (status) |
|---|---|---|
| EXP-009.1 | Incremental | **T01 ativo** |
| EXP-009.2 | Templated | T02 diferido |
| EXP-009.3 | Enumerated | T03 diferido |
| EXP-009.4 | Checked | T04 diferido |
| EXP-009.5 | Composite | T05 diferido |
| EXP-009.6 | Hierarchical | T06 diferido |
| EXP-009.7 | High-entropy | T07 diferido |

Quando T01 fechar, este mapping pode mudar — proxima natureza
nao e' garantida ser T02, depende dos gaps identificados em T01.

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

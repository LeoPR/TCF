---
title: T-REVAL-H-DA-07 — Revalidacao H-DA-07 (OBAT shape-preserve) em real-world
status: closed
resolution: confirmed-real-world
priority: P2
created: 2026-05-22
updated: 2026-05-22
closed: 2026-05-22
blocked-by: []
related:
  - tickets/T-REVAL-H-DA-01-06-10.md
  - tickets/T-CODE-PACOTE1-WELD-CANONICAL.md
  - experiments/lab/dirty/2026-05-22-h-da-07-shape-preserve-revalidacao/
  - experiments/lab/dirty/notas/roadmap-hipoteses.md
  - experiments/lab/dirty/notas/revisao-conceitual-2026-05-21.md
---

# T-REVAL-H-DA-07 — Revalidacao OBAT shape-preserve

## Contexto / motivacao

H-DA-07 (OBAT shape-preserve via `processar_with_hint`) era classificada
em revisao 2026-05-21 como categoria B residual:
- **confirmada-empirica condicional**: -32% em D11+D16 sinteticos
- MAS **+17% em D1-D9** (regressao!)
- Gerenciada via auto-pre `detect_cadence` (gating)
- Nao revalidada em real-world em T-REVAL Categoria B

Apos welding canonical Pacote 1 (ADR-0011, 2026-05-22), pipeline
canonical M10 inclui:
- `detect_cadence_from_features` (regras 1+2, ADR-0008)
- `processar_with_hint(prefer_shape_consistency=True)` quando dispara
- `processar` canonical caso contrario

Pergunta cientifica: em real-world (Adult+TPC-H), o gating `detect_cadence`
+ shape-preserve mantem zero regressao OU introduz ganhos/perdas
significativos vs encoder sem shape-preserve?

## Hipoteses sob revalidacao

### H-DA-07a — shape-preserve nao regride em real-world

Em real-world, detect_cadence dispara so' onde shape-preserve ajuda
(ou pelo menos nao prejudica). Welding canonical Pacote 1 e' seguro
em real-world.

### H-DA-07b — Identificar colunas problematicas (se houver)

Se alguma coluna real-world regredir, classificar:
- Tipo de regressao (lengths nao-uniformes? shape mudando?)
- Magnitude (% bytes)
- Acao: ajustar threshold de detect_cadence? ou aceitar como condicional?

## Plano

Lab dirty: `experiments/lab/dirty/2026-05-22-h-da-07-shape-preserve-revalidacao/`

### Sub-exp 01 — medicao on/off

Comparar 2 variantes em D1-D9 + Adult Census + TPC-H:
- **V1 (off)**: pipeline manual sem shape-preserve (`processar` canonical sempre)
- **V2 (on)**: pipeline canonical M10 (`tcf.encode` com cadence + shape-preserve quando dispara)

Por coluna: bytes V1, bytes V2, delta (negativo = ganho V2; positivo = regressao V2).
Per total: weighted gain/loss.

### Criterio

- **Confirmada**: V2 <= V1 em >= 95% das colunas reais (zero ou minimas
  regressoes); ganho weighted >= 0%
- **Refutada-parcial**: regressoes em > 5% das colunas; ajuste de
  threshold necessario
- **Refutada**: regressao weighted > 1% real-world (pior que off)

## Conexoes

- [T-REVAL Categoria B](T-REVAL-H-DA-01-06-10.md) — onde H-DA-07 ficou pendente
- [T-CODE-PACOTE1-WELD-CANONICAL](T-CODE-PACOTE1-WELD-CANONICAL.md) — welding canonical
- [Revisao conceitual](../experiments/lab/dirty/notas/revisao-conceitual-2026-05-21.md)
- [Roadmap H-DA-07](../experiments/lab/dirty/notas/roadmap-hipoteses.md)

## Updates datados

### 2026-05-22 — abertura

Ticket criado seguindo convencao YAML frontmatter. Categoria B residual
de T-REVAL nao revalidada em real-world. Welding Pacote 1 canonical
ja' inclui pipeline shape-preserve com gating — esta revalidacao
mede se gating funciona corretamente em real-world.

### 2026-05-22 — execucao + fechamento

Sub-exp 01 medindo shape-preserve on/off em D1-D9 + Adult+TPC-H.

**Resultados** (66 colunas total: 9 sint D1-D9 + 57 real):

| Camada | off (B) | on (B) | delta | pct |
|---|---:|---:|---:|---:|
| Sintetico D1-D9 | 1,584 | 1,523 | -61 | -3.85% |
| Real-world (Adult+TPC-H) | 893,864 | 889,714 | -4,150 | **-0.46%** |

**Distribuicao** (62/66 colunas sem mudanca — gating funciona):
- 2 wins (shape-preserve ajuda):
  - `tpch.customer-5k/c_name`: -4,514B (**-98.19%**) DRAMATICO
  - `sintetico/D9-frequencia-alta/val`: -61B (-48.03%)
- 2 losses (regressoes pequenas):
  - `tpch.lineitem-5k/l_extendedprice`: +335B (+0.65%)
  - `tpch.customer-5k/c_acctbal`: +29B (+0.20%)

**Veredito**: CONFIRMADA real-world (zero regressao significativa).
- Real-world losses: 2/57 colunas (3.5% << 5% threshold)
- Real-world weighted: -0.46% (ganho marginal)
- Wins enormes em colunas com formato sequencial (c_name = Customer#NNNN)
- Losses pequenas em numericos onde shape-preserve nao ajuda mas erra pouco

**Resolution**: confirmed-real-world. Gating `detect_cadence` opera
corretamente — dispara em colunas onde shape-preserve ajuda
significativamente; nao dispara (62/66) na maioria.

Status roadmap atualizado: `confirmada-empirica real-world (gating
detect_cadence preserva neutralidade em 94% das colunas)`.

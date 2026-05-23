# Sub-exp 01 — H-DA-07 shape-preserve on/off

## Estrategia

- **V1 (off)**: pipeline canonical M10 SEM `processar_with_hint`
  (so' `processar` canonical, mesmo detect_min_len + HCCSeqRLE)
- **V2 (on)**: pipeline canonical M10 default (com cadence +
  shape-preserve quando dispara)

Mede impacto isolado do gating `detect_cadence` + `processar_with_hint`
no real-world (Adult + TPC-H) e D1-D9 (controle).

## Tabela completa (apenas colunas com diferenca)

| Source | Col | off (B) | on (B) | delta | pct |
|---|---|---:|---:|---:|---:|
| tpch.customer-5k | c_name | 4,597 | 83 | -4514 | -98.19% |
| sintetico | val | 127 | 66 | -61 | -48.03% |
| tpch.customer-5k | c_acctbal | 14,658 | 14,687 | +29 | +0.20% |
| tpch.lineitem-5k | l_extendedprice | 51,408 | 51,743 | +335 | +0.65% |

## Agregado

| Camada | off (B) | on (B) | delta | pct |
|---|---:|---:|---:|---:|
| Sintetico D1-D9 | 1,584 | 1,523 | -61 | -3.85% |
| Real-world (Adult+TPC-H) | 893,864 | 889,714 | -4,150 | -0.46% |
| **Total** | **895,448** | **891,237** | **-4,211** | **-0.47%** |

## Distribuicao

- Colunas com diferenca: 4/66
- Wins (shape-preserve ajuda): 2
- Losses (shape-preserve regride): 2
  - Real-world losses: 2/57 cols

## Veredito

**CONFIRMADA real-world: zero regressao significativa**

**Status sugerido H-DA-07**: `confirmada-empirica real-world`


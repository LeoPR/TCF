# Sub-exp 04 — validacao prototipo EXP-010 (H-DA-11)

## Strategy

Welding canonical em src/tcf adiado (CLAUDE.md exige aprovacao
explicita). Welding intermediario em EXP-010 prototype:
- novo `auto_min_len.py` (heur v3 + gating)
- modificado `delta_aware.encode_column` (default `min_len=None`
  -> auto-detect)

Esta validacao mede o ganho real do prototipo, comparativo entre:
- baseline: `encode_column(rows, min_len=3)` (explicit)
- novo: `encode_column(rows)` (min_len auto-detect)

## D1-D9 (M9 baseline INVARIANT)

| Dataset | base (B) | new (B) | delta | ml | RT |
|---|---:|---:|---:|---|---|
| D1-emails-simples | 118 | 118 | +0 | 3 | OK |
| D2-emails-quote-id | 166 | 166 | +0 | 3 | OK |
| D3-stress-substring | 177 | 177 | +0 | 3 | OK |
| D4-caos-mix | 113 | 113 | +0 | 3 | OK |
| D5-padroes-multiplos | 281 | 281 | +0 | 3 | OK |
| D6-poucos-em-ruido | 287 | 287 | +0 | 3 | OK |
| D7-aninhamento | 215 | 215 | +0 | 3 | OK |
| D8-cabeca-cauda | 100 | 100 | +0 | 3 | OK |
| D9-frequencia-alta | 66 | 66 | +0 | 3 | OK |
| **TOTAL** | **1523** | **1523** | **+0** | — | 9/9 |

**M9 baseline preservado**: **SIM** (total=1523B)
**RT 100%**: **SIM**

## Real-world Adult + TPC-H

- Total baseline (ml=3 explicit): 940,720B
- Total novo (auto-detect):       889,757B
- **Gain**: +50,963B (5.42% weighted)
- RT: 57/57

### Top 10 wins

| Col | base | new | ml | delta | pct |
|---|---:|---:|---|---:|---:|
| tpch.lineitem-5k/l_comment | 163,073 | 133,426 | 6 | -29647 | -18.18% |
| tpch.lineitem-5k/l_shipdate | 41,240 | 36,001 | 6 | -5239 | -12.70% |
| tpch.lineitem-5k/l_commitdate | 40,010 | 35,465 | 6 | -4545 | -11.36% |
| tpch.customer-5k/c_phone | 33,836 | 29,687 | 6 | -4149 | -12.26% |
| tpch.lineitem-5k/l_receiptdate | 40,013 | 35,948 | 6 | -4065 | -10.16% |
| tpch.customer-5k/c_comment | 108,461 | 105,151 | 6 | -3310 | -3.05% |
| tpch.customer-5k/c_address | 43,416 | 43,408 | 6 | -8 | -0.02% |

## Veredito

- D1-D9 baseline preservado: OK
- D1-D9 RT 100%: OK
- Real-world gain >= 5%: OK (5.42%; nota: vs EXP-010 baseline ja' otimizado, diferente dos 9.87% predito vs M8A canonical puro)
- Real-world RT 100%: OK

**PROTOTYPE H-DA-11: CONFIRMED**

## Proximos passos

- Welding canonical em `src/tcf/encoder.py` aguarda aprovacao
  explicita do owner (regra CLAUDE.md)
- ADR-0010 atualizado registrando estado intermediario


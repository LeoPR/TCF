# Sub-exp 05 — validacao welding canonical src/tcf (H-DA-11)

## Strategy

Welding canonical em src/tcf:
- `src/tcf/auto_min_len.py` (novo modulo, detect_min_len + helper)
- `src/tcf/encoder.py` (encode() chama detect_min_len em vez de min_len=3)

Comparativo:
- baseline: M8AVirtualRefsSyntax + processar(min_len=3) explicit
- welded: `tcf.encode(values)` (auto-detect)

## D1-D9 (M9 baseline 1615B INVARIANT)

| Dataset | base (B) | new (B) | delta | RT |
|---|---:|---:|---:|---|
| D1-emails-simples | 118 | 118 | +0 | OK |
| D2-emails-quote-id | 166 | 166 | +0 | OK |
| D3-stress-substring | 177 | 177 | +0 | OK |
| D4-caos-mix | 113 | 113 | +0 | OK |
| D5-padroes-multiplos | 281 | 281 | +0 | OK |
| D6-poucos-em-ruido | 287 | 287 | +0 | OK |
| D7-aninhamento | 215 | 215 | +0 | OK |
| D8-cabeca-cauda | 100 | 100 | +0 | OK |
| D9-frequencia-alta | 158 | 158 | +0 | OK |
| **TOTAL** | **1615** | **1615** | **+0** | 9/9 |

**M9 baseline 1615B**: MATCH (base medido=1615B)
**Welding preserva baseline**: SIM (new=1615B)
**RT 100%**: SIM (9/9)

## Real-world (Adult + TPC-H)

- Baseline total: 1,008,003B
- Welded total:   908,502B
- **Delta**: -99,501B (**9.87%** weighted)
- RT: 57/57

### Top 10 wins

| Col | base | new | delta | pct |
|---|---:|---:|---:|---:|
| tpch.lineitem-5k/l_comment | 163,073 | 133,426 | -29647 | -18.18% |
| adult-5000/fnlwgt | 60,457 | 38,219 | -22238 | -36.78% |
| tpch.lineitem-5k/l_extendedprice | 71,446 | 51,408 | -20038 | -28.05% |
| tpch.lineitem-5k/l_shipdate | 41,249 | 36,201 | -5048 | -12.24% |
| tpch.lineitem-5k/l_commitdate | 40,023 | 35,779 | -4244 | -10.60% |
| tpch.customer-5k/c_phone | 33,836 | 29,687 | -4149 | -12.26% |
| tpch.lineitem-5k/l_receiptdate | 40,013 | 36,139 | -3874 | -9.68% |
| tpch.customer-5k/c_comment | 108,461 | 105,151 | -3310 | -3.05% |
| tpch.customer-5k/c_acctbal | 17,326 | 14,658 | -2668 | -15.40% |
| tpch.lineitem-5k/l_partkey | 28,134 | 26,549 | -1585 | -5.63% |

## Veredito canonical welding

- D1-D9 baseline preservado: OK
- D1-D9 RT 100%: OK
- Real-world gain >= 7%: OK (9.87%)
- Real-world RT 100%: OK

**CANONICAL WELDING: CONFIRMED**


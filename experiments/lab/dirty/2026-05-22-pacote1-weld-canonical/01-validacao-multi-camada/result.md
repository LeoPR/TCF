# Sub-exp 01 — validacao welding Pacote 1 canonical (M9 → M10)

## Pipeline canonical novo (M10)

```
values
  → analyze_column (features)
  → detect_cadence_from_features (regras 1+2)
  → detect_min_len_from_features (heur v3, gating n>=100)
  → OBAT: processar_with_hint OR processar
  → HCC: HCCSeqRLE (M8A + seq-RLE near-identical)
  → texto TCF
```

## D1-D9 novo baseline M10

| Dataset | M10 (B) | RT |
|---|---:|---|
| D1-emails-simples | 118 | OK |
| D2-emails-quote-id | 166 | OK |
| D3-stress-substring | 177 | OK |
| D4-caos-mix | 113 | OK |
| D5-padroes-multiplos | 281 | OK |
| D6-poucos-em-ruido | 287 | OK |
| D7-aninhamento | 215 | OK |
| D8-cabeca-cauda | 100 | OK |
| D9-frequencia-alta | 66 | OK |
| **TOTAL M10** | **1523** | 9/9 |

M9 baseline (historico): 1615B
M10 baseline (novo): 1523B
Delta: -92B (-5.70%)

## EXP-010 set (20 datasets)

| Dataset | M10 (B) | RT |
|---|---:|---|
| D1-emails-simples | 118 | OK |
| D2-emails-quote-id | 166 | OK |
| D3-stress-substring | 177 | OK |
| D4-caos-mix | 113 | OK |
| D5-padroes-multiplos | 281 | OK |
| D6-poucos-em-ruido | 287 | OK |
| D7-aninhamento | 215 | OK |
| D8-cabeca-cauda | 100 | OK |
| D9-frequencia-alta | 66 | OK |
| D11a-datas-dia | 71 | OK |
| D11b-datas-borda | 173 | OK |
| D11c-datas-mensal | 72 | OK |
| D11d-datetime-min | 61 | OK |
| D11e-datetime-mensal | 84 | OK |
| D11f-datetime-ms | 66 | OK |
| D11g-datetime-us | 71 | OK |
| D11h-datetime-ns | 74 | OK |
| D16a-ids-3digits | 11 | OK |
| D16b-ids-4digits | 28 | OK |
| D16c-ids-prefixados | 38 | OK |
| **TOTAL** | **2272** | 20/20 |

## Real-world (Adult + TPC-H, 57 cols)

- Total M10: 889,714B
- vs M9 puro (1,008,003B): -118,289 (+11.73%)
- vs M9+H-DA-11 (908,502B): -18,788 (+2.07%)
- RT: 57/57

## Veredito

- D1-D9 RT 100%: OK
- EXP-010 set RT 100%: OK
- Real-world RT 100%: OK
- Real-world gain >= 10% vs M9 puro: OK (11.73%)

**WELDING PACOTE 1 CANONICAL: CONFIRMED**


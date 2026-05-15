# Resultado — 03-cadencia-mensal-D11c-datas-mensal

Dataset com 13 linhas: fatura mensal dia 5 por 13 meses
(Jan/2025 a Jan/2026). Padrao realistic (sistema real de cobranca).

## Bytes

| Pipeline | Pre-tx bytes | TCF bytes | vs raw csv | vs TCF puro |
|---|---:|---:|---:|---:|
| TCF puro | — | 109 | 74.1% | 100.0% |
| Pre-tx v0 + TCF | 47 | 53 | 36.1% | 48.6% |
| **Pre-tx v1 + TCF** | **47** | **22** | **15.0%** | **20.2%** |

Raw CSV: 147 bytes

## Hipoteses

- **H1 (RT v1 preserva dados)**: CONFIRMADA
- **H2 (escala vence em cadencia, v1 < v0)**: CONFIRMADA
  - v1 TCF: 22 bytes
  - v0 TCF: 53 bytes
  - Diferenca: -31 bytes (-58.5%)
- **H3 (pre-tx v0 < TCF puro)**: CONFIRMADA

## Pre-tx outputs (comparacao visual)

### V0 (dia-only) — deltas variam por mes

```
2025-01-05
31
28
31
30
31
30
31
31
30
31
30
31
```

### V1 (escalas) — todos iguais a `1M`

```
2025-01-05
1M
1M
1M
1M
1M
1M
1M
1M
1M
1M
1M
1M
```

## Debug

Estagios intermediarios em `outputs/`:
- `01a-pretx-v0.txt` / `01b-pretx-v1.txt` — outputs do pretx
- `02a-tcf-v0.tcf` / `02b-tcf-v1.tcf` / `02c-tcf-puro.tcf` — TCF encoded
- `03-obat-tokens-v1.txt` / `04-hcc-trace-v1.txt` / `05-hcc-rede-v1.txt` — debug v1
- `06a-postx-v0.txt` / `06b-postx-v1.txt` — outputs do postx
- `07-rt-v0.txt` / `08-rt-v1.txt` — RT results

## Conexoes

- [`README.md`](README.md) — pergunta cientifica
- [`../README.md`](../README.md) — T01 macro pai
- [`pretx_dia_mes_ano.py`](pretx_dia_mes_ano.py) — encoder v1
- [`../01-prova-conceito-D11a-dia/`](../01-prova-conceito-D11a-dia/) e
  [`../02-bordas-D11b/`](../02-bordas-D11b/) — sub-exps com encoder v0

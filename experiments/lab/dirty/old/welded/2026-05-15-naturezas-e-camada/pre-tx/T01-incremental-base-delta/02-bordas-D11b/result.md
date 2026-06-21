# Resultado — 02-bordas-D11b-datas-borda

Dataset com 14 linhas YYYY-MM-DD, exercitando bordas de mes/ano (incluindo Feb 29 em ano bissexto 2024).

## Bordas exercitadas

- Jan→Feb (mes 31 dias): 2024-01-31 → 2024-02-01
- Feb 29 (ano bissexto 2024): 2024-02-28 → 2024-02-29
- Feb 29 → Mar 1 (leap): 2024-02-29 → 2024-03-01
- Year boundary: 2024-12-31 → 2025-01-01 (e 2025→2026)
- Feb 28 → Mar 1 (non-leap): 2025-02-28 → 2025-03-01
- Jan 31 → Mar 1 (com Feb non-leap): 2026-01-31 → 2026-02-28 → 2026-03-01

## Bytes

| Etapa | Bytes | vs raw csv | vs TCF puro |
|---|---:|---:|---:|
| Raw CSV | 158 | 100.0% | — |
| Pre-tx output | 45 | 28.5% | — |
| TCF puro | 173 | 109.5% | 100.0% |
| **Pre-tx + TCF** | **59** | **37.3%** | **34.1%** |

## Roundtrip

- TCF roundtrip (pre-tx → tcf encode → tcf decode == pre-tx): **OK**
- RT full (pos-tx output == input): **OK**

## Conclusao desta iteracao

- H1 (RT preserva bordas calendar): **CONFIRMADA**.
- H2 (pre-tx + TCF < TCF puro): **CONFIRMADA** (59 vs 173 bytes).

Comparacao com 01-D11a (12 linhas, sem bordas):
- D11a: raw=136, pretx=34, tcf_puro=87, pretx+tcf=42
- D11b: raw=158, pretx=45, tcf_puro=173, pretx+tcf=59

## Debug

Estagios intermediarios em `outputs/` (regeneravel via `run.py`):
- `03-obat-tokens.txt`, `04-hcc-trace.txt`, `05-hcc-rede.txt`

## Conexoes

- [`README.md`](README.md) — pergunta cientifica + metodo
- [`../README.md`](../README.md) — T01 macro pai
- [`../01-prova-conceito-D11a-dia/`](../01-prova-conceito-D11a-dia/) — sub-exp 01 (encoder copiado dali)

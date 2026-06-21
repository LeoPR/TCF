# Resultado — 01-prova-conceito-D11a-dia

Executado a partir de [`D11a-datas-dia.csv`](../../../../../../../datasets/synthetic/D11a-datas-dia.csv) (12 linhas).

## Bytes

| Etapa | Bytes | vs raw csv | vs TCF puro |
|---|---:|---:|---:|
| Raw CSV (com header) | 136 | 100.0% | — |
| Pre-tx output | 34 | 25.0% | — |
| TCF puro | 87 | 64.0% | 100.0% |
| **TCF de pre-tx** | **42** | **30.9%** | **48.3%** |

## Roundtrip

- TCF roundtrip (pre-tx output): **OK**
- RT full (pos-tx output == input): **OK**

## Conclusao desta iteracao

- Hipotese pre-tx reduz bytes vs TCF puro: **CONFIRMADA** (42 vs 87 bytes).
- Hipotese pipeline preserva dados (RT): **CONFIRMADA**.

## Debug

Estagios intermediarios em `outputs/` (regeneravel via `run.py`):
- `00-input.txt` ... `08-rt-result.txt`
- `03-obat-tokens.txt` — arvore OBAT da saida pre-tx
- `04-hcc-trace.txt` — composicao HCC
- `05-hcc-rede.txt` — rede de refs HCC

## Conexoes

- [`README.md`](README.md) — pergunta cientifica + metodo
- [`../README.md`](../README.md) — T01 macro pai
- [`pretx_dia.py`](pretx_dia.py) / [`postx_dia.py`](postx_dia.py) — encoder/decoder

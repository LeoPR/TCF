# 03 — Cadencia mensal (D11c) com encoder v1 (escalas M/Y)

**Estado**: aberto (terceira iteracao do T01)
**Macro pai**: [`../README.md`](../README.md) — T01 incremental
**Dataset**: [`D11c-datas-mensal.csv`](../../../../../../../datasets/synthetic/D11c-datas-mensal.csv)
**Encoder**: v1 (escalas dia/M/Y) — primeira aparicao da linguagem com escalas

## Pergunta cientifica

Em dataset com **cadencia mensal** (fatura todo dia 5 do mes),
encoder com escalas `+1M` produz bytes menores que encoder v0
(dia-only) apos passar pelo TCF?

Hipotese: sim. Razao intuitiva — com v0, deltas variam
(`31, 28, 31, 30, ...` dependendo do mes), sem repeticao exata
significativa. Com v1, todos os 12 deltas viram `1M` exato:
TCF/HCC compactam repeticao trivialmente (`*12|1M` ou similar).

## Hipoteses

- **H1 (RT v1)**: encoder v1 preserva RT em D11c (12 transicoes mes×31/30/28 dias).
- **H2 (escala vence em cadencia)**: pre-tx v1 + TCF < pre-tx v0 + TCF em D11c.
- **H3 (ambos vencem TCF puro)**: pre-tx v0 e v1 ambos < TCF puro.

## Dataset D11c (13 linhas, fatura mensal dia 5)

Padrao realistic — pagamento/fatura todo dia 5 por 13 meses.

| # | Data | Delta vs anterior | dias | meses |
|---|---|---:|---:|---:|
| 1 | 2025-01-05 | base | — | — |
| 2 | 2025-02-05 | +1M | 31 | 1 |
| 3 | 2025-03-05 | +1M | 28 | 1 |
| 4 | 2025-04-05 | +1M | 31 | 1 |
| 5 | 2025-05-05 | +1M | 30 | 1 |
| 6 | 2025-06-05 | +1M | 31 | 1 |
| 7 | 2025-07-05 | +1M | 30 | 1 |
| 8 | 2025-08-05 | +1M | 31 | 1 |
| 9 | 2025-09-05 | +1M | 31 | 1 |
| 10 | 2025-10-05 | +1M | 30 | 1 |
| 11 | 2025-11-05 | +1M | 31 | 1 |
| 12 | 2025-12-05 | +1M | 30 | 1 |
| 13 | 2026-01-05 | +1M | 31 | 1 |

Total: **12 deltas, todos `+1M` exato**. Em dias varia
`31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31`.

## Linguagem v1 (escalas)

Decoder reconhece sufixo:
- `<N>` (sem letra) = N dias
- `<N>M` = N meses
- `<N>Y` = N anos
- Sinal explicito so' pra negativo: `-3`, `-1M`, `-2Y`

Encoder escolhe **maior escala exata possivel**:
1. Ano exato (mes + dia iguais a previa)?  → emite `NY`
2. Mes exato (dia igual)?  → emite `NM`
3. Senao → emite dias

## Comparacao com sub-experimentos anteriores

Este sub-experimento roda **3 pipelines** em D11c pra comparar:

1. **TCF puro** (sem pre-tx)
2. **Pre-tx v0** (dia-only) + TCF
3. **Pre-tx v1** (escalas) + TCF

Resultado esperado (H2): v1 < v0 << TCF puro.

## Como rodar

```bash
python experiments/lab/dirty/2026-05-15-naturezas-e-camada/pre-tx/T01-incremental-base-delta/03-cadencia-mensal-D11c/run.py
```

## Saidas

`outputs/` (gitignored):
- `00-input.txt`, `01a-pretx-v0.txt`, `01b-pretx-v1.txt`
- `02a-tcf-v0.tcf`, `02b-tcf-v1.tcf`, `02c-tcf-puro.tcf`
- `03-obat-tokens-v1.txt`, `04-hcc-trace-v1.txt`, `05-hcc-rede-v1.txt`
- `06a-postx-v0.txt`, `06b-postx-v1.txt`
- `07-rt-v0.txt`, `08-rt-v1.txt`
- `bytes-comparison.md`

`result.md` — resumo dos 3 pipelines.

## Criterio de fechamento

- [ ] RT v0 OK e RT v1 OK (ambos preservam dados)
- [ ] Pre-tx v1 + TCF < pre-tx v0 + TCF (H2)
- [ ] Pre-tx v0 + TCF e' menor que TCF puro (H3)
- [ ] Debug v1 (OBAT/HCC) inspecionado

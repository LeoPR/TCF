# Resumo — Sub-exp 04 (H-DA-07: OBAT shape-consistency hint)

Pipeline comparativo:
- **baseline** = OBAT canonical + HCC canonical (sub-exp 01)
- **t02** = OBAT canonical + HCC fork seq-RLE (sub-exp 02)
- **fork** = OBAT fork shape-preserve + HCC fork seq-RLE (este)

## Tabela

| Dataset | rows | uniq | baseline | t02 | fork | Δ vs t02 | Δ vs baseline | RT |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| [D11a-datas-dia](D11a-datas-dia/6-diff-bodies.md) | 12 | 12 | 87 | 84 | 71 | -13 | -16 | OK |
| [D11b-datas-borda](D11b-datas-borda/6-diff-bodies.md) | 14 | 14 | 173 | 173 | 153 | -20 | -20 | OK |
| [D11c-datas-mensal](D11c-datas-mensal/6-diff-bodies.md) | 13 | 13 | 109 | 78 | 72 | -6 | -37 | OK |
| [D11d-datetime-min](D11d-datetime-min/6-diff-bodies.md) | 13 | 13 | 110 | 73 | 61 | -12 | -49 | OK |
| [D11e-datetime-mensal](D11e-datetime-mensal/6-diff-bodies.md) | 13 | 13 | 121 | 90 | 84 | -6 | -37 | OK |
| [D11f-datetime-ms](D11f-datetime-ms/6-diff-bodies.md) | 13 | 13 | 115 | 78 | 66 | -12 | -49 | OK |
| [D11g-datetime-us](D11g-datetime-us/6-diff-bodies.md) | 13 | 13 | 120 | 83 | 71 | -12 | -49 | OK |
| [D11h-datetime-ns](D11h-datetime-ns/6-diff-bodies.md) | 13 | 13 | 123 | 86 | 74 | -12 | -49 | OK |

## Totais

- baseline: 958 B
- t02:      745 B  (-213 vs baseline, -22.2%)
- fork:     652 B  (-93 vs t02, -12.5%)
-           (-306 vs baseline, -31.9%)

RT: 8/8

## Por dataset, ver `outputs/<ds>/`

- `1-tokens-canonical.txt`, `2-tokens-fork.txt` — tokens emitidos
- `3-body-fork-canonical-obat.tcf` — body usando OBAT canonical + HCC fork
- `4-body-fork-fork-obat.tcf` — body usando OBAT fork + HCC fork
- `5-rt-status.txt` — numerico
- `6-diff-bodies.md` — comparativo lado-a-lado


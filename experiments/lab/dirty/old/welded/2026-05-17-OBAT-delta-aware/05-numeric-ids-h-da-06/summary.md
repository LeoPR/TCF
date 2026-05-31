# Resumo — Sub-exp 05 (H-DA-06 numeric IDs)

Pipeline comparativo (igual sub-exp 04):
- baseline = OBAT canonical + HCC canonical
- t02 = OBAT canonical + HCC fork seq-RLE
- fork = OBAT fork shape-preserve + HCC fork seq-RLE

## Tabela

| Dataset | rows | uniq | baseline | t02 | fork | Δ vs t02 | Δ vs baseline | RT |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| [D16a-ids-3digits](D16a-ids-3digits/6-diff-bodies.md) | 13 | 13 | 65 | 11 | 11 | +0 | -54 | OK |
| [D16b-ids-4digits](D16b-ids-4digits/6-diff-bodies.md) | 13 | 13 | 62 | 35 | 28 | -7 | -34 | OK |
| [D16c-ids-prefixados](D16c-ids-prefixados/6-diff-bodies.md) | 13 | 13 | 70 | 47 | 38 | -9 | -32 | OK |

## Totais

- baseline: 197 B
- t02:      93 B  (-104 vs baseline)
- fork:     77 B  (-16 vs t02, -120 vs baseline)

RT: 3/3


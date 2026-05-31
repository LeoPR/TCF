# Sub-exp 03 — validar heur v3 vs M9 baseline D1-D9

## INVARIANT

M9 single-col baseline = soma bytes D1-D9 com default ml=3.
Qualquer welding em src/tcf NAO pode regredir esse total.

## Tabela

| dataset | n | avg | card | num | default | v3 | d(v3) | v3+gating | d(gated) |
|---|---:|---:|---:|---|---:|---:|---:|---:|---:|
| D1-emails-simples | 12 | 14.9 | 1.00 | n | 118 | ml6=119 | +1 | ml3=118 | +0 |
| D2-emails-quote-id | 12 | 19.6 | 1.00 | n | 166 | ml6=156 | -10 | ml3=166 | +0 |
| D3-stress-substring | 12 | 27.7 | 1.00 | n | 177 | ml6=169 | -8 | ml3=177 | +0 |
| D4-caos-mix | 12 | 12.0 | 1.00 | n | 113 | ml6=110 | -3 | ml3=113 | +0 |
| D5-padroes-multiplos | 12 | 33.8 | 1.00 | n | 281 | ml6=280 | -1 | ml3=281 | +0 |
| D6-poucos-em-ruido | 12 | 43.4 | 1.00 | n | 287 | ml6=287 | +0 | ml3=287 | +0 |
| D7-aninhamento | 12 | 27.1 | 1.00 | n | 215 | ml6=215 | +0 | ml3=215 | +0 |
| D8-cabeca-cauda | 12 | 31.0 | 1.00 | n | 100 | ml6=100 | +0 | ml3=100 | +0 |
| D9-frequencia-alta | 20 | 17.6 | 1.00 | n | 158 | ml6=174 | +16 | ml3=158 | +0 |

## Total

- **M9 baseline**: 1615B
- Heur v3 (no gating): 1610B (-5B)
- Heur v3+gating (n>=100): 1615B (+0B)

## Veredito

v3 MELHORA M9 (5B) — pode wedldar SEM gating

## Implicacao welding

Welding deve usar **gating por n_rows >= 100**:

```python
def detect_min_len(values):
    if len(values) < 100:
        return 3  # baseline seguro para datasets pequenos
    return heur_v3(features_of(values))
```

D1-D9 (5-50 rows) cai no fallback. Adult+TPC-H (1000+ rows) recebe heur v3.

# H04 — Variantes de Encoding Numérico

**Status:** ABERTO  
**Deps:** P04, P05  
**LLM calls:** ~600

## Hipótese

Para perguntas aritméticas (soma, média, max, min), a accuracy decresce com a perda de precisão:  
`raw_float > int_scaled > bins_16`

**H4_0 (nula):** `μ_raw_float = μ_int_scaled = μ_bins_16` em perguntas aritméticas.

## Variantes

| Variante | Exemplo (`vl=2.50`) | Chars | Decodificável? |
|----------|---------------------|-------|----------------|
| `raw_float` | `2.5` | 3 | sim, sem perda |
| `int_scaled` | `250` (×100) | 3 | sim, ÷100 |
| `bins_16` | `2` (bin index) | 1 | lossy — precisa de `# BINS: min=1.0 max=12.4 n=16` |

## Design

```
3 variantes × 4 perguntas (Q1-Q4) × 10 modelos × 5 runs = 600 calls
```

## Trade-off Esperado

```
Accuracy:  raw_float ≥ int_scaled >> bins_16
Tokens:    bins_16 < int_scaled ≈ raw_float
```

**Fronteira de Pareto:** Ponto onde bins_16 empata em accuracy com raw_float a menor custo de tokens → recomendação prática do paper para modelos grandes (que conseguem operar com bins).

## Nota

`bins_16` não é reversível — falha H01 por design. Mas pode ser válido para queries ordinais (max/min) onde o modelo só precisa identificar o bin mais alto/baixo, não o valor exato.

Reportar separadamente: accuracy em Q1/Q2 (precisão necessária) vs Q3/Q4 (ordinal suficiente).

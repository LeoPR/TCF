# Sub-exp 03 — prototipos cap K + cap iter (H-PERF-05e + 05f)

**Decisao sub-exp 02**: v1/v2 zero-risk so' deram 1.04x. Gargalo real
e' o loop O(R²) por linha × 99 iters em colunas com refs longos.

Pra ganho real, atacar:
- **v3 cap K**: limitar tamanho max de sub-tupla considerada (K_max)
- **v4 cap iter**: limitar iter_traces max (vs 99 atual)

Ambos podem PERDER bytes. **Medir** trade-off.

## Variantes

| ID | Cap K | Cap iter | Risco bytes |
|---|---|---|---|
| v0 | infinito (16) | 99 | referencia |
| v3-K8 | 8 | 99 | medir |
| v3-K6 | 6 | 99 | medir |
| v3-K4 | 4 | 99 | medir |
| v4-i50 | infinito | 50 | medir |
| v4-i30 | infinito | 30 | medir |
| v5 | 6 | 50 | combined |

## Validacao

1. Bytes vs v0 em D1-D9 + lineitem 1k+5k + Adult Census subset
2. Speedup
3. Se byte loss < 1% absoluto → candidato a welding

## Aceite

- Pelo menos 1 variante: speedup >=2x em lineitem 5k com byte loss <1%
- Documentar matriz speedup × byte loss pra escolha informada

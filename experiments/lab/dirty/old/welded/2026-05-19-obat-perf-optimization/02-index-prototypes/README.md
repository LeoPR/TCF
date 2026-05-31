# Sub-exp 02 — index prototypes

**Objetivo**: testar 3 otimizacoes isoladas, medir ganho em tempo
SEM mudar bytes em D1-D9 (M9 baseline 1615B).

## Variantes

| ID | Nome | Mudanca | Risco bytes |
|---|---|---|---|
| v0 | baseline | copia do `src/tcf/core/online.py` | referencia |
| v1 | len-elim | pre-computa `len(prev)` + evita slice anteriores | **zero** (idiom) |
| v2 | hash-pref | v1 + hash bigrama pra prefix | **zero** se bucket ordenado por id |
| v3 | hash-pref-suf | v2 + hash bigrama pra suffix | **zero** se ambos buckets ordenados |

## Validacao por variante

1. **Byte-match**: tokens emitidos IDENTICOS a v0 em:
   - D1-D9 (controle algoritmo)
   - lineitem 1000 rows (real-world subset)
2. **Tempo**: encode lineitem 5000 rows
3. **Allocacao**: aproximada (line_profiler opcional)

## Arquivos

- `obat_v0_baseline.py` — copia de online.py (NAO importa src/tcf;
  isolacao garante baseline canonical preservado)
- `obat_v1_len_elim.py` — otimizacao 1
- `obat_v2_hash_pref.py` — otimizacao 2 (estende v1)
- `obat_v3_hash_pref_suf.py` — otimizacao 3 (estende v2)
- `benchmark.py` — roda todas, mede, compara bytes
- `result.md` — analise final

## Aceite

- Pelo menos 1 variante: encode 5x+ mais rapido que v0 SEM mudar
  bytes em D1-D9
- Documentar trade-offs (memoria, k=2 vs k=3, etc.)
- Recomendar variante pra sub-exp 03 (welding)

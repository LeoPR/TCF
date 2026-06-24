# 2026-06-24 — H-PERF-05d re-caracterização [lab read-only]

Re-caracteriza o **counter-incremental** do HCC `_detect_compositions` contra o código ATUAL
(prune ADR-0019 + Cython welded DEPOIS do lab original). Decisão do owner (2026-06-24): otimizar o
código, alvo H-PERF-05d, **lab read-only primeiro** — trazer speedup + divergência + escolha (a)/(b)
antes de tocar `src/tcf`.

- `profile_current.py` — profile fresco do encode (lineitem l_comment 5k, de Z:).
- `result.md` — achados + ceiling de speedup + divergência + decisão (a) fix byte-canonical / (b) M11 re-pin.

**NÃO modifica** o lab fechado [`old/refuted/2026-05-22-h-perf-05d-counter-incremental/`](../old/refuted/2026-05-22-h-perf-05d-counter-incremental/)
(regra: lab fechado não se altera; abre-se novo). `src/tcf` intocado.

**Achado + VEREDITO (FECHADO 2026-06-24, owner)**: o rebuild do Counter é ~46% do encode (não 92% —
corrigi a estimativa). Incremental MEDIDO = **~1,5×** pure-Python (não 4–5×), divergência **+0,03–0,05%
só em datetime** (free-text byte-idêntico, RT 100%). A "outra metade" (loop de candidatos) é ~99%
cheap-skip, cortável só com reescrita incremental substancial do detector, e o ganho é **só
pure-Python** (Cython já cobre o compilado, ~2,67×). **Retornos decrescentes → não vale weld.**
`src/tcf` intocado. Frente certa pra velocidade de produção = port Cython, não reescrita do algoritmo.

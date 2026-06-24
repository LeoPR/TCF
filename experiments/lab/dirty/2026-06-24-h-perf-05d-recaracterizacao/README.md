# 2026-06-24 — H-PERF-05d re-caracterização [lab read-only]

Re-caracteriza o **counter-incremental** do HCC `_detect_compositions` contra o código ATUAL
(prune ADR-0019 + Cython welded DEPOIS do lab original). Decisão do owner (2026-06-24): otimizar o
código, alvo H-PERF-05d, **lab read-only primeiro** — trazer speedup + divergência + escolha (a)/(b)
antes de tocar `src/tcf`.

- `profile_current.py` — profile fresco do encode (lineitem l_comment 5k, de Z:).
- `result.md` — achados + ceiling de speedup + divergência + decisão (a) fix byte-canonical / (b) M11 re-pin.

**NÃO modifica** o lab fechado [`old/refuted/2026-05-22-h-perf-05d-counter-incremental/`](../old/refuted/2026-05-22-h-perf-05d-counter-incremental/)
(regra: lab fechado não se altera; abre-se novo). `src/tcf` intocado.

**Achado**: o prune já minimizou a avaliação de candidatos; o rebuild do Counter é hoje ~todo o custo
do `_detect_compositions` (~92% do encode) → o incremental ataca exatamente isso (ceiling ~4–5× no
pure-Python). Divergência conhecida: +0,08% só em datetime (free-text byte-idêntico).

# H-PERF-06-v2 Fase A — Relatório consolidado

> Prune algorítmico + early-termination em HCC `_detect_compositions`,
> com gate byte-canonical. Workflow multi-agente (wf_668f0e90-8ee,
> 2026-05-30): 72 agentes, 7 fases (Map → Baseline → Propose → Verify →
> Prototype → Measure → Synthesize).

## TL;DR

| Métrica | Valor |
|---|---|
| Baseline `_detect_compositions` | **87.72%** do tempo de encode (17.0s de 19.39s) |
| Dataset baseline | online-retail 20k linhas, 8 colunas (1.606.263 chars → 413.648B) |
| Candidatos propostos | 24 (6 lentes × 4) |
| Prototipados + medidos | 20 |
| Speedup > 1 | 15 |
| **Único byte-safe em D1-D9 + D17a + real-world** | **#15 `tier-scoring-02-topK-heap-with-safe-skip` (1.354×)** |

## Baseline (Fase 2)

Profile real (cProfile, online-retail 20k) **confirma** a hipótese
H-PERF-06-v2: `_detect_compositions` domina o encode.

| Função | cumtime | % | chamadas |
|---|---|---|---|
| `_detect_compositions` (syntax.py:225) | 17.008s | **87.72%** | 8 |
| `_estimate_baseline_chars` (syntax.py:364) | 3.592s | 18.53% | 291.183 |
| `len()` (builtin) | 1.962s | 10.12% | 9.833.462 |
| `list.append` | 1.208s | 6.23% | 4.190.333 |
| `list.extend` | 0.886s | 4.57% | 459.941 |

`tottime` puro do corpo do detector = 10.301s (53.13%); somado a
`_estimate_baseline_chars` (291k chamadas) = ~72% do encode. Confirma
que o alvo de otimização é o número de sub-tuplas enumeradas, não as
operações per-iteração.

## Resultado líder validado (Fase 5-6)

**#15 `tier-scoring-02-topK-heap-with-safe-skip` — 1.354× speedup**
(19.39s → 14.33s)

- Substitui o full-scan de candidatos por heap top-K com skip
  provadamente seguro (descarta candidatos cujo upper-bound `net` é
  menor que o K-ésimo melhor já visto).
- Reduz `_detect_compositions` em ~33% sem alterar o pick final.
- **Bytes idênticos** em D1-D9 (1523B), D17a (322B), online-retail
  (413.648B) — único variante byte-safe nos 3 níveis.
- Compatível com `PYTHONHASHSEED=0` (tie-break preservado: heap
  ordering idêntica ao first-wins atual).

## Achado metodológico crítico

**#03 `prune-k-03-adaptive-min-k-by-iter`** — 1.413× MAS **regrediu
bytes em real-world** (+2458B / +0.59% em online-retail), **apesar de
passar D1-D9 (1523B) + D17a (322B)**.

Padrão idêntico ao incidente Pacote 2 (2026-05-21: 15.7% sintético vs
0.13-1.13% real-world). O mini-suite D1-D9 + D17a **não cobre o regime
`n_tam_est >= 3`** que aparece em colunas reais com `atom_count` alto.
Picks K=2 que parecem "rarely profitable" em sintéticos são regulares
e necessários em colunas reais.

→ Gerou o ticket **T-REGRESSION-REAL-WORLD** (gate de welding).

## Lições dos UNSAFE (4 rejeitados)

1. **#03 adaptive-min-k** — passou mini-suite, falhou real-world. Lição:
   regression mini-suite é insuficiente para prune algorítmico.
2. **#04 rare-k2-second-chance** — 0.70× (27.6s). Half-measure: estado
   entre iterações sem pruning agressivo custa mais do que economiza.
3. **#02 zero-net-prepeek** — falhou D1-D9 (1527B vs 1523B). Pre-peek de
   candidatos net=0 alterou a ordem de avaliação → mudou tie-break do
   Counter. Lição: qualquer reorganização da ordem de visita das
   sub-tuplas é alto-risco para byte-canonical.

Padrão geral: o detector HCC é **determinístico-por-construção mas
frágil-a-refactor**. Prune só é seguro quando provadamente não remove
um candidato que o pick original escolheria — e essa prova precisa ser
feita contra real-world, não apenas mini-suite.

## Avaliação Amdahl

Baseline P = 0.8772. Sp = 1/((1−P) + P/N):

| Redução de `_detect_compositions` | Speedup total | Tempo |
|---|---|---|
| 25% (N=1.33) | 1.22× | 15.9s |
| 50% (N=2.0) | 1.78× | 10.9s |
| 75% (N=4.0) | 2.92× | 6.6s |
| 80% (N=5.0) | 3.21× | 6.0s |
| 90% (N=10) | 4.50× | 4.3s |
| 100% (N=∞) | 8.15× (teto absoluto) | — |

O líder byte-safe medido (1.354×) corresponde a ~33% de redução do
detector — bate o Amdahl esperado. **Python puro com byte-canonical
preservado topa em ~1.5-1.8×.** Para >2× é necessário Cython/Rust
(Fase B) ou afrouxar o contrato canonical.

## Próximos passos

1. **T-REGRESSION-REAL-WORLD** (P1) — congelar bytes de amostras Adult,
   TPC-H, online-retail no regression suite. **Precede** qualquer
   welding de prune algorítmico.
2. **Welding de #15** — após T-REGRESSION-REAL-WORLD; abrir
   H-PERF-06-v2-T01 + ADR-0019. Re-validar #15 contra as amostras
   real-world primeiro (Fase 4 do ticket).
3. **Fase B (Cython)** — track paralelo; alvo `_detect_compositions` +
   `_estimate_baseline_chars` + enumeração O(R²). Target pós-Cython
   realista: 4-6× total. Compatível com filosofia "texto +
   explicabilidade" (código compilado é interno, não muda formato).
4. **16 candidatos marginais (~1%)** — backlog; não welding individual
   (overhead de código não compensa). Bundle possível se Fase B abrir
   revisão integral.

## Open questions

1. Regression real-world (T-REGRESSION-REAL-WORLD) precede tudo.
2. Cobertura HCC em colunas com cardinalidade extrema (>50k únicas) não
   exercitada — possível regime onde mesmo #15 regride.
3. Interação #15 × seq-RLE não isolada (medições usaram pipeline
   canonical completo).
4. Determinismo multi-thread (test_parallel) precisa re-validação
   pós-mudança de ordem de visita.
5. Medições são single-run cProfile; ganhos <5% (#11, #16, #18, #20)
   indistinguíveis de ruído sem N≥5 repetições.

## Estrutura do lab

- `00-baseline/` — runner + baseline.prof + profile
- `NN-<candidate-id>/` — 20 sub-experimentos (syntax_variant.py fork +
  runner_regression.py + runner_profile.py + variant.prof)
- Workflow script: `.claude/workflows/h-perf-06-v2-fase-a.js`

## Conexões

- [docs/theory/h-perf-06-exploration.md](../../../../docs/theory/h-perf-06-exploration.md) — estudo original (REFRAMED)
- [tickets/T-REGRESSION-REAL-WORLD.md](../../../../tickets/T-REGRESSION-REAL-WORLD.md) — gate de welding
- [ADR-0018](../../../../docs/adr/0018-v2-format-roadmap.md) — V2-J streaming (alternativa estrutural Fase C)

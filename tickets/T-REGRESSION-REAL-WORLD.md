---
title: T-REGRESSION-REAL-WORLD — Estender regression suite para amostras real-world (gate prune algoritmico)
status: closed-done
priority: P1
created: 2026-05-30
closed: 2026-05-31
blocked-by: []
related:
  - tests/test_regression_v1_baseline.py  (mini-suite atual, D1-D9 + D17a)
  - experiments/lab/dirty/2026-05-27-h-perf-06-v2-fase-a/  (workflow que expos a lacuna)
  - docs/theory/h-perf-06-exploration.md  (alvo: validar prune antes de weldar)
---

# T-REGRESSION-REAL-WORLD — Real-world regression gate

## Contexto

A Fase A de H-PERF-06-v2 (workflow 2026-05-30) descobriu que o regression
mini-suite atual (D1-D9 = 1523B + D17a = 322B) **NAO COBRE o regime
`n_tam_est >= 3`** que aparece em colunas reais com `atom_count` alto.

Caso concreto: candidato `prune-k-03-adaptive-min-k-by-iter` deu 1.413x
speedup, **passou** D1-D9 (1523B) + D17a (322B), mas **regrediu bytes em
online-retail 20k**: +2458B / +0.59% (413.648B → 416.106B).

Padrao identico ao incidente 2026-05-21 (Pacote 2 escape deduction: 15.7%
sintetico vs 0.13-1.13% real-world). Confirma empiricamente a [filosofia
ja' registrada](experiments/lab/dirty/notas/revisao-conceitual-2026-05-21.md)
de que sintetico/mini-suite NAO basta.

**Sem este ticket fechado, NAO weldar prune algoritmico** (e.g., #15
`tier-scoring-02-topK-heap-with-safe-skip` da Fase A esta gated por isso).

## Estado atual

- **Mini-suite existe**: `tests/test_regression_v1_baseline.py` congela
  D1-D9 (1523B total + per-dataset) + D17a (322B) byte-canonical.
- **Real-world ausente do regression**: Adult Census, TPC-H lineitem,
  online-retail nao tem bytes congelados. Sao usados em benchmarks
  (`experiments/lab/dirty/`) mas nao em testes.
- **Infra existe**: `scripts/dataset_reader.py` le canonicos do hub SQLite
  em `Z:/tcf-data/interim/`.

## Plano

### Fase 1 — Escolher amostras canonicas

Critica: amostras tem que ser **fixadas** (mesmo seed/criterio) pra
byte-canonical ser estavel. Candidatos por dataset:

- **Adult Census**: amostra fixed-seed de N=5.000 linhas (colunas
  textuais: workclass, education, occupation, country, marital_status,
  relationship, race, sex)
- **TPC-H lineitem**: amostra fixed-seed de N=5.000 linhas (colunas:
  l_shipinstruct, l_shipmode, l_comment ou subset)
- **online-retail**: amostra fixed-seed de N=5.000 linhas (colunas:
  Description, StockCode, Country, InvoiceDate)

Cada um devera resultar em byte-count INVARIANT (e.g., adult-5k = 12.345B,
tpch-5k = 8.765B, retail-5k = 23.456B). Numeros placeholder; medir.

### Fase 2 — Tests

Adicionar em `tests/test_regression_v1_baseline.py`:

- `TestRealWorldByteCanonical`:
  - test_adult_5k_invariant (1 byte-count fixo, RT)
  - test_tpch_5k_invariant (idem)
  - test_retail_5k_invariant (idem)
- Marcar como `@pytest.mark.real_world` pra opt-in (skip em CI rapido,
  obrigatorio em pre-welding de prune algoritmico)

### Fase 3 — Doc + gate

- ADR-0019 ou atualizar ADR-0017: regression real-world e' GATE
  bloqueante pra welding de qualquer mudanca em `_detect_compositions`
  ou pre-pass que toque HCC.
- Atualizar `CLAUDE.md` no "Antes de declarar confirmada-empirica" pra
  incluir "se mudanca toca HCC, RT real-world obrigatorio".

### Fase 4 — Re-validar candidato #15 (gated)

- Rodar `experiments/lab/dirty/2026-05-27-h-perf-06-v2-fase-a/15-tier-scoring-02-topK-heap-with-safe-skip/`
  contra Adult + TPC-H samples (Fase 1)
- Confirmar byte-canonical em todas as 3 amostras
- Se OK → ABRIR ticket H-PERF-06-v2-T01 (welding)
- Se NOK → registrar como segundo caso da licao "mini-suite insuficiente"

## Resolucao (2026-05-31)

Implementado em `experiments/lab/dirty/2026-05-31-regression-real-world/`.
Desvio do plano original (melhor): em vez de amostras fixed-seed via shaper
+ `@pytest.mark.real_world` (skip se Z: ausente), usei **fixtures committadas
deterministicas** (primeiros 2000 valores de colunas free-text) — portaveis,
sem dependencia de Z:, sem shaper (que ainda nao tem aprovacao estatistica,
ver T-SHAPER-SCIENTIFIC-GATING). Regression fixture precisa ser ESTAVEL, nao
estatisticamente representativa.

Achado: amostras de 100 linhas (as committadas pre-existentes) NAO discriminam
#03 — mesmo blind spot do mini-suite. Colunas categoricas low-card (adult)
tambem nao. So' free-text >=1000 linhas atinge o regime. Fixtures escolhidas
(2000 linhas, provadas discriminantes):
- retail Description (27581B), retail StockCode (11437B), lineitem l_comment (50598B)

#15 (topK-heap) confirmado byte-safe nas 3 — Fase 4 concluida, welding
desbloqueado (abrir H-PERF-06-v2-T01).

## Criterio de aceite

- [x] Fixtures deterministicas committadas + gerador reproduzivel documentado
- [x] Bytes-count frozen em `tests/test_real_world_snapshots.py` (7 testes verdes)
- [x] Tests passam com baseline atual (sem mudanca em src/tcf)
- [x] CLAUDE.md atualizado (gate em "Antes de declarar confirmada-empirica")
- [x] #15 re-validado byte-safe nas fixtures real-world (Fase 4)
- [x] Fixtures PROVAM poder discriminante (catch #03: +549/+92/+427)

## Conexao

- Bloqueia: H-PERF-06-v2-T01 (welding de #15) e qualquer outro prune
  algoritmico futuro
- Motivado por: Fase A workflow (wf_668f0e90-8ee, 2026-05-30)
- Filosofia: [feedback-validacao-e-dados](C:/Users/leona/.claude/projects/.../memory/feedback_validacao_e_dados.md),
  [checklist 5-perguntas em CLAUDE.md](../CLAUDE.md)
- Custo estimado: 1 sessao (Fase 1+2+3); Fase 4 depende de #15

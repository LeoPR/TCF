# 0019 — Weld do prune top-K em HCC _detect_compositions (H-PERF-06-v2 #15)

**Status**: accepted
**Date**: 2026-05-31
**Deciders**: project owner
**Tags**: performance, hcc, internal-optimization, byte-canonical, v1.x

> Otimização **interna** (sem mudança de formato nem de API). Compatível
> com o freeze v1.0 (ADR-0017): output byte-idêntico, `#TCF.6` intacto.

## Context and Problem Statement

O estudo H-PERF-06 (reframed, ver
[docs/theory/h-perf-06-exploration.md](../theory/h-perf-06-exploration.md))
mostrou via profiling real que o hotspot do encode **não** é lcp/lcs
(1.8%, Amdahl-blocked) e sim HCC `_detect_compositions`: **87.72%** do
tempo em online-retail 20k (17.0s de 19.4s). Dentro dele,
`_estimate_baseline_chars` é chamado ~291k vezes (18.5%).

A Fase A (workflow multi-agente, 2026-05-30) gerou 24 candidatos de prune
algorítmico, prototipados em fork dirty
([experiments/lab/dirty/2026-05-27-h-perf-06-v2-fase-a](../../experiments/lab/dirty/2026-05-27-h-perf-06-v2-fase-a)).
Apenas **um** candidato foi byte-safe em todos os níveis de regressão:
`#15 tier-scoring-02-topK-heap-with-safe-skip`.

Achado crítico: o candidato `#03` deu speedup maior (1.41×) mas **regrediu
bytes em real-world** (+0.59% em online-retail) apesar de passar o
mini-suite (D1-D9 + D17a). Isso motivou o gate
[T-REGRESSION-REAL-WORLD](../../tickets/T-REGRESSION-REAL-WORLD.md)
(test_real_world_snapshots.py), pré-requisito deste weld.

## Decision

Weldar **apenas** o candidato #15 em
[src/tcf/composicional/syntax.py](../../src/tcf/composicional/syntax.py)
`_detect_compositions`. Duas mudanças, contidas no loop de candidatos:

1. **Cheap upper-bound prune** antes de chamar `_estimate_baseline_chars`:
   para cada sub-tupla, computa um limite superior conservador de `net` e
   descarta o candidato se nem o upper-bound bate o `best_net` corrente.
2. **Running-max inline**: funde os dois passos (build candidates → pick)
   num único loop, atualizando `best`/`best_net` durante a iteração.

### Safety byte-canonical (invariante)

```
net      = (R-1) * (baseline - n_tam)
baseline <= K * n_est_ub + (K-1)          # upper bound de _estimate_baseline_chars
n_tam    >= n_tam_min                       # para todo K >= 2
n_est_ub = max(2, len(str(atom_count + comp_acc_k + len(contagem) + 9)))  >= n_est
n_tam_min = len(str(atom_count + comp_acc_k + 1))                          <= n_tam
=> ub_net >= net  (sempre)
```

Como `ub_net >= net`, `if ub_net <= best_net: continue` só descarta
candidatos cujo `net` real também perderia o pick. A **ordem do Counter**
é preservada e o tie-break continua first-wins (`net > best_net`, estrito),
idêntico ao algoritmo de 2 passos original. `candidates` continua sendo
construído (consumido por `_build_trace`).

## Evidência

- **Byte-canonical preservado**: suite completa **269 passed, 2 xfailed**.
  D1-D9 = 1523B, D17a = 322B, e as 3 fixtures real-world
  (description-2k=27581B, stockcode-2k=11437B, lcomment-2k=50598B)
  byte-idênticas pré/pós weld.
- **Prune ativo**: `_estimate_baseline_chars` chamado **87.4% menos**
  (72.121 → 9.093 em online-retail Description 8k).
- **Speedup**: 1.22× nessa coluna isolada; 1.354× medido na Fase A no
  encode completo (8 col × 20k) onde o hotspot domina mais.

## Amdahl / escopo

Com P=0.8772, Python puro byte-safe topa em ~1.5-1.8×. Para >2× é
necessário Cython (Fase B, alvo `_detect_compositions` +
`_estimate_baseline_chars`) ou V2-J streaming (ADR-0018). Este weld é o
ganho algorítmico seguro disponível sem ferramenta nova.

## Consequences

- **Positivo**: ~1.2-1.35× no encode real-world, sem custo de formato.
- **Neutro**: trace (`_build_trace`) inalterado; API e `#TCF.6` intactos.
- **Gate permanente**: mudanças futuras em `_detect_compositions` /
  pre-pass / qualquer prune devem passar **os dois** suites de regressão
  (mini + real-world). Registrado em CLAUDE.md.
- **Compatível v1.x** (ADR-0017): otimização interna, não muda bytes nem
  superfície pública.

## Conexões

- [docs/theory/h-perf-06-exploration.md](../theory/h-perf-06-exploration.md) — estudo (reframed)
- [T-REGRESSION-REAL-WORLD](../../tickets/T-REGRESSION-REAL-WORLD.md) — gate (pré-requisito)
- [ADR-0017](0017-format-spec-v1-frozen.md) — freeze (este weld respeita)
- [ADR-0018](0018-v2-format-roadmap.md) — Fase B/Cython + V2-J streaming (futuro)

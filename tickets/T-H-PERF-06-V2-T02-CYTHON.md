---
title: T-H-PERF-06-V2-T02 — Acelerador Cython opcional de _detect_compositions (Fase B)
status: closed-done
priority: P1
created: 2026-05-31
closed: 2026-05-31
blocked-by: []
related:
  - docs/adr/0020-cython-optional-accelerator.md
  - tickets/T-H-PERF-06-V2-T01-WELD-15.md  (Fase A #15, pre-req — closed-done)
  - experiments/lab/dirty/old/welded/2026-05-31-h-perf-06-v2-fase-b/
---

# T-H-PERF-06-V2-T02 — Fase B (Cython)

## Resumo

Acelerador Cython OPCIONAL de `_detect_compositions` (hotspot pos-weld =
64.5% tottime). Owner aprovou tocar src/tcf + escolheu distribuicao
"acelerador opcional + fallback silencioso".

## Entregue

- `src/tcf/_core/detect.pyx` — porte Cython (typed locals; estruturas Python
  mantidas -> byte-safe por construcao)
- `src/tcf/_core/__init__.py`
- `composicional/syntax.py` — runtime try-import + fallback pure-Python
  silencioso (`_detect_compositions_accelerated` flag)
- `hatch_build.py` — hook best-effort (compila no pip install; nunca falha)
- `pyproject.toml` — cython em build-system.requires + hook registrado +
  sdist enxuto (exclui experiments/old/docs/datasets; 18MB->54KB)
- ADR-0020

## Gate (criterio de aceite)

- [x] Re-profile pos-weld (alvo correto: corpo de _detect, nao _estimate)
- [x] Byte-canonical compiled: 269 passed, 2 xfailed (D1-D9=1523B, D17a=322B,
      3 fixtures real-world exatas)
- [x] Byte-canonical fallback (pyd oculto): accelerated=False, bytes identicos
- [x] Speedup: 2.15x encode completo / 2.31x coluna detect-dominada / 2.67x vs pre-weld
- [x] Wheel platform-tagged inclui .pyd; sdist source-only contem hook+pyx+fallback
- [x] src/tcf tocado SOMENTE com aprovacao (acelerador + wiring)

## Nao incluido (backlog/futuro)

- **CI multi-plataforma (cibuildwheel)**: nao feito (research-stage; decisao
  futura se/quando release publica). Hoje: build local best-effort.
- **Cython em outras funcoes** (_tokenize_pieces, _emit_body, online.py):
  alvos menores pos-weld; reavaliar so' se Fase B nao bastar.
- **V2-J streaming** (ADR-0018): alternativa estrutural v2.0, ortogonal.

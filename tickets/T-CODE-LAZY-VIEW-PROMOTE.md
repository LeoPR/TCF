---
title: T-CODE-LAZY-VIEW-PROMOTE — Promover lazy view do gadget pro core (tcf.view)
status: closed
priority: P1
created: 2026-06-21
updated: 2026-06-21
related:
  - experiments/lab/dirty/notas/v08-plano-etapas.md
  - experiments/lab/dirty/2026-06-19-lazy-testbank/result.md
  - src/tcf/view.py
  - tickets/T-DOC-LAZY-REFERENCE.md
  - tickets/T-DIST-RELEASE-0.8.0.md
---

# T-CODE-LAZY-VIEW-PROMOTE (A4 do plano 0.8)

## Contexto / motivação

A view lazy/consultável (descomprime só o suficiente pra responder `count/sum/min/
max/avg` + `where` + group-by) viveu como **gadget** em `scripts/tcf_lazy/` durante
A1-A3 (banco de testes, fechamento de bug de dupla-contagem, otimização do caminho do
algoritmo). `scripts/` **não vai no wheel** (`pyproject` `packages=["src/tcf"]`, sdist
exclui `/scripts`) — então o lazy não shipava no pacote. Shipar o lazy é o **escopo
central do 0.8** (`v08-plano-etapas.md` §A).

## Plano (executado)

Mover `scripts/tcf_lazy/lazy.py` → **`src/tcf/view.py`** (camada read-only do core;
lê `#TCF.7`/`#TCF.6`, **não muda encode/decode/formato**), exportar no `__init__`,
deixar `scripts/tcf_lazy/` como **shim de compat**.

## Critério de aceite (atingido)

- [x] `git mv` preserva history (`RM scripts/tcf_lazy/lazy.py -> src/tcf/view.py`).
- [x] `from tcf import view, LazyTCF, Filtered` funciona; `view in tcf.__all__`.
- [x] Shim: `from tcf_lazy import view` re-exporta o **mesmo objeto** (`test_a4_shim_backcompat`).
- [x] **Zero regressão byte-canonical**: D1-D9=1523B, D17a=303B, real-world=89616B intactos.
- [x] Suíte CI-friendly verde: **380 passed**, 2 skipped, 1 xfailed (`-m "not requires_data"`).
- [x] `EXPECTED_PUBLIC_API` (test_regression_v1_baseline) atualizado com os 3 exports.

## Aprovação

Owner aprovou o toque em `src/tcf/` (aditivo, read-only, risco baixo) em 2026-06-21.

## Riscos / notas

- Aditivo: não toca encode/decode/formato; único acoplamento é reuso de internos
  já usados (`tcf.multi._decode_v2b/_decode_struct_split`, `tcf.decoder._decode_column`).
- **Versão NÃO bumpada** aqui (segue 0.7.1). O bump 0.7.1→0.8.0 + nota de release saem
  juntos no workstream C ([T-DIST-RELEASE-0.8.0](T-DIST-RELEASE-0.8.0.md)) — o teste
  `test_version_pre_1_0` segue pinando 0.7.1 até lá.
- A5 (reference Diátaxis da API) é o próximo de A: [T-DOC-LAZY-REFERENCE](T-DOC-LAZY-REFERENCE.md).

## Updates

- **2026-06-21**: executado e verificado (380 passed). `src/tcf/view.py` no wheel via
  `packages=["src/tcf"]` (sem mudança no pyproject). CLOSED.

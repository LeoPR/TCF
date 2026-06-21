# 0020 — Acelerador Cython opcional de _detect_compositions (H-PERF-06-v2 Fase B)

**Status**: accepted
**Date**: 2026-05-31
**Deciders**: project owner
**Tags**: performance, cython, packaging, internal-optimization, byte-canonical, v1.x

> Acelerador **opcional** com fallback pure-Python silencioso. Output
> byte-idêntico, sem mudança de formato/API (compatível ADR-0017). Core
> compilado é interno (espírito ADR-0018): só acelera, não compete com gzip.

## Context

Após o weld #15 (ADR-0019), re-profiling pós-weld (online-retail 20k×8col)
mostrou que `_estimate_baseline_chars` deixou de ser hotspot (3.59s→0.21s; o
#15 cortou 87% das chamadas). O alvo real passou a ser o **corpo de
`_detect_compositions`** (tottime 9.53s = **64.5%** do encode), dominado pelos
loops de enumeração de sub-tuplas, Counter e substituição — mais 7.2M `len()`
+ 3.6M `append()` disparados de dentro dele.

Python puro topa em ~1.8× (Amdahl). Para ir além sem mudar bytes, é preciso
código compilado (Fase B).

## Decision

Adicionar `src/tcf/_core/detect.pyx` — porte Cython de `_detect_compositions`
com **typed locals** (`cdef Py_ssize_t` em contadores/comprimentos, `cdef
list` nas listas quentes) mantendo **todas as estruturas Python** (Counter/
dict/tuple/list) → ordem de inserção e tie-break first-wins preservados
byte-exato. Distribuição como **acelerador opcional** (escolha do owner):

1. **Runtime**: `composicional/syntax.py` tenta
   `from tcf._core.detect import _detect_compositions` e, se presente, troca o
   método pure-Python por ele. `except Exception` → fallback silencioso ao
   pure-Python (que permanece o caminho canônico/legível). Flag
   `M8AVirtualRefsSyntax._detect_compositions_accelerated`.
2. **Build**: hook hatchling best-effort (`hatch_build.py`) tenta compilar no
   `pip install`; se Cython/compilador ausente ou qualquer erro, **não falha**
   — emite warning e gera wheel pure-Python. `cython>=3.0` em
   `build-system.requires`. Wheel com extensão = platform-specific.
3. **sdist enxuto**: `[tool.hatch.build.targets.sdist]` exclui experiments/,
   old/ (v0.5 legado), docs/, datasets/ — sdist 18MB→54KB, source-only
   (corrige defeito latente: `old/` vinha sendo empacotado).

## Por que opcional (não wheels prebuilt / não opt-in extra)

Lib research-stage sob freeze v1.0. "Acelerador opcional + fallback" dá o
ganho a quem tem toolchain (owner, p/ experimentos em datasets maiores) sem
exigir maquinário cibuildwheel (prematuro) nem deixar a maioria sem speedup
(opt-in extra). `pip install tcf` funciona em qualquer ambiente.

## Evidência

- **Byte-canonical (compiled)**: suite completa **269 passed, 2 xfailed**.
  D1-D9=1523B, D17a=322B, 3 fixtures real-world exatas.
- **Byte-canonical (fallback)**: com .pyd oculto, `accelerated=False`,
  D1-D9=1523B, description-2k=27581B — pure-Python idêntico.
- **Speedup**: 2.31× (coluna detect-dominada) / **2.15×** (encode completo
  20k×8col, 6.43s→2.99s) / 2.67× vs pré-weld. Rompe o teto Amdahl.
- **Packaging**: wheel `cp313-win_amd64` (92KB) inclui o .pyd; sdist (54KB)
  contém hook + .pyx + fallback pure-Python + metadata.

## Consequences

- **Positivo**: ~2.15× no encode quando compilado; install puro-Python sempre
  funciona; sem mudança de bytes/formato/API.
- **Custo**: nova subárvore `src/tcf/_core/` + hook de build + dep de build
  cython. Sem CI de wheels multi-plataforma ainda (decisão futura se/quando
  release).
- **Gate**: `_core/detect.pyx` e o pure-Python em syntax.py DEVEM permanecer
  byte-equivalentes; ambos cobertos pelos dois suites de regressão (mini +
  real-world). Mudança num exige a no outro.
- **NUNCA modificar src/tcf sem aprovação** agora inclui `src/tcf/_core/`.

## Conexões

- [ADR-0019](0019-hcc-detect-compositions-topk-prune.md) — weld #15 (pré-req)
- [ADR-0018](0018-v2-format-roadmap.md) — core compilado interno (V2-L spirit)
- [ADR-0017](0017-format-spec-v1-frozen.md) — freeze (este respeita: byte-idêntico)
- Lab: `experiments/lab/dirty/old/welded/2026-05-31-h-perf-06-v2-fase-b/`

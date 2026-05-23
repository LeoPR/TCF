---
title: T-CI-2 — Refactor tests CI-friendly (archive v0.5 + marker requires_data + new core_rt)
status: closed
resolution: refactor-completed
priority: P3
created: 2026-05-23
updated: 2026-05-23
closed: 2026-05-23
blocked-by: []
related:
  - tickets/T-CI-1-github-actions.md
  - tests/_archive_v05/
  - tests/test_core_rt.py
---

# T-CI-2 — Refactor tests CI-friendly

## Contexto / motivacao

T-CI-1 Fase 1 (workflow CI lint apenas) identificou que `tests/`
nao podia rodar em CI:
- 4 arquivos com imports v0.5 broken (encode_columns, EncodeConfig,
  tcf.timing — removidos em v0.6)
- 2 arquivos dependentes de SQLite Z:/tcf-data
- 1 arquivo com fixtures missing

Refactor necessario antes do job `test` no CI.

## Plano

Approach pragmatico (sem mockar SQLite real):
1. **Archive tests v0.5 broken**: mover pra `tests/_archive_v05/` (preserva
   git history, excluir de discovery)
2. **Marker `requires_data`**: tests SQLite-dependent ganham marker;
   CI roda `pytest -m "not requires_data"`
3. **Tests CI-friendly novos**: criar `test_core_rt.py` com round-trip
   basicos sem deps externos (target M10 baseline + edge cases)

## Implementacao

### Archive v0.5 broken (`tests/_archive_v05/`)

Movidos via `git mv`:
- `test_compression_benchmark.py` (importa `encode_columns`)
- `test_encode_canonical.py` (importa `encode_columns`, `EncodeConfig`)
- `test_encode_decode.py` (importa `EncodeConfig`)
- `test_p01_p02_p03.py` (importa `llm_eval.*` v0.5 Phase 1)
- `test_timing.py` (importa `tcf.timing` modulo removido)

README documentando archive criado.

### `tests/conftest.py`

Pytest config: auto-marca tests em `test_shaper` com `requires_data`
(via `pytest_collection_modifyitems`).

### `pyproject.toml [tool.pytest.ini_options]`

```toml
testpaths = ["tests"]
norecursedirs = ["_archive_v05", "fixtures"]
markers = [
    "requires_data: tests that need SQLite hubs in Z:/tcf-data/ (skipped in CI)",
]
```

### `tests/test_core_rt.py` (NOVO)

31 tests CI-friendly cobrindo:
- Round-trip basico (single, duplicates, special chars, comma fix ADR-0007)
- M10 baseline INVARIANT (1523B em D1-D9)
- ColumnFeatures (H-DA-11c)
- detect_min_len (H-DA-11, gating + heur v3)
- Edge cases (unicode, long string, many duplicates)
- 1 xfail documentado (encode([]) edge case)

### `.github/workflows/ci.yml` (job test ATIVADO)

```yaml
test:
  runs-on: ubuntu-latest
  strategy:
    matrix:
      python-version: ['3.10', '3.11', '3.12']
  steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-python@v5 (com matrix.python-version)
    - pip install -e ".[dev]"
    - pytest tests/ -m "not requires_data" -v
```

## Validacao local

`pytest tests/ -m "not requires_data" -q`:
```
30 passed, 50 deselected, 1 xfailed in 0.53s
```

Tests deselected sao do `test_shaper.py` (precisa SQLite Z:/).

## Criterio de aceite

- [x] Tests v0.5 broken movidos pra tests/_archive_v05/
- [x] tests/conftest.py com marker requires_data
- [x] pyproject.toml com testpaths + norecursedirs + markers
- [x] tests/test_core_rt.py com tests CI-friendly (30 pass + 1 xfail)
- [x] .github/workflows/ci.yml com job test ativo (matrix 3.10/3.11/3.12)

## Updates datados

### 2026-05-23 — execucao + fechamento

Refactor completo em uma rodada. CI agora roda lint + test em 3 versoes
Python. Tests dataset-dependentes (Z:/SQLite) ficam disponiveis pra
rodar local mas pulam em CI via marker.

Aprendizado: solucao "marker + archive + new minimal suite" foi mais
pragmatica que mockar SQLite (que requereria duplicar fixtures + criar
DBs in-memory). 30 RT tests cobrem APIs principais.

**Resolution**: refactor-completed.

## Conexoes

- T-CI-1 (Fase 1 lint) — pre-requisito
- ADR-0011 (M10 baseline 1523B testado em test_m10_baseline_invariant)
- ADR-0010 (auto_min_len testado)
- ADR-0007 (comma fix testado em test_pacote3_comma_in_literal)

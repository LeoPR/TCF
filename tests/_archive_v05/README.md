# tests/_archive_v05/

**Status**: ARCHIVED 2026-05-23 (T-CI-2)

Tests do ciclo v0.5 (LLM benchmark Phase 1, formato columnar) que
importam APIs nao-existentes no v0.6+ canonical:
- `encode_columns`, `encode_rows`, `EncodeConfig` (removidos em v0.6)
- `tcf.timing` (modulo removido)
- `llm_eval.metrics`, `llm_eval.ground_truth` (Phase 1 LLM, ainda em
  `experiments/eval/` mas nao parte do core)

Esses tests ficam aqui como REFERENCIA HISTORICA. Nao sao coletados
por pytest (excluidos via `pyproject.toml [tool.pytest.ini_options]
norecursedirs`).

## Conteudo

| Arquivo | Origem | Por que arquivado |
|---|---|---|
| `test_compression_benchmark.py` | v0.5 | importa `encode_columns` (removido) |
| `test_encode_canonical.py` | v0.5 | importa `encode_columns`, `EncodeConfig`, depende Z:/SQLite |
| `test_encode_decode.py` | v0.5 | importa `EncodeConfig` (removido) |
| `test_p01_p02_p03.py` | v0.5 LLM Phase 1 | importa `llm_eval.*`, depende `data/` dir |
| `test_timing.py` | v0.5 | importa `tcf.timing` (modulo removido) |

## Restauracao futura

Se v0.5 LLM benchmark for revivido como projeto a parte, mover esses
tests pra repo dedicado. Ate' la' ficam aqui.

Tests CI-friendly novos pra v0.6+ canonical vivem em `tests/`:
- `test_core_rt.py` — round-trip basicos sem deps externos
- `test_shaper.py` — integration (requires SQLite Z:/, skipado em CI)

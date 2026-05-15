"""Compactacao composicional — M8.A welded para src/.

`syntax.py`: copia adaptada de
`experiments/lab/dirty/2026-05-16-M8-virtual-refs-clean-output/M8-A-detector-unificado/syntax.py`.

Detector unificado (refs atomicos + virtuais) + emit composicional
(`~` cria ref auto-nomeado, `,` concat efemero). Convencao output:
sem brackets, LF only.

Adaptacoes vs original (welding step 2, 2026-05-17):
- `from online import ...` → `from tcf.core.online import ...`
- `from syntax_base import ...` → `from tcf.core.syntax_base import ...`
- removido `sys.path.insert(...)` (Python package resolve naturalmente)

Logica de encode/decode permanece byte-exata. Validado por M12.

Para uso definitivo via `from tcf import encode`, ver welding step 3
(API publica).
"""

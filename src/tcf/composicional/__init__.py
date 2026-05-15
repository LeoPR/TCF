"""HCC — Hierarchical Compositional Coding.

Camada 2 do TCF. Consome tokens raiz de OBAT e produz texto TCF
compacto via:
- Detector iterativo greedy de sub-tuplas reusaveis
- Emit com operadores `~` (cria ref auto-nomeado) e `,` (concat efemero)
- Pairwise left-assoc binarization
- Range `a..b` como caso particular de composicao por sequencia
- Output: sem brackets, LF only

`syntax.py` e' adaptacao byte-exata em logica de
`experiments/lab/dirty/2026-05-16-M8-virtual-refs-clean-output/M8-A-detector-unificado/syntax.py`
(codnome de origem: `M8.A`).

Adaptacoes vs original (welding step 2, 2026-05-17):
- `from online import ...` → `from tcf.core.online import ...`
- `from syntax_base import ...` → `from tcf.core.syntax_base import ...`
- removido `sys.path.insert(...)` (Python package resolve naturalmente)

Logica de encode/decode permanece byte-exata. Validado por M12 + M13 + M14.

Ver `docs/algorithms/HCC.md` para detalhamento (estrutura,
sub-linguagem matematica, body-order constraint, diferencial vs
Re-Pair / Sequitur / LZW).

Para uso via API publica: `from tcf import encode, decode`.
"""

"""schema_gadget — ferramenta AUXILIAR de análise de schema/qualidade.

NAO faz parte do TCF-core. Filosofia: **só detecta e alerta, NUNCA arruma**
(ver docs/theory/schema-gadget-design.md). Consome estruturas genéricas
(dict[tabela, dict[col, valores]]) e/ou SideOutputs do TCF, em paralelo,
sem modificar `src/tcf/`.

Fase 1 (implementada): fk_detect — descobre FK candidates por overlap de
valores entre colunas de tabelas diferentes.
"""

from .fk_detect import FKCandidate, detect_fk_candidates

__all__ = ["FKCandidate", "detect_fk_candidates"]

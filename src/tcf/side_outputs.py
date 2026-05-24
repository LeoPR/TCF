"""SideOutputs — recipiente opcional pra capturar info interna do pipeline.

Passar uma instancia em `encode(data, side_outputs=...)` faz com que
informacao que normalmente eh produzida internamente mas DESCARTADA
(logs do OBAT, traces do HCC, decisoes das heuristicas pre-pass) seja
coletada pra inspecao, debug, ou consumo por modulos futuros (e.g.,
schema_builder, encoder manager).

Filosofia (ADR-0014):
- Sem `side_outputs=`: overhead zero (logs continuam sendo gerados
  internamente, so' descartados — comportamento pre-existente).
- Com `side_outputs=`: campos populados; consumidor le' os que precisa.

Multi-col: `per_col[name]` aninha um SideOutputs por coluna. Campos
single-col ficam None no container externo.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tcf.column_features import ColumnFeatures


@dataclass
class SideOutputs:
    """Recipiente pra side outputs capturados durante encode."""

    # --- Pre-pass (per coluna) ---
    column_features: "ColumnFeatures | None" = None
    cadence_detected: bool | None = None
    cadence_info: dict | None = None
    min_len: int | None = None

    # --- OBAT (per coluna) ---
    obat_log: str | None = None
    obat_used_hint: bool | None = None  # True = processar_with_hint, False = canonical

    # --- HCC (per coluna) ---
    hcc_trace: str | None = None
    hcc_rede: str | None = None
    seq_rle_runs: list[dict] = field(default_factory=list)

    # --- Bytes (per coluna, util pra schema builder/estatisticas) ---
    body_bytes: int | None = None

    # --- Multi-col (so' populado se input foi dict) ---
    multi_info: dict | None = None
    per_col: dict[str, "SideOutputs"] | None = None

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

    # --- Natures / CAMADA 0 (pre-tx por natureza, ADR-0015) ---
    # apply-rate do encode_value, por coluna:
    #   {col_name: {'spec', 'total', 'compressible', 'apply_rate', 'by_status'}}
    # Single-col usa a chave 'val'. So' populado se nature/nature_per_col foi
    # passado E side_outputs nao e' None. NAO afeta os bytes do .tcf — e'
    # telemetria do efeito colateral (quantos valores comprimiram vs cairam
    # literal). Habilita auto-detect informado no futuro (Fase 3 schema natures).
    nature_apply: dict | None = None

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
    # body_bytes = tamanho do CANDIDATO TCF da coluna (a coluna FOI encodada nesse
    # tamanho antes do min() V2-A escolher) — telemetria valida de custo de
    # compute/memoria do pipeline. NAO e' necessariamente o que foi pro body:
    # ver emitted_bytes/emitted_mode (semanticas DISTINTAS por decisao do owner,
    # BUG-07 T-QA-8 F0 2026-07-10).
    body_bytes: int | None = None
    # Bytes REALMENTE emitidos no body da coluna + modo vencedor do min()
    # ('tcf'|'raw'|'dict'|'split'). Capturados NO PONTO da selecao em
    # multi/core.py — a contagem ja' existe pro size do header (zero passada
    # extra; "contar no processo, nao no fim"). So' multi-col; None em single.
    emitted_bytes: int | None = None
    emitted_mode: str | None = None

    # --- Multi-col (so' populado se input foi dict) ---
    multi_info: dict | None = None
    per_col: dict[str, "SideOutputs"] | None = None

"""Schema builder — orquestrador que consume SideOutputs (T-CODE-SCHEMA-BUILDER Fase 1).

`build_schema(data)` chama `encode()` internamente (com `SideOutputs`),
extrai features per-coluna + decisoes de heuristicas, e monta
`TableSchema` rico.

API:

    from tcf import build_schema

    # Single-coluna
    schema = build_schema(["a@x.com", "b@x.com"])
    # -> TableSchema(n_cols=1, is_multi_col=False, columns={"val": ColumnSchema(...)})

    # Multi-coluna
    schema = build_schema({"id": ["1", "2"], "name": ["a", "b"]})
    # -> TableSchema(n_cols=2, is_multi_col=True, columns={"id": ..., "name": ...})

    # Serializar
    print(schema.to_json())

Reaproveitamento (ADR-0014):
- ColumnFeatures (analyze_column, H-DA-11c)
- detect_cadence_from_features (ADR-0008)
- detect_min_len_from_features (ADR-0010)
- HCC seq_rle_runs (ADR-0011)

Fase 1: orquestracao basica. Naturezas detectadas (templated/checked/
enumerated/etc) ficam como **placeholder vazio em `natures`** ate'
META-TYPE-ENCODERS reabrir (Fase 3).

Status: Fase 1 WELDED 2026-05-24.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from tcf.side_outputs import SideOutputs


@dataclass
class ColumnSchema:
    """Schema de uma coluna individual.

    Campos derivados de:
    - ColumnFeatures (analyze_column): n_rows, n_unicas, avg_len,
      cardinality, is_numeric, sample
    - Heuristicas pre-pass: cadence_detected, cadence_rule, min_len
    - HCC pos-encode: body_bytes, seq_rle_runs_count
    - Placeholder futuro: natures (T02-T07 META-TYPE-ENCODERS)
    """

    name: str
    n_rows: int
    n_unicas: int
    avg_len: float
    cardinality: float
    is_numeric: bool
    cadence_detected: bool
    cadence_rule: str | None
    min_len: int
    body_bytes: int
    seq_rle_runs_count: int
    sample: list[str] = field(default_factory=list)
    natures: list[str] = field(default_factory=list)  # placeholder Fase 3

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TableSchema:
    """Schema de uma tabela inteira (single ou multi-col).

    Containers per-coluna em `columns`. Bytes desagregados em
    header_bytes / body_bytes (multi-col) ou total = body (single-col).
    """

    n_rows: int
    n_cols: int
    columns: dict[str, ColumnSchema]
    total_bytes: int
    header_bytes: int
    body_bytes: int
    is_multi_col: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "n_rows": self.n_rows,
            "n_cols": self.n_cols,
            "total_bytes": self.total_bytes,
            "header_bytes": self.header_bytes,
            "body_bytes": self.body_bytes,
            "is_multi_col": self.is_multi_col,
            "columns": {name: col.to_dict() for name, col in self.columns.items()},
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)


def build_schema(data: list[str] | dict[str, list[str]]) -> TableSchema:
    """Orquestrador: encode internamente + monta TableSchema das SideOutputs.

    Args:
        data: list[str] (single-col) ou dict[str, list[str]] (multi-col).

    Returns:
        TableSchema completo (com ColumnSchema per-coluna).

    Notes:
        - Chama encode() internamente; o texto encoded eh descartado
          (use encode() diretamente se precisar do texto + schema).
        - Output deterministico: build_schema(data) sempre retorna o
          mesmo schema pra mesmo data.
        - Naturezas (`columns[name].natures`) ficam vazias na Fase 1.
          Fase 3 integrara' detect_templated/checked/etc.
    """
    from tcf.encoder import encode
    from tcf.side_outputs import SideOutputs

    side = SideOutputs()
    encode(data, side_outputs=side)

    if isinstance(data, list):
        # Single-col: side eh a side da unica coluna (nao tem per_col)
        col_schema = _column_schema_from_side("val", data, side)
        return TableSchema(
            n_rows=len(data),
            n_cols=1,
            columns={"val": col_schema},
            total_bytes=side.body_bytes or 0,
            header_bytes=0,
            body_bytes=side.body_bytes or 0,
            is_multi_col=False,
        )

    if isinstance(data, dict):
        # Multi-col: side.per_col[name] tem SideOutputs aninhado por coluna
        cols: dict[str, ColumnSchema] = {}
        for name, values in data.items():
            per_side = side.per_col[name]
            cols[name] = _column_schema_from_side(name, values, per_side)

        mi = side.multi_info or {}
        return TableSchema(
            n_rows=mi.get("n_rows", 0),
            n_cols=mi.get("n_cols", 0),
            columns=cols,
            total_bytes=mi.get("total_bytes", 0),
            header_bytes=mi.get("header_bytes", 0),
            body_bytes=mi.get("body_bytes", 0),
            is_multi_col=True,
        )

    raise TypeError(
        f"build_schema espera list[str] ou dict[str, list[str]], "
        f"recebeu {type(data).__name__}"
    )


def _column_schema_from_side(
    name: str,
    values: list[str] | None,
    side: "SideOutputs",
) -> ColumnSchema:
    """Constroi ColumnSchema de uma SideOutputs single-col."""
    cf = side.column_features

    cadence_rule: str | None = None
    if side.cadence_detected and side.cadence_info:
        cadence_rule = (
            side.cadence_info.get("rule_hit")
            or side.cadence_info.get("reason")
        )

    return ColumnSchema(
        name=name,
        n_rows=cf.n_rows if cf else (len(values) if values else 0),
        n_unicas=cf.n_unicas if cf else 0,
        avg_len=round(cf.avg_len, 3) if cf else 0.0,
        cardinality=round(cf.cardinality, 4) if cf else 0.0,
        is_numeric=cf.is_numeric if cf else False,
        cadence_detected=side.cadence_detected or False,
        cadence_rule=cadence_rule,
        min_len=side.min_len or 0,
        body_bytes=side.body_bytes or 0,
        seq_rle_runs_count=len(side.seq_rle_runs or []),
        sample=list(cf.sample) if cf else [],
        natures=[],  # placeholder Fase 3 (T-CODE-SCHEMA-BUILDER)
    )

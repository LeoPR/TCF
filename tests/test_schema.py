"""Tests build_schema (T-CODE-SCHEMA-BUILDER Fase 1).

Valida orquestrador `build_schema(data)` que consome SideOutputs e
produz `TableSchema` rico. Reaproveita 100% do que ja' existe (zero
recomputacao).
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from tcf import build_schema, ColumnSchema, TableSchema


ROOT = Path(__file__).resolve().parent.parent
DATASETS_DIR = ROOT / "datasets" / "synthetic"


def _ler_csv_multi(name: str) -> dict[str, list[str]]:
    with (DATASETS_DIR / f"{name}.csv").open(encoding="utf-8") as f:
        r = csv.reader(f)
        header = next(r)
        cols = {h: [] for h in header}
        for row in r:
            for h, v in zip(header, row):
                cols[h].append(v)
    return cols


# ---------------------------------------------------------------------------
# Dispatch por tipo
# ---------------------------------------------------------------------------

class TestBuildSchemaDispatch:
    def test_list_returns_single_col_schema(self):
        schema = build_schema(["a", "b", "c"])
        assert isinstance(schema, TableSchema)
        assert not schema.is_multi_col
        assert schema.n_cols == 1
        assert "val" in schema.columns

    def test_dict_returns_multi_col_schema(self):
        schema = build_schema({"x": ["1", "2"], "y": ["a", "b"]})
        assert isinstance(schema, TableSchema)
        assert schema.is_multi_col
        assert schema.n_cols == 2
        assert set(schema.columns.keys()) == {"x", "y"}

    def test_invalid_type_raises(self):
        with pytest.raises(TypeError):
            build_schema(123)


# ---------------------------------------------------------------------------
# ColumnSchema populado corretamente
# ---------------------------------------------------------------------------

class TestColumnSchema:
    def test_simple_column_features(self):
        schema = build_schema(["abc", "abcd", "abcde"])
        col = schema.columns["val"]
        assert col.n_rows == 3
        assert col.n_unicas == 3
        assert col.cardinality == 1.0
        assert col.avg_len == 4.0  # (3+4+5)/3
        assert col.is_numeric is False

    def test_numeric_column_detected(self):
        schema = build_schema(["1", "2", "3", "4", "5"])
        col = schema.columns["val"]
        assert col.is_numeric is True

    def test_cadence_detected_dates(self):
        schema = build_schema([
            "2026-01-01", "2026-01-02", "2026-01-03",
            "2026-01-04", "2026-01-05",
        ])
        col = schema.columns["val"]
        # Datas com cadencia uniforme -> regra 1 detect_cadence
        assert col.cadence_detected is True
        assert col.cadence_rule is not None

    def test_low_cardinality_column(self):
        # 3 valores unicos em 10 rows -> cardinalidade baixa
        schema = build_schema(["A", "B", "A", "C", "B", "A", "C", "B", "A", "B"])
        col = schema.columns["val"]
        assert col.n_unicas == 3
        assert col.cardinality == 0.3

    def test_sample_captured(self):
        schema = build_schema(["x", "y", "z"])
        col = schema.columns["val"]
        assert col.sample == ["x", "y", "z"]

    def test_min_len_captured(self):
        schema = build_schema(["abc", "abcd", "abcde"])
        col = schema.columns["val"]
        assert col.min_len >= 1

    def test_body_bytes_positive(self):
        schema = build_schema(["a", "b", "c"])
        col = schema.columns["val"]
        assert col.body_bytes > 0

    def test_natures_empty_in_fase_1(self):
        """Fase 1: natures eh placeholder vazio (Fase 3 integra)."""
        schema = build_schema(["a", "b"])
        col = schema.columns["val"]
        assert col.natures == []


# ---------------------------------------------------------------------------
# TableSchema multi-col
# ---------------------------------------------------------------------------

class TestTableSchemaMulti:
    def test_multi_n_rows_consistent(self):
        schema = build_schema({"a": ["1", "2", "3"], "b": ["x", "y", "z"]})
        assert schema.n_rows == 3
        assert schema.columns["a"].n_rows == 3
        assert schema.columns["b"].n_rows == 3

    def test_multi_byte_breakdown(self):
        schema = build_schema({"a": ["1", "2"], "b": ["x", "y"]})
        assert schema.total_bytes == schema.header_bytes + schema.body_bytes
        assert schema.header_bytes > 0  # multi sempre tem header
        assert schema.body_bytes > 0

    def test_multi_each_column_has_features(self):
        schema = build_schema({"id": ["1", "2"], "name": ["a", "b"]})
        for name in ("id", "name"):
            col = schema.columns[name]
            assert col.name == name
            assert col.body_bytes > 0
            assert col.n_rows == 2


# ---------------------------------------------------------------------------
# TableSchema single-col
# ---------------------------------------------------------------------------

class TestTableSchemaSingle:
    def test_single_no_header(self):
        schema = build_schema(["a", "b"])
        assert schema.header_bytes == 0
        assert schema.total_bytes == schema.body_bytes

    def test_single_uses_val_as_default_name(self):
        schema = build_schema(["a", "b"])
        assert "val" in schema.columns


# ---------------------------------------------------------------------------
# D17a real dataset
# ---------------------------------------------------------------------------

class TestD17aSchema:
    def test_d17a_basic_shape(self):
        cols = _ler_csv_multi("D17a-multi-column-mixed")
        schema = build_schema(cols)
        assert schema.n_rows == 13
        assert schema.n_cols == 4
        assert schema.total_bytes == 300  # D17a 0.7 (V2-B: era 307; ADR-0024/0025)
        assert set(schema.columns.keys()) == {
            "timestamp", "id", "email", "categoria",
        }

    def test_d17a_timestamp_cadence(self):
        cols = _ler_csv_multi("D17a-multi-column-mixed")
        schema = build_schema(cols)
        # timestamps com cadencia uniforme
        assert schema.columns["timestamp"].cadence_detected is True

    def test_d17a_id_numeric_cadence(self):
        cols = _ler_csv_multi("D17a-multi-column-mixed")
        schema = build_schema(cols)
        # IDs sao numericos com alta card
        assert schema.columns["id"].is_numeric is True
        assert schema.columns["id"].cadence_detected is True

    def test_d17a_categoria_low_cardinality(self):
        cols = _ler_csv_multi("D17a-multi-column-mixed")
        schema = build_schema(cols)
        # A/B/C em 13 rows = 0.23 cardinalidade
        assert schema.columns["categoria"].cardinality < 0.5


# ---------------------------------------------------------------------------
# Serializacao
# ---------------------------------------------------------------------------

class TestSerialization:
    def test_to_dict_serializable(self):
        schema = build_schema({"x": ["1", "2"]})
        d = schema.to_dict()
        assert d["n_cols"] == 1
        assert "columns" in d
        assert "x" in d["columns"]

    def test_to_json_valid(self):
        schema = build_schema({"x": ["1", "2"]})
        s = schema.to_json()
        # JSON deve ser parseavel de volta
        parsed = json.loads(s)
        assert parsed["n_cols"] == 1

    def test_to_json_d17a(self):
        cols = _ler_csv_multi("D17a-multi-column-mixed")
        schema = build_schema(cols)
        s = schema.to_json()
        parsed = json.loads(s)
        assert parsed["total_bytes"] == 300  # D17a 0.7 (V2-B: era 307; ADR-0024/0025)
        assert len(parsed["columns"]) == 4


# ---------------------------------------------------------------------------
# Determinismo
# ---------------------------------------------------------------------------

class TestDeterminism:
    def test_same_input_same_schema(self):
        data = {"a": ["1", "2", "3"], "b": ["x", "y", "z"]}
        s1 = build_schema(data)
        s2 = build_schema(data)
        assert s1.to_dict() == s2.to_dict()

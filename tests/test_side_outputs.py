"""Tests SideOutputs (ADR-0014) — captura opcional de info interna.

Valida que passar `side_outputs=SideOutputs()` em `encode()` captura:
- Pre-pass features (ColumnFeatures, cadence_info, min_len)
- OBAT log + flag used_hint
- HCC trace + rede + seq_rle_runs
- Body bytes per coluna
- Multi-col: multi_info + per_col (com SideOutputs aninhados)
"""

from __future__ import annotations

import pytest

from tcf import encode, SideOutputs
from tcf.column_features import ColumnFeatures


class TestSideOutputsSingleCol:
    def test_no_side_outputs_returns_str_only(self):
        text = encode(["a", "b", "c"])
        assert isinstance(text, str)

    def test_side_outputs_captures_column_features(self):
        side = SideOutputs()
        encode(["abc", "abcd", "abcde"], side_outputs=side)
        assert isinstance(side.column_features, ColumnFeatures)
        assert side.column_features.n_rows == 3
        assert side.column_features.n_unicas == 3

    def test_side_outputs_captures_cadence_decision(self):
        side = SideOutputs()
        encode(["a", "b", "c"], side_outputs=side)
        assert side.cadence_detected in (True, False)
        assert isinstance(side.cadence_info, dict)

    def test_side_outputs_captures_min_len(self):
        side = SideOutputs()
        encode(["abc", "abcd"], side_outputs=side)
        assert isinstance(side.min_len, int)
        assert side.min_len >= 1

    def test_side_outputs_captures_obat_log(self):
        side = SideOutputs()
        encode(["abc", "abcd", "abcde"], side_outputs=side)
        assert isinstance(side.obat_log, str)
        assert len(side.obat_log) > 0
        assert isinstance(side.obat_used_hint, bool)

    def test_side_outputs_captures_hcc_trace_rede(self):
        side = SideOutputs()
        encode(["abc", "abcd", "abcde"], side_outputs=side)
        assert isinstance(side.hcc_trace, str)
        assert isinstance(side.hcc_rede, str)
        # Trace tem secoes
        assert "DETECTOR" in side.hcc_trace or len(side.hcc_trace) > 0

    def test_side_outputs_captures_seq_rle_runs(self):
        side = SideOutputs()
        # Dataset com cadencia gera seq_rle_runs (datetimes)
        encode(
            ["2026-01-01", "2026-01-02", "2026-01-03", "2026-01-04"],
            side_outputs=side,
        )
        assert isinstance(side.seq_rle_runs, list)

    def test_side_outputs_captures_body_bytes(self):
        side = SideOutputs()
        text = encode(["a", "b", "c"], side_outputs=side)
        assert side.body_bytes == len(text.encode("utf-8"))


class TestSideOutputsMultiCol:
    def test_multi_info_populated(self):
        side = SideOutputs()
        encode({"x": ["1", "2"], "y": ["a", "b"]}, side_outputs=side)
        assert isinstance(side.multi_info, dict)
        assert side.multi_info["n_rows"] == 2
        assert side.multi_info["n_cols"] == 2
        assert side.multi_info["total_bytes"] > 0
        assert side.multi_info["header_bytes"] > 0
        assert side.multi_info["body_bytes"] > 0

    def test_per_col_has_all_columns(self):
        side = SideOutputs()
        encode({"a": ["1"], "b": ["2"], "c": ["3"]}, side_outputs=side)
        assert set(side.per_col.keys()) == {"a", "b", "c"}

    def test_per_col_nested_side_outputs(self):
        side = SideOutputs()
        encode({"col1": ["abc", "abcd", "abcde"]}, side_outputs=side)
        assert "col1" in side.per_col
        nested = side.per_col["col1"]
        assert isinstance(nested, SideOutputs)
        assert nested.column_features is not None
        assert nested.body_bytes is not None
        assert nested.obat_log is not None

    def test_multi_info_consistency(self):
        side = SideOutputs()
        text = encode({"a": ["x", "y"], "b": ["1", "2"]}, side_outputs=side)
        assert side.multi_info["total_bytes"] == len(text.encode("utf-8"))
        assert (
            side.multi_info["total_bytes"]
            == side.multi_info["header_bytes"] + side.multi_info["body_bytes"]
        )

    def test_single_col_fields_none_in_multi_container(self):
        """Multi container nao tem features per-coluna (vai em per_col)."""
        side = SideOutputs()
        encode({"x": ["1", "2"]}, side_outputs=side)
        assert side.column_features is None
        assert side.obat_log is None
        assert side.hcc_trace is None


class TestSideOutputsOverhead:
    """Garante que SEM side_outputs nao ha' regressao."""

    def test_d17a_same_bytes_with_and_without_side(self):
        import csv
        from pathlib import Path

        ds = Path(__file__).resolve().parent.parent / "datasets" / "synthetic" / "D17a-multi-column-mixed.csv"
        with ds.open(encoding="utf-8") as f:
            r = csv.reader(f)
            header = next(r)
            cols = {h: [] for h in header}
            for row in r:
                for h, v in zip(header, row):
                    cols[h].append(v)

        text_without = encode(cols)
        side = SideOutputs()
        text_with = encode(cols, side_outputs=side)
        assert text_without == text_with  # byte-identical
        assert len(text_without.encode("utf-8")) == 302  # 0.7 (V2-B: era 307; ADR-0024/0025)

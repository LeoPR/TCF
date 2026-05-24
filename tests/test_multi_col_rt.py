"""Tests round-trip (RT) basicos pra src/tcf multi-column (ADR-0013).

Tests SEM dependencias externas — rodam em CI sem precisar de
Z:/tcf-data SQLite. Validam:
- encode_table / decode_table round-trip
- D17a baseline 322 bytes INVARIANT (preservado vs EXP-011)
- Edge cases: tabela vazia, lengths diferentes, nomes invalidos
- Per-column info dict

Conexao:
- ADR-0013 (multi-column canonical API welded)
- ADR-0004 (header format)
- ADR-0011 (Pacote 1 canonical M10 single-col, base do multi)
- T-EXP-MULTI-COL-SCALING (validacao real-world 9 tabelas)
"""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from tcf import encode_table, decode_table


ROOT = Path(__file__).resolve().parent.parent
DATASETS_DIR = ROOT / "datasets" / "synthetic"


def _ler_csv_multi(name: str) -> dict[str, list[str]]:
    """Le CSV multi-column. Retorna dict[col_name, list[str]]."""
    with (DATASETS_DIR / f"{name}.csv").open(encoding="utf-8") as f:
        r = csv.reader(f)
        header = next(r)
        cols = {h: [] for h in header}
        for row in r:
            for h, v in zip(header, row):
                cols[h].append(v)
    return cols


# ---------------------------------------------------------------------------
# Round-trip basico
# ---------------------------------------------------------------------------

class TestRoundTripBasic:
    def test_minimal_table(self):
        table = {"id": ["1", "2", "3"], "name": ["a", "b", "c"]}
        text, info = encode_table(table)
        decoded = decode_table(text)
        assert decoded == table

    def test_single_column_table(self):
        table = {"only": ["x", "y", "z"]}
        text, info = encode_table(table)
        decoded = decode_table(text)
        assert decoded == table

    def test_many_columns_table(self):
        table = {f"col{i}": [f"v{i}_{j}" for j in range(5)] for i in range(8)}
        text, info = encode_table(table)
        decoded = decode_table(text)
        assert decoded == table

    def test_repeated_values(self):
        table = {
            "categoria": ["A", "B", "A", "B", "A", "A", "C"],
            "val": ["1", "2", "1", "2", "1", "1", "3"],
        }
        text, info = encode_table(table)
        decoded = decode_table(text)
        assert decoded == table


# ---------------------------------------------------------------------------
# D17a INVARIANT baseline
# ---------------------------------------------------------------------------

class TestD17aBaseline:
    """D17a INVARIANT: 322 bytes preservado vs EXP-011 (M9 era).

    Se este test quebrar, indica regressao em algum componente do
    pipeline (analyze_column, detect_cadence, detect_min_len, OBAT,
    HCC, multi.encode_table header). NAO modificar sem ADR explicito.
    """

    def test_d17a_total_bytes_invariant(self):
        table = _ler_csv_multi("D17a-multi-column-mixed")
        text, info = encode_table(table)
        assert info["total_bytes"] == 322, (
            f"D17a baseline 322B INVARIANT broken: got {info['total_bytes']}. "
            f"Check ADR-0013, ADR-0011, ADR-0004."
        )

    def test_d17a_round_trip(self):
        table = _ler_csv_multi("D17a-multi-column-mixed")
        text, info = encode_table(table)
        decoded = decode_table(text)
        assert decoded == table

    def test_d17a_header_format(self):
        table = _ler_csv_multi("D17a-multi-column-mixed")
        text, _ = encode_table(table)
        lines = text.split("\n", 2)
        assert lines[0] == "#TCF.6 M", f"shebang invalido: {lines[0]!r}"
        assert lines[1].startswith("# "), f"meta invalido: {lines[1]!r}"
        # Meta tem 4 colunas (timestamp, id, email, categoria)
        meta = lines[1][2:]  # strip "# "
        pairs = meta.split(",")
        assert len(pairs) == 4
        assert all("=" in p for p in pairs)


# ---------------------------------------------------------------------------
# Info dict
# ---------------------------------------------------------------------------

class TestInfoDict:
    def test_info_has_required_keys(self):
        table = {"a": ["x", "y"], "b": ["1", "2"]}
        text, info = encode_table(table)
        for k in ("n_rows", "n_cols", "total_bytes", "header_bytes",
                  "body_bytes", "per_col"):
            assert k in info, f"missing key {k}"

    def test_info_sizes_consistent(self):
        table = {"a": ["x", "y"], "b": ["1", "2"]}
        text, info = encode_table(table)
        assert info["total_bytes"] == info["header_bytes"] + info["body_bytes"]
        assert len(text.encode("utf-8")) == info["total_bytes"]

    def test_per_col_has_all_columns(self):
        table = {"a": ["1"], "b": ["2"], "c": ["3"]}
        text, info = encode_table(table)
        assert set(info["per_col"].keys()) == {"a", "b", "c"}
        for col in ("a", "b", "c"):
            assert info["per_col"][col]["n_values"] == 1
            assert info["per_col"][col]["body_bytes"] > 0


# ---------------------------------------------------------------------------
# Edge cases / validacao
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_empty_table_raises(self):
        with pytest.raises(ValueError, match="vazia"):
            encode_table({})

    def test_mismatched_lengths_raises(self):
        with pytest.raises(ValueError, match="lengths"):
            encode_table({"a": ["1", "2"], "b": ["x"]})

    def test_col_name_with_comma_raises(self):
        with pytest.raises(ValueError, match="reservado"):
            encode_table({"a,b": ["1", "2"]})

    def test_col_name_with_equals_raises(self):
        with pytest.raises(ValueError, match="reservado"):
            encode_table({"a=b": ["1", "2"]})

    def test_null_values_converted_to_empty_str(self):
        table = {"a": ["x", None, "y"]}
        text, _ = encode_table(table)
        decoded = decode_table(text)
        assert decoded == {"a": ["x", "", "y"]}

    def test_decode_invalid_magic_raises(self):
        with pytest.raises(ValueError, match="magic"):
            decode_table("#TCF.6\n# 0=foo\n")  # missing M flag

    def test_decode_no_shebang_raises(self):
        with pytest.raises(ValueError):
            decode_table("")

"""Tests round-trip (RT) basicos pra src/tcf multi-column.

Tests SEM dependencias externas — rodam em CI sem precisar de
Z:/tcf-data SQLite. Validam:
- encode(dict) / decode(text) round-trip (API unificada, ADR-0014)
- D17a baseline 322 bytes INVARIANT (preservado vs EXP-011)
- Edge cases: tabela vazia, lengths diferentes, nomes invalidos
- Self-describing format (decoder dispatcha pelo shebang)

Conexao:
- ADR-0014 (API unificada encode(list|dict) + side_outputs)
- ADR-0013 (multi-column canonical API welded)
- ADR-0011 (Pacote 1 canonical M10 single-col, base do multi)
- ADR-0004 (header format)
- T-EXP-MULTI-COL-SCALING (validacao real-world 9 tabelas)
"""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from tcf import encode, decode


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
        text = encode(table)
        decoded = decode(text)
        assert decoded == table
        assert isinstance(decoded, dict)

    def test_single_column_table(self):
        table = {"only": ["x", "y", "z"]}
        text = encode(table)
        decoded = decode(text)
        assert decoded == table
        assert isinstance(decoded, dict)

    def test_many_columns_table(self):
        table = {f"col{i}": [f"v{i}_{j}" for j in range(5)] for i in range(8)}
        text = encode(table)
        decoded = decode(text)
        assert decoded == table

    def test_repeated_values(self):
        table = {
            "categoria": ["A", "B", "A", "B", "A", "A", "C"],
            "val": ["1", "2", "1", "2", "1", "1", "3"],
        }
        text = encode(table)
        decoded = decode(text)
        assert decoded == table


# ---------------------------------------------------------------------------
# Dispatch por tipo (ADR-0014)
# ---------------------------------------------------------------------------

class TestUnifiedDispatch:
    def test_encode_list_returns_body_no_shebang(self):
        text = encode(["abc", "abcd", "abcde"])
        assert not text.startswith("#TCF.6 M")
        assert decode(text) == ["abc", "abcd", "abcde"]

    def test_encode_dict_returns_multi_with_shebang(self):
        text = encode({"x": ["1", "2"]})
        assert text.startswith("#TCF.6 M\n")

    def test_decode_routes_by_shebang_to_dict(self):
        text = encode({"x": ["a", "b"]})
        assert isinstance(decode(text), dict)

    def test_decode_routes_no_shebang_to_list(self):
        text = encode(["a", "b", "c"])
        assert isinstance(decode(text), list)

    def test_encode_invalid_type_raises(self):
        with pytest.raises(TypeError):
            encode(123)

    def test_round_trip_identity_list(self):
        data = ["one", "two", "three"]
        assert decode(encode(data)) == data

    def test_round_trip_identity_dict(self):
        data = {"a": ["1", "2"], "b": ["x", "y"]}
        assert decode(encode(data)) == data


# ---------------------------------------------------------------------------
# D17a INVARIANT baseline
# ---------------------------------------------------------------------------

class TestD17aBaseline:
    """D17a INVARIANT: 322 bytes preservado vs EXP-011 (M9 era).

    Se este test quebrar, indica regressao em algum componente do
    pipeline (analyze_column, detect_cadence, detect_min_len, OBAT,
    HCC, multi header). NAO modificar sem ADR explicito.
    """

    def test_d17a_total_bytes_invariant(self):
        table = _ler_csv_multi("D17a-multi-column-mixed")
        text = encode(table)
        n_bytes = len(text.encode("utf-8"))
        assert n_bytes == 322, (
            f"D17a baseline 322B INVARIANT broken: got {n_bytes}. "
            f"Check ADR-0014, ADR-0013, ADR-0011, ADR-0004."
        )

    def test_d17a_round_trip(self):
        table = _ler_csv_multi("D17a-multi-column-mixed")
        text = encode(table)
        decoded = decode(text)
        assert decoded == table

    def test_d17a_header_format(self):
        table = _ler_csv_multi("D17a-multi-column-mixed")
        text = encode(table)
        lines = text.split("\n", 2)
        assert lines[0] == "#TCF.6 M", f"shebang invalido: {lines[0]!r}"
        assert lines[1].startswith("# "), f"meta invalido: {lines[1]!r}"
        meta = lines[1][2:]
        pairs = meta.split(",")
        assert len(pairs) == 4
        assert all("=" in p for p in pairs)


# ---------------------------------------------------------------------------
# Edge cases / validacao
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_empty_table_raises(self):
        with pytest.raises(ValueError, match="vazia"):
            encode({})

    def test_mismatched_lengths_raises(self):
        with pytest.raises(ValueError, match="lengths"):
            encode({"a": ["1", "2"], "b": ["x"]})

    def test_col_name_with_comma_raises(self):
        with pytest.raises(ValueError, match="reservado"):
            encode({"a,b": ["1", "2"]})

    def test_col_name_with_equals_raises(self):
        with pytest.raises(ValueError, match="reservado"):
            encode({"a=b": ["1", "2"]})

    def test_null_values_converted_to_empty_str(self):
        table = {"a": ["x", None, "y"]}
        text = encode(table)
        decoded = decode(text)
        assert decoded == {"a": ["x", "", "y"]}

    def test_decode_invalid_magic_raises(self):
        # Comeca com #TCF.6 M -> rota multi -> erro de magic na rota interna
        with pytest.raises(ValueError):
            decode("#TCF.6 M\nbad\n")


# ---------------------------------------------------------------------------
# Deprecated aliases (ADR-0014 backward compat)
# ---------------------------------------------------------------------------

class TestDeprecatedAliases:
    def test_encode_table_emits_deprecation_warning(self):
        from tcf import encode_table
        with pytest.warns(DeprecationWarning, match="encode_table"):
            text, info = encode_table({"a": ["1", "2"]})
        assert isinstance(info, dict)

    def test_decode_table_emits_deprecation_warning(self):
        from tcf import encode_table, decode_table
        with pytest.warns(DeprecationWarning):
            text, _ = encode_table({"a": ["1", "2"]})
        with pytest.warns(DeprecationWarning, match="decode_table"):
            decoded = decode_table(text)
        assert decoded == {"a": ["1", "2"]}

    def test_encode_table_legacy_info_keys_preserved(self):
        from tcf import encode_table
        with pytest.warns(DeprecationWarning):
            text, info = encode_table({"a": ["x", "y"], "b": ["1", "2"]})
        for k in ("n_rows", "n_cols", "total_bytes", "header_bytes",
                  "body_bytes", "per_col"):
            assert k in info

    def test_encode_table_per_col_body_bytes(self):
        from tcf import encode_table
        with pytest.warns(DeprecationWarning):
            text, info = encode_table({"a": ["1"], "b": ["2"], "c": ["3"]})
        assert set(info["per_col"].keys()) == {"a", "b", "c"}
        for col in ("a", "b", "c"):
            assert info["per_col"][col]["n_values"] == 1
            assert info["per_col"][col]["body_bytes"] > 0

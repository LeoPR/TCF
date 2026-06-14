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
# V2-A fallback identity (ADR-0022, abre v2.0 #TCF.7) — opt-in
# ---------------------------------------------------------------------------

class TestV2AFallback:
    """V2-A: por coluna, min(TCF, raw). Opt-in (`fallback=True`); default
    preserva byte-canonical v1 (#TCF.6). Marcador `!<size>=<name>`."""

    # coluna baixa-card curta (padrao beijing 'hour') infla em TCF -> raw vence
    HOUR = [str(i % 24) for i in range(300)]
    NOME = [f"item_{i:04d}_descricao_longa_unica" for i in range(300)]

    def _table(self):
        return {"hour": list(self.HOUR), "nome": list(self.NOME)}

    def test_default_off_byte_identical(self):
        table = self._table()
        assert encode(table) == encode(table, fallback=False)
        assert encode(table).startswith("#TCF.6 M")

    def test_fallback_emits_v2_when_beneficial(self):
        table = self._table()
        text = encode(table, fallback=True)
        assert text.startswith("#TCF.7 M"), "coluna hour devia cair pra raw"
        assert decode(text) == table

    def test_fallback_never_larger(self):
        table = self._table()
        v1 = len(encode(table, fallback=False).encode("utf-8"))
        v2 = len(encode(table, fallback=True).encode("utf-8"))
        assert v2 <= v1

    def test_fallback_no_benefit_stays_v1(self):
        # nenhuma coluna fica menor como raw -> #TCF.6 mesmo com fallback=True
        table = {"a": ["abc", "abcd", "abcde"], "b": ["xyz", "xyzw", "xyzwv"]}
        text = encode(table, fallback=True)
        assert text.startswith("#TCF.6 M")
        assert decode(text) == table

    def test_fallback_round_trip_with_empties(self):
        table = {"x": ["", "1", "2", "", "3"], "y": ["a", "b", "c", "d", "e"]}
        text = encode(table, fallback=True)
        assert decode(text) == table

    def test_v2_decode_self_describing(self):
        # decode nao precisa de flag — o '!' por par diz o modo
        table = self._table()
        text = encode(table, fallback=True)
        assert decode(text) == table

    def test_fallback_marker_only_before_size(self):
        # '!' aparece so' antes do size, nunca toca o nome.
        # #TCF.7 dispensa o prefixo '# ' do meta (ADR-0023) -> meta direto.
        table = self._table()
        text = encode(table, fallback=True)
        meta = text.split("\n", 2)[1]
        assert not meta.startswith("# ")  # v7: sem prefixo
        pairs = meta.split(",")
        # hour caiu pra raw -> par "!<size>=hour"; nome TCF -> "<size>=nome"
        assert any(p.startswith("!") and p.split("=", 1)[1] == "hour" for p in pairs)
        assert any(not p.startswith("!") and p.split("=", 1)[1] == "nome" for p in pairs)

    def test_fallback_ignored_for_single_col(self):
        # list (single-col) nao tem header -> fallback ignorado, sem shebang
        text = encode(["abc", "abcd"], fallback=True)
        assert not text.startswith("#TCF.")
        assert decode(text) == ["abc", "abcd"]


# ---------------------------------------------------------------------------
# Header v2 minimo (ADR-0023, O-FMT-15+16) — opt-in min_header
# ---------------------------------------------------------------------------

class TestMinHeaderV2:
    """Header minimo: #TCF.7 dispensa o prefixo do meta (sem `#`, sem espaco) e
    omite o size da ultima coluna. Opt-in (`min_header=True`); default preserva
    byte-canonical v1 (#TCF.6)."""

    def _table(self):
        return {
            "nome":   ["Ana Souza", "Bruno Lima", "Carla Nunes", "Diego Rocha"],
            "email":  ["a@acme.com.br", "b@acme.com.br", "c@acme.com.br", "d@acme.com.br"],
            "cidade": ["Sao Paulo", "Sao Paulo", "Sao Paulo", "Rio de Janeiro"],
            "plano":  ["Premium", "Premium", "Basic", "Premium"],
        }

    def test_default_off_byte_identical(self):
        table = self._table()
        assert encode(table) == encode(table, min_header=False)
        assert encode(table).startswith("#TCF.6 M")

    def test_min_header_emits_v2(self):
        text = encode(self._table(), min_header=True)
        assert text.startswith("#TCF.7 M")
        assert decode(text) == self._table()

    def test_min_header_meta_shape(self):
        text = encode(self._table(), min_header=True)
        meta = text.split("\n", 2)[1]
        # #TCF.7: meta SEM prefixo '#' (o flag M no shebang ja' declara colunas)
        assert not meta.startswith("#")
        pairs = meta.split(",")
        # todos menos o ultimo tem 'size=name'; ultimo e' bare (sem '=')
        assert all("=" in p for p in pairs[:-1])
        assert "=" not in pairs[-1]
        assert pairs[-1] == "plano"

    def test_min_header_smaller_than_v1(self):
        table = self._table()
        assert len(encode(table, min_header=True).encode("utf-8")) < \
            len(encode(table).encode("utf-8"))

    def test_composes_with_fallback(self):
        # coluna baixa-card cai pra raw (!) E header minimo (ultima bare)
        table = {
            "hour": [str(i % 24) for i in range(60)],
            "nome": [f"item_{i:03d}_unico_longo" for i in range(60)],
        }
        text = encode(table, min_header=True, fallback=True)
        assert text.startswith("#TCF.7 M")
        assert decode(text) == table

    def test_last_col_raw_and_bare(self):
        # ultima coluna em fallback raw: par vira '!name' (sem size)
        table = {
            "nome": [f"reg_{i:03d}_descricao_unica_e_longa" for i in range(40)],
            "hour": [str(i % 24) for i in range(40)],   # ultima, baixa-card -> raw
        }
        text = encode(table, min_header=True, fallback=True)
        assert decode(text) == table

    def test_single_col_dict(self):
        table = {"only": ["x", "y", "z"]}
        text = encode(table, min_header=True)
        assert decode(text) == table

    def test_ignored_for_list(self):
        text = encode(["abc", "abcd"], min_header=True)
        assert not text.startswith("#TCF.")
        assert decode(text) == ["abc", "abcd"]

    @pytest.mark.parametrize("table", [
        {"a": ["1", "2"], "b": ["x", "y"]},
        {"a": ["", "1", ""], "b": ["p", "q", "r"]},     # vazios + ultima
        {"x": ["só uma"], "y": ["coluna", "dupla"][:1]}, # 1 linha
    ])
    def test_round_trip_various(self, table):
        assert decode(encode(table, min_header=True)) == table


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

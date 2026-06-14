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
from tcf.multi import _encode_multi  # toggles internos (legado #TCF.6 p/ comparacao)


def _legacy_v6(table):
    """Produz o formato legado #TCF.6 (sem fallback nem header minimo).
    O `encode()` publico nao expoe isso (0.7 e' default, ADR-0024)."""
    return _encode_multi(table, fallback=False, min_header=False)


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
        # 0.7 e' o default agora (ADR-0024)
        text = encode({"x": ["1", "2"]})
        assert text.startswith("#TCF.7 M\n")

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
    """D17a baseline. 0.7 e' o default (ADR-0024): D17a = 307B (#TCF.7).
    O legado #TCF.6 (322B) continua produzivel internamente (_legacy_v6) e
    decodavel. Baselines = guardas de regressao re-pinaveis em mudanca
    intencional (ADR-0024), nao contrato eterno.
    """

    def test_d17a_total_bytes_baseline(self):
        table = _ler_csv_multi("D17a-multi-column-mixed")
        n_bytes = len(encode(table).encode("utf-8"))
        assert n_bytes == 307, (
            f"D17a baseline 0.7 (307B) mudou: got {n_bytes}. Re-pina so' se a "
            f"mudanca de formato for INTENCIONAL (ADR-0024)."
        )

    def test_d17a_legacy_v6_baseline(self):
        # #TCF.6 legado segue produzivel + decodavel (322B INVARIANT historico)
        table = _ler_csv_multi("D17a-multi-column-mixed")
        legacy = _legacy_v6(table)
        assert len(legacy.encode("utf-8")) == 322
        assert legacy.startswith("#TCF.6 M")
        assert decode(legacy) == table

    def test_d17a_round_trip(self):
        table = _ler_csv_multi("D17a-multi-column-mixed")
        assert decode(encode(table)) == table

    def test_d17a_header_format(self):
        table = _ler_csv_multi("D17a-multi-column-mixed")
        text = encode(table)
        lines = text.split("\n", 2)
        assert lines[0] == "#TCF.7 M", f"shebang invalido: {lines[0]!r}"
        # 0.7: meta sem prefixo; ultima coluna bare (sem '=')
        assert not lines[1].startswith("# ")
        pairs = lines[1].split(",")
        assert len(pairs) == 4
        assert all("=" in p for p in pairs[:-1])
        assert "=" not in pairs[-1]


# ---------------------------------------------------------------------------
# Default 0.7 / #TCF.7 (ADR-0024): fallback (ADR-0022) + header minimo (ADR-0023)
# ---------------------------------------------------------------------------

class TestDefault07:
    """0.7 e' o default do encode multi-col (ADR-0024): #TCF.7 com fallback
    (min(TCF,raw) por coluna, marcador `!`) + header minimo (meta sem prefixo,
    ultima coluna sem size). Single-col nao tem header -> inalterado."""

    def _table(self):
        return {
            "hour": [str(i % 24) for i in range(300)],          # baixa-card -> raw
            "nome": [f"item_{i:04d}_descricao_longa_unica" for i in range(300)],
        }

    def test_default_is_v7(self):
        assert encode(self._table()).startswith("#TCF.7 M")

    def test_default_round_trip(self):
        t = self._table()
        assert decode(encode(t)) == t

    def test_default_meta_no_prefix(self):
        # header minimo: meta sem prefixo '#' (o flag M ja' declara colunas)
        meta = encode(self._table()).split("\n", 2)[1]
        assert not meta.startswith("#")

    def test_default_last_col_bare(self):
        # ultima coluna sem size (corpo ate' EOF)
        pairs = encode(self._table()).split("\n", 2)[1].split(",")
        assert "=" not in pairs[-1]

    def test_default_fallback_marker(self):
        # coluna baixa-card (hour) cai pra raw -> algum par com '!'
        meta = encode(self._table()).split("\n", 2)[1]
        assert any(p.startswith("!") for p in meta.split(","))

    def test_default_not_larger_than_legacy(self):
        t = self._table()
        assert len(encode(t).encode("utf-8")) <= len(_legacy_v6(t).encode("utf-8"))

    def test_self_describing_decode(self):
        # decode nao precisa de flag — magic + forma dos pares dizem tudo
        t = self._table()
        assert decode(encode(t)) == t

    def test_single_col_unaffected(self):
        text = encode(["abc", "abcd"])
        assert not text.startswith("#TCF.")
        assert decode(text) == ["abc", "abcd"]

    @pytest.mark.parametrize("table", [
        {"a": ["1", "2"], "b": ["x", "y"]},
        {"a": ["", "1", ""], "b": ["p", "q", "r"]},          # vazios
        {"x": ["uma"], "y": ["linha"]},                      # 1 linha
        {"only": ["x", "y", "z"]},                           # 1 coluna
        {"nome": ["Ana", "Bruno"], "cidade": ["SP", "SP"]},  # raw + RLE
    ])
    def test_round_trip_various(self, table):
        assert decode(encode(table)) == table


# ---------------------------------------------------------------------------
# Legado #TCF.6 (produzivel internamente + decodavel — decode-compat pré-1.0)
# ---------------------------------------------------------------------------

class TestLegacyV6:
    """O encoder publico so' escreve 0.7; o #TCF.6 legado e' produzivel via
    toggles internos (_legacy_v6, p/ comparacao/regressao) e o decoder ainda
    LE ele (decode-compat pré-1.0, ADR-0024)."""

    def _table(self):
        return {"a": ["abc", "abcd"], "b": ["x", "y"]}

    def test_legacy_is_v6_with_prefix(self):
        legacy = _legacy_v6(self._table())
        assert legacy.startswith("#TCF.6 M\n# ")
        meta = legacy.split("\n", 2)[1]
        assert all("=" in p for p in meta[2:].split(","))  # todos com size

    def test_decoder_reads_legacy(self):
        t = self._table()
        assert decode(_legacy_v6(t)) == t


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

"""Tests round-trip (RT) basicos pra src/tcf multi-column.

Tests SEM dependencias externas — rodam em CI sem precisar de
Z:/tcf-data SQLite. Validam:
- encode(dict) / decode(text) round-trip (API unificada, ADR-0014)
- D17a baseline 300 bytes (#TCF.8M default, ADR-0032)
- Edge cases: tabela vazia, lengths diferentes, nomes invalidos
- Self-describing format (decoder dispatcha pelo shebang #TCF.8M)

Conexao:
- ADR-0032 (#TCF.8M vira default; legado #TCF.6/.7 cortado)
- ADR-0014 (API unificada encode(list|dict) + side_outputs)
- ADR-0013 (multi-column canonical API welded)
- ADR-0011 (Pacote 1 canonical M10 single-col, base do multi)
- ADR-0004/0029 (header format / discriminador)
"""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from tcf import encode, decode
from tcf.side_outputs import SideOutputs

# #TCF.8M e' o UNICO multi-col vivo (ADR-0032). Legado #TCF.6/.7 cortado de src/tcf
# (git-as-compat pra comparacao historica). Meta INLINE apos o magic '#TCF.8M'.

ROOT = Path(__file__).resolve().parent.parent
DATASETS_DIR = ROOT / "datasets" / "synthetic"

_MAGIC = "#TCF.8M"


def _meta8(text: str) -> str:
    """Meta INLINE do #TCF.8M: apos o magic (7 chars), ate' a 1a '\\n'."""
    line0 = text.split("\n", 1)[0]
    assert line0.startswith(_MAGIC), f"esperado {_MAGIC!r}: {line0[:12]!r}"
    return line0[len(_MAGIC):]


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
        assert not text.startswith(_MAGIC)
        assert decode(text) == ["abc", "abcd", "abcde"]

    def test_encode_dict_returns_multi_with_shebang(self):
        # #TCF.8M e' o default agora (ADR-0032; meta INLINE apos o magic)
        text = encode({"x": ["1", "2"]})
        assert text.startswith(_MAGIC)

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
    """D17a baseline. #TCF.8M default (ADR-0032): D17a = 300B (V2-B na coluna
    `categoria`, hex). Baselines = guardas de regressao re-pinaveis em mudanca
    intencional (ADR-0024/0025), nao contrato eterno.
    """

    def test_d17a_total_bytes_baseline(self):
        table = _ler_csv_multi("D17a-multi-column-mixed")
        n_bytes = len(encode(table).encode("utf-8"))
        assert n_bytes == 300, (
            f"D17a baseline (#TCF.8M, 300B) mudou: got {n_bytes}. Re-pina so' se a "
            f"mudanca de formato for INTENCIONAL (ADR-0024/0025)."
        )

    def test_d17a_round_trip(self):
        table = _ler_csv_multi("D17a-multi-column-mixed")
        assert decode(encode(table)) == table

    def test_d17a_header_format(self):
        table = _ler_csv_multi("D17a-multi-column-mixed")
        text = encode(table)
        line0 = text.split("\n", 1)[0]
        assert line0.startswith(_MAGIC), f"shebang invalido: {line0[:12]!r}"
        # #TCF.8M: meta INLINE (sem prefixo '# '); ultima coluna bare (sem '=')
        meta = line0[len(_MAGIC):]
        assert not meta.startswith("# ")
        pairs = meta.split(",")
        assert len(pairs) == 4
        assert all("=" in p for p in pairs[:-1])
        assert "=" not in pairs[-1]


# ---------------------------------------------------------------------------
# Default #TCF.8M (ADR-0032): fallback (ADR-0022) + header minimo (ADR-0023)
# ---------------------------------------------------------------------------

class TestDefault08:
    """#TCF.8M e' o default do encode multi-col (ADR-0032): fallback (min(TCF,raw,
    dict,split) por coluna) + header minimo (meta inline, ultima coluna sem size).
    Single-col nao tem header -> inalterado (orfao, 0029/0030)."""

    def _table(self):
        return {
            "hour": [str(i % 24) for i in range(300)],          # baixa-card -> dict (@)
            "code": [f"{(i * 2654435761) & 0xFFFFFF:06x}"       # all-uniq incompr. -> raw (!)
                     for i in range(300)],
            "nome": [f"item_{i:04d}_descricao_longa_unica" for i in range(300)],  # -> tcf
        }

    def test_default_is_v8(self):
        assert encode(self._table()).startswith(_MAGIC)

    def test_default_round_trip(self):
        t = self._table()
        assert decode(encode(t)) == t

    def test_default_meta_no_prefix(self):
        # header minimo: meta INLINE, sem prefixo '# '
        meta = _meta8(encode(self._table()))
        assert not meta.startswith("# ")

    def test_default_last_col_bare(self):
        # ultima coluna sem size (corpo ate' EOF)
        pairs = _meta8(encode(self._table())).split(",")
        assert "=" not in pairs[-1]

    def test_default_fallback_marker(self):
        # coluna all-unique incompressivel (code) cai pra raw -> algum par com '!'
        meta = _meta8(encode(self._table()))
        assert any(p.startswith("!") for p in meta.split(","))

    def test_default_dict_marker(self):
        # coluna baixa-card (hour) vira dicionario V2-B -> algum par com '@'
        meta = _meta8(encode(self._table()))
        assert any(p.startswith("@") for p in meta.split(","))

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
# Controles explicitos: fallback/min_header opt-out (Segment 1, 2026-06-14)
# ---------------------------------------------------------------------------

class TestExplicitControls:
    """fallback/min_header re-expostos como knobs OPT-OUT (default True). Todo
    multi-col sai #TCF.8M (ADR-0032); `min_header` controla so' a omissao do size
    da ultima coluna; `fallback` controla os `!`/`@`/`%` (raw/dict/split)."""

    def _table(self):
        return {
            "hour": [str(i % 24) for i in range(120)],          # baixa-card -> dict (@)
            "code": [f"{(i * 2654435761) & 0xFFFFFF:06x}"       # all-uniq incompr. -> raw (!)
                     for i in range(120)],
            "nome": [f"item_{i:03d}_descricao_unica" for i in range(120)],  # -> tcf
        }

    def test_default_zero_param_is_v8(self):
        assert encode(self._table()).startswith(_MAGIC)

    def test_fallback_off_keeps_min_header(self):
        # todas TCF (sem '!' nem '@') mas header minimo (ultima bare).
        # fallback=False desliga raw E dict (V2-B). Ainda #TCF.8M (ADR-0032).
        t = self._table()
        text = encode(t, fallback=False, min_header=True)
        assert text.startswith(_MAGIC)
        meta = _meta8(text)
        assert "!" not in meta
        assert "@" not in meta                     # dict tambem off (fallback=False)
        assert "=" not in meta.split(",")[-1]      # ultima sem size (min_header)
        assert decode(text) == t

    def test_min_header_off_keeps_fallback(self):
        # fallback ('!'/'@') mas sem header minimo: a ultima coluna MANTEM size
        # (todos os pares tem '='). Ainda #TCF.8M.
        t = self._table()
        text = encode(t, fallback=True, min_header=False)
        assert text.startswith(_MAGIC)
        meta = _meta8(text)
        assert "!" in meta
        assert all("=" in p.lstrip("!@") for p in meta.split(","))
        assert decode(text) == t

    def test_all_combos_round_trip(self):
        t = self._table()
        for fb in (True, False):
            for mh in (True, False):
                assert decode(encode(t, fallback=fb, min_header=mh)) == t

    def test_single_col_ignores_knobs(self):
        text = encode(["abc", "abcd"], fallback=False, min_header=False)
        assert not text.startswith("#TCF.")
        assert decode(text) == ["abc", "abcd"]

    # --- min_len override (Segment 2) em multi-col ---

    def test_min_len_default_unchanged(self):
        t = self._table()
        assert encode(t) == encode(t, min_len=None)

    @pytest.mark.parametrize("ml", [2, 5, 99])
    def test_min_len_override_multi_rt(self, ml):
        t = self._table()
        assert decode(encode(t, min_len=ml)) == t

    def test_min_len_parallel_byte_identical(self):
        t = self._table()
        assert encode(t, min_len=4) == encode(t, min_len=4, parallel=True)


# ---------------------------------------------------------------------------
# O-FMT-02: sort_by (natural sort, order-free) — Segment #5
# ---------------------------------------------------------------------------

class TestSortBy:
    """`sort_by="col"` reordena as linhas pela chave antes de encodar (O-FMT-02).
    Order-free: decode retorna a ordem ORDENADA (original nao recuperavel).
    Default None = sem reordenar (inalterado)."""

    def test_default_none_unchanged(self):
        t = {"a": ["1", "2", "3"], "b": ["x", "y", "z"]}
        assert encode(t) == encode(t, sort_by=None)

    def test_reorders_and_preserves_rows(self):
        t = {"cidade": ["SP", "RJ", "SP", "MG", "RJ", "SP"],
             "valor":  ["1", "2", "3", "4", "5", "6"]}
        dec = decode(encode(t, sort_by="cidade"))
        assert dec["cidade"] == sorted(dec["cidade"])            # chave ordenada
        assert sorted(zip(t["cidade"], t["valor"])) == \
               sorted(zip(dec["cidade"], dec["valor"]))          # mesmo multiset

    def test_sort_can_shrink(self):
        n = 120
        t = {"k": [["a", "b", "c"][i % 3] for i in range(n)],
             "v": [["x", "y", "z"][i % 3] for i in range(n)]}    # v correlaciona k
        assert len(encode(t, sort_by="k").encode("utf-8")) <= \
               len(encode(t).encode("utf-8"))

    def test_invalid_column_raises(self):
        with pytest.raises(ValueError, match="sort_by"):
            encode({"a": ["1"], "b": ["x"]}, sort_by="nope")

    def test_mismatched_lengths_raises(self):
        with pytest.raises(ValueError):
            encode({"a": ["1", "2"], "b": ["x"]}, sort_by="a")

    def test_ignored_for_list(self):
        # list nao tem colunas -> sort_by ignorado, ordem original preservada
        text = encode(["c", "a", "b"], sort_by="whatever")
        assert decode(text) == ["c", "a", "b"]


# ---------------------------------------------------------------------------
# V2-B dicionario/categorico (ADR-0025)
# ---------------------------------------------------------------------------

class TestV2BDict:
    """Coluna low-card vira [tabela de unicos] + [stream de indices], marcador
    '@'. Entra como 3o candidato do fallback (min tcf,raw,v2b) -> zero-regressao
    por construcao. Gated por `fallback` (off junto com raw)."""

    def _lowcard_table(self):
        ufs = ["SP", "RJ", "MG", "BA", "RS", "PR", "SC", "GO", "PE", "CE", "DF", "ES"]
        n = 400
        return {
            "uf": [ufs[i % len(ufs)] for i in range(n)],     # low-card -> @
            "id": [f"{i:05d}" for i in range(n)],            # all-unique -> nao dict
        }

    def test_dict_marker_present(self):
        meta = _meta8(encode(self._lowcard_table()))
        assert any(p.startswith("@") for p in meta.split(","))

    def test_dict_round_trip(self):
        t = self._lowcard_table()
        assert decode(encode(t)) == t

    def test_lowcard_goes_dict(self):
        side = SideOutputs()
        encode(self._lowcard_table(), side_outputs=side)
        assert "uf" in side.multi_info["dict_cols"]
        assert "id" not in side.multi_info["dict_cols"]   # all-unique nao vira dict

    def test_allunique_no_dict(self):
        # K == N (sem repeticao) -> V2-B nao aplica
        t = {"x": [f"v{i}" for i in range(50)], "y": [f"w{i}" for i in range(50)]}
        side = SideOutputs()
        encode(t, side_outputs=side)
        assert side.multi_info["dict_cols"] == []

    def test_dict_off_when_fallback_off(self):
        # fallback=False desliga raw E dict -> #TCF.8M byte-limpo (so' tcf)
        t = self._lowcard_table()
        text = encode(t, fallback=False, min_header=False)
        assert text.startswith(_MAGIC)
        assert "@" not in _meta8(text)
        assert decode(text) == t

    def test_dict_not_larger(self):
        # V2-B so' e' escolhido se MENOR -> total nunca cresce vs sem dict
        t = self._lowcard_table()
        with_dict = len(encode(t).encode("utf-8"))
        without = len(encode(t, fallback=False, min_header=True).encode("utf-8"))
        assert with_dict <= without

    @pytest.mark.parametrize("t", [
        {"a": ["x", "y", "x", "y", "x", "y"], "b": ["1", "2", "3", "4", "5", "6"]},
        {"a": ["", "A", "", "A", "", "B"], "b": ["p", "q", "r", "s", "t", "u"]},  # vazios
        {"u": ["á", "é", "á", "é", "í", "á", "é", "í"],                            # utf-8
         "v": [str(i) for i in range(8)]},
    ])
    def test_dict_rt_edge_cases(self, t):
        assert decode(encode(t)) == t

    def test_decode_v2b_helper_direct(self):
        import tcf.multi as m
        vals = ["A", "B", "C", "A", "B", "A", "C", "C"]
        body = m._v2b_encode(vals, cfg=m.DEFAULT_PIPELINE, min_len=None)
        assert body is not None
        assert m._decode_v2b(body) == vals


# ---------------------------------------------------------------------------
# Split estrutural (ADR-0026, H-STRUCT-01)
# ---------------------------------------------------------------------------

class TestStructSplit:
    """Valor estruturado (decimal/data/datetime/id) -> split em campos (template
    1x) -> cada campo low-card esmagado pelo V2-B. Marcador '%'. Candidato
    per-coluna no min() (zero-regressao). Gate: template 100% uniforme."""

    def _struct_table(self):
        n = 200
        return {
            "preco": [f"{i * 97}.{i % 100:02d}" for i in range(n)],            # decimal
            "data": [f"20{10 + i % 9}-{1 + i % 12:02d}-{1 + i % 28:02d}"
                     for i in range(n)],                                       # data
            "nome": [f"cliente_{i}_unico" for i in range(n)],                  # free-text
        }

    def test_split_marker_present(self):
        meta = _meta8(encode(self._struct_table()))
        assert any(p.startswith("%") for p in meta.split(","))

    def test_split_round_trip(self):
        t = self._struct_table()
        assert decode(encode(t)) == t

    def test_decimal_and_date_split(self):
        side = SideOutputs()
        encode(self._struct_table(), side_outputs=side)
        sc = side.multi_info["split_cols"]
        assert "preco" in sc and "data" in sc
        assert "nome" not in sc

    def test_non_uniform_no_split(self):
        t = {"a": ["1.5", "12.34.56", "2.7", "8", "9.9"] * 40,
             "b": [str(i) for i in range(200)]}
        side = SideOutputs()
        encode(t, side_outputs=side)
        assert "a" not in side.multi_info["split_cols"]

    def test_mixed_signs_no_split(self):
        t = {"a": [f"{'-' if i % 2 else ''}{i}.{i % 100:02d}" for i in range(200)],
             "b": [str(i) for i in range(200)]}
        side = SideOutputs()
        encode(t, side_outputs=side)
        assert "a" not in side.multi_info["split_cols"]

    def test_off_when_fallback_off(self):
        t = self._struct_table()
        text = encode(t, fallback=False, min_header=False)
        assert text.startswith(_MAGIC)
        assert "%" not in _meta8(text)
        assert decode(text) == t

    def test_split_not_larger(self):
        t = self._struct_table()
        with_split = len(encode(t).encode("utf-8"))
        without = len(encode(t, fallback=False, min_header=True).encode("utf-8"))
        assert with_split <= without

    @pytest.mark.parametrize("vals", [
        [f"-{i * 131}.{i % 100:02d}" for i in range(200)],                  # negativos
        [f"R$ {i * 97}.{i % 100:02d}" for i in range(200)],                 # prefixo
        [f"€ -{i * 53}.{(i * 7) % 100:02d}" for i in range(200)],      # utf8 + neg
        [f"{(i * 99173) % 1000:03d}.{(i * 7) % 1000:03d}-{i % 100:02d}"
         for i in range(200)],                                              # id-like
    ])
    def test_split_rt_edge_content(self, vals):
        t = {"v": vals, "k": [str(i) for i in range(len(vals))]}
        assert decode(encode(t)) == t

    def test_name_guard_marker_prefix(self):
        for bad in ["%x", "!x", "@x"]:
            with pytest.raises(ValueError, match="marcador"):
                encode({bad: ["1", "2"], "b": ["x", "y"]})

    def test_decode_struct_split_helper_direct(self):
        import tcf.multi as m
        vals = [f"{i}.{i % 10}" for i in range(20)]
        body = m._struct_split_encode(vals, cfg=m.DEFAULT_PIPELINE, min_len=None)
        assert body is not None
        assert m._decode_struct_split(body) == vals


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
        with pytest.raises(ValueError, match="separador"):
            encode({"a,b": ["1", "2"]})

    def test_col_name_with_equals_raises(self):
        with pytest.raises(ValueError, match="separador"):
            encode({"a=b": ["1", "2"]})

    def test_col_name_with_colon_raises(self):
        # INTERIM ate' o escaping (T-FMT-NAME-ESCAPING): ':' rejeitado (ADR-0032)
        with pytest.raises(ValueError, match="separador"):
            encode({"a:b": ["1", "2"], "c": ["3", "4"]})

    def test_null_values_converted_to_empty_str(self):
        table = {"a": ["x", None, "y"]}
        text = encode(table)
        decoded = decode(text)
        assert decoded == {"a": ["x", "", "y"]}

    def test_decode_legacy_magic_raises(self):
        # #TCF.6/.7 CORTADOS (ADR-0032) -> fail-loud com dica de git
        with pytest.raises(ValueError, match="legado"):
            decode("#TCF.6 M\nbad\n")
        with pytest.raises(ValueError, match="legado"):
            decode("#TCF.7 M\nbad\n")

    def test_decode_reserved_discriminator_raises(self):
        # #TCF.8H (hierarquico reservado, ADR-0031) -> fail-loud, nao decode orfao
        with pytest.raises(ValueError, match="RESERVADO|reservado"):
            decode("#TCF.8Hfoo\nbody")


# Aliases v0.6 encode_table/decode_table APOSENTADOS 2026-06-24
# (T-CODE-LEGACY-PRUNE-PRE-07). Testes de deprecation removidos junto.

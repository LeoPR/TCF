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

from tcf import encode, decode, view
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

    def test_encode_escalar_solto_vira_8h(self):
        # CONTRATO ATUALIZADO (Passo 2): escalar solto deixou de ser TypeError e vira `.8H`
        # `#V` (envelope; decode desembrulha e devolve o escalar). Dado nao-serializavel
        # (ex.: funcao) continua fail-loud na fronteira do .8H.
        assert decode(encode(123)) == 123
        assert encode(123).startswith("#TCF.8H#V")
        with pytest.raises(Exception):
            encode(lambda: 1)

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
        assert text.startswith("#TCF.8\n")   # version-stamp, nao o multi '#TCF.8M'
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
# Controles explicitos: fallback/min_header opt-out (Segment 1)
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
        assert text.startswith("#TCF.8\n")   # version-stamp, nao o multi '#TCF.8M'
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

    def test_name_starting_with_mode_prefix_escaped_rt(self):
        # nome comecando com !@% (colidiria com o parse de modo) -> escapado -> RT
        for nm in ["%x", "!x", "@x"]:
            t = {nm: ["1.5", "2.7"] * 100, "b": [str(i) for i in range(200)]}
            assert decode(encode(t)) == t

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
    def test_dict_vazio_vira_8h_E(self):
        # CONTRATO ATUALIZADO (Passo 2): `{}` (definicao vazia) vira `.8H` `#E`, nao fail-loud.
        assert encode({}) == "#TCF.8H#E\n"
        assert decode(encode({})) == {}

    def test_dict_ragged_vira_8h_objeto(self):
        # CONTRATO ATUALIZADO (Passo 2): dict com colunas de tamanhos diferentes (ragged) deixa
        # de ser erro-de-tabela e vira `.8H` OBJETO (cada campo = seu proprio array). RT preserva.
        d = {"a": ["1", "2"], "b": ["x"]}
        assert encode(d).startswith("#TCF.8H#O")
        assert decode(encode(d)) == d

    @pytest.mark.parametrize("table", [
        {"a,b": ["1", "2"], "c": ["x", "y"]},           # virgula
        {"x=y": ["1", "2"], "z": ["3", "4"]},           # igual
        {"created:at": ["1", "2"], "v": ["a", "b"]},    # dois-pontos
        {"!raw": ["1", "2"], "@d": ["3", "4"], "%s": ["5", "6"]},  # prefixos de modo
        {":": ["1", "2"], "=": ["3", "4"]},             # nome = so' separador
        {"a:b,c=d": ["1", "2"], "z": ["x", "y"]},       # multi-separador
        {"lit\\bs": ["1", "2"], "c": ["3", "4"]},       # backslash literal
    ])
    def test_col_name_with_separators_escaped_rt(self, table):
        # T-FMT-NAME-ESCAPING (M2): nomes com ,/=/:/!@%/\\ escapados via backslash -> RT
        assert decode(encode(table)) == table

    def test_col_name_with_newline_raises(self):
        # '\n' e' o separador de linha do meta -> irrepresentavel (unico rejeitado)
        with pytest.raises(ValueError, match="separador de linha"):
            encode({"a\nb": ["1", "2"]})

    def test_coluna_com_none_fica_no_8m(self):
        # A tabela RETANGULAR fica no `.8M` mesmo com `None` ou com coluna tipada: o
        # tipo viaja como tag de 1 byte no meta e o nulo pelo slot 0 do core. Antes ela
        # ia pro `.8H`, que nao roda o `min(tcf,raw,dict,split)` e cobrava ate' +43,6%
        # de bytes. O `None` segue PRESERVADO (nao vira '').
        table = {"a": ["x", None, "y"]}
        assert encode(table).startswith("#TCF.8M")
        assert decode(encode(table)) == {"a": ["x", None, "y"]}   # None PRESERVADO
        # o que E' aninhado continua no `.8H`
        assert encode([{"a": {"b": 1}}]).startswith("#TCF.8H")

    def test_decode_legacy_magic_raises(self):
        # #TCF.6/.7 CORTADOS (ADR-0032) -> fail-loud com dica de git
        with pytest.raises(ValueError, match="legado"):
            decode("#TCF.6 M\nbad\n")
        with pytest.raises(ValueError, match="legado"):
            decode("#TCF.7 M\nbad\n")

    def test_decode_unknown_discriminator_raises(self):
        # discriminador desconhecido apos #TCF.8 -> fail-loud, nao decode orfao silencioso.
        # ('H' NAO e' mais reservado — foi WELDED, T-CODE-TCF8H-WELD; ver test abaixo.)
        with pytest.raises(ValueError, match="desconhecido"):
            decode("#TCF.8Zfoo\nbody")

    def test_decode_hierarchical_welded(self):
        # #TCF.8H agora DECODA (weld T-CODE-TCF8H-WELD): RT de um documento aninhado via
        # a API unica encode()/decode() (Passo 2 — encode rota list[dict] pro .8H).
        doc = [{"nome": "Ana", "telefones": ["t1", "t2"]},
               {"nome": "Bruno", "telefones": ["t3"]}]
        assert decode(encode(doc)) == doc


# Aliases v0.6 encode_table/decode_table APOSENTADOS 2026-06-24
# (T-CODE-LEGACY-PRUNE-PRE-07). Testes de deprecation removidos junto.


class TestTagDeTipoNoMeta:
    """A tabela retangular TIPADA fica no `.8M`, e o tipo custa 1 byte de header.

    Antes, uma coluna `int` ou um `None` mandavam a tabela inteira pro `.8H`, que nao
    roda o `min(tcf,raw,dict,split)`: medido, +43,6% de bytes no adult-census.
    """

    def test_uma_letra_no_meta(self):
        t = {"a": ["x", "y"], "n": [1, 2], "z": ["p", "q"]}
        texto = {"a": ["x", "y"], "n": ["1", "2"], "z": ["p", "q"]}
        w, w_txt = encode(t), encode(texto)
        assert w.startswith("#TCF.8M")
        assert len(w) - len(w_txt) == 1          # so' a tag
        assert "N=n" in w.splitlines()[0]

    @pytest.mark.parametrize("tabela", [
        {"a": ["x", "y"], "n": [1, 2], "z": ["p", "q"]},          # int
        {"a": ["x", "y"], "f": [1.5, 2.5], "z": ["p", "q"]},      # float
        {"a": ["x", "y"], "b": [True, False], "z": ["p", "q"]},   # bool
        {"a": ["x", "y"], "n": [1, None], "z": ["p", "q"]},       # tipado com nulo
        {"a": ["x", None], "z": ["p", "q"]},                      # texto com nulo
        {"n": [1, 2]},                                            # unica coluna, tipada
        {"a": ["x", "y"], "n": [10, 20]},                         # tipada e ULTIMA
    ])
    def test_round_trip_preserva_tipo(self, tabela):
        assert decode(encode(tabela)) == tabela

    def test_tabela_de_texto_nao_muda(self):
        """Sem coluna tipada, o header sai igual ao de antes: a tag e' opt-in do dado."""
        t = {"a": ["x", "y"], "z": ["p", "q"]}
        assert encode(t).splitlines()[0] == "#TCF.8M!3=a,!z"

    def test_bool_usa_a_grafia_do_8h(self):
        """`true`/`false`, nao `True`/`False`: duas grafias quebrariam a canonicidade."""
        corpo = encode({"a": ["x", "y"], "b": [True, False], "z": ["p", "q"]})
        assert "true" in corpo and "True" not in corpo

    def test_aninhado_continua_no_8h(self):
        """O `.8H` segue dono do que E' aninhado: dict na celula e ragged.

        O 0-linha RETANGULAR saiu desta lista em 2026-08-26: ele ganhou grafia propria
        no `.8M` (corpo `@` com tabelinha vazia). O ragged continua aqui.
        """
        assert encode([{"a": {"b": 1}}]).startswith("#TCF.8H")
        assert encode([{"a": 1}, {"b": 2}]).startswith("#TCF.8H")
        assert encode({"a": [], "b": ["x"]}).startswith("#TCF.8H")
        assert encode({"a": []}) == "#TCF.8M@a\n0\n"

    def test_size_hex_canonico(self):
        """A tag so' e' inequivoca porque o size e' hex minusculo canonico."""
        from tcf.multi.core import _hex_size
        assert _hex_size("1b") == 27
        for ruim in ("1B", "0x5", "+5", "-5", "5_0", " 5", "05"):
            with pytest.raises(ValueError, match="size"):
                _hex_size(ruim)


class TestTagEColunaAnonima:
    """A tag de tipo convive com `drop_names` e com nome que TERMINA na tag.

    Latente achado ao fechar o view: com `drop_names` a ultima coluna tipada saia
    `!3N` e o decode a lia como coluna de NOME '3N', devolvendo string. O tipo se
    perdia calado, e o `view` reportava a coluna errada.
    """

    def test_anonima_tipada(self):
        w = encode({"n": [1, 2]}, drop_names=True)
        assert decode(w) == {"0": [1, 2]}          # posicional, e INT
        assert view(w).columns == ["0"]

    def test_anonima_varias_colunas(self):
        t = {"a": ["x", "y"], "n": [1, 2], "b": [True, False]}
        w = encode(t, drop_names=True)
        assert decode(w) == {"0": ["x", "y"], "1": [1, 2], "2": [True, False]}

    @pytest.mark.parametrize("nome", ["N", "B", "3N", "colunaN", "xB"])
    def test_nome_terminando_em_tag(self, nome):
        """`!N` seria ao mesmo tempo o nome 'N' e a anonima de tipo N: o nome escapa."""
        for valores in (["x", "y"], [1, 2]):
            t = {nome: valores}
            assert decode(encode(t)) == t

    def test_nome_e_anonima_nao_colidem(self):
        """As duas formas que colidiam agora sao distinguiveis no wire."""
        nomeada = encode({"N": ["x", "y"]})
        anonima = encode({"n": [1, 2]}, drop_names=True)
        assert nomeada.splitlines()[0] != anonima.splitlines()[0]
        assert decode(nomeada) == {"N": ["x", "y"]}
        assert decode(anonima) == {"0": [1, 2]}


class TestSplitRecusaNulo:
    """REGRESSÃO: `None` numa coluna estourava o encode com `TypeError` cru.

    O candidato `%split` guarda template mais campos de dígito, e não tem onde
    representar nulo. Faltava a guarda que os outros candidatos já têm: o
    `_fallback_safe` recusa nulo no modo raw pela mesma razão, e explica no comentário
    que o raw achataria o nulo numa linha vazia, perdendo a distinção entre `None` e
    `""`. Quem atende essa coluna é o candidato tcf, que tem slot próprio.

    O defeito PARECIA posicional (só a primeira linha), e não era: qualquer posição
    derrubava, desde que o primeiro valor formasse um template com 2 ou mais campos de
    dígito. Com template mais fraco a função retornava antes e o nulo passava, o que
    escondia o alcance real.

    Desistir do candidato não custa bytes: medido em 6 formas de template forte por 4
    frações de nulo, o modo que atende a coluna já é menor que o teto de um split
    tolerante, nas 24 combinações.
    Lab: `experiments/lab/dirty/2026-08/2026-08-25/2026-08-25-0400-split-e-nulo/`.
    """

    @pytest.mark.parametrize("rotulo,tab", [
        ("nulo-na-primeira", {"g": ["a", "b"], "v": [None, "a1b2"]}),
        ("nulo-no-meio", {"g": ["a", "b", "c"], "v": ["a1b2", None, "c3d4"]}),
        ("nulo-no-fim", {"g": ["a", "b"], "v": ["a1b2", None]}),
        ("coluna-toda-nula", {"g": ["a", "b"], "v": [None, None]}),
        ("nulo-com-template-forte",
         {"g": ["x"] * 50,
          "v": [f"10.0.{i}.{i}" if i % 5 else None for i in range(50)]}),
        ("grupo-todo-nulo", {"g": ["a", "a", "b", "b"], "v": [None, None, "1", "2"]}),
        ("nulo-e-vazio", {"g": ["a", "b", "c"], "v": [None, "", "1a2b"]}),
    ])
    def test_encoda_e_faz_roundtrip(self, rotulo, tab):
        blob = encode(tab)
        assert decode(blob) == tab, rotulo

    def test_single_col_com_nulo_e_template(self):
        dado = [None, "a1b2", "c3d4"]
        assert decode(encode(dado)) == dado

    def test_split_recusa_direto(self):
        """A guarda é no candidato, não no chamador: ele devolve `None`, não levanta."""
        from tcf.multi.split import _struct_split_encode
        from tcf.pipeline import PipelineConfig
        cfg = PipelineConfig()
        assert _struct_split_encode([None, "a1b2", "c3d4"], cfg=cfg, min_len=None) is None
        assert _struct_split_encode(["a1b2", None, "c3d4"], cfg=cfg, min_len=None) is None
        # sem nulo continua concorrendo
        assert _struct_split_encode(["10.0.1.2", "10.0.3.4", "10.0.5.6"] * 20,
                                    cfg=cfg, min_len=None) is not None

    def test_a_coluna_sem_nulo_nao_muda(self):
        """A guarda não pode tirar o split de quem não tem nulo."""
        from tcf.view import view
        col = [f"10.0.{i % 256}.{(i * 7) % 256}" for i in range(600)]
        blob = encode({"c": col, "x": [str(i) for i in range(600)]})
        assert view(blob)._mode["c"] == "split"
        assert decode(blob)["c"] == col

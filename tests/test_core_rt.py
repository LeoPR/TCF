"""Tests round-trip (RT) basicos pra src/tcf canonical (M10+).

Tests SEM dependencias externas — rodam em CI sem precisar de
Z:/tcf-data SQLite. Validam pipeline canonical:
- analyze_column + detect_cadence + detect_min_len
- OBAT (processar / processar_with_hint)
- HCC + seq-RLE (HCCSeqRLE.encode/decode)

Conexao:
- ADR-0011 (Pacote 1 welded canonical M10)
- ADR-0010 (auto-detect min_len)
- ADR-0008 (detect_cadence regra 2)
"""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from tcf import encode, decode
from tcf.auto_min_len import detect_min_len, detect_min_len_from_features
from tcf.column_features import analyze_column, _is_numeric_string


ROOT = Path(__file__).resolve().parent.parent
DATASETS_DIR = ROOT / "datasets" / "synthetic"

D1_D9 = [
    "D1-emails-simples",
    "D2-emails-quote-id",
    "D3-stress-substring",
    "D4-caos-mix",
    "D5-padroes-multiplos",
    "D6-poucos-em-ruido",
    "D7-aninhamento",
    "D8-cabeca-cauda",
    "D9-frequencia-alta",
]


def _ler_csv(name: str) -> list[str]:
    with (DATASETS_DIR / f"{name}.csv").open(encoding="utf-8") as f:
        r = csv.reader(f)
        next(r)
        return [row[0] for row in r if row]


# ---------------------------------------------------------------------------
# Round-trip basico
# ---------------------------------------------------------------------------


class TestRoundTripBasic:
    def test_empty(self):
        # Contrato definido no BUG-03 (T-QA-8 F0 lote 2, owner 2026-07-10):
        # 0 linhas e 1-linha-vazia colidem por construcao no formato -> encode
        # fail-loud (era xfail documentando o RT quebrado). Registro-'0' pra
        # declarar schema fica pro trilho de armazenamento (parquet/tcfx).
        with pytest.raises(ValueError, match="0 linhas|linhas"):
            encode([])

    def test_single_string(self):
        values = ["hello"]
        text = encode(values)
        assert decode(text) == values

    def test_duplicates(self):
        values = ["foo", "foo", "bar", "foo"]
        text = encode(values)
        assert decode(text) == values

    def test_with_special_chars(self):
        # Bug fix ADR-0007: separator pra `,`/`~` em literais
        values = ["abc,def", "ghi~jkl", "ABC*DEF"]
        text = encode(values)
        assert decode(text) == values

    def test_pacote3_comma_in_literal(self):
        # Caso patologico do EXP-013 TPC-H: "pending, bold reques"
        values = ["pending, bold reques", "pending, calm reques"]
        text = encode(values)
        assert decode(text) == values

    def test_digit_literals(self):
        # Digit literals devem ser escapados corretamente
        values = ["123", "abc 456 def", "789xyz"]
        text = encode(values)
        assert decode(text) == values


# ---------------------------------------------------------------------------
# Bug T-CODE-EMPTY-FRAG-INDEX-RT (2026-06-13): valor vazio + back-ref HCC
# ---------------------------------------------------------------------------


class TestEmptyValueFragIndex:
    """String vazia nao podia deslocar o index de fragmento HCC.

    Dois modos historicos (achados na caracterizacao V2-A, receita
    nome_fantasia):
    1. Empty desloca frag id -> back-ref de valor posterior com prefixo
       compartilhado corrompe/crasha (fix decode-side em syntax._parse_decl).
    2. Empty no FIM era comido por rstrip('\\n') (fix em hcc_seqrle.encode).
    Contrato: decode(encode(x)) == x. Byte-canonical preservado (decode-only +
    [:-1] == rstrip pra body sem vazios finais).
    """

    @pytest.mark.parametrize(
        "values",
        [
            # repro real (receita) + minimos sinteticos (empty inicial + prefixo)
            ["", "RESTAURANTE AR DE MINAS", "RESIDENCIAL NOVA BATALHA"],
            ["", "AAAB", "AAAC"],
            ["", "PREFIXOxxx", "PREFIXOyyy"],
            ["", "RES", "RESID"],  # modo 1 crashava: KeyError
            ["", "", "AAAB", "AAAC"],  # dois emptys iniciais
            ["", "ABCDEF", "GHIJKL"],  # empty sem prefixo compartilhado
            # empty NAO-primeiro + ref posterior (regrediu o 1o fix incondicional;
            # OBAT nao conta '' apos outra unica -> decode nao pode reservar frag)
            [
                "RED RETROSPOT MINI CASES",
                "",
                "HEART OF WICKER LARGE",
                "HEART OF WICKER SMALL",
            ],
            ["X", "", "PREFIXOaaa", "PREFIXObbb"],
            # modo 2: empty no fim (era perdido por rstrip)
            ["RESTAURANTE AR DE MINAS", "RESIDENCIAL NOVA BATALHA", ""],
            ["a", "b", "", ""],  # multiplos emptys finais
            # regressao: empty no meio JA passava — nao pode quebrar
            ["RESTAURANTE AR DE MINAS", "", "RESIDENCIAL NOVA BATALHA"],
        ],
    )
    def test_empty_value_roundtrip(self, values):
        text = encode(values)
        assert decode(text) == values

    def test_multi_col_empty_value(self):
        # mesma classe no caminho multi-col (per-col passa por HCCSeqRLE)
        table = {
            "nome": ["", "RESTAURANTE AR DE MINAS", "RESIDENCIAL NOVA BATALHA"],
            "uf": ["SP", "SP", "RJ"],
        }
        text = encode(table)
        assert decode(text) == table


# ---------------------------------------------------------------------------
# min_len override (Segment 2, 2026-06-14)
# ---------------------------------------------------------------------------


class TestMinLenOverride:
    """`encode(..., min_len=N)` sobrepoe o auto (detect_min_len). Default None =
    auto -> comportamento inalterado."""

    EMAILS = [
        "ana@acme.com.br",
        "bruno@acme.com.br",
        "carla@acme.com.br",
        "diego@acme.com.br",
    ]

    def test_default_none_equals_auto(self):
        assert encode(self.EMAILS) == encode(self.EMAILS, min_len=None)

    def test_high_min_len_disables_affix(self):
        # min_len enorme -> nenhum afixo casa -> output difere do auto; RT ok
        auto = encode(self.EMAILS)
        forced = encode(self.EMAILS, min_len=99)
        assert forced != auto
        assert decode(forced) == self.EMAILS

    def test_invalid_min_len_raises(self):
        with pytest.raises(ValueError, match="min_len"):
            encode(self.EMAILS, min_len=0)
        with pytest.raises(ValueError, match="min_len"):
            encode(self.EMAILS, min_len=-1)

    @pytest.mark.parametrize("ml", [2, 3, 4, 8, 50])
    def test_round_trip_various_min_len(self, ml):
        assert decode(encode(self.EMAILS, min_len=ml)) == self.EMAILS


# ---------------------------------------------------------------------------
# M10 baseline D1-D9 (INVARIANT 1523B)
# ---------------------------------------------------------------------------


class TestM10Baseline:
    """D1-D9 single-col baseline M10 = 1523B (ADR-0011)."""

    @pytest.mark.parametrize("ds", D1_D9)
    def test_d1_d9_rt(self, ds):
        values = _ler_csv(ds)
        text = encode(values)
        assert decode(text) == values

    def test_m10_baseline_invariant(self):
        """Total bytes D1-D9 = 1523B (INVARIANT desde 2026-05-22)."""
        total = 0
        for ds in D1_D9:
            values = _ler_csv(ds)
            text = encode(values)
            total += len(text.encode("utf-8"))
        assert total == 1523, (
            f"M10 baseline mudou: {total}B (esperado 1523B). "
            "Welding nao-zero-risk pode ter alterado pipeline canonical."
        )


# ---------------------------------------------------------------------------
# ColumnFeatures (H-DA-11c)
# ---------------------------------------------------------------------------


class TestColumnFeatures:
    def test_empty(self):
        f = analyze_column([])
        assert f.n_rows == 0
        assert f.n_unicas == 0
        assert f.avg_len == 0.0

    def test_simple(self):
        f = analyze_column(["abc", "def", "abc"])
        assert f.n_rows == 3
        assert f.n_unicas == 2
        assert f.avg_len == 3.0
        assert f.cardinality == pytest.approx(2 / 3)
        assert not f.is_numeric

    def test_numeric(self):
        f = analyze_column(["123", "456", "789"])
        assert f.is_numeric

    def test_numeric_partial_not_numeric(self):
        f = analyze_column(["123", "abc"])
        assert not f.is_numeric

    def test_sample_size(self):
        # sample default = 20
        values = [str(i) for i in range(100)]
        f = analyze_column(values)
        assert len(f.sample) == 20


# ---------------------------------------------------------------------------
# detect_min_len (H-DA-11, ADR-0010)
# ---------------------------------------------------------------------------


class TestDetectMinLen:
    def test_gating_small_dataset(self):
        """n < 100 sempre retorna 3 (preserva M9/M10 baseline)."""
        values = ["abc"] * 50
        assert detect_min_len(values) == 3

    def test_gating_threshold(self):
        # Exatamente 99 -> 3 (gating ativa)
        values = [f"v{i}" for i in range(99)]
        assert detect_min_len(values) == 3

    def test_low_cardinality_returns_3(self):
        # 200 rows mas 2 valores unicos = card 0.01 < 0.2 -> 3
        values = ["A", "B"] * 100
        assert detect_min_len(values) == 3

    def test_high_card_long_strings_returns_6(self):
        # avg_len >= 25 -> 6
        values = [f"very_long_string_padding_{i:05d}_extra" for i in range(200)]
        assert detect_min_len(values) == 6

    def test_high_card_short_strings_returns_4(self):
        # avg ~5, card alta -> 4 (regra "avg>=3 + card>=0.2")
        values = [f"id_{i:03d}" for i in range(200)]
        # avg = 6 chars (id_NNN), card = 1.0
        # cai em "avg >= 5 + is_num? not" -> "avg >= 3 + card >= 0.2" -> 4
        result = detect_min_len(values)
        assert result == 4

    def test_features_api_equiv(self):
        # Backward-compat wrapper deve dar mesmo resultado que from_features
        values = ["abc"] * 200
        f = analyze_column(values)
        assert detect_min_len(values) == detect_min_len_from_features(f)


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_unicode(self):
        values = ["alpha", "beta", "gamma"]
        text = encode(values)
        assert decode(text) == values

    def test_long_string(self):
        values = ["x" * 1000]
        text = encode(values)
        assert decode(text) == values

    def test_many_duplicates(self):
        values = ["same"] * 500
        text = encode(values)
        assert decode(text) == values

    def test_is_numeric_string_helpers(self):
        assert _is_numeric_string("123")
        assert _is_numeric_string("-1.5")
        assert _is_numeric_string("0")
        assert _is_numeric_string("1e5")
        assert not _is_numeric_string("")
        assert not _is_numeric_string("abc")
        assert not _is_numeric_string("12abc")


class TestRTEdges:
    """Regressao das 2 violacoes de RT achadas na revisao 2026-07-04 (T-CODE-RT-EDGES).

    Bug 1: seq-RLE comia whitespace do template (raw.strip() no decode).
    Bug 2: `\\n`/`\\r` embutido corrompia o RT em silencio (sem validacao na fronteira).
    """

    @pytest.mark.parametrize(
        "values",
        [
            ["a1 ", "a2 ", "a3 "],  # trailing space (repro original)
            ["a1\t", "a2\t", "a3\t"],  # trailing tab
            ["a1  ", "a2  ", "a3  "],  # trailing double space
            [" a1", " a2", " a3"],  # leading space
            ["x1 y", "x2 y", "x3 y"],  # whitespace interno
            ["1 ", "2 ", "3 "],  # digito + space (seq puro)
            ["ip10.0.0.1 ", "ip10.0.0.2 ", "ip10.0.0.3 "],  # multi-run + trailing
        ],
    )
    def test_seqrle_preserves_whitespace(self, values):
        # bug 1: o whitespace ESTA no template do marker; o decode nao pode strippar
        assert decode(encode(values)) == values

    @pytest.mark.parametrize(
        "values",
        [
            ["a\nb", "c"],
            ["a\rb"],
            ["ok", "line\nbreak"],
        ],
    )
    def test_reject_linebreak_single(self, values):
        with pytest.raises(ValueError):
            encode(values)

    def test_reject_linebreak_multi(self):
        with pytest.raises(ValueError):
            encode({"col": ["a\nb", "c"]})

    def test_clean_data_still_encodes(self):
        # a validacao nao pode rejeitar dado limpo
        assert decode(encode(["ok", "fine", "clean"])) == ["ok", "fine", "clean"]

    @pytest.mark.parametrize(
        "sep",
        [
            "\v",  # vertical tab
            "\f",  # form feed
            "\u0085",  # NEL
            "\u2028",  # line separator
            "\u2029",  # paragraph separator
        ],
    )
    def test_unicode_line_separators_single_roundtrip(self, sep):
        # BUG-14: estes chars sao dados validos (LF-only no formato), nao delimitadores.
        values = [f"a{sep}b", "ok"]
        assert decode(encode(values)) == values

    @pytest.mark.parametrize(
        "sep",
        [
            "\v",  # vertical tab
            "\f",  # form feed
            "\u0085",  # NEL
            "\u2028",  # line separator
            "\u2029",  # paragraph separator
        ],
    )
    def test_unicode_line_separators_multi_roundtrip(self, sep):
        table = {
            "a": [f"a{sep}b", "x"],
            "b": ["1", "2"],
        }
        assert decode(encode(table)) == table


class TestBug15CaretLeadingLiteral:
    """BUG-15 (achado 2026-07-12 pelo RT counter-proof do lab spec-camadas): um
    literal começando com '^' (marcador de ref do HCC) quebrava o RT em modo
    tcf/dict — o decode lia a linha como '^eid' (crash em não-dígito, corrupção
    SILENCIOSA em dígito). O '*'-líder já era escapado (`\*`); o '^'-líder não.
    Fix: escape simétrico do '^'-líder no emit (decode de-escapa via _parse_decl)."""

    def test_caret_literal_tcf_mode(self):
        col = ["^abc"] * 30 + ["y"] * 30           # ganha tcf
        assert decode(encode(col)) == col

    def test_caret_literal_dict_mode(self):
        col = ["^ab", "^cd"] * 40                   # ganha dict (K=2)
        assert decode(encode(col)) == col

    def test_caret_digit_no_silent_corruption(self):
        # '^12' NÃO pode ser lido como ref pro eid 12 (era corrupção silenciosa)
        col = ["^12"] * 30 + ["real"] * 30
        assert decode(encode(col)) == col

    def test_caret_multi_col(self):
        table = {"a": ["^x"] * 20 + ["z"] * 20, "b": [str(i) for i in range(40)]}
        assert decode(encode(table)) == table

    def test_caret_only_and_empty_after(self):
        for col in (["^"] * 30 + ["a"] * 30, ["^^^"] * 30 + ["b"] * 30):
            assert decode(encode(col)) == col

    def test_mid_string_caret_unchanged(self):
        # '^' NO MEIO nunca foi ambíguo -> deve seguir byte-neutro (sem escape)
        col = ["a^b", "c^d^e", "x"]
        assert decode(encode(col)) == col

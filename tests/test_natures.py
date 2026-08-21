"""Tests pra src/tcf/natures (ADR-0015 welding TemplatedCheckedSpec).

Valida:
- SPEC_CPF e SPEC_CNPJ encode/decode round-trip
- Fallback marker pra valores nao-compressible
- Integration com tcf.encode/decode (single + multi-col)
- D17a INVARIANT preservado (sem nature param = sem mudanca; pin vivo em test_regression_v1_baseline)
- Classify taxonomy (Kim 2003)
"""

from __future__ import annotations

import csv
from dataclasses import replace
from pathlib import Path

import pytest

from tcf import encode, decode, SPEC_CPF, SPEC_CNPJ
from tcf.natures import (
    encode_value,
    decode_value,
    classify_value,
    BASE94,
    MARKER_LITERAL,
    SPEC_IP,
    SPEC_DATA_ISO,
    SPEC_REGISTRY,
    _resolve_nature_id,
)
from tcf.side_outputs import SideOutputs


ROOT = Path(__file__).resolve().parent.parent


# ===========================================================================
# Spec validation
# ===========================================================================


class TestSpecs:
    def test_cpf_spec_attrs(self):
        assert SPEC_CPF.name == "cpf"
        assert SPEC_CPF.body_length == 9
        assert SPEC_CPF.check_length == 2
        assert SPEC_CPF.encoded_length == 5

    def test_cnpj_spec_attrs(self):
        assert SPEC_CNPJ.name == "cnpj"
        assert SPEC_CNPJ.body_length == 12
        assert SPEC_CNPJ.check_length == 2
        assert SPEC_CNPJ.encoded_length == 7

    def test_base94_size_sufficient(self):
        # 80^5 > 10^9 (CPF body 9 digits)
        assert len(BASE94) ** 5 > 10**9
        # 80^7 > 10^12 (CNPJ body 12 digits)
        assert len(BASE94) ** 7 > 10**12

    def test_base94_safe_chars(self):
        # Nenhum char reservado TCF
        forbidden = set("\n\r\t ,~*\\#=[]<>\"'`")
        for c in BASE94:
            assert c not in forbidden
        # Marker tambem fora
        assert MARKER_LITERAL not in BASE94


# ===========================================================================
# CPF — encode/decode/classify
# ===========================================================================


class TestCPF:
    def test_encode_decode_valid(self):
        valid = "529.982.247-25"  # known valid
        encoded, status = encode_value(SPEC_CPF, valid)
        assert status == "compressible"
        decoded = decode_value(SPEC_CPF, encoded)
        assert decoded == valid

    def test_encode_format_mismatch(self):
        encoded, status = encode_value(SPEC_CPF, "12345678909")  # no mask
        assert status == "format_unmasked"
        assert encoded.startswith(MARKER_LITERAL)

    def test_encode_check_invalid(self):
        encoded, status = encode_value(SPEC_CPF, "529.982.247-99")  # wrong check
        assert status == "check_invalid"
        assert encoded.startswith(MARKER_LITERAL)

    def test_encode_empty(self):
        encoded, status = encode_value(SPEC_CPF, "")
        assert status == "empty_value"

    def test_decode_literal_fallback(self):
        # Encoded with marker -> decoded back unchanged
        original = "abc.def.ghi-jk"
        encoded = MARKER_LITERAL + original
        decoded = decode_value(SPEC_CPF, encoded)
        assert decoded == original

    def test_classify_taxonomy(self):
        assert classify_value(SPEC_CPF, "") == "empty_value"
        assert classify_value(SPEC_CPF, "529.982.247-25") == "compressible"
        assert classify_value(SPEC_CPF, "52998224725") == "format_unmasked"
        assert classify_value(SPEC_CPF, "529.982.247-99") == "check_invalid"


# ===========================================================================
# CNPJ — encode/decode
# ===========================================================================


class TestCNPJ:
    def test_encode_decode_valid(self):
        # Valid CNPJ
        valid = "11.222.333/0001-81"
        encoded, status = encode_value(SPEC_CNPJ, valid)
        assert status == "compressible"
        decoded = decode_value(SPEC_CNPJ, encoded)
        assert decoded == valid

    def test_classify_taxonomy_cnpj(self):
        assert classify_value(SPEC_CNPJ, "") == "empty_value"
        assert classify_value(SPEC_CNPJ, "11.222.333/0001-81") == "compressible"


# ===========================================================================
# Integration with tcf.encode/decode
# ===========================================================================


class TestEncodeIntegration:
    def test_d17a_invariant_without_nature(self):
        """D17a INVARIANT preservado quando nature NAO eh fornecido."""
        with (ROOT / "datasets/synthetic/D17a-multi-column-mixed.csv").open(
            encoding="utf-8"
        ) as f:
            r = csv.reader(f)
            header = next(r)
            cols = {h: [] for h in header}
            for row in r:
                for h, v in zip(header, row):
                    cols[h].append(v)
        text = encode(cols)
        assert (
            len(text.encode("utf-8")) == 300
        )  # D17a 0.7 (V2-B: era 307; ADR-0024/0025)

    def test_single_col_with_nature(self):
        cpfs = ["529.982.247-25", "111.444.777-35"]
        text = encode(cpfs, nature=SPEC_CPF)
        decoded = decode(text, nature=SPEC_CPF)
        assert decoded == cpfs

    def test_single_col_with_nature_mixed_valid_invalid(self):
        cpfs = [
            "529.982.247-25",  # valid
            "529.982.247-99",  # check invalid
            "abc.def.ghi-jk",  # format mismatch
            "111.444.777-35",  # valid
        ]
        text = encode(cpfs, nature=SPEC_CPF)
        decoded = decode(text, nature=SPEC_CPF)
        assert decoded == cpfs  # RT 100% mesmo com fallbacks

    def test_multi_col_with_nature_per_col(self):
        table = {
            "cpf": ["529.982.247-25", "111.444.777-35"],
            "cnpj": ["11.222.333/0001-81", "11.222.333/0001-81"],
            "plain": ["foo", "bar"],
        }
        text = encode(
            table,
            nature_per_col={
                "cpf": SPEC_CPF,
                "cnpj": SPEC_CNPJ,
            },
        )
        decoded = decode(
            text,
            nature_per_col={
                "cpf": SPEC_CPF,
                "cnpj": SPEC_CNPJ,
            },
        )
        assert decoded == table

    def test_multi_col_partial_nature(self):
        """nature_per_col so' pra algumas colunas; outras default."""
        table = {
            "cpf": ["529.982.247-25"],
            "plain": ["whatever"],
        }
        text = encode(table, nature_per_col={"cpf": SPEC_CPF})
        decoded = decode(text, nature_per_col={"cpf": SPEC_CPF})
        assert decoded == table

    def test_default_behavior_unchanged_without_nature(self):
        """Default encode SEM nature param: byte-canonical preservado."""
        cpfs = ["529.982.247-25", "111.444.777-35"]
        text_with = encode(cpfs)
        text_without = encode(cpfs)
        assert text_with == text_without

    def test_compression_gain_with_nature(self):
        """Nature deve comprimir CPFs validos vs M10 puro."""
        cpfs = ["529.982.247-25"] * 5 + ["111.444.777-35"] * 5
        bytes_default = len(encode(cpfs).encode("utf-8"))
        bytes_nature = len(encode(cpfs, nature=SPEC_CPF).encode("utf-8"))
        # Nature deve ser menor pra CPFs validos
        assert bytes_nature < bytes_default


# ===========================================================================
# Self-describing — nature-id no header (#TCF.8, ADR-0027)
# ===========================================================================


class TestNatureMarkHeader:
    def test_self_describing_roundtrip(self):
        """A feature central: encode com nature -> decode SEM nature recupera."""
        table = {
            "cpf": ["529.982.247-25", "111.444.777-35"],
            "doc": ["11.222.333/0001-81", "11.222.333/0001-81"],
            "plain": ["foo", "bar"],
        }
        text = encode(table, nature_per_col={"cpf": SPEC_CPF, "doc": SPEC_CNPJ})
        assert decode(text) == table  # SEM nature_per_col no decode

    def test_magic_is_tcf8m_inline(self):
        table = {"doc": ["11.222.333/0001-81"], "plain": ["x"]}
        text = encode(table, nature_per_col={"doc": SPEC_CNPJ})
        line0 = text.split("\n")[0]
        assert line0.startswith("#TCF.8M")  # disc M, SEM espaco (ADR-0029)
        assert not line0.startswith("#TCF.8 ")  # nao colide com single+spec
        assert ":cnpj" in line0  # meta INLINE na linha do shebang

    def test_default_no_nature_id(self):
        """Sem nature -> #TCF.8M sem sufixo :id (ADR-0032 default; determinístico)."""
        table = {"a": ["529.982.247-25", "111.444.777-35"], "b": ["x", "y"]}
        text = encode(table)  # SEM nature
        line0 = text.split("\n", 1)[0]
        assert line0.startswith("#TCF.8M")
        assert text == encode(table)  # determinístico
        assert ":" not in line0[len("#TCF.8M") :]  # nenhum :id no meta inline

    def test_no_double_apply_with_nature_in_decode(self):
        """Precedência: encode+decode ambos com nature_per_col -> RT (header vence)."""
        table = {"cpf": ["529.982.247-25"], "doc": ["11.222.333/0001-81"]}
        npc = {"cpf": SPEC_CPF, "doc": SPEC_CNPJ}
        text = encode(table, nature_per_col=npc)
        assert decode(text, nature_per_col=npc) == table  # não dupla-aplica

    def test_ip_self_describing(self):
        table = {"ip": ["192.168.1.1", "10.0.0.1"], "x": ["a", "b"]}
        text = encode(table, nature_per_col={"ip": SPEC_IP})
        assert text.startswith("#TCF.8M")  # inline meta (ADR-0029)
        assert decode(text) == table

    def test_unknown_nature_id_raises(self):
        """Id desconhecido -> ERRO (T-QA-8 BUG-13b, owner 2026-07-10): revoga o
        forward-compat de 2026-06-24 — warning + dado cru base-94 calado era
        corrupção silenciosa; pre-1.0 sem compat (ADR-0024)."""
        table = {"doc": ["11.222.333/0001-81"], "x": ["a"]}
        text = encode(table, nature_per_col={"doc": SPEC_CNPJ})
        tampered = text.replace(":cnpj", ":FUTURE9")
        with pytest.raises(ValueError, match="desconhecido"):
            decode(tampered)

    def test_colon_in_colname_with_nature_rt(self):
        """T-FMT-NAME-ESCAPING (M2): ':' no nome escapado '\\:'; a nature `:id` e' o
        ULTIMO ':' NAO-escapado -> RT preserva nome-com-':' + nature."""
        table = {"ns:col": ["529.982.247-25"], "x": ["a"]}
        text = encode(table, nature_per_col={"ns:col": SPEC_CPF})
        assert decode(text, nature_per_col={"ns:col": SPEC_CPF}) == table

    def test_colon_in_colname_without_nature_rt(self):
        """':' no nome (sem nature) escapado -> RT (M2)."""
        table = {"created:at": ["2026-01-01", "2026-01-02"], "x": ["a", "b"]}
        assert decode(encode(table)) == table

    def test_resolve_nature_id(self):
        assert _resolve_nature_id("cpf") is SPEC_CPF
        assert _resolve_nature_id("cnpj") is SPEC_CNPJ
        assert _resolve_nature_id("ip") is SPEC_IP
        assert _resolve_nature_id("nao-existe") is None  # tolerante, não raise
        # RE-PIN 2026-08-13 (weld A ADR-0041): a resolucao passou a ser por WIRE_ID
        # (plano do DADO) e ESTRITA — `dt` resolve, `data-iso` NAO (wire historico
        # le-se out-of-band; ADR-0024).
        assert _resolve_nature_id("dt") is SPEC_DATA_ISO
        assert _resolve_nature_id("data-iso") is None
        # O vocabulario continua FECHADO nos DOIS planos — o teste existe pra que
        # crescer seja decisao, nao acidente. (name-plane pinado desde 2026-08-08.)
        from tcf.natures import _WIRE_REGISTRY

        # RE-PIN 2026-08-14 (weld EXP-018): o registry ganhou `int-pad`/`ipad`.
        # RE-PIN 2026-08-21 (weld H-15-01): ganhou `cnpj-alfa`/`cnpja` — o CNPJ
        # alfanumerico da IN RFB 2.229/2024. COEXISTE com `cnpj`, nao o substitui.
        assert set(SPEC_REGISTRY) == {
            "cpf", "cnpj", "cnpj-alfa", "ip", "data-iso", "int-pad"}
        assert set(_WIRE_REGISTRY) == {"cpf", "cnpj", "cnpja", "ip", "dt", "ipad"}


# ===========================================================================
# Colunas anonimas / posicionais — drop_names (nome = ordem, SQL-like)
# ===========================================================================


class TestDropNames:
    def test_roundtrip_posicional(self):
        table = {"a": ["x", "y"], "b": ["p", "q"]}
        text = encode(table, drop_names=True)
        assert decode(text) == {"0": ["x", "y"], "1": ["p", "q"]}  # nome = ordem

    def test_forca_tcf8m(self):
        text = encode({"a": ["x"], "b": ["y"]}, drop_names=True)
        assert text.startswith("#TCF.8M")  # anonimo = feature v8

    def test_meta_sem_nomes(self):
        text = encode({"aaa": ["x"], "bbb": ["y"]}, drop_names=True)
        line0 = text.split("\n")[0]
        assert "aaa" not in line0 and "bbb" not in line0  # nomes omitidos

    def test_menor_que_nomeado(self):
        table = {
            "coluna_longa_um": ["x", "y", "x"],
            "coluna_longa_dois": ["p", "q", "p"],
        }
        assert len(encode(table, drop_names=True)) < len(encode(table))

    def test_com_nature(self):
        table = {"doc": ["11.222.333/0001-81"], "x": ["a"]}
        text = encode(table, nature_per_col={"doc": SPEC_CNPJ}, drop_names=True)
        assert decode(text) == {"0": ["11.222.333/0001-81"], "1": ["a"]}

    def test_named_default_inalterado(self):
        table = {"a": ["x", "y"], "b": ["p", "q"]}
        assert decode(encode(table)) == table  # default nomeado intacto


# ===========================================================================
# Discriminador #TCF.8 (1 char apos '#TCF.8': M / espaco / newline) — ADR-0029
# ===========================================================================


class TestDiscriminatorV8:
    def test_disc_multi_M(self):
        t = encode(
            {"doc": ["11.222.333/0001-81"], "x": ["a"]},
            nature_per_col={"doc": SPEC_CNPJ},
        )
        assert t[:7] == "#TCF.8M"  # M logo apos #TCF.8 (sem espaco)
        assert decode(t) == {"doc": ["11.222.333/0001-81"], "x": ["a"]}

    def test_disc_single_space(self):
        t = encode(["529.982.247-25", "111.444.777-35"], nature=SPEC_CPF)
        assert t[:7] == "#TCF.8 "  # espaco apos #TCF.8

    def test_version_stamp_emit_and_interpret(self):
        """#TCF.8\\n = carimbo opt-in (magic-number p/ file/libmagic)."""
        vals = ["a@b.com", "c@d.com", "a@b.com"]
        t = encode(vals, stamp=True)
        assert t.split("\n")[0] == "#TCF.8"  # linha so' '#TCF.8' (disc = newline)
        assert decode(t) == vals  # interpreta -> list (single-col)

    def test_version_stamp_e_o_default(self):
        """ADR-0034 (supersede o default do ADR-0029): header e' DEFAULT em 100% dos casos.
        O escape (orfao) existe, mas so' EXPLICITO — transmissao / container tipo parquet."""
        vals = ["a@b.com", "c@d.com"]
        assert encode(vals).startswith("#TCF.8\n")                 # default = COM header
        assert not encode(vals, stamp=False).startswith("#TCF.")   # escape explicito

    def test_version_stamp_interpret_construido(self):
        """Capacidade de interpretar um #TCF.8\\n<body> (mesmo construido a mao)."""
        plain = encode(["x", "y", "x"], stamp=False)  # body orfao (escape explicito)
        stamped = "#TCF.8\n" + plain
        assert decode(stamped) == ["x", "y", "x"]

    def test_stamp_ignorado_com_nature(self):
        """Com nature, o header de spec ja' versiona -> stamp e' no-op."""
        t = encode(["529.982.247-25"], nature=SPEC_CPF, stamp=True)
        assert t.startswith("#TCF.8 ")  # forma de spec, nao '#TCF.8\\n'
        assert decode(t) == ["529.982.247-25"]


# ===========================================================================
# Self-describing SINGLE-COL — nature-id no header (#TCF.8 sem M, ADR-0027)
# ===========================================================================


class TestNatureMarkSingleCol:
    def test_no_spec_byte_identico(self):
        """Single-col SEM spec -> version-stamp `#TCF.8`, nunca header de spec (ADR-0034)."""
        vals = ["529.982.247-25", "111.444.777-35", "529.982.247-25"]
        text = encode(vals)  # sem nature
        # version-stamp (default), nao '#TCF.8 :id'. O sufixo de POLARIDADE (weld
        # 2026-07-26) pode acompanhar o stamp: `#TCF.8`, `#TCF.8!` ou `#TCF.8!!`.
        linha0 = text.split("\n")[0]
        assert linha0.startswith("#TCF.8") and ":" not in linha0
        assert not text.startswith("#TCF.8 ")  # nenhum header de spec
        assert text == encode(vals)  # deterministico
        assert decode(text) == vals

    def test_spec_self_describing(self):
        """Feature: encode single-col com nature -> decode SEM nature recupera."""
        cpfs = ["529.982.247-25", "111.444.777-35", "abc.def.ghi-jk"]
        text = encode(cpfs, nature=SPEC_CPF)
        assert decode(text) == cpfs  # SEM nature no decode

    def test_magic_sem_m_uma_linha(self):
        cpfs = ["529.982.247-25", "111.444.777-35"]
        text = encode(cpfs, nature=SPEC_CPF)
        # header numa LINHA SO': '#TCF.8 :cpf' (sem ' M' -> single; nome vazio)
        assert text.split("\n")[0] == "#TCF.8 :cpf"
        assert not text.startswith("#TCF.8 M")  # nao colide com multi

    def test_retorna_list_nao_dict(self):
        text = encode(["529.982.247-25"], nature=SPEC_CPF)
        assert isinstance(decode(text), list)  # single-col -> list

    def test_nome_opcional(self):
        cpfs = ["529.982.247-25", "111.444.777-35"]
        text = encode(cpfs, nature=SPEC_CPF, name="docs")
        assert text.split("\n")[0] == "#TCF.8 docs:cpf"  # nome no header
        assert decode(text) == cpfs  # nome nao afeta os valores

    def test_nome_comecando_com_m_nao_colide(self):
        """Regressao: nome 'Meu' -> '#TCF.8 Meu:cpf' NAO pode virar multi."""
        cpfs = ["529.982.247-25", "111.444.777-35"]
        text = encode(cpfs, nature=SPEC_CPF, name="Meu")
        assert text.split("\n")[0] == "#TCF.8 Meu:cpf"
        assert decode(text) == cpfs  # decodifica como single, nao multi

    def test_ip_single_col_self_describing(self):
        # FLOOR total-byte (owner 2026-07-12): o IP nature COMPETE. Achado: em
        # single-col o padding do IP EMPATA com o pipeline (o núcleo já normaliza),
        # então o IP nature raramente vence (só onde há estrutura de subnet que a
        # nature explora melhor — ADR-0016). RT sempre; header condicional ao win.
        ips = ["192.168.1.1", "10.0.0.1", "172.16.0.1"]
        text = encode(ips, nature=SPEC_IP)
        assert decode(text) == ips  # RT independe do win
        line0 = text.split("\n")[0]
        # win (spec) OU piso (version-stamp, com ou sem sufixo de polaridade)
        assert line0 == "#TCF.8 :ip" or (line0.startswith("#TCF.8") and ":" not in line0)

    def test_unknown_id_raises(self):
        # ERRO estrito (BUG-13b, owner 2026-07-10 — antes: warning + cru calado)
        text = encode(["529.982.247-25", "111.444.777-35"], nature=SPEC_CPF)
        tampered = text.replace(":cpf", ":FUTURE9", 1)
        with pytest.raises(ValueError, match="desconhecido"):
            decode(tampered)

    def test_no_double_apply(self):
        """Precedencia header-vence: encode+decode ambos com nature -> RT."""
        cpfs = ["529.982.247-25", "111.444.777-35"]
        text = encode(cpfs, nature=SPEC_CPF)
        assert decode(text, nature=SPEC_CPF) == cpfs

    def test_custom_spec_roundtrip_requires_matching_out_of_band(self):
        # RE-PIN 2026-08-13 (weld A ADR-0041): spec de terceiro precisa de wire_id
        # PROPRIO — `replace(name=...)` sozinho herdaria o wire_id core `cpf` e a
        # emissao recusa a mascarada (pin em TestWireIdDoisPlanos). Convencao `x*`.
        custom = replace(SPEC_CPF, name="custom-cpf", wire_id="xcpf")
        cpfs = ["529.982.247-25", "111.444.777-35"]
        text = encode(cpfs, nature=custom)
        assert text.split("\n", 1)[0] == "#TCF.8 :xcpf"
        with pytest.raises(ValueError, match="desconhecido"):
            decode(text)
        assert decode(text, nature=custom) == cpfs
        wrong = replace(SPEC_CPF, name="other-cpf", wire_id="xother")
        with pytest.raises(ValueError, match="nao coincide"):
            decode(text, nature=wrong)

    def test_name_com_colon_rejeitado(self):
        with pytest.raises(ValueError, match="':'|reservado"):
            encode(["529.982.247-25"], nature=SPEC_CPF, name="ns:bad")


# ===========================================================================
# Telemetria de apply-rate (SideOutputs.nature_apply) — byte-neutra
# ===========================================================================


class TestNatureApplyTelemetry:
    def test_byte_neutral_with_side_outputs(self):
        """Coletar telemetria NAO muda os bytes do .tcf."""
        cpfs = ["529.982.247-25", "abc.def.ghi-jk", "111.444.777-35", ""]
        out_no = encode(cpfs, nature=SPEC_CPF)
        out_yes = encode(cpfs, nature=SPEC_CPF, side_outputs=SideOutputs())
        assert out_no == out_yes

    def test_single_col_apply_rate(self):
        cpfs = [
            "529.982.247-25",  # compressible
            "111.444.777-35",  # compressible
            "529.982.247-99",  # check_invalid
            "abc.def.ghi-jk",  # format_mismatch
            "",  # empty_value
        ]
        so = SideOutputs()
        encode(cpfs, nature=SPEC_CPF, side_outputs=so)
        stats = so.nature_apply["val"]
        assert stats["spec"] == "cpf"
        assert stats["total"] == 5
        assert stats["compressible"] == 2
        assert stats["apply_rate"] == 2 / 5
        assert stats["by_status"]["compressible"] == 2
        assert stats["by_status"]["format_mismatch"] == 1
        assert stats["by_status"]["empty_value"] == 1
        assert sum(stats["by_status"].values()) == 5

    def test_no_telemetry_without_side_outputs(self):
        """Sem side_outputs, caminho zero-overhead: nada coletado."""
        so = SideOutputs()
        assert so.nature_apply is None  # default

    def test_multi_col_per_column_stats(self):
        table = {
            "cpf": ["529.982.247-25", "nao-cpf"],
            "cnpj": ["11.222.333/0001-81", "11.222.333/0001-81"],
            "plain": ["foo", "bar"],  # sem nature
        }
        so = SideOutputs()
        out = encode(
            table, nature_per_col={"cpf": SPEC_CPF, "cnpj": SPEC_CNPJ}, side_outputs=so
        )
        # byte-neutro vs sem telemetria
        assert out == encode(table, nature_per_col={"cpf": SPEC_CPF, "cnpj": SPEC_CNPJ})
        assert set(so.nature_apply) == {"cpf", "cnpj"}  # so' colunas com nature
        assert so.nature_apply["cpf"]["total"] == 2
        assert so.nature_apply["cpf"]["compressible"] == 1
        assert so.nature_apply["cnpj"]["compressible"] == 2
        assert so.nature_apply["cnpj"]["apply_rate"] == 1.0

    def test_no_nature_apply_when_no_nature(self):
        """side_outputs passado mas sem nature: nature_apply fica None."""
        so = SideOutputs()
        encode(["foo", "bar"], side_outputs=so)
        assert so.nature_apply is None


# ===========================================================================
# Spec polymorfismo — strategy pattern
# ===========================================================================


class TestPolymorphism:
    def test_same_function_different_specs(self):
        """encode_value funciona com qualquer TemplatedCheckedSpec."""
        cpf = "529.982.247-25"
        cnpj = "11.222.333/0001-81"

        enc_cpf, st_cpf = encode_value(SPEC_CPF, cpf)
        enc_cnpj, st_cnpj = encode_value(SPEC_CNPJ, cnpj)

        assert st_cpf == "compressible"
        assert st_cnpj == "compressible"
        # CPF encoded eh 5 chars, CNPJ 7 chars
        assert len(enc_cpf) == 5
        assert len(enc_cnpj) == 7

    def test_spec_is_frozen_dataclass(self):
        """TemplatedCheckedSpec deve ser immutable."""
        with pytest.raises(Exception):  # FrozenInstanceError
            SPEC_CPF.name = "modified"


class TestDataIsoSpec:
    """`SPEC_DATA_ISO` — data `YYYY-MM-DD` -> ordinal decimal (weld T-DATA-LAZY-ISO).

    O alvo e' DECIMAL, nao denso como o CPF: o que paga em data e' deixar a aritmetica
    visivel pro `*N+M|` do seq-RLE, nao densidade. Medido no lab 2026-08-07-2311.
    """

    def test_classify_e_rt_por_valor(self):
        from tcf.natures import SPEC_DATA_ISO as S

        casos = [
            ("2026-01-31", "compressible"),
            ("20260131", "length_wrong"),        # forma BASICA da ISO 8601
            ("2026-1-1", "length_wrong"),
            ("2026-01-31Z", "length_wrong"),     # sufixo de fuso
            ("2026-01-31+02:00", "length_wrong"),
            ("+10000-12-31", "length_wrong"),    # fora de 0000-9999 (chrono emite)
            ("31-JAN-26", "length_wrong"),       # o default do Oracle
            ("5/1/2021", "length_wrong"),
            ("", "empty_value"),
            ("nao-e-data", "format_mismatch"),
            ("2026-02-30", "format_mismatch"),   # data que nao existe
        ]
        for v, esperado in casos:
            assert S.classify_value(v) == esperado, v
            payload, st = S.encode_value(v)
            assert st == esperado
            assert S.decode_value(payload) == v, f"RT quebrou em {v!r}"

    def test_guard_de_reemissao_e_load_bearing(self):
        """`fromisoformat` aceita mais do que emite desde a 3.11 — o guard e' o que
        impede duas grafias de colapsarem no mesmo ordinal."""
        import datetime as dt

        from tcf.natures import SPEC_DATA_ISO as S

        # o parser aceita, mas a grafia nao e' a canonica -> tem de virar literal
        assert dt.date.fromisoformat("20191204") == dt.date(2019, 12, 4)
        assert S.classify_value("20191204") != "compressible"
        payload, _ = S.encode_value("20191204")
        assert S.decode_value(payload) == "20191204"

    def test_no_encode_ganha_onde_o_obat_e_fraco(self):
        """O spec so' vence onde o core nao alcanca — e RECUSA onde o core ja' resolve."""
        import datetime as dt

        from tcf import decode, encode
        from tcf.natures import SPEC_DATA_ISO as S

        base = dt.date(2026, 1, 1)
        # passo mensal: o OBAT rende ~4% sozinho; o ordinal colapsa no seq-RLE
        mensal = [(base + dt.timedelta(days=30 * i)).isoformat() for i in range(200)]
        w = encode(mensal, nature=S)
        # RE-PIN 2026-08-13 (weld A ADR-0041): o header carrega o wire_id `dt`.
        assert w.startswith("#TCF.8 :dt"), w[:24]
        assert len(w.encode()) < len(encode(mensal).encode()) // 10
        assert decode(w) == mensal

        # agrupado: o RLE do core ja' resolve; o spec o DESTRUIRIA -> o FLOOR recusa
        agrup = [(base + dt.timedelta(days=i // 20)).isoformat() for i in range(200)]
        w2 = encode(agrup, nature=S)
        assert not w2.startswith("#TCF.8 :dt")
        assert len(w2.encode()) <= len(encode(agrup).encode())
        assert decode(w2) == agrup

    def test_nunca_pior_com_coluna_suja(self):
        import datetime as dt

        from tcf import decode, encode
        from tcf.natures import SPEC_DATA_ISO as S

        base = dt.date(2026, 1, 1)
        for pct in (10, 50, 100):
            vals = [(base + dt.timedelta(days=i)).isoformat() for i in range(200)]
            for j in range(200 * pct // 100):
                vals[(j * 97) % 200] = f"lixo {j}"
            w = encode(vals, nature=S)
            assert decode(w) == vals, f"RT quebrou com {pct}% de lixo"
            assert len(w.encode()) <= len(encode(vals).encode()), f"regrediu com {pct}%"


class TestNatureSlotNulo:
    """`None` e' do CORE, nao do spec (fix 2026-08-08).

    ANTES deste fix as QUATRO natures estouravam `TypeError: can only concatenate str
    (not "NoneType") to str` numa coluna com null — e a mesma coluna SEM `nature=`
    encodava sem reclamar. Alcancavel por `encode->decode` com dado normal.
    """

    def test_as_quatro_natures_aceitam_null(self):
        from tcf import decode, encode
        from tcf.natures import SPEC_CNPJ, SPEC_CPF, SPEC_DATA_ISO, SPEC_IP

        amostras = [
            (SPEC_CPF, "000.000.000-00"),
            (SPEC_CNPJ, "00.000.000/0000-00"),
            (SPEC_IP, "192.168.0.1"),
            (SPEC_DATA_ISO, "2026-01-31"),
        ]
        for spec, v in amostras:
            col = [v, None, v, None, v] * 8
            w = encode(col, nature=spec)
            volta = decode(w)
            assert volta == col, f"{spec.name}: RT quebrou"
            assert volta[1] is None, f"{spec.name}: o null virou {volta[1]!r}"

    def test_null_nao_ganha_marcador(self):
        """O slot nulo e' materializado pelo core; marcar seria inventar uma segunda
        grafia pro mesmo nada, e a inversa teria de desfazer exatamente isso."""
        from tcf.natures import SPEC_CPF, encode_value

        payload, status = encode_value(SPEC_CPF, None)
        assert payload is None
        assert status == "null_slot"


class TestNatureFloorVeOBaselineReal:
    """O FLOOR da nature compara contra o que o encoder EMITIRIA, nao so' contra o core.

    Antes deste fix o baseline era so' o corpo do core; o bN de dominio (ADR-0036) tambem
    e' candidato na rota flat e costuma vencer justo nas colunas de baixa cardinalidade que
    atraem nature. Medido antes: coluna de 2 CPFs repetidos saia com 61 B sem `nature=` e
    198 B com — a nature "vencia" um baseline que o encoder nao emitiria.
    """

    def test_nature_nao_regride_contra_bn(self):
        from tcf import decode, encode
        from tcf.natures import SPEC_CPF, SPEC_IP

        for spec, v1, v2 in [(SPEC_CPF, "000.000.000-00", "111.111.111-11"),
                             (SPEC_IP, "192.168.0.1", "10.0.0.1")]:
            col = [v1, v2] * 30                       # k=2 -> o bN e' o baseline real
            sem = encode(col)
            com = encode(col, nature=spec)
            assert len(com.encode()) <= len(sem.encode()), (
                f"{spec.name}: nature regrediu {len(com.encode()) - len(sem.encode())} B "
                f"contra o baseline real"
            )
            assert decode(com) == col


# ===========================================================================
# Weld A ADR-0041 — spec em dois campos: name (CODIGO) x wire_id (DADO)
# ===========================================================================


class TestWireIdDoisPlanos:
    """ADR-0041 (owner, 2026-08-13): `name` legivel NUNCA viaja; `wire_id` curto e' o
    `:id` do header. Regra `^[a-z][a-z0-9]{0,7}$` fail-loud no registro e na emissao;
    resolucao ESTRITA (id historico nao resolve — valvula out-of-band)."""

    def test_campos_separados_e_fallback(self):
        from tcf.natures import SPEC_CPF, SPEC_CNPJ, SPEC_IP, SPEC_DATA_ISO

        # data-iso e' o unico com wire_id != name (o rename que motivou o ADR)
        assert SPEC_DATA_ISO.name == "data-iso" and SPEC_DATA_ISO.wire_id == "dt"
        for s in (SPEC_CPF, SPEC_CNPJ, SPEC_IP):
            assert s.wire_id == s.name  # fallback: vazio -> name

    def test_flip_do_floor_em_n11(self):
        """O PIN que o rename compra: em N=11 datas diarias a nature passa a VENCER o
        FLOOR (com `:data-iso`, 10 B de tag, ela perdia e o encoder emitia o core).
        E' a medicao do ADR-0041 §Contexto-1 virando contrato: o id curto nao e'
        cosmetica, ele decide a competicao no regime de payload minusculo."""
        import datetime as dt

        from tcf import decode, encode
        from tcf.natures import SPEC_DATA_ISO as S

        base = dt.date(2026, 1, 1)
        for n, vence in [(10, False), (11, True), (12, True)]:
            vals = [(base + dt.timedelta(days=i)).isoformat() for i in range(n)]
            w = encode(vals, nature=S)
            assert w.startswith("#TCF.8 :dt") == vence, (n, w.splitlines()[0])
            assert decode(w) == vals

    def test_emissao_recusa_grafia_hostil_nas_tres_rotas(self):
        """A validacao mora na PORTA do encode — a rota .8H envolve a emissao num
        try/except que cai pro piso, e validar la' dentro ENGOLIRIA o spec hostil."""
        import dataclasses
        import datetime as dt

        import pytest

        from tcf import encode
        from tcf.natures import SPEC_DATA_ISO as S

        base = dt.date(2026, 1, 1)
        datas = [(base + dt.timedelta(days=30 * i)).isoformat() for i in range(60)]
        v = [str(i % 3) for i in range(60)]
        recs = [{"quando": d} for d in datas]
        for ruim in ("DT", "Dt", "8d", "ab_c", "x-y", "", "a" * 9, "a,b", "a:b",
                     "dt fim", "data-iso"):
            spec = dataclasses.replace(S, wire_id=ruim) if ruim else _sem_wire(S)
            with pytest.raises(ValueError, match="wire_id"):
                encode(datas, nature=spec)
            with pytest.raises(ValueError, match="wire_id"):
                encode({"d": datas, "v": v}, nature_per_col={"d": spec})
            with pytest.raises(ValueError, match="wire_id"):
                encode(recs, nature_per_col={"quando": spec})

    def test_registro_recusa_grafia_e_colisao(self):
        import dataclasses

        import pytest

        from tcf.natures import SPEC_DATA_ISO, _WIRE_REGISTRY, SPEC_REGISTRY, _register

        antes = (dict(SPEC_REGISTRY), dict(_WIRE_REGISTRY))
        # grafia invalida: recusada ANTES de inserir em qualquer plano
        with pytest.raises(ValueError, match="wire_id"):
            _register(dataclasses.replace(SPEC_DATA_ISO, name="outra", wire_id="X!"))
        # colisao de wire_id (name novo, wire ja' tomado): idem
        with pytest.raises(ValueError, match="colisao"):
            _register(dataclasses.replace(SPEC_DATA_ISO, name="outra", wire_id="dt"))
        # colisao de name: idem
        with pytest.raises(ValueError, match="registrado"):
            _register(dataclasses.replace(SPEC_DATA_ISO, wire_id="dt2"))
        assert (dict(SPEC_REGISTRY), dict(_WIRE_REGISTRY)) == antes, (
            "falha de registro deixou estado parcial"
        )

    def test_wire_historico_falha_alto_e_valvula_le(self):
        """Resolucao ESTRITA (decisao 3): `:data-iso` pre-rename nao resolve — falha
        com mensagem acionavel; le-se com a valvula out-of-band (ADR-0024: o passado
        se le pelo git, nao por bagagem no codigo)."""
        import dataclasses
        import datetime as dt

        import pytest

        from tcf import decode, encode
        from tcf.natures import SPEC_DATA_ISO as S

        base = dt.date(2026, 1, 1)
        vals = [(base + dt.timedelta(days=30 * i)).isoformat() for i in range(60)]
        w = encode(vals, nature=S)
        assert w.startswith("#TCF.8 :dt\n")
        velho = w.replace("#TCF.8 :dt\n", "#TCF.8 :data-iso\n", 1)  # wire pre-rename
        with pytest.raises(ValueError, match="data-iso.*out-of-band"):
            decode(velho)
        # spec out-of-band DIVERGENTE do id tambem falha alto (nunca escolhe calado)
        with pytest.raises(ValueError, match="nao coincide"):
            decode(velho, nature=S)
        valvula = dataclasses.replace(S, wire_id="data-iso")
        assert decode(velho, nature=valvula) == vals

    def test_telemetria_fica_no_plano_do_codigo(self):
        """`nature_apply['spec']` reporta o NAME legivel — a telemetria e' pro dev,
        nao pro fio. O wire_id aparece so' no header."""
        import datetime as dt

        from tcf import encode
        from tcf.natures import SPEC_DATA_ISO as S
        from tcf.side_outputs import SideOutputs

        base = dt.date(2026, 1, 1)
        vals = [(base + dt.timedelta(days=30 * i)).isoformat() for i in range(60)]
        so = SideOutputs()
        w = encode(vals, nature=S, side_outputs=so)
        assert so.nature_apply["val"]["spec"] == "data-iso"
        assert ":dt\n" in w and "data-iso" not in w


def _sem_wire(spec):
    """Spec com wire_id='' SEM passar pelo __post_init__ (que faria fallback pro name):
    simula objeto hostil que nem dataclass e'."""
    class _Falso:
        name = spec.name
        wire_id = ""
    return _Falso()


class TestMascaradaDeWireIdCore:
    """Buraco NOVO dos dois planos, fechado na porta de emissao: `replace(SPEC_CPF,
    name=...)` herda `wire_id='cpf'` — emitiria `:cpf` e o decode resolveria o spec
    CORE; transformacao derivada divergente corromperia CALADO (pre-ADR-0041 o id
    era o name, o buraco nao existia)."""

    def test_emissao_recusa_spec_derivado_com_wire_id_core(self):
        from dataclasses import replace

        import pytest

        from tcf import encode
        from tcf.natures import SPEC_CPF

        derivado = replace(SPEC_CPF, name="custom-cpf")  # herda wire_id="cpf"
        assert derivado.wire_id == "cpf"
        with pytest.raises(ValueError, match="mascarada|pertence ao spec core"):
            encode(["529.982.247-25", "111.444.777-35"], nature=derivado)

    def test_noop_replace_e_o_proprio_core_continuam_passando(self):
        from dataclasses import replace

        from tcf import decode, encode
        from tcf.natures import SPEC_CPF

        cpfs = ["529.982.247-25", "111.444.777-35"]
        # o proprio spec core e o clone campo-a-campo igual NAO sao mascarada
        for spec in (SPEC_CPF, replace(SPEC_CPF)):
            assert decode(encode(cpfs, nature=spec)) == cpfs


class TestLacunaImpostorDuckType:
    """LACUNA CONHECIDA (`T-SPEC-IMPOSTOR`), **pre-existente ao ADR-0041** — medida na
    cacada do weld A (2026-08-13) e reproduzida IDENTICA no commit anterior.

    Um duck-type que se declara com a identidade do core (`name` E `wire_id` iguais)
    mas transforma DIFERENTE vence o FLOOR, emite `:dt`, e o decode resolve pelo
    registry -> aplica o spec CORE -> 200 valores deslocados 1000 dias, SEM excecao.
    E' a classe "corrupcao calada".

    Por que nao foi fechado NESTE weld: a fronteira de confianca da emissao e' o
    `name` (registry-first no decode) e ela e' PRE-weld — apertar exigiria decidir
    entre quebrar o clone funcional compilado de `.dsl` (que legitimamente se chama
    `cpf`) ou verificar equivalencia por amostragem contra o spec do registry. E'
    decisao de escopo proprio, nao carona de rename.

    O que o weld A FEZ aqui: estreitou o buraco de "coincidir o name" para "coincidir
    name E wire_id" — `replace(SPEC_CPF, name='custom')`, que herda o wire_id, agora
    e' recusado (TestMascaradaDeWireIdCore).

    Este teste PINA a lacuna: quando `T-SPEC-IMPOSTOR` fechar, ele falha — e quem
    fechar atualiza aqui. Nao e' contrato desejado; e' fronteira medida.
    """

    def test_impostor_ainda_passa_hoje(self):
        import datetime as dt

        from tcf import decode, encode

        class _Impostor:
            name = "data-iso"
            wire_id = "dt"

            def classify_value(self, v):
                return "compressible"

            def encode_value(self, v):
                return (str(dt.date.fromisoformat(v).toordinal() + 1000), "compressible")

            def decode_value(self, p):
                return dt.date.fromordinal(int(p) - 1000).isoformat()

        base = dt.date(2026, 1, 1)
        datas = [(base + dt.timedelta(days=30 * i)).isoformat() for i in range(200)]
        w = encode(datas, nature=_Impostor())
        assert w.startswith("#TCF.8 :dt")     # venceu o FLOOR e carimbou id do core
        assert decode(w) != datas             # LACUNA: corrompe calado (T-SPEC-IMPOSTOR)

    def test_spec_sem_wire_id_recusa_ensinando(self):
        """Consequencia NOVA do weld: spec duck-typed escrito antes do ADR-0041 nao
        emite mais. A recusa tem de ENSINAR o campo que falta, nao so' citar a regra."""
        import pytest

        from tcf import encode

        class _Antigo:
            name = "meu-spec"

            def classify_value(self, v):
                return "compressible"

            def encode_value(self, v):
                return (v.replace("-", ""), "compressible")

            def decode_value(self, p):
                return f"{p[:4]}-{p[4:6]}-{p[6:]}"

        with pytest.raises(ValueError, match="sem o campo `wire_id`"):
            encode(["2026-01-01", "2026-02-01"], nature=_Antigo())


class TestIntPadSpecWeld:
    """Weld EXP-018 (2026-08-14): `IntPadSpec` + a rota tipada aberta a spec.

    Antes deste weld, `encode([1,2,3], nature=SPEC)` era ValueError: a rota tipada nao
    aceitava spec NEM `min_len`, e "entra int, spec int, devolve int" nao era expressavel.
    O spec agora e' mais um candidato do MESMO `min()` — como o bool ja' faz com o denso.
    """

    def test_ganha_onde_a_largura_varia(self):
        """O gatilho: progressao cuja largura muda quebra o marcador em 3; o pad faz 1."""
        from tcf import decode, encode
        from tcf.natures import int_pad_para

        vals = list(range(1, 601))
        spec = int_pad_para(vals)
        assert spec is not None and spec.largura == 3
        base, w = encode(vals), encode(vals, nature=spec)
        assert w.startswith("#TCF.8n :ipad"), w[:24]
        assert len(w.encode()) < len(base.encode())
        assert decode(w) == vals
        assert all(type(x) is int for x in decode(w))     # o TIPO volta, nao a grafia

    def test_decode_resolve_sozinho_pelo_registry(self):
        """`:ipad` esta' no registry: o wire e' auto-contido, sem out-of-band."""
        from tcf import decode, encode
        from tcf.natures import int_pad_para

        vals = [i * 7 for i in range(600)]
        w = encode(vals, nature=int_pad_para(vals))
        assert decode(w) == vals          # sem passar nature=

    def test_nunca_pior_e_recusa_onde_nao_paga(self):
        """A metade que sustenta tudo: onde o pad nao ativa nada, o FLOOR fica no core."""
        import random

        from tcf import decode, encode
        from tcf.natures import int_pad_para

        rnd = random.Random(20260814)
        casos = {
            "largura ja fixa": [100000 + i for i in range(300)],
            "baixa cardinalidade": [rnd.choice([10, 20, 30, 40, 50]) for _ in range(300)],
            "negativos": [rnd.randrange(-500, 501) for _ in range(300)],
            "aleatorio sem progressao": [rnd.randrange(1, 99999) for _ in range(300)],
            "quase constante": [42] * 297 + [43, 44, 45],
        }
        for nome, vals in casos.items():
            spec = int_pad_para(vals)
            base = encode(vals)
            w = encode(vals, nature=spec) if spec else base
            assert len(w.encode()) <= len(base.encode()), f"NUNCA-PIOR violado em {nome}"
            assert decode(w) == vals, nome

    def test_slot_nulo_atravessa(self):
        """O null e' do TIPO, nao da grafia: atravessa o spec sem quebrar a progressao."""
        from tcf import decode, encode
        from tcf.natures import int_pad_para

        vals = [None if i % 37 == 0 else i for i in range(1, 601)]
        assert vals.count(None) == 16 and vals[0] == 1     # ancora o regime do teste
        w = encode(vals, nature=int_pad_para(vals))
        got = decode(w)
        assert got == vals
        assert got[36] is None and type(got[0]) is int     # o nulo volta nulo, o int volta int

    def test_guard_de_canonicidade_recusa_zero_a_esquerda(self):
        """`'007'` NAO e' o inteiro 7 — mesma tecnica de re-emissao do `data_iso`."""
        from tcf.natures import IntPadSpec

        s = IntPadSpec(largura=6)
        assert s.classify_value("7") == "compressible"
        assert s.classify_value("007") == "format_noncanonical"
        assert s.classify_value("-7") == "format_mismatch"
        assert s.classify_value("7.5") == "format_mismatch"
        assert s.classify_value("1234567") == "length_wrong"
        # o RT do fallback literal e' byte-exato
        for v in ("007", "-7", "7.5", "1234567"):
            p, _st = s.encode_value(v)
            assert s.decode_value(p) == v

    def test_dimensiona_recusa_quando_nao_ha_o_que_padear(self):
        from tcf.natures import int_pad_para

        assert int_pad_para([100, 200, 300]) is None      # largura ja' uniforme
        assert int_pad_para([]) is None
        assert int_pad_para([None, None]) is None
        assert int_pad_para([1, 22, 333]).largura == 3

    def test_min_len_tambem_passa_na_rota_tipada(self):
        """O outro mecanismo que a porta recusava. Byte-neutro quando nao muda nada."""
        from tcf import decode, encode

        vals = [1750000000 + i * 60 for i in range(600)]
        w = encode(vals, min_len=12)
        assert decode(w) == vals
        assert len(w.encode()) < len(encode(vals).encode())

    def test_registry_ganhou_ipad_nos_dois_planos(self):
        from tcf.natures import SPEC_REGISTRY, _WIRE_REGISTRY, _resolve_nature_id

        # RE-PIN 2026-08-21 (weld H-15-01): + `cnpj-alfa`/`cnpja`.
        assert set(SPEC_REGISTRY) == {
            "cpf", "cnpj", "cnpj-alfa", "ip", "data-iso", "int-pad"}
        assert set(_WIRE_REGISTRY) == {"cpf", "cnpj", "cnpja", "ip", "dt", "ipad"}
        assert _resolve_nature_id("ipad").name == "int-pad"


# ===========================================================================
# CNPJ ALFANUMERICO — weld H-15-01/02 (IN RFB no 2.229/2024, vigente jul/2026)
# ===========================================================================


def _dv_num(i: int) -> str:
    """DV do CNPJ numerico `00000{i:03d}0001`, pra montar fixtures validas."""
    corpo = f"00000{i:03d}0001"
    return "".join(str(d) for d in SPEC_CNPJ.check_fn([int(c) for c in corpo]))


def _cnpj_num(i: int) -> str:
    return f"00.000.{i:03d}/0001-{_dv_num(i)}"


class TestCnpjAlfanumerico:
    """As 12 primeiras posicoes aceitam `[0-9A-Z]`; os 2 DV seguem decimais.

    O DV e' o MESMO mod-11 com OS MESMOS pesos — muda so' a conversao
    char->valor (`ASCII - 48`). E' por isso que o numerico gera DV identico nas
    duas regras, e por isso `SPEC_CNPJ` nao precisou mudar.
    """

    # --- a LEI: o exemplo publicado, e o DV que ele exige -------------------
    def test_exemplo_publicado_da_receita(self):
        from tcf.natures import SPEC_CNPJ_ALFA

        v = "12.ABC.345/01DE-35"
        assert SPEC_CNPJ_ALFA.classify_value(v) == "compressible"
        payload, status = SPEC_CNPJ_ALFA.encode_value(v)
        assert status == "compressible"
        assert len(payload) == 10
        assert SPEC_CNPJ_ALFA.decode_value(payload) == v

    def test_dv_errado_e_recusado_e_vira_literal(self):
        from tcf.natures import SPEC_CNPJ_ALFA

        v = "12.ABC.345/01DE-34"          # mesmo corpo, DV trocado
        assert SPEC_CNPJ_ALFA.classify_value(v) == "check_invalid"
        payload, status = SPEC_CNPJ_ALFA.encode_value(v)
        assert status == "check_invalid"
        assert payload.startswith(MARKER_LITERAL)
        assert SPEC_CNPJ_ALFA.decode_value(payload) == v      # nunca perde dado

    def test_letra_e_numero_pelo_mapeamento_da_IN(self):
        """`_valor` e' ASCII-48 — universal nos dois dominios."""
        from tcf.natures import SPEC_CNPJ_ALFA

        assert SPEC_CNPJ_ALFA._valor("0") == 0
        assert SPEC_CNPJ_ALFA._valor("9") == 9
        assert SPEC_CNPJ_ALFA._valor("A") == 17
        assert SPEC_CNPJ_ALFA._valor("Z") == 42
        # e no spec numerico da' exatamente o digito — por isso nada mudou la'
        assert [SPEC_CNPJ._valor(c) for c in "0123456789"] == list(range(10))

    def test_retrocompat_dv_identico_nas_duas_regras(self):
        """CNPJ numerico gera o MESMO DV sob a regra nova — por CONSTRUCAO."""
        from tcf.natures import SPEC_CNPJ_ALFA

        assert SPEC_CNPJ.check_fn is SPEC_CNPJ_ALFA.check_fn
        for i in range(0, 60, 7):
            v = _cnpj_num(i)
            assert SPEC_CNPJ.classify_value(v) == "compressible"
            assert SPEC_CNPJ_ALFA.classify_value(v) == "compressible"

    # --- a GRAVACAO: base 36, e por que nao 43 -----------------------------
    def test_base_densa_e_a_capacidade(self):
        from tcf.natures import ALFABETO_CNPJ_ALFA, SPEC_CNPJ_ALFA

        assert len(ALFABETO_CNPJ_ALFA) == 36
        assert SPEC_CNPJ.encoded_length == 7          # base 10  -> 7 chars
        assert SPEC_CNPJ_ALFA.encoded_length == 10    # base 36  -> 10 chars
        assert 36 ** 12 <= len(BASE94) ** 10
        # o mapeamento LEGAL como base (43, por causa do gap 10-16) NAO caberia
        assert 43 ** 12 > len(BASE94) ** 10

    def test_extremos_do_dominio(self):
        """RE-PIN ADR-0043: corpo 100% decimal agora COMPACTA em 7 chars (o caso
        particular por valor); qualquer letra no corpo -> 10. RT nos dois."""
        from tcf.natures import SPEC_CNPJ_ALFA

        for corpo, esperado in (("000000000000", 7), ("999999999999", 7),
                                ("ZZZZZZZZZZZZ", 10), ("A00000000000", 10),
                                ("99999999999Z", 10), ("0000000000ZZ", 10)):
            dv = "".join(str(d) for d in SPEC_CNPJ_ALFA.check_fn(
                [ord(c) - 48 for c in corpo]))
            s = corpo + dv
            v = f"{s[:2]}.{s[2:5]}.{s[5:8]}/{s[8:12]}-{s[12:]}"
            payload, status = SPEC_CNPJ_ALFA.encode_value(v)
            assert status == "compressible", v
            assert len(payload) == esperado, (v, payload)
            assert SPEC_CNPJ_ALFA.decode_value(payload) == v

    # --- o WIRE: self-describing, e o legado intocado ----------------------
    def test_wire_self_describing_sem_spec_no_decode(self):
        from tcf.natures import SPEC_CNPJ_ALFA

        col = ["12.ABC.345/01DE-35", "12.ABC.345/01DE-35", "AA.AAA.AAA/AAAA-38"]
        col = [v for v in col if SPEC_CNPJ_ALFA.classify_value(v) == "compressible"]
        texto = encode(col, nature=SPEC_CNPJ_ALFA)
        assert texto.startswith("#TCF.8 :cnpja")
        assert decode(texto) == col          # resolve pelo registry, sem out-of-band

    def test_spec_cnpj_numerico_ficou_byte_intocado(self):
        """O legado nao paga pelo novo: mesmo wire e mesmo tamanho de payload."""
        col = [_cnpj_num(i) for i in range(5)]
        texto = encode(col, nature=SPEC_CNPJ)
        assert texto.startswith("#TCF.8 :cnpj\n")
        assert decode(texto) == col
        for v in col:
            payload, status = SPEC_CNPJ.encode_value(v)
            assert status == "compressible"
            assert len(payload) == 7

    def test_coluna_mista_numerico_e_alfa(self):
        from tcf.natures import SPEC_CNPJ_ALFA

        col = [_cnpj_num(3), "12.ABC.345/01DE-35", _cnpj_num(9)]
        texto = encode(col, nature=SPEC_CNPJ_ALFA)
        assert decode(texto) == col
        # os TRES sao compressiveis sob o alfa (digito esta' no alfabeto)
        assert all(SPEC_CNPJ_ALFA.classify_value(v) == "compressible" for v in col)

    def test_alfa_sob_spec_numerico_vira_literal_sem_corromper(self):
        col = [_cnpj_num(3), "12.ABC.345/01DE-35"]
        texto = encode(col, nature=SPEC_CNPJ)
        assert decode(texto) == col
        payload, status = SPEC_CNPJ.encode_value("12.ABC.345/01DE-35")
        assert status == "format_mismatch"
        assert payload.startswith(MARKER_LITERAL)

    # --- o CHOOSER (H-15-02) -----------------------------------------------
    def test_chooser_um_alfa_ja_vira_cnpja(self):
        """RE-PIN ADR-0043. Na versao ADR-0042 (comprimentos fixos) este teste
        afirmava o contrario — 1 alfa em 200 numericos ficava no `cnpj`, porque
        o alfa de 10 chars taxava os 199 numericos. Com o compacto POR VALOR os
        numericos custam os MESMOS 7 chars sob `cnpja`, entao um unico alfa
        compressivel (10 < 1+18 do literal) ja' decide — sem heuristica."""
        from tcf.natures import SPEC_CNPJ_ALFA, cnpj_spec_para

        col = [_cnpj_num(i) for i in range(200)]
        col[0] = "12.ABC.345/01DE-35"
        assert cnpj_spec_para(col) is SPEC_CNPJ_ALFA

    def test_chooser_vira_pro_alfa_quando_domina(self):
        from tcf.natures import SPEC_CNPJ_ALFA, cnpj_spec_para

        assert cnpj_spec_para(["12.ABC.345/01DE-35"] * 100) is SPEC_CNPJ_ALFA

    def test_chooser_empate_e_none_preferem_o_legado(self):
        from tcf.natures import cnpj_spec_para

        assert cnpj_spec_para([]) is SPEC_CNPJ            # empate 0 == 0
        assert cnpj_spec_para([None, None]) is SPEC_CNPJ  # None e' slot do core

    def test_chooser_roundtrip_em_qualquer_mistura(self):
        from tcf.natures import cnpj_spec_para

        base = [_cnpj_num(i) for i in range(60)]
        for k in (0, 1, 15, 30, 45, 60):
            col = ["12.ABC.345/01DE-35"] * k + base[k:]
            texto = encode(col, nature=cnpj_spec_para(col))
            assert decode(texto) == col, f"RT quebrou em k={k}"

    def test_digito_unicode_mudou_de_ROTULO_e_nao_de_byte(self):
        """A unica mudanca de comportamento do weld H-15-01, pinada de proposito.

        `classify_value` trocou `v.isdigit()` por "todo char no alfabeto".
        Digito unicode (arabico-indico) passava no `isdigit()` e era rotulado
        `format_unmasked`; agora e' `format_mismatch`. Os BYTES sao os mesmos —
        os dois status caem em literal —, muda so' a telemetria, e o rotulo novo
        e' o mais fiel (o simbolo nao pertence ao alfabeto deste spec).
        Diferencial pre/pos-weld: 8.036 encodes e 5.010 decodes, 0 divergencia
        de byte; esta foi a UNICA divergencia de rotulo.
        """
        v = "٥٢٩٩٨٢٢٤٧٢٥"
        assert len(v) == 11 and v.isdigit()          # o `isdigit()` antigo dizia sim
        assert classify_value(SPEC_CPF, v) == "format_mismatch"
        payload, status = encode_value(SPEC_CPF, v)
        assert payload == MARKER_LITERAL + v         # BYTE identico ao pre-weld
        assert decode_value(SPEC_CPF, payload) == v

    # --- ADR-0043: um CNPJ so', compacto POR VALOR ---------------------------
    def test_payload_numerico_e_BYTE_IDENTICO_ao_legado(self):
        """O caso compacto nao e' parecido — e' o MESMO payload do SPEC_CNPJ,
        por construcao (indices do sub-alfabeto '0..9' SAO os digitos)."""
        from tcf.natures import SPEC_CNPJ_ALFA

        for i in range(0, 60, 7):
            v = _cnpj_num(i)
            p_legado, _ = SPEC_CNPJ.encode_value(v)
            p_unific, _ = SPEC_CNPJ_ALFA.encode_value(v)
            assert p_legado == p_unific
            assert len(p_unific) == 7

    def test_emissao_canonica_por_valor(self):
        """Corpo decimal SEMPRE sai compacto (7); com letra SEMPRE pleno (10).
        Deterministico — nenhum valor tem duas grafias emitidas."""
        from tcf.natures import SPEC_CNPJ_ALFA

        p1, _ = SPEC_CNPJ_ALFA.encode_value(_cnpj_num(3))
        p2, _ = SPEC_CNPJ_ALFA.encode_value("12.ABC.345/01DE-35")
        assert (len(p1), len(p2)) == (7, 10)

    def test_decode_tolera_nao_canonico_de_10(self):
        """Corpo numerico gravado em 10 chars (nunca emitido) DECODIFICA — decode
        tolerante, emissao canonica, como o modo C: baseline nunca pinna isso."""
        from tcf.natures import ALFABETO_CNPJ_ALFA, SPEC_CNPJ_ALFA

        n = 0
        for c in "061475630001":
            n = n * 36 + ALFABETO_CNPJ_ALFA.index(c)
        chars = []
        for _ in range(10):
            chars.append(BASE94[n % len(BASE94)])
            n //= len(BASE94)
        nao_canonico = "".join(reversed(chars))
        assert SPEC_CNPJ_ALFA.decode_value(nao_canonico) == "06.147.563/0001-93"

    def test_minuscula_nao_pertence_ao_dominio(self):
        """NT 2025.001/XSD: `[0-9A-Z]{12}[0-9]{2}` — MAIUSCULA-only. Minuscula e'
        variante de REPRESENTACAO: aceita-la canonizando a saida perderia o RT
        byte-canonical, entao e' classe CONTRATO (H-15-06, aguarda a assinatura
        do T-FMT-CONTRACT-SIGNATURE). Hoje: literal — nao ganha, nunca corrompe."""
        from tcf.natures import SPEC_CNPJ_ALFA

        v = "12.abc.345/01de-35"
        assert SPEC_CNPJ_ALFA.classify_value(v) == "format_mismatch"
        payload, _ = SPEC_CNPJ_ALFA.encode_value(v)
        assert payload == MARKER_LITERAL + v
        assert SPEC_CNPJ_ALFA.decode_value(payload) == v      # byte-RT intacto

    def test_contrato_do_compacto_falha_alto(self):
        """Inclui as 3 guardas achadas pela revisao adversarial PRE-commit, que
        CONSTRUIU os specs malformados: base 1 (decode nao TERMINA em payload
        adulterado), vazio+0 (IndexError onde o contrato e' pass-through), e
        igualdade (ramo pleno vira codigo morto calado)."""
        from tcf.natures import SPEC_CNPJ_ALFA

        with pytest.raises(ValueError, match="PROPRIO"):
            replace(SPEC_CNPJ_ALFA, name="y1", wire_id="y1", alfabeto_compacto="abc")
        with pytest.raises(ValueError, match="MENOR"):
            replace(SPEC_CNPJ_ALFA, name="y2", wire_id="y2",
                    encoded_length_compacto=10)
        with pytest.raises(ValueError, match="insuficiente"):
            replace(SPEC_CNPJ_ALFA, name="y3", wire_id="y3",
                    encoded_length_compacto=6)
        # base 1: o laco de expansao do decode nao terminaria (n%1=0, n//1=n)
        with pytest.raises(ValueError, match="PROPRIO"):
            replace(SPEC_CNPJ_ALFA, name="y4", wire_id="y4",
                    alfabeto_compacto="0", encoded_length_compacto=1)
        # vazio + comprimento 0: colidiria com o pass-through do payload ''
        with pytest.raises(ValueError, match="PROPRIO"):
            replace(SPEC_CNPJ_ALFA, name="y5", wire_id="y5",
                    alfabeto_compacto="", encoded_length_compacto=0)
        with pytest.raises(ValueError, match=">=1"):
            replace(SPEC_CNPJ_ALFA, name="y6", wire_id="y6",
                    encoded_length_compacto=0)
        # igualdade ao alfabeto pleno: o ramo de 10 chars nunca emitiria
        with pytest.raises(ValueError, match="PROPRIO"):
            replace(SPEC_CNPJ_ALFA, name="y7", wire_id="y7",
                    alfabeto_compacto=SPEC_CNPJ_ALFA.alfabeto)

    def test_header_e_o_unico_byte_de_diferenca_no_numerico(self):
        """Pina o '+1 B' que os docs afirmam: coluna 100% numerica custa
        exatamente 1 byte a mais no unificado — o char extra de ':cnpja'."""
        from tcf.natures import SPEC_CNPJ_ALFA

        col = [_cnpj_num(i) for i in range(50)]
        w_legado = encode(col, nature=SPEC_CNPJ)
        w_unific = encode(col, nature=SPEC_CNPJ_ALFA)
        assert decode(w_legado) == col and decode(w_unific) == col
        assert len(w_unific.encode()) - len(w_legado.encode()) == 1

    # --- o CONTRATO do alfabeto (fail-loud no __post_init__) ---------------
    def test_alfabeto_invalido_falha_alto(self):
        from tcf.natures import SPEC_CNPJ_ALFA

        with pytest.raises(ValueError, match="simbolo repetido"):
            replace(SPEC_CNPJ_ALFA, name="x1", wire_id="x1", alfabeto="0012")
        with pytest.raises(ValueError, match="digitos decimais"):
            replace(SPEC_CNPJ_ALFA, name="x2", wire_id="x2",
                    alfabeto="ABCDEFGHIJKL")
        with pytest.raises(ValueError, match="insuficiente"):
            replace(SPEC_CNPJ_ALFA, name="x3", wire_id="x3", encoded_length=7)

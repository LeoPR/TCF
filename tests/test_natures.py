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
        # ADR-0044: UM spec so'. Pleno = 10 (base 36); compacto = 7 (base 10,
        # payload byte-identico ao wire `:cnpj` historico).
        assert SPEC_CNPJ.encoded_length == 10
        assert SPEC_CNPJ.encoded_length_compacto == 7
        assert len(SPEC_CNPJ.alfabeto) == 36

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
        text = encode(cpfs, schema=SPEC_CPF)
        decoded = decode(text, schema=SPEC_CPF)
        assert decoded == cpfs

    def test_single_col_with_nature_mixed_valid_invalid(self):
        cpfs = [
            "529.982.247-25",  # valid
            "529.982.247-99",  # check invalid
            "abc.def.ghi-jk",  # format mismatch
            "111.444.777-35",  # valid
        ]
        text = encode(cpfs, schema=SPEC_CPF)
        decoded = decode(text, schema=SPEC_CPF)
        assert decoded == cpfs  # RT 100% mesmo com fallbacks

    def test_multi_col_with_nature_per_col(self):
        table = {
            "cpf": ["529.982.247-25", "111.444.777-35"],
            "cnpj": ["11.222.333/0001-81", "11.222.333/0001-81"],
            "plain": ["foo", "bar"],
        }
        text = encode(
            table,
            schema={
                "cpf": SPEC_CPF,
                "cnpj": SPEC_CNPJ,
            },
        )
        decoded = decode(
            text,
            schema={
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
        text = encode(table, schema={"cpf": SPEC_CPF})
        decoded = decode(text, schema={"cpf": SPEC_CPF})
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
        bytes_nature = len(encode(cpfs, schema=SPEC_CPF).encode("utf-8"))
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
        text = encode(table, schema={"cpf": SPEC_CPF, "doc": SPEC_CNPJ})
        assert decode(text) == table  # SEM nature_per_col no decode

    def test_magic_is_tcf8m_inline(self):
        table = {"doc": ["11.222.333/0001-81"], "plain": ["x"]}
        text = encode(table, schema={"doc": SPEC_CNPJ})
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
        text = encode(table, schema=npc)
        assert decode(text, schema=npc) == table  # não dupla-aplica

    def test_ip_self_describing(self):
        table = {"ip": ["192.168.1.1", "10.0.0.1"], "x": ["a", "b"]}
        text = encode(table, schema={"ip": SPEC_IP})
        assert text.startswith("#TCF.8M")  # inline meta (ADR-0029)
        assert decode(text) == table

    def test_unknown_nature_id_raises(self):
        """Id desconhecido -> ERRO (T-QA-8 BUG-13b, owner 2026-07-10): revoga o
        forward-compat de 2026-06-24 — warning + dado cru base-94 calado era
        corrupção silenciosa; pre-1.0 sem compat (ADR-0024)."""
        table = {"doc": ["11.222.333/0001-81"], "x": ["a"]}
        text = encode(table, schema={"doc": SPEC_CNPJ})
        tampered = text.replace(":cnpj", ":FUTURE9")
        with pytest.raises(ValueError, match="desconhecido"):
            decode(tampered)

    def test_colon_in_colname_with_nature_rt(self):
        """T-FMT-NAME-ESCAPING (M2): ':' no nome escapado '\\:'; a nature `:id` e' o
        ULTIMO ':' NAO-escapado -> RT preserva nome-com-':' + nature."""
        table = {"ns:col": ["529.982.247-25"], "x": ["a"]}
        text = encode(table, schema={"ns:col": SPEC_CPF})
        assert decode(text, schema={"ns:col": SPEC_CPF}) == table

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
        # RE-PIN 2026-08-21 (ADR-0044): o CNPJ alfanumerico entrou como UM SO'
        # spec `cnpj` — o `cnpj-alfa`/`cnpja` do ADR-0042 nao chegou a existir
        # fora desta sessao. O vocabulario voltou a 5.
        assert set(SPEC_REGISTRY) == {"cpf", "cnpj", "ip", "data-iso", "int-pad"}
        assert set(_WIRE_REGISTRY) == {"cpf", "cnpj", "ip", "dt", "ipad"}


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
        text = encode(table, schema={"doc": SPEC_CNPJ}, drop_names=True)
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
            schema={"doc": SPEC_CNPJ},
        )
        assert t[:7] == "#TCF.8M"  # M logo apos #TCF.8 (sem espaco)
        assert decode(t) == {"doc": ["11.222.333/0001-81"], "x": ["a"]}

    def test_disc_single_space(self):
        t = encode(["529.982.247-25", "111.444.777-35"], schema=SPEC_CPF)
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
        t = encode(["529.982.247-25"], schema=SPEC_CPF, stamp=True)
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
        text = encode(cpfs, schema=SPEC_CPF)
        assert decode(text) == cpfs  # SEM nature no decode

    def test_magic_sem_m_uma_linha(self):
        cpfs = ["529.982.247-25", "111.444.777-35"]
        text = encode(cpfs, schema=SPEC_CPF)
        # header numa LINHA SO': '#TCF.8 :cpf' (sem ' M' -> single; nome vazio)
        assert text.split("\n")[0] == "#TCF.8 :cpf"
        assert not text.startswith("#TCF.8 M")  # nao colide com multi

    def test_retorna_list_nao_dict(self):
        text = encode(["529.982.247-25"], schema=SPEC_CPF)
        assert isinstance(decode(text), list)  # single-col -> list

    def test_nome_opcional(self):
        cpfs = ["529.982.247-25", "111.444.777-35"]
        text = encode(cpfs, schema=SPEC_CPF, name="docs")
        assert text.split("\n")[0] == "#TCF.8 docs:cpf"  # nome no header
        assert decode(text) == cpfs  # nome nao afeta os valores

    def test_nome_comecando_com_m_nao_colide(self):
        """Regressao: nome 'Meu' -> '#TCF.8 Meu:cpf' NAO pode virar multi."""
        cpfs = ["529.982.247-25", "111.444.777-35"]
        text = encode(cpfs, schema=SPEC_CPF, name="Meu")
        assert text.split("\n")[0] == "#TCF.8 Meu:cpf"
        assert decode(text) == cpfs  # decodifica como single, nao multi

    def test_ip_single_col_self_describing(self):
        # FLOOR total-byte (owner 2026-07-12): o IP nature COMPETE. Achado: em
        # single-col o padding do IP EMPATA com o pipeline (o núcleo já normaliza),
        # então o IP nature raramente vence (só onde há estrutura de subnet que a
        # nature explora melhor — ADR-0016). RT sempre; header condicional ao win.
        ips = ["192.168.1.1", "10.0.0.1", "172.16.0.1"]
        text = encode(ips, schema=SPEC_IP)
        assert decode(text) == ips  # RT independe do win
        line0 = text.split("\n")[0]
        # win (spec) OU piso (version-stamp, com ou sem sufixo de polaridade)
        assert line0 == "#TCF.8 :ip" or (line0.startswith("#TCF.8") and ":" not in line0)

    def test_unknown_id_raises(self):
        # ERRO estrito (BUG-13b, owner 2026-07-10 — antes: warning + cru calado)
        text = encode(["529.982.247-25", "111.444.777-35"], schema=SPEC_CPF)
        tampered = text.replace(":cpf", ":FUTURE9", 1)
        with pytest.raises(ValueError, match="desconhecido"):
            decode(tampered)

    def test_no_double_apply(self):
        """Precedencia header-vence: encode+decode ambos com nature -> RT."""
        cpfs = ["529.982.247-25", "111.444.777-35"]
        text = encode(cpfs, schema=SPEC_CPF)
        assert decode(text, schema=SPEC_CPF) == cpfs

    def test_custom_spec_roundtrip_requires_matching_out_of_band(self):
        # RE-PIN 2026-08-13 (weld A ADR-0041): spec de terceiro precisa de wire_id
        # PROPRIO — `replace(name=...)` sozinho herdaria o wire_id core `cpf` e a
        # emissao recusa a mascarada (pin em TestWireIdDoisPlanos). Convencao `x*`.
        custom = replace(SPEC_CPF, name="custom-cpf", wire_id="xcpf")
        cpfs = ["529.982.247-25", "111.444.777-35"]
        text = encode(cpfs, schema=custom)
        assert text.split("\n", 1)[0] == "#TCF.8 :xcpf"
        with pytest.raises(ValueError, match="desconhecido"):
            decode(text)
        assert decode(text, schema=custom) == cpfs
        wrong = replace(SPEC_CPF, name="other-cpf", wire_id="xother")
        with pytest.raises(ValueError, match="nao coincide"):
            decode(text, schema=wrong)

    def test_name_com_colon_rejeitado(self):
        with pytest.raises(ValueError, match="':'|reservado"):
            encode(["529.982.247-25"], schema=SPEC_CPF, name="ns:bad")


# ===========================================================================
# Telemetria de apply-rate (SideOutputs.nature_apply) — byte-neutra
# ===========================================================================


class TestNatureApplyTelemetry:
    def test_byte_neutral_with_side_outputs(self):
        """Coletar telemetria NAO muda os bytes do .tcf."""
        cpfs = ["529.982.247-25", "abc.def.ghi-jk", "111.444.777-35", ""]
        out_no = encode(cpfs, schema=SPEC_CPF)
        out_yes = encode(cpfs, schema=SPEC_CPF, side_outputs=SideOutputs())
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
        encode(cpfs, schema=SPEC_CPF, side_outputs=so)
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
            table, schema={"cpf": SPEC_CPF, "cnpj": SPEC_CNPJ}, side_outputs=so
        )
        # byte-neutro vs sem telemetria
        assert out == encode(table, schema={"cpf": SPEC_CPF, "cnpj": SPEC_CNPJ})
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
        w = encode(mensal, schema=S)
        # RE-PIN 2026-08-13 (weld A ADR-0041): o header carrega o wire_id `dt`.
        assert w.startswith("#TCF.8 :dt"), w[:24]
        assert len(w.encode()) < len(encode(mensal).encode()) // 10
        assert decode(w) == mensal

        # agrupado: o RLE do core ja' resolve; o spec o DESTRUIRIA -> o FLOOR recusa
        agrup = [(base + dt.timedelta(days=i // 20)).isoformat() for i in range(200)]
        w2 = encode(agrup, schema=S)
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
            w = encode(vals, schema=S)
            assert decode(w) == vals, f"RT quebrou com {pct}% de lixo"
            assert len(w.encode()) <= len(encode(vals).encode()), f"regrediu com {pct}%"


class TestNatureSlotNulo:
    """`None` e' do CORE, nao do spec (fix 2026-08-08).

    ANTES deste fix as QUATRO natures estouravam `TypeError: can only concatenate str
    (not "NoneType") to str` numa coluna com null — e a mesma coluna SEM `schema=`
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
            w = encode(col, schema=spec)
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
    atraem nature. Medido antes: coluna de 2 CPFs repetidos saia com 61 B sem `schema=` e
    198 B com — a nature "vencia" um baseline que o encoder nao emitiria.
    """

    def test_nature_nao_regride_contra_bn(self):
        from tcf import decode, encode
        from tcf.natures import SPEC_CPF, SPEC_IP

        for spec, v1, v2 in [(SPEC_CPF, "000.000.000-00", "111.111.111-11"),
                             (SPEC_IP, "192.168.0.1", "10.0.0.1")]:
            col = [v1, v2] * 30                       # k=2 -> o bN e' o baseline real
            sem = encode(col)
            com = encode(col, schema=spec)
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
            w = encode(vals, schema=S)
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
                encode(datas, schema=spec)
            with pytest.raises(ValueError, match="wire_id"):
                encode({"d": datas, "v": v}, schema={"d": spec})
            with pytest.raises(ValueError, match="wire_id"):
                encode(recs, schema={"quando": spec})

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
        w = encode(vals, schema=S)
        assert w.startswith("#TCF.8 :dt\n")
        velho = w.replace("#TCF.8 :dt\n", "#TCF.8 :data-iso\n", 1)  # wire pre-rename
        with pytest.raises(ValueError, match="data-iso.*out-of-band"):
            decode(velho)
        # spec out-of-band DIVERGENTE do id tambem falha alto (nunca escolhe calado)
        with pytest.raises(ValueError, match="nao coincide"):
            decode(velho, schema=S)
        valvula = dataclasses.replace(S, wire_id="data-iso")
        assert decode(velho, schema=valvula) == vals

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
        w = encode(vals, schema=S, side_outputs=so)
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
            encode(["529.982.247-25", "111.444.777-35"], schema=derivado)

    def test_noop_replace_e_o_proprio_core_continuam_passando(self):
        from dataclasses import replace

        from tcf import decode, encode
        from tcf.natures import SPEC_CPF

        cpfs = ["529.982.247-25", "111.444.777-35"]
        # o proprio spec core e o clone campo-a-campo igual NAO sao mascarada
        for spec in (SPEC_CPF, replace(SPEC_CPF)):
            assert decode(encode(cpfs, schema=spec)) == cpfs


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
        w = encode(datas, schema=_Impostor())
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
            encode(["2026-01-01", "2026-02-01"], schema=_Antigo())


class TestIntPadSpecWeld:
    """Weld EXP-018 (2026-08-14): `IntPadSpec` + a rota tipada aberta a spec.

    Antes deste weld, `encode([1,2,3], schema=SPEC)` era ValueError: a rota tipada nao
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
        base, w = encode(vals), encode(vals, schema=spec)
        assert w.startswith("#TCF.8n :ipad"), w[:24]
        assert len(w.encode()) < len(base.encode())
        assert decode(w) == vals
        assert all(type(x) is int for x in decode(w))     # o TIPO volta, nao a grafia

    def test_decode_resolve_sozinho_pelo_registry(self):
        """`:ipad` esta' no registry: o wire e' auto-contido, sem out-of-band."""
        from tcf import decode, encode
        from tcf.natures import int_pad_para

        vals = [i * 7 for i in range(600)]
        w = encode(vals, schema=int_pad_para(vals))
        assert decode(w) == vals          # sem passar schema=

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
            w = encode(vals, schema=spec) if spec else base
            assert len(w.encode()) <= len(base.encode()), f"NUNCA-PIOR violado em {nome}"
            assert decode(w) == vals, nome

    def test_slot_nulo_atravessa(self):
        """O null e' do TIPO, nao da grafia: atravessa o spec sem quebrar a progressao."""
        from tcf import decode, encode
        from tcf.natures import int_pad_para

        vals = [None if i % 37 == 0 else i for i in range(1, 601)]
        assert vals.count(None) == 16 and vals[0] == 1     # ancora o regime do teste
        w = encode(vals, schema=int_pad_para(vals))
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

        # RE-PIN 2026-08-21 (ADR-0044): CNPJ unificado, vocabulario de volta a 5.
        assert set(SPEC_REGISTRY) == {"cpf", "cnpj", "ip", "data-iso", "int-pad"}
        assert set(_WIRE_REGISTRY) == {"cpf", "cnpj", "ip", "dt", "ipad"}
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

        v = "12.ABC.345/01DE-35"
        assert SPEC_CNPJ.classify_value(v) == "compressible"
        payload, status = SPEC_CNPJ.encode_value(v)
        assert status == "compressible"
        assert len(payload) == 10
        assert SPEC_CNPJ.decode_value(payload) == v

    def test_dv_errado_e_recusado_e_vira_literal(self):

        v = "12.ABC.345/01DE-34"          # mesmo corpo, DV trocado
        assert SPEC_CNPJ.classify_value(v) == "check_invalid"
        payload, status = SPEC_CNPJ.encode_value(v)
        assert status == "check_invalid"
        assert payload.startswith(MARKER_LITERAL)
        assert SPEC_CNPJ.decode_value(payload) == v      # nunca perde dado

    def test_letra_e_numero_pelo_mapeamento_da_IN(self):
        """`_valor` e' ASCII-48 — universal nos dois dominios."""

        assert SPEC_CNPJ._valor("0") == 0
        assert SPEC_CNPJ._valor("9") == 9
        assert SPEC_CNPJ._valor("A") == 17
        assert SPEC_CNPJ._valor("Z") == 42
        # e no spec numerico da' exatamente o digito — por isso nada mudou la'
        assert [SPEC_CNPJ._valor(c) for c in "0123456789"] == list(range(10))

    def test_retrocompat_dv_identico_nas_duas_regras(self):
        """CNPJ numerico gera o MESMO DV sob a regra nova — por CONSTRUCAO.

        RE-ESCRITO 2026-08-21: com UM spec so' (ADR-0044) a versao anterior virou
        tautologia (`X is X`). A afirmacao que importa nao e' entre specs, e' entre
        REGRAS: calcular o DV pelo mapeamento novo (ASCII-48) tem de dar o mesmo
        que pelo antigo (int(digito)) em todo o dominio numerico.
        """
        for i in range(0, 400, 3):
            corpo = f"{i:012d}"
            novo_mapa = SPEC_CNPJ.check_fn([ord(c) - 48 for c in corpo])
            velho_mapa = SPEC_CNPJ.check_fn([int(c) for c in corpo])
            assert novo_mapa == velho_mapa, corpo
        for i in range(0, 60, 7):
            assert SPEC_CNPJ.classify_value(_cnpj_num(i)) == "compressible"

    # --- a GRAVACAO: base 36, e por que nao 43 -----------------------------
    def test_base_densa_e_a_capacidade(self):
        from tcf.natures import ALFABETO_CNPJ

        assert len(ALFABETO_CNPJ) == 36
        assert SPEC_CNPJ.encoded_length_compacto == 7   # base 10 -> 7 chars
        assert SPEC_CNPJ.encoded_length == 10           # base 36 -> 10 chars
        # os DOIS sao MINIMOS em base-80: nao ha' versao menor a achar
        assert len(BASE94) ** 6 < 10 ** 12 <= len(BASE94) ** 7
        assert len(BASE94) ** 9 < 36 ** 12 <= len(BASE94) ** 10
        assert 36 ** 12 <= len(BASE94) ** 10
        # o mapeamento LEGAL como base (43, por causa do gap 10-16) NAO caberia
        assert 43 ** 12 > len(BASE94) ** 10

    def test_extremos_do_dominio(self):
        """RE-PIN ADR-0043: corpo 100% decimal agora COMPACTA em 7 chars (o caso
        particular por valor); qualquer letra no corpo -> 10. RT nos dois."""

        for corpo, esperado in (("000000000000", 7), ("999999999999", 7),
                                ("ZZZZZZZZZZZZ", 10), ("A00000000000", 10),
                                ("99999999999Z", 10), ("0000000000ZZ", 10)):
            dv = "".join(str(d) for d in SPEC_CNPJ.check_fn(
                [ord(c) - 48 for c in corpo]))
            s = corpo + dv
            v = f"{s[:2]}.{s[2:5]}.{s[5:8]}/{s[8:12]}-{s[12:]}"
            payload, status = SPEC_CNPJ.encode_value(v)
            assert status == "compressible", v
            assert len(payload) == esperado, (v, payload)
            assert SPEC_CNPJ.decode_value(payload) == v

    # --- o WIRE: self-describing, e o legado intocado ----------------------
    def test_wire_self_describing_sem_spec_no_decode(self):

        col = ["12.ABC.345/01DE-35", "12.ABC.345/01DE-35", "AA.AAA.AAA/AAAA-38"]
        col = [v for v in col if SPEC_CNPJ.classify_value(v) == "compressible"]
        texto = encode(col, schema=SPEC_CNPJ)
        assert texto.startswith("#TCF.8 :cnpj")
        assert decode(texto) == col          # resolve pelo registry, sem out-of-band

    def test_spec_cnpj_numerico_ficou_byte_intocado(self):
        """O legado nao paga pelo novo: mesmo wire e mesmo tamanho de payload."""
        col = [_cnpj_num(i) for i in range(5)]
        texto = encode(col, schema=SPEC_CNPJ)
        assert texto.startswith("#TCF.8 :cnpj\n")
        assert decode(texto) == col
        for v in col:
            payload, status = SPEC_CNPJ.encode_value(v)
            assert status == "compressible"
            assert len(payload) == 7

    def test_coluna_mista_numerico_e_alfa(self):

        col = [_cnpj_num(3), "12.ABC.345/01DE-35", _cnpj_num(9)]
        texto = encode(col, schema=SPEC_CNPJ)
        assert decode(texto) == col
        # os TRES sao compressiveis sob o alfa (digito esta' no alfabeto)
        assert all(SPEC_CNPJ.classify_value(v) == "compressible" for v in col)

    # --- o LEGADO sob id UNICO: o que torna o compacto LOAD-BEARING --------
    def test_le_o_wire_legado_de_7_chars(self):
        """ADR-0044. O `:cnpj` historico gravava o corpo em base 10 com 7 chars.
        Com UM spec so', esse payload TEM de continuar decodificando — e e' o
        caso compacto que garante isso. Sem ele o decode devolveria o payload
        cru como se fosse o valor: corrupcao SILENCIOSA, nao erro alto."""
        # constroi o payload EXATAMENTE como o spec numerico pre-unificacao fazia
        v = "06.147.563/0001-93"
        n = int("061475630001")
        chars = []
        for _ in range(7):
            chars.append(BASE94[n % len(BASE94)])
            n //= len(BASE94)
        payload_legado = "".join(reversed(chars))

        assert SPEC_CNPJ.encode_value(v)[0] == payload_legado   # emite igual
        assert SPEC_CNPJ.decode_value(payload_legado) == v      # e le' de volta

    def test_sem_o_compacto_o_legado_corromperia_calado(self):
        """A prova por contraste do que o teste acima protege — e a justificativa
        de o caso compacto ser LOAD-BEARING e nao otimizacao."""
        sem = replace(SPEC_CNPJ, name="sem-compacto", wire_id="xsemc",
                      alfabeto_compacto=None, encoded_length_compacto=0)
        payload_legado = SPEC_CNPJ.encode_value("06.147.563/0001-93")[0]
        assert len(payload_legado) == 7
        # nao levanta: devolve o payload cru como se fosse o valor
        assert sem.decode_value(payload_legado) == payload_legado

    def test_coluna_numerica_emite_wire_byte_identico_ao_historico(self):
        """Unificar nao pode custar byte nenhum a quem so' tem CNPJ numerico."""
        col = [_cnpj_num(i) for i in range(50)]
        texto = encode(col, schema=SPEC_CNPJ)
        assert texto.splitlines()[0] == "#TCF.8 :cnpj"
        assert decode(texto) == col
        assert all(len(SPEC_CNPJ.encode_value(v)[0]) == 7 for v in col)

    # --- RESTAURADOS 2026-08-21 -------------------------------------------
    # Meu recorte na unificacao (ADR-0044) engoliu estes SEIS por descuido de
    # fatiamento — inclusive as guardas que a revisao adversarial do ADR-0043
    # tinha me feito escrever. A revisao seguinte pegou. Ficam aqui, agora
    # apontando pro spec unico.

    def test_emissao_canonica_por_valor(self):
        """Corpo decimal SEMPRE sai compacto (7); com letra SEMPRE pleno (10).
        Deterministico — nenhum valor tem duas grafias EMITIDAS."""
        p1, _ = SPEC_CNPJ.encode_value(_cnpj_num(3))
        p2, _ = SPEC_CNPJ.encode_value("12.ABC.345/01DE-35")
        assert (len(p1), len(p2)) == (7, 10)

    def test_decode_tolera_nao_canonico_de_10(self):
        """Corpo numerico gravado em 10 chars (nunca emitido) DECODIFICA — decode
        tolerante, emissao canonica, como o modo C: baseline nunca pinna isso."""
        from tcf.natures import ALFABETO_CNPJ

        n = 0
        for c in "061475630001":
            n = n * 36 + ALFABETO_CNPJ.index(c)
        chars = []
        for _ in range(10):
            chars.append(BASE94[n % len(BASE94)])
            n //= len(BASE94)
        nao_canonico = "".join(reversed(chars))
        assert SPEC_CNPJ.decode_value(nao_canonico) == "06.147.563/0001-93"
        # e o canonico do MESMO valor tem 7 — duas grafias LEGIVEIS, uma EMITIDA
        assert len(SPEC_CNPJ.encode_value("06.147.563/0001-93")[0]) == 7

    def test_payload_numerico_e_BYTE_IDENTICO_ao_legado(self):
        """O caso compacto nao e' parecido com o legado — e' o MESMO payload,
        por construcao (os indices do sub-alfabeto '0..9' SAO os digitos)."""
        for i in range(0, 200, 11):
            v = _cnpj_num(i)
            corpo = "".join(c for c in v if c.isdigit())[:12]
            n = int(corpo)
            chars = []
            for _ in range(7):
                chars.append(BASE94[n % len(BASE94)])
                n //= len(BASE94)
            esperado = "".join(reversed(chars))     # o que o spec numerico emitia
            assert SPEC_CNPJ.encode_value(v)[0] == esperado, v

    def test_minuscula_nao_pertence_ao_dominio(self):
        """NT 2025.001/XSD: `[0-9A-Z]{12}[0-9]{2}` — MAIUSCULA-only. Minuscula e'
        variante de REPRESENTACAO: aceita-la canonizando a saida perderia o RT
        byte-canonical, entao e' classe CONTRATO (H-15-06, aguarda a assinatura
        do T-FMT-CONTRACT-SIGNATURE). Hoje: literal — nao ganha, nunca corrompe."""
        v = "12.abc.345/01de-35"
        assert SPEC_CNPJ.classify_value(v) == "format_mismatch"
        payload, _ = SPEC_CNPJ.encode_value(v)
        assert payload == MARKER_LITERAL + v
        assert SPEC_CNPJ.decode_value(payload) == v      # byte-RT intacto

    def test_digito_unicode_mudou_de_ROTULO_e_nao_de_byte(self):
        """A unica mudanca de comportamento do weld do alfabeto, pinada de
        proposito. `classify_value` trocou `v.isdigit()` por "todo char no
        alfabeto". Digito unicode (arabico-indico) passava no `isdigit()` e era
        rotulado `format_unmasked`; agora e' `format_mismatch`. Os BYTES sao os
        mesmos — os dois status caem em literal —, muda so' a telemetria, e o
        rotulo novo e' o mais fiel (o simbolo nao pertence ao alfabeto)."""
        v = "\u0665\u0662\u0669\u0669\u0668\u0662\u0662\u0664\u0667\u0662\u0665"
        assert len(v) == 11 and v.isdigit()          # o `isdigit()` antigo dizia sim
        assert classify_value(SPEC_CPF, v) == "format_mismatch"
        payload, status = encode_value(SPEC_CPF, v)
        assert payload == MARKER_LITERAL + v         # BYTE identico ao pre-weld
        assert decode_value(SPEC_CPF, payload) == v

    def test_contrato_do_compacto_falha_alto(self):
        """As guardas do sub-alfabeto compacto — TODAS vieram da revisao
        adversarial do ADR-0043, que CONSTRUIU os specs malformados que elas
        barram: base 1 (decode nao TERMINA em payload adulterado), vazio+0
        (IndexError onde o contrato e' pass-through), e igualdade (o ramo pleno
        vira codigo morto calado)."""
        with pytest.raises(ValueError, match="PROPRIO"):
            replace(SPEC_CNPJ, name="y1", wire_id="y1", alfabeto_compacto="abc")
        with pytest.raises(ValueError, match="MENOR"):
            replace(SPEC_CNPJ, name="y2", wire_id="y2", encoded_length_compacto=10)
        with pytest.raises(ValueError, match="insuficiente"):
            replace(SPEC_CNPJ, name="y3", wire_id="y3", encoded_length_compacto=6)
        # base 1: o laco de expansao do decode nao terminaria (n%1=0, n//1=n)
        with pytest.raises(ValueError, match="PROPRIO"):
            replace(SPEC_CNPJ, name="y4", wire_id="y4",
                    alfabeto_compacto="0", encoded_length_compacto=1)
        # vazio + comprimento 0: colidiria com o pass-through do payload ''
        with pytest.raises(ValueError, match="PROPRIO"):
            replace(SPEC_CNPJ, name="y5", wire_id="y5",
                    alfabeto_compacto="", encoded_length_compacto=0)
        with pytest.raises(ValueError, match=">=1"):
            replace(SPEC_CNPJ, name="y6", wire_id="y6", encoded_length_compacto=0)
        # igualdade ao alfabeto pleno: o ramo de 10 chars nunca emitiria
        with pytest.raises(ValueError, match="PROPRIO"):
            replace(SPEC_CNPJ, name="y7", wire_id="y7",
                    alfabeto_compacto=SPEC_CNPJ.alfabeto)
        # o caso INVERSO (revisao 2026-08-21): comprimento sem sub-alfabeto e'
        # estado inconsistente esperando alguem confiar nele
        with pytest.raises(ValueError, match="sem alfabeto_compacto"):
            replace(SPEC_CNPJ, name="y8", wire_id="y8", alfabeto_compacto=None)
        # e a forma correta de derivar um spec SEM compacto constroi
        sem = replace(SPEC_CNPJ, name="y9", wire_id="y9",
                      alfabeto_compacto=None, encoded_length_compacto=0)
        assert sem.alfabeto_compacto is None

    # --- ADR-0045: bordas -------------------------------------------------
    def test_lf_final_nao_e_mais_engolido(self):
        """O `$` da regex casava ANTES de um LF final; o filtro de simbolos
        descartava o LF e o valor voltava SEM ele — RT quebrado, silencioso.
        Trocado por `\Z`. Atingia CPF, CNPJ e IP nao-padded; `data-iso` escapava
        por checar o comprimento."""
        from tcf.natures import SPEC_IP

        for spec, base in ((SPEC_CPF, "529.982.247-25"),
                           (SPEC_CNPJ, "11.222.333/0001-81"),
                           (SPEC_CNPJ, "12.ABC.345/01DE-35"),
                           (SPEC_IP, "192.168.0.1")):
            v = base + chr(10)
            payload, _ = encode_value(spec, v)
            assert payload == MARKER_LITERAL + v, (spec.name, base)
            assert decode_value(spec, payload) == v, (spec.name, base)

    def test_format_bordered_e_um_rotulo_acionavel(self):
        """Borda NAO comprime (trim mudaria o dado; o RT byte-canonical e'
        constituicao) — mas ganha rotulo proprio, porque `format_mismatch` diz
        'nao reconheco essa forma' e isto diz 'o dado esta' certo, o pipeline a
        montante e' que esta' sujo'. Os BYTES sao os mesmos dos dois jeitos."""
        from tcf.natures import SPEC_IP

        LF, TAB = chr(10), chr(9)
        bordados = ["  11.222.333/0001-81  ", "11.222.333/0001-81" + TAB,
                    "11.222.333/0001-81" + LF, LF + "11.222.333/0001-81"]
        for v in bordados:
            assert classify_value(SPEC_CNPJ, v) == "format_bordered", v
            payload, status = encode_value(SPEC_CNPJ, v)
            assert status == "format_bordered"
            assert payload == MARKER_LITERAL + v      # BYTE de literal, como antes
            assert decode_value(SPEC_CNPJ, payload) == v
        # o rotulo vale para os DOIS tipos de spec
        assert classify_value(SPEC_IP, " 192.168.0.1 ") == "format_bordered"
        assert classify_value(SPEC_CPF, " 529.982.247-25 ") == "format_bordered"

    def test_format_bordered_e_ESTREITO(self):
        """So' e' `format_bordered` o que vira COMPRESSIVEL depois do trim. Lixo
        com borda continua `format_mismatch`; DV errado continua `check_invalid`."""
        assert classify_value(SPEC_CNPJ, "  lixo  ") == "format_mismatch"
        assert classify_value(SPEC_CNPJ, "  11.222.333/0001-99  ") == "format_mismatch"
        assert classify_value(SPEC_CNPJ, "11.222.333/0001-99") == "check_invalid"
        assert classify_value(SPEC_CNPJ, "11.222.333/0001-81") == "compressible"

    # --- o CONTRATO do alfabeto (fail-loud no __post_init__) ---------------
    def test_alfabeto_invalido_falha_alto(self):

        with pytest.raises(ValueError, match="simbolo repetido"):
            replace(SPEC_CNPJ, name="x1", wire_id="x1", alfabeto="0012")
        with pytest.raises(ValueError, match="digitos decimais"):
            replace(SPEC_CNPJ, name="x2", wire_id="x2",
                    alfabeto="ABCDEFGHIJKL")
        with pytest.raises(ValueError, match="insuficiente"):
            replace(SPEC_CNPJ, name="x3", wire_id="x3", encoded_length=7)

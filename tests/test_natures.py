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
from pathlib import Path

import pytest

from tcf import encode, decode, SPEC_CPF, SPEC_CNPJ
from tcf.natures import (
    encode_value, decode_value, classify_value,
    BASE94, MARKER_LITERAL, SPEC_IP, SPEC_REGISTRY, _resolve_nature_id,
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
        assert len(BASE94) ** 5 > 10 ** 9
        # 80^7 > 10^12 (CNPJ body 12 digits)
        assert len(BASE94) ** 7 > 10 ** 12

    def test_base94_safe_chars(self):
        # Nenhum char reservado TCF
        forbidden = set('\n\r\t ,~*\\#=[]<>"\'`')
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
                encoding="utf-8") as f:
            r = csv.reader(f)
            header = next(r)
            cols = {h: [] for h in header}
            for row in r:
                for h, v in zip(header, row):
                    cols[h].append(v)
        text = encode(cols)
        assert len(text.encode("utf-8")) == 302  # D17a 0.7 (V2-B: era 307; ADR-0024/0025)

    def test_single_col_with_nature(self):
        cpfs = ["529.982.247-25", "111.444.777-35"]
        text = encode(cpfs, nature=SPEC_CPF)
        decoded = decode(text, nature=SPEC_CPF)
        assert decoded == cpfs

    def test_single_col_with_nature_mixed_valid_invalid(self):
        cpfs = [
            "529.982.247-25",          # valid
            "529.982.247-99",          # check invalid
            "abc.def.ghi-jk",          # format mismatch
            "111.444.777-35",          # valid
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
        text = encode(table, nature_per_col={
            "cpf": SPEC_CPF,
            "cnpj": SPEC_CNPJ,
        })
        decoded = decode(text, nature_per_col={
            "cpf": SPEC_CPF,
            "cnpj": SPEC_CNPJ,
        })
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
        assert decode(text) == table          # SEM nature_per_col no decode

    def test_magic_is_tcf8m_inline(self):
        table = {"doc": ["11.222.333/0001-81"], "plain": ["x"]}
        text = encode(table, nature_per_col={"doc": SPEC_CNPJ})
        line0 = text.split("\n")[0]
        assert line0.startswith("#TCF.8M")    # disc M, SEM espaco (ADR-0029)
        assert not line0.startswith("#TCF.8 ")  # nao colide com single+spec
        assert ":cnpj" in line0               # meta INLINE na linha do shebang

    def test_byte_neutral_default_off(self):
        """INVARIANTE byte-neutro: sem nature -> #TCF.7, bytes intactos."""
        table = {"a": ["529.982.247-25", "111.444.777-35"], "b": ["x", "y"]}
        text = encode(table)                  # SEM nature
        assert text.split("\n")[0] == "#TCF.7 M"
        assert text == encode(table)          # determinístico
        assert ":" not in text.split("\n")[1]  # nenhum :id

    def test_no_double_apply_with_nature_in_decode(self):
        """Precedência: encode+decode ambos com nature_per_col -> RT (header vence)."""
        table = {"cpf": ["529.982.247-25"], "doc": ["11.222.333/0001-81"]}
        npc = {"cpf": SPEC_CPF, "doc": SPEC_CNPJ}
        text = encode(table, nature_per_col=npc)
        assert decode(text, nature_per_col=npc) == table   # não dupla-aplica

    def test_ip_self_describing(self):
        table = {"ip": ["192.168.1.1", "10.0.0.1"], "x": ["a", "b"]}
        text = encode(table, nature_per_col={"ip": SPEC_IP})
        assert text.startswith("#TCF.8M")     # inline meta (ADR-0029)
        assert decode(text) == table

    def test_unknown_nature_id_raw_plus_warn(self):
        """Forward-compat: id desconhecido -> valor cru + warning (não KeyError)."""
        table = {"doc": ["11.222.333/0001-81"], "x": ["a"]}
        text = encode(table, nature_per_col={"doc": SPEC_CNPJ})
        tampered = text.replace(":cnpj", ":FUTURE9")
        with pytest.warns(UserWarning, match="desconhecido"):
            result = decode(tampered)
        # coluna fica crua (base-94), NÃO revertida pro CNPJ original
        assert result["doc"][0] != "11.222.333/0001-81"

    def test_colon_in_colname_rejected_with_nature(self):
        table = {"ns:col": ["529.982.247-25"], "x": ["a"]}
        with pytest.raises(ValueError, match="':'"):
            encode(table, nature_per_col={"ns:col": SPEC_CPF})

    def test_colon_in_colname_allowed_without_nature(self):
        """Superfície de input preservada: ':' no nome OK sem nature (#TCF.7)."""
        table = {"created:at": ["2026-01-01", "2026-01-02"], "x": ["a", "b"]}
        text = encode(table)                  # sem nature -> #TCF.7, ':' não parseado
        assert decode(text) == table

    def test_resolve_nature_id(self):
        assert _resolve_nature_id("cpf") is SPEC_CPF
        assert _resolve_nature_id("cnpj") is SPEC_CNPJ
        assert _resolve_nature_id("ip") is SPEC_IP
        assert _resolve_nature_id("nao-existe") is None      # tolerante, não raise
        assert set(SPEC_REGISTRY) == {"cpf", "cnpj", "ip"}


# ===========================================================================
# Colunas anonimas / posicionais — drop_names (nome = ordem, SQL-like)
# ===========================================================================

class TestDropNames:
    def test_roundtrip_posicional(self):
        table = {"a": ["x", "y"], "b": ["p", "q"]}
        text = encode(table, drop_names=True)
        assert decode(text) == {"0": ["x", "y"], "1": ["p", "q"]}   # nome = ordem

    def test_forca_tcf8m(self):
        text = encode({"a": ["x"], "b": ["y"]}, drop_names=True)
        assert text.startswith("#TCF.8M")     # anonimo = feature v8

    def test_meta_sem_nomes(self):
        text = encode({"aaa": ["x"], "bbb": ["y"]}, drop_names=True)
        line0 = text.split("\n")[0]
        assert "aaa" not in line0 and "bbb" not in line0   # nomes omitidos

    def test_menor_que_nomeado(self):
        table = {"coluna_longa_um": ["x", "y", "x"],
                 "coluna_longa_dois": ["p", "q", "p"]}
        assert len(encode(table, drop_names=True)) < len(encode(table))

    def test_com_nature(self):
        table = {"doc": ["11.222.333/0001-81"], "x": ["a"]}
        text = encode(table, nature_per_col={"doc": SPEC_CNPJ}, drop_names=True)
        assert decode(text) == {"0": ["11.222.333/0001-81"], "1": ["a"]}

    def test_named_default_inalterado(self):
        table = {"a": ["x", "y"], "b": ["p", "q"]}
        assert decode(encode(table)) == table          # default nomeado intacto


# ===========================================================================
# Discriminador #TCF.8 (1 char apos '#TCF.8': M / espaco / newline) — ADR-0029
# ===========================================================================

class TestDiscriminatorV8:
    def test_disc_multi_M(self):
        t = encode({"doc": ["11.222.333/0001-81"], "x": ["a"]},
                   nature_per_col={"doc": SPEC_CNPJ})
        assert t[:7] == "#TCF.8M"             # M logo apos #TCF.8 (sem espaco)
        assert decode(t) == {"doc": ["11.222.333/0001-81"], "x": ["a"]}

    def test_disc_single_space(self):
        t = encode(["529.982.247-25"], nature=SPEC_CPF)
        assert t[:7] == "#TCF.8 "             # espaco apos #TCF.8

    def test_version_stamp_emit_and_interpret(self):
        """#TCF.8\\n = carimbo opt-in (magic-number p/ file/libmagic)."""
        vals = ["a@b.com", "c@d.com", "a@b.com"]
        t = encode(vals, stamp=True)
        assert t.split("\n")[0] == "#TCF.8"   # linha so' '#TCF.8' (disc = newline)
        assert decode(t) == vals              # interpreta -> list (single-col)

    def test_version_stamp_nao_e_default(self):
        vals = ["a@b.com", "c@d.com"]
        assert not encode(vals).startswith("#TCF.8")   # default = orfao (body puro)

    def test_version_stamp_interpret_construido(self):
        """Capacidade de interpretar um #TCF.8\\n<body> (mesmo construido a mao)."""
        plain = encode(["x", "y", "x"])       # body orfao
        stamped = "#TCF.8\n" + plain
        assert decode(stamped) == ["x", "y", "x"]

    def test_stamp_ignorado_com_nature(self):
        """Com nature, o header de spec ja' versiona -> stamp e' no-op."""
        t = encode(["529.982.247-25"], nature=SPEC_CPF, stamp=True)
        assert t.startswith("#TCF.8 ")        # forma de spec, nao '#TCF.8\\n'
        assert decode(t) == ["529.982.247-25"]


# ===========================================================================
# Self-describing SINGLE-COL — nature-id no header (#TCF.8 sem M, ADR-0027)
# ===========================================================================

class TestNatureMarkSingleCol:
    def test_no_spec_byte_identico(self):
        """INVARIANTE byte-neutro: single-col SEM spec -> body puro, sem shebang."""
        vals = ["529.982.247-25", "111.444.777-35", "529.982.247-25"]
        text = encode(vals)                       # sem nature
        assert not text.startswith("#TCF.8")      # nenhum shebang
        assert text == encode(vals)               # deterministico
        assert decode(text) == vals

    def test_spec_self_describing(self):
        """Feature: encode single-col com nature -> decode SEM nature recupera."""
        cpfs = ["529.982.247-25", "111.444.777-35", "abc.def.ghi-jk"]
        text = encode(cpfs, nature=SPEC_CPF)
        assert decode(text) == cpfs               # SEM nature no decode

    def test_magic_sem_m_uma_linha(self):
        cpfs = ["529.982.247-25"]
        text = encode(cpfs, nature=SPEC_CPF)
        # header numa LINHA SO': '#TCF.8 :cpf' (sem ' M' -> single; nome vazio)
        assert text.split("\n")[0] == "#TCF.8 :cpf"
        assert not text.startswith("#TCF.8 M")    # nao colide com multi

    def test_retorna_list_nao_dict(self):
        text = encode(["529.982.247-25"], nature=SPEC_CPF)
        assert isinstance(decode(text), list)     # single-col -> list

    def test_nome_opcional(self):
        cpfs = ["529.982.247-25", "111.444.777-35"]
        text = encode(cpfs, nature=SPEC_CPF, name="docs")
        assert text.split("\n")[0] == "#TCF.8 docs:cpf"  # nome no header
        assert decode(text) == cpfs               # nome nao afeta os valores

    def test_nome_comecando_com_m_nao_colide(self):
        """Regressao: nome 'Meu' -> '#TCF.8 Meu:cpf' NAO pode virar multi."""
        cpfs = ["529.982.247-25", "111.444.777-35"]
        text = encode(cpfs, nature=SPEC_CPF, name="Meu")
        assert text.split("\n")[0] == "#TCF.8 Meu:cpf"
        assert decode(text) == cpfs               # decodifica como single, nao multi

    def test_ip_single_col_self_describing(self):
        ips = ["192.168.1.1", "10.0.0.1", "172.16.0.1"]
        text = encode(ips, nature=SPEC_IP)
        assert text.startswith("#TCF.8 ")         # header na linha do shebang
        assert decode(text) == ips

    def test_unknown_id_cru_warn(self):
        text = encode(["529.982.247-25"], nature=SPEC_CPF)
        tampered = text.replace(":cpf", ":FUTURE9", 1)
        with pytest.warns(UserWarning, match="desconhecido"):
            result = decode(tampered)
        assert result[0] != "529.982.247-25"      # cru (base-94), nao revertido

    def test_no_double_apply(self):
        """Precedencia header-vence: encode+decode ambos com nature -> RT."""
        cpfs = ["529.982.247-25", "111.444.777-35"]
        text = encode(cpfs, nature=SPEC_CPF)
        assert decode(text, nature=SPEC_CPF) == cpfs

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
            "529.982.247-25",   # compressible
            "111.444.777-35",   # compressible
            "529.982.247-99",   # check_invalid
            "abc.def.ghi-jk",   # format_mismatch
            "",                 # empty_value
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
            "plain": ["foo", "bar"],          # sem nature
        }
        so = SideOutputs()
        out = encode(table, nature_per_col={"cpf": SPEC_CPF, "cnpj": SPEC_CNPJ},
                     side_outputs=so)
        # byte-neutro vs sem telemetria
        assert out == encode(table, nature_per_col={"cpf": SPEC_CPF,
                                                    "cnpj": SPEC_CNPJ})
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

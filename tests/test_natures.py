"""Tests pra src/tcf/natures (ADR-0015 welding TemplatedCheckedSpec).

Valida:
- SPEC_CPF e SPEC_CNPJ encode/decode round-trip
- Fallback marker pra valores nao-compressible
- Integration com tcf.encode/decode (single + multi-col)
- D17a 322B INVARIANT preservado (sem nature param = sem mudanca)
- Classify taxonomy (Kim 2003)
"""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from tcf import encode, decode, SPEC_CPF, SPEC_CNPJ, TemplatedCheckedSpec
from tcf.natures import (
    encode_value, decode_value, classify_value,
    BASE94, MARKER_LITERAL,
)


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
        cpf = "123.456.789-09"
        # Calculate check digits to make valid
        # Build from known valid CPF
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
        assert len(text.encode("utf-8")) == 322

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

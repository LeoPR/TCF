"""Tests SPEC_IP — TemplatedPaddedSpec (ADR-0015 extensao).

Testa nova categoria TCU-NoCheckVarLength: IPv4 padded.
"""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from tcf import encode, decode, SPEC_IP
from tcf.natures.templated_padded import TemplatedPaddedSpec


ROOT = Path(__file__).resolve().parent.parent
LAB_DATA = ROOT / "experiments" / "lab" / "dirty" / "2026-05-24-cpf-templated-checked" / "data"


class TestSpecIP:
    def test_spec_ip_attrs(self):
        assert SPEC_IP.name == "ip"
        assert SPEC_IP.slot_widths == (3, 3, 3, 3)
        assert SPEC_IP.total_padded_length == 12
        assert SPEC_IP.separator == "."

    def test_encode_canonical_ip(self):
        payload, status = SPEC_IP.encode_value("192.168.1.1")
        assert status == "compressible"
        assert payload == "192168001001"

    def test_decode_canonical_ip(self):
        original = SPEC_IP.decode_value("192168001001")
        assert original == "192.168.1.1"

    def test_round_trip_simple(self):
        ips = ["192.168.1.1", "10.0.0.1", "172.16.0.1"]
        for ip in ips:
            payload, _ = SPEC_IP.encode_value(ip)
            assert SPEC_IP.decode_value(payload) == ip

    def test_padded_zeros_falls_back_to_literal(self):
        # 192.168.001.001 (padded form) NOT canonical -> literal fallback
        payload, status = SPEC_IP.encode_value("192.168.001.001")
        assert status == "format_padded_zeros"
        assert payload.startswith("_")
        assert SPEC_IP.decode_value(payload) == "192.168.001.001"

    def test_octet_in_slot_width_range_accepted(self):
        # Spec generica nao enforca semantica IP — qualquer 0-999 cabe em width=3
        # RT preservado (TCF nao valida semantica per ADR-0015 filosofia).
        payload, status = SPEC_IP.encode_value("192.168.1.300")
        assert status == "compressible"
        assert SPEC_IP.decode_value(payload) == "192.168.1.300"

    def test_octet_overflow_slot_width(self):
        # Octet 1000 nao cabe em width=3 -> range_invalid
        payload, status = SPEC_IP.encode_value("192.168.1.1000")
        # Regex `\d{1,3}` nao casa "1000" (4 digits) -> format_mismatch
        assert status == "format_mismatch"

    def test_format_mismatch_falls_back(self):
        payload, status = SPEC_IP.encode_value("not-an-ip")
        assert status == "format_mismatch"

    def test_empty_falls_back(self):
        payload, status = SPEC_IP.encode_value("")
        assert status == "empty_value"


class TestEncodeIntegrationIP:
    """Integration com encode()/decode() via nature param."""

    def test_encode_with_nature_ip(self):
        ips = ["192.168.1.1", "192.168.1.2", "192.168.1.3"]
        text = encode(ips, nature=SPEC_IP)
        decoded = decode(text, nature=SPEC_IP)
        assert decoded == ips

    @pytest.mark.skipif(
        not (LAB_DATA / "D-IP-subnet.csv").exists(),
        reason="D-IP-subnet.csv nao encontrado",
    )
    def test_subnet_compression_dramatic(self):
        """1000 IPs subnet com SPEC_IP deve ser ~229B (1.71% ratio)."""
        with (LAB_DATA / "D-IP-subnet.csv").open(encoding="utf-8") as f:
            r = csv.reader(f)
            next(r)
            ips = [row[0] for row in r if row]
        assert len(ips) == 1000

        text = encode(ips, nature=SPEC_IP)
        n_bytes = len(text.encode("utf-8"))

        # Esperado: ~229B (sub-exp 08 variante C)
        # Tolerancia: 200-300B
        assert 200 <= n_bytes <= 300, (
            f"D-IP-subnet 1000 com SPEC_IP: esperado ~229B, got {n_bytes}B"
        )

        decoded = decode(text, nature=SPEC_IP)
        assert decoded == ips, "RT FAIL no D-IP-subnet 1000"

    def test_default_unchanged_without_nature(self):
        """Sem nature, behavior identico ao M10 puro."""
        ips = ["192.168.1.1", "10.0.0.1"]
        text_with_nature = encode(ips, nature=SPEC_IP)
        text_without = encode(ips)
        # Diferentes (nature comprime)
        assert text_with_nature != text_without
        # Mas RT preserva ambos
        assert decode(text_with_nature, nature=SPEC_IP) == ips
        assert decode(text_without) == ips

    def test_multi_col_mixed_natures(self):
        from tcf import SPEC_CPF
        table = {
            "cpf": ["104.332.181-00", "960.013.389-14"],
            "ip": ["192.168.1.1", "10.0.0.1"],
        }
        text = encode(table, nature_per_col={"cpf": SPEC_CPF, "ip": SPEC_IP})
        decoded = decode(text, nature_per_col={"cpf": SPEC_CPF, "ip": SPEC_IP})
        assert decoded == table


class TestProtocolUniformity:
    """SPEC_IP e SPEC_CPF compartilham mesma Protocol interface."""

    def test_both_have_encode_value_method(self):
        from tcf import SPEC_CPF
        assert hasattr(SPEC_IP, "encode_value")
        assert hasattr(SPEC_CPF, "encode_value")
        assert hasattr(SPEC_IP, "decode_value")
        assert hasattr(SPEC_CPF, "decode_value")
        assert hasattr(SPEC_IP, "classify_value")
        assert hasattr(SPEC_CPF, "classify_value")

    def test_both_handle_invalid_uniformly(self):
        from tcf import SPEC_CPF
        # Empty string returns empty_value pra ambos
        _, status_cpf = SPEC_CPF.encode_value("")
        _, status_ip = SPEC_IP.encode_value("")
        assert status_cpf == status_ip == "empty_value"

    def test_polymorphic_dispatch_via_encoder(self):
        """encode() polimorfico — mesma signatura, specs diferentes."""
        from tcf import SPEC_CPF
        cpfs = ["104.332.181-00"]
        ips = ["192.168.1.1"]
        # Mesma funcao encode, specs diferentes
        text_cpf = encode(cpfs, nature=SPEC_CPF)
        text_ip = encode(ips, nature=SPEC_IP)
        assert decode(text_cpf, nature=SPEC_CPF) == cpfs
        assert decode(text_ip, nature=SPEC_IP) == ips

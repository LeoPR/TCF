"""Testes do natures_compiler (gadget: DSL textual -> nature executavel).

Prova central: o spec COMPILADO do DSL se comporta IDENTICO ao spec canonico escrito a
mao em src/tcf/natures/ (CPF/CNPJ/IP). Gadget em scripts/, nao toca src/tcf.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from tcf import encode, decode                          # noqa: E402
from tcf.natures import SPEC_CPF, SPEC_CNPJ, SPEC_IP     # noqa: E402
from natures_compiler import compile_file, compile_spec, parse_dsl  # noqa: E402

EX = ROOT / "scripts" / "natures_compiler" / "examples"


def _equivalente(compiled, hand, samples):
    """compiled e hand produzem o MESMO encode_value/decode_value em cada amostra."""
    for v in samples:
        assert compiled.encode_value(v) == hand.encode_value(v), f"encode divergiu em {v!r}"
        payload = compiled.encode_value(v)[0]
        assert compiled.decode_value(payload) == hand.decode_value(payload), f"decode divergiu em {v!r}"


CPF_SAMPLES = ["111.111.111-11", "222.222.222-22", "123.456.789-09", "000.000.000-00",
               "111.111.111-12", "12345678901", "abc", ""]
CNPJ_SAMPLES = ["11.111.111/1111-11", "22.222.222/2222-22", "11.222.333/0001-81", "abc", ""]
IP_SAMPLES = ["192.168.0.1", "0.0.0.0", "255.255.255.255", "192.168.001.001", "999.1.1.1", "x"]


def test_cpf_compilado_equivale_ao_core():
    c = compile_file(EX / "cpf.dsl")
    assert c.encoded_length == SPEC_CPF.encoded_length
    assert c.body_length == SPEC_CPF.body_length and c.check_length == SPEC_CPF.check_length
    _equivalente(c, SPEC_CPF, CPF_SAMPLES)


def test_cnpj_compilado_equivale_ao_core():
    c = compile_file(EX / "cnpj.dsl")
    assert c.encoded_length == SPEC_CNPJ.encoded_length
    _equivalente(c, SPEC_CNPJ, CNPJ_SAMPLES)


def test_ip_compilado_equivale_ao_core():
    c = compile_file(EX / "ip.dsl")
    assert c.slot_widths == SPEC_IP.slot_widths
    _equivalente(c, SPEC_IP, IP_SAMPLES)


def test_end_to_end_via_encode_decode():
    c = compile_file(EX / "cpf.dsl")
    cpfs = ["111.111.111-11", "222.222.222-22"]
    assert decode(encode(cpfs, nature=c), nature=c) == cpfs


def test_valida_template_vs_digitos():
    # template NNN-DD = 5 digitos, mas body+check = 11 -> rejeita
    with pytest.raises(ValueError):
        compile_spec({"name": "x", "template": "NNN-DD", "body_length": 9,
                      "check_length": 2, "check_algorithm": "mod11-cpf"})


def test_check_algorithm_desconhecido_rejeitado():
    with pytest.raises(ValueError):
        compile_spec({"name": "x", "check_algorithm": "verhoeff",
                      "padding_slots": [1], "separator": "."})


def test_padded_sem_slots_rejeitado():
    with pytest.raises(ValueError):
        compile_spec({"name": "x", "check_algorithm": "none"})


def test_check_length_incoerente_rejeitado():
    with pytest.raises(ValueError):
        compile_spec({"name": "x", "template": "NNNNNNNNN-D", "body_length": 9,
                      "check_length": 1, "check_algorithm": "mod11-cpf"})


def test_parse_dsl_flat():
    d = parse_dsl("name: ip\npadding_slots: [3, 3]\nseparator: .\n# comentario\nbody_length: 6")
    assert d == {"name": "ip", "padding_slots": [3, 3], "separator": ".", "body_length": 6}


# --- F1.5: registry (lookup por nome, gadget) ---

def test_registry_semeado_com_core():
    from natures_compiler import registry
    assert registry.get("cpf") is SPEC_CPF
    assert registry.get("cnpj") is SPEC_CNPJ
    assert registry.get("ip") is SPEC_IP


def test_registry_get_desconhecido():
    from natures_compiler import registry
    with pytest.raises(KeyError):
        registry.get("inexistente")


def test_registry_register_duplicado():
    from natures_compiler import registry
    spec = compile_file(EX / "cpf.dsl")
    with pytest.raises(ValueError):
        registry.register("cpf", spec)                 # ja' existe
    registry.register("cpf_dsl", spec)                 # nome novo: ok
    assert registry.get("cpf_dsl") is spec


def test_registry_load_dir():
    from natures_compiler import registry
    loaded = registry.load_dir(EX)
    assert {"cpf", "cnpj", "ip"} <= set(loaded)


def test_registry_end_to_end():
    from natures_compiler import registry
    spec = registry.get("cpf")
    cpfs = ["111.111.111-11", "222.222.222-22"]
    assert decode(encode(cpfs, nature=spec), nature=spec) == cpfs

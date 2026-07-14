"""RT do codec hierárquico #TCF.8H (weld T-CODE-TCF8H-WELD, ADR-0031).

Gate de CAPACIDADE: decode(encode_hierarchical(x)) == x nos clássicos de transmissão
(cadastro, pedido, telemetria) e nas bordas da classe coberta. O compressor de coluna
(L1) é reusado; este módulo (L2/L3) é aditivo — o flat fica byte-idêntico (guardado
pelos test_core_rt / test_regression_v1_baseline / test_real_world_snapshots).
"""
import pytest

from tcf import decode, encode, encode_hierarchical
from tcf.hierarchical import HierarchicalError


CLASSICOS = {
    "cadastro-multi-lista": [
        {"nome": "Ana Souza", "cpf": "111.111.111-11",
         "endereco": {"rua": "Rua A, 100", "cidade": "Sao Paulo",
                      "geo": {"lat": "-23.55", "lon": "-46.63"}},
         "telefones": ["+55 11 99999-0001", "+55 11 3333-0001"],
         "emails": ["ana@acme.com.br", "ana@gmail.com"]},
        {"nome": "Bruno Lima", "cpf": "222.222.222-22",
         "endereco": {"rua": "Av. B, 1500", "cidade": "Sao Paulo",
                      "geo": {"lat": "-23.56", "lon": "-46.65"}},
         "telefones": ["+55 11 99999-0002"],
         "emails": []},
    ],
    "pedido-aninhado": [
        {"cliente": "Ana", "pedidos": [
            {"data": "2026-01", "itens": [{"produto": "Teclado", "qtd": "1"},
                                          {"produto": "Mouse", "qtd": "2"}]},
            {"data": "2026-02", "itens": [{"produto": "Monitor", "qtd": "1"}]}]},
        {"cliente": "Bruno", "pedidos": []},
    ],
    "telemetria": [
        {"device": "estufa-01",
         "sensores": {"temp": {"un": "C"}, "umid": {"un": "%"}},
         "leituras": [{"ts": "06:00", "temp": "21.4", "umid": "63.0"},
                      {"ts": "06:15", "temp": "21.6", "umid": "63.4"}]},
    ],
    "ambiguidade-mesma-chave": [
        {"cli": "Ana", "pedidos": [
            {"data": "X", "itens": [{"p": "a"}]},
            {"data": "X", "itens": [{"p": "b"}]}]}],  # count resolve (nao funde)
    "array-escalar-duplicatas": [{"nome": "Ana", "tags": ["x", "x", "y"]}],
    "array-vazio-unico": [{"nome": "Ana", "telefones": []}],
    "array-vazio-primeiro": [{"n": "Ana", "tel": []},
                             {"n": "Bob", "tel": ["t1", "t2"]}],
}


@pytest.mark.parametrize("name", list(CLASSICOS))
def test_roundtrip_classicos(name):
    doc = CLASSICOS[name]
    blob = encode_hierarchical(doc)
    assert blob.startswith("#TCF.8H")           # sem-espaco (ADR-0031)
    assert decode(blob) == doc                  # decode() auto-roteia pelo magic


def test_flat_intacto():
    # weld aditivo: single-col e multi-col inalterados
    assert decode(encode(["abc", "abcd", "abcde"])) == ["abc", "abcd", "abcde"]
    assert decode(encode({"id": ["1", "2"], "n": ["a", "b"]})) == {"id": ["1", "2"], "n": ["a", "b"]}


def test_ragged_fail_loud():
    # objeto com chave faltando = fora da classe coberta (precisa def-level) -> fail-loud
    with pytest.raises(HierarchicalError, match="ausente|ragged"):
        encode_hierarchical([{"a": "1", "b": "2"}, {"a": "3"}])


def test_nao_dict_fail_loud():
    with pytest.raises(HierarchicalError):
        encode_hierarchical(["nao", "e", "objeto"])


def test_malformed_blob_fail_loud():
    with pytest.raises(HierarchicalError):
        decode("#TCF.8Hnome#:X[]\nbody")   # count size invalido

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


# --- nomes ADVERSARIAIS (auditoria 2026-07-15): chars da gramática do meta em NOMES ---
# Antes do escaping (portado do .8M): ','/'{' corrompiam CALADO, '['/']'/'}' TRAVAVAM o
# parse, ':'/'#' falhavam tarde, espaço inicial era comido. Agora: RT byte-exato.
ADVERSARIAL_NAMES = [
    "a:b", "c,d", "ef#", "g[h", "i{j", "a]b", "a}b",     # chars estruturais do meta
    "Order Date", " x", "x ",                            # espaços (inicial/interno/final)
    "k\\l", "a\\,b", "fim\\",                            # backslash literal + combinações
    "tudo,:#[]{}\\ junto",
]


@pytest.mark.parametrize("nome", ADVERSARIAL_NAMES)
def test_nome_adversarial_escalar_rt(nome):
    docs = [{nome: "1", "outro": "2"}, {nome: "3", "outro": "4"}]
    assert decode(encode_hierarchical(docs)) == docs


def test_nome_adversarial_em_toda_posicao_da_arvore():
    # nome com meta-chars em OBJETO, ARRAY-de-objetos e ARRAY-escalar (interações
    # escaping × colchetes estruturais × omit-closes)
    docs = [{"p,e{d": [{"it[em]": "1", "en{d": {"r,ua": "A"}}],
             "tag#s": ["x", "y"], "no}me": "Ana"}]
    assert decode(encode_hierarchical(docs)) == docs


def test_nome_escapado_no_fim_nao_quebra_omit_closes():
    # último campo DFS com nome terminando em ']'/'}': o omit-closes não pode comer
    # o closer ESCAPADO (só os estruturais)
    docs = [{"a": [{"ultimo]": "1"}]}, {"a": []}]
    assert decode(encode_hierarchical(docs)) == docs
    docs2 = [{"b": {"fecha}": "2"}}]
    assert decode(encode_hierarchical(docs2)) == docs2


def test_nome_vazio_fail_loud():
    with pytest.raises(HierarchicalError, match="vazio"):
        encode_hierarchical([{"": "v"}])


def test_nome_com_newline_fail_loud():
    with pytest.raises(HierarchicalError, match="\\\\n"):
        encode_hierarchical([{"a\nb": "v"}])


def test_escape_invalido_no_blob_fail_loud():
    # escape fora da whitelist = marcador de corrupção (unescape ESTRITO, como no .8M)
    with pytest.raises(HierarchicalError, match="nao-estrutural|dangling"):
        decode("#TCF.8H\\qx\ncorpo")


# --- property-test seedado: fuzz da classe coberta (promovido do lab 2026-07-14-2120) ---
# Guarda permanente: milhares de documentos aleatorios DENTRO da classe coberta devem
# fazer RT byte-exato. Seed fixa -> deterministico, sem flakiness. N modesto p/ a suite;
# o lab roda 8000 (fuzz.py).
def _gen_scalar(rng):
    r = rng.random()
    if r < 0.25:
        return str(rng.randint(0, 999999))
    if r < 0.45:
        return rng.choice(["ativo", "inativo", "SP", "RJ", "MG"])
    if r < 0.60:
        return rng.choice(["a,b", "x|y", "l\\m", "p:q", "c#d"])   # separadores -> escaping
    return "".join(rng.choice("abcdefghij .-_0123456789") for _ in range(rng.randint(1, 20)))


def _gen_schema(rng, depth):
    schema = {}
    for i in range(rng.randint(1, 4)):
        # ~25% dos nomes carregam chars adversariais do meta (auditoria 2026-07-15)
        nome = f"f{i}"
        if rng.random() < 0.25:
            nome += rng.choice([",a", ":b", "#c", "[d", "]e", "{f", "}g", " h", "\\i"])
        r = rng.random()
        if depth > 0 and r < 0.22:
            schema[nome] = ("obj", _gen_schema(rng, depth - 1))
        elif depth > 0 and r < 0.44:
            schema[nome] = ("arr_obj", _gen_schema(rng, depth - 1))
        elif r < 0.60:
            schema[nome] = ("arr_sca", None)
        else:
            schema[nome] = ("scalar", None)
    return schema


def _gen_record(rng, schema):
    rec = {}
    for name, (kind, sub) in schema.items():
        if kind == "scalar":
            rec[name] = _gen_scalar(rng)
        elif kind == "obj":
            rec[name] = _gen_record(rng, sub)
        elif kind == "arr_obj":
            rec[name] = [_gen_record(rng, sub) for _ in range(rng.choice([0, 1, 1, 2, 3]))]
        elif kind == "arr_sca":
            rec[name] = [_gen_scalar(rng) for _ in range(rng.choice([0, 1, 1, 2, 4]))]
    return rec


def test_fuzz_classe_coberta_seedado():
    import random
    rng = random.Random(20260714)   # seed fixa (reproduzivel)
    for _ in range(1200):
        schema = _gen_schema(rng, depth=rng.randint(0, 3))
        recs = [_gen_record(rng, schema) for _ in range(rng.randint(1, 8))]
        assert decode(encode_hierarchical(recs)) == recs

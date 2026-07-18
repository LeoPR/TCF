"""DOIS CONTRATOS — o TCF lê DATASET, não JSON (enquadramento do owner, 2026-07-17).

CONTRATO A (da lib json; NÃO é responsabilidade do TCF — é nossa responsabilidade CONHECER):
    texto JSON --loads--> dataset --dumps--> texto JSON
CONTRATO B (do TCF; o único que o core assina):
    dataset --encode--> .tcf --decode--> dataset        sobre a classe D_json

D_json (definida por DOCUMENTO OFICIAL — tabela de conversão do módulo json do CPython 3.13 +
RFC 8259/7493, não por experimento) = fecho recursivo de:
    dict[str,·] · list · str(Unicode válido) · int · float FINITO · True · False · None
    — e qualquer um deles na raiz (RFC 8259 §2).

Grupos deste arquivo:
  CONTRATO A  — sanidade do AMBIENTE: a lib se comporta como a PRÓPRIA doc declara.
                (não testa o TCF; se quebrar, mudou o CPython, não nós)
  D_JSON      — o critério do owner, só onde ele vale:  ∀D∈D_json: J-RT-TX(D) ⟹ T-RT(D)
                PARIDADE (pins) · LACUNAS (xfail strict — não fecham em silêncio) · RAIZ (P4b)
  FORA_DA_CLASSE — NaN/Inf/tuple/chave-não-str/surrogate: NÃO SÃO PARIDADE. A própria doc do
                CPython os declara desvio/lossy ("loads(dumps(x)) != x if x has non-string
                keys"; "not valid JSON"). São pinos do comportamento do TCF na fronteira
                dataset ⊃ JSON (hoje fail-loud; futuro = representar, E7/H-HIER-SCALAR-01).

Fontes: notas/dataset-json-dois-contratos.md (citações verbatim da doc oficial) ·
lab 2026-07-17-0140 (medições) · docs.python.org/3.13/library/json.html.
"""
from __future__ import annotations

import json

import pytest

from tcf import decode, encode_hierarchical


def j_rt_tx(docs) -> bool:
    """Contrato A com transmissão: dumps -> bytes UTF-8 -> loads. True se volta igual."""
    try:
        wire = json.dumps(docs, ensure_ascii=False).encode("utf-8")
        return json.loads(wire.decode("utf-8")) == docs
    except Exception:                                   # noqa: BLE001
        return False


def t_rt_tx(docs) -> bool:
    """Contrato B com transmissão: encode -> bytes UTF-8 -> decode. True se volta igual."""
    try:
        wire = encode_hierarchical(docs).encode("utf-8")
        return decode(wire.decode("utf-8")) == docs
    except Exception:                                   # noqa: BLE001
        return False


# =====================================================================================
# CONTRATO A — sanidade do ambiente: a lib faz o que a PRÓPRIA doc declara (3.13)
# =====================================================================================

class TestContratoA_DocOficial:
    def test_dup_lastwins_como_documentado(self):
        """Doc: "it ignores all but the last name-value pair for a given name"."""
        assert json.loads('{"x": 1, "x": 2, "x": 3}') == {"x": 3}

    def test_nan_emitido_por_default_como_documentado(self):
        """Doc: desvio DECLARADO — "Infinite and NaN number values are accepted and output"."""
        assert json.dumps(float("nan")) == "NaN"        # token fora da RFC 8259 §6, declarado

    def test_allow_nan_false_e_o_modo_estrito_documentado(self):
        """Doc: allow_nan=False -> ValueError "in strict compliance with the JSON specification"."""
        with pytest.raises(ValueError):
            json.dumps(float("nan"), allow_nan=False)

    def test_chave_nao_str_quebra_rt_como_documentado(self):
        """Doc: "loads(dumps(x)) != x if x has non-string keys" — o LOSSY é contrato declarado."""
        x = {1: "x"}
        assert json.loads(json.dumps(x)) != x

    def test_tuple_vira_list_como_documentado(self):
        """Doc (tabela): encode "list, tuple -> array"; decode "array -> list". Tipo não volta."""
        assert json.loads(json.dumps((1, 2))) == [1, 2]


# =====================================================================================
# D_JSON — o critério do owner:  ∀D ∈ D_json:  J-RT-TX(D) ⟹ T-RT(D)
# =====================================================================================

PARIDADE = {
    "escalares": [{"id": 1, "nome": "Ana", "ok": True, "v": 1.5, "n": None}],
    "aninhado": [{"a": {"b": [1, 2]}, "c": [{"d": "x"}]}],
    "unicode": [{"a": "café 中文 🎉"}],
    "nfc-vs-nfd": [{"café": 1, "café": 2}],            # E-com-acento vs e+combining: 2 chaves
    "tab-em-valor": [{"a": "x\ty"}],
    "nul-em-valor": [{"a": "x\x00y"}],
    "menos-zero": [{"a": -0.0}],
    "precisao": [{"a": 0.1 + 0.2}],
    "array-vazio": [{"a": []}],
    "objeto-vazio": [{"a": {}, "b": 1}],
    "null-em-campo": [{"a": None, "b": 1}],
    "ragged": [{"a": 1, "c": 2}, {"a": 3, "obs": "o", "c": 4}],
    # TCF ⊃ I-JSON: RFC 7493 §2.2 restringe a 2^53-1; int é D_json (RFC 8259 não limita) e RT-a
    "int-acima-2^53": [{"a": 2 ** 53 + 1}],
    "int-gigante": [{"a": 10 ** 30}],
    # --- PROMOVIDOS 2026-07-17 (eram LACUNA; weld do escape D_json fechou as 3) ---
    "chave-vazia": [{"": "x", "a": 1}],                 # str "" é D_json ({"": v} é JSON válido)
    "lf-em-valor": [{"a": "x\ny"}],                     # str com LF é D_json (multilinha real)
    "chave-com-lf": [{"a\nb": "x"}],
    "backslash-em-valor": [{"a": "C:\\temp\\x"}],       # o escape-do-escape (custo: +1B por `\`)
    "backslash-e-lf": [{"a": "a\\b\nc\\\\d"}],          # composição adversarial
    "chave-vazia-e-lf": [{"": "x\ny", "a\nb": "\\"}],   # nome vazio + LF em nome + `\` em valor
    "so-lf": [{"a": "\n", "b": "\n\n\n"}],
    "so-backslash": [{"a": "\\", "b": "\\\\"}],
    # --- PROMOVIDO 2026-07-17 (auditoria do escape: CR é D_json e ficara de fora do alfabeto) ---
    "cr-em-valor": [{"a": "x\ry"}],
    "crlf-em-valor": [{"a": "linha1\r\nlinha2"}],       # o par CRLF real (Windows)
    "cr-em-nome": [{"a\rb": "v"}],
}

# Vazio: as 3 lacunas de DATASET fecharam no weld do escape (2026-07-17). Resta só o eixo RAIZ.
# Se uma nova lacuna aparecer, entra aqui como xfail(strict) — some em silêncio nunca.
LACUNAS: dict[str, list] = {}

RAIZ_LACUNAS = {
    "objeto-unico": {"a": 1},
    "array-de-escalares": [1, 2],
    "escalar": 42,
    "string": "x",
    "nulo": None,
    "array-vazio": [],
    "lista-objeto-vazio": [{}],
}


@pytest.mark.parametrize("nome", list(PARIDADE))
def test_paridade_d_json(nome):
    """Os dois contratos fazem RT. Quebrar aqui = regressão de capacidade do TCF."""
    docs = PARIDADE[nome]
    assert j_rt_tx(docs), f"{nome}: o Contrato A parou de valer (mudou o ambiente?)"
    assert t_rt_tx(docs), f"{nome}: REGRESSÃO — D∈D_json com J-RT e sem T-RT"


@pytest.mark.parametrize("nome", list(LACUNAS))
@pytest.mark.xfail(strict=True, reason="lacuna DENTRO de D_json (escala E2/E4/E6) — "
                                       "implementar => XPASS => promover pra PARIDADE")
def test_lacuna_d_json(nome):
    """D∈D_json onde o json faz RT e o TCF ainda não — a superfície de implementação."""
    docs = LACUNAS[nome]
    assert j_rt_tx(docs), f"{nome}: premissa — Contrato A vale"
    assert t_rt_tx(docs), f"{nome}: TCF ainda não cobre (esperado)"


@pytest.mark.parametrize("nome", list(RAIZ_LACUNAS))
def test_raiz_d_json_ainda_fail_loud(nome):
    """Raiz livre é D_json (RFC 8259 §2). O TCF aceita só list[dict] — pino do estado (P4b)."""
    v = RAIZ_LACUNAS[nome]
    assert j_rt_tx(v), f"{nome}: premissa — Contrato A vale na raiz"
    assert not t_rt_tx(v), f"{nome}: raiz aceita — P4b implementado? atualizar pino"


def test_criterio_global_d_json():
    """Agregado: nenhum caso de PARIDADE pode regredir sem alarme."""
    quebrados = [n for n, d in PARIDADE.items() if j_rt_tx(d) and not t_rt_tx(d)]
    assert not quebrados, f"regressão do critério em D_json: {quebrados}"


# =====================================================================================
# FORA DA CLASSE — dataset ⊃ JSON. NÃO é paridade: a própria doc declara desvio/lossy.
# Pinos do comportamento ATUAL do TCF (fail-loud). Evolução = representar (E7), nunca copiar.
# =====================================================================================

FORA_DA_CLASSE = {
    # (dataset, por que está fora de D_json — pela DOC/norma, não por opinião)
    "nan": ([{"a": float("nan")}], "RFC 8259 §6 not permitted; doc CPython: extensão declarada"),
    "mais-inf": ([{"a": float("inf")}], "idem"),
    "menos-inf": ([{"a": float("-inf")}], "idem"),
    "tuple": ([{"a": (1, 2)}], "tabela oficial: tuple->array; array->list — tipo não volta"),
    "chave-int": ([{1: "x"}], 'doc: "loads(dumps(x)) != x if x has non-string keys"'),
    "chave-int-e-str": ([{1: "x", "1": "y"}], "coerção FABRICA duplicata no texto (medido)"),
    "surrogate": ([{"a": "\ud800"}], "não-transmissível em UTF-8 (RFC 8259 §8.1; I-JSON §2.1)"),
}


@pytest.mark.parametrize("nome", list(FORA_DA_CLASSE))
def test_fora_da_classe_tcf_recusa(nome):
    """O TCF fail-louda datasets fora de D_json — hoje. Se passar a aceitar algum,
    foi decisão de formato (E7/H-HIER-SCALAR-01): atualizar este pino JUNTO da decisão."""
    docs, _motivo = FORA_DA_CLASSE[nome]
    assert not t_rt_tx(docs), (
        f"{nome}: o TCF passou a aceitar dataset fora de D_json — decisão E7 tomada? "
        f"atualizar pino e docs juntos")

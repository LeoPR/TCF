"""CRITÉRIO DO FLUXO — o caminho JSON vs o caminho TCF (pino do owner, 2026-07-17).

    dataset -> encode -> json -> TRANSMITE -> recebe -> json -> decode -> dataset
    dataset -> encode -> tcf  -> TRANSMITE -> recebe -> tcf  -> decode -> dataset

CRITÉRIO:  ∀D:  J-RT-TX(D)  ⟹  T-RT(D)
"se o caminho JSON faz round-trip ATRAVÉS DA TRANSMISSÃO, o caminho TCF tem de fazer também".

A etapa TRANSMITE (encode p/ bytes UTF-8) é o que torna o critério honesto: sem ela o lone
surrogate 'passaria' (o escape \\uXXXX do ensure_ascii o esconde) e mediríamos uma paridade
que não existe no fio.

O que este arquivo pina:
  - PARIDADE: casos onde os DOIS caminhos fazem RT — regressão em qualquer um = alarme.
  - LACUNA: casos onde o json (conforme I-JSON) faz e o TCF não — a superfície de implementação.
    São `xfail(strict=True)`: quando um for implementado, o teste vira XPASS e OBRIGA a mover
    o caso pra PARIDADE (o pino não deixa fechar a lacuna em silêncio).
  - TCF-ESTRITO: casos onde o TCF recusa e o json só 'passa' fora da norma (RFC 8259 §6).
    Pinar impede que alguém 'conserte' o TCF afrouxando pra copiar um bug do json.

Lab de origem (medições + I-JSON checker):
experiments/lab/dirty/2026-07-17-0140-paridade-fluxo-json-vs-tcf/
"""
from __future__ import annotations

import json

import pytest

from tcf import decode, encode_hierarchical


def j_rt_tx(docs) -> bool:
    """Caminho JSON COM transmissão: dumps -> bytes UTF-8 -> loads. True se volta igual."""
    try:
        wire = json.dumps(docs, ensure_ascii=False).encode("utf-8")
        return json.loads(wire.decode("utf-8")) == docs
    except Exception:                                   # noqa: BLE001
        return False


def t_rt_tx(docs) -> bool:
    """Caminho TCF COM transmissão: encode -> bytes UTF-8 -> decode. True se volta igual."""
    try:
        wire = encode_hierarchical(docs).encode("utf-8")
        return decode(wire.decode("utf-8")) == docs
    except Exception:                                   # noqa: BLE001
        return False


# --- os DOIS caminhos fazem RT: o critério vale (14 casos medidos 2026-07-17) ---
PARIDADE = {
    "escalares": [{"id": 1, "nome": "Ana", "ok": True, "v": 1.5, "n": None}],
    "aninhado": [{"a": {"b": [1, 2]}, "c": [{"d": "x"}]}],
    "unicode": [{"a": "café 中文 🎉"}],
    "nfc-vs-nfd": [{"café": 1, "café": 2}],
    "tab-em-valor": [{"a": "x\ty"}],
    "nul-em-valor": [{"a": "x\x00y"}],
    "menos-zero": [{"a": -0.0}],
    "precisao": [{"a": 0.1 + 0.2}],
    "array-vazio": [{"a": []}],
    "objeto-vazio": [{"a": {}, "b": 1}],
    "null-em-campo": [{"a": None, "b": 1}],
    "ragged": [{"a": 1, "c": 2}, {"a": 3, "obs": "o", "c": 4}],
    # TCF ⊃ I-JSON: inteiros > 2^53 fazem RT aqui e o I-JSON os proíbe (RFC 7493 §2.2)
    "int-acima-2^53": [{"a": 2 ** 53 + 1}],
    "int-gigante": [{"a": 10 ** 30}],
}

# --- o json (conforme I-JSON) faz RT e o TCF NÃO: a superfície de implementação ---
LACUNAS = {
    "chave-vazia": [{"": "x", "a": 1}],
    "lf-em-valor": [{"a": "x\ny"}],
    "chave-com-lf": [{"a\nb": "x"}],
}

# --- o TCF recusa e o json só 'passa' emitindo token inválido por RFC 8259 §6 ---
TCF_ESTRITO = {
    "mais-infinito": [{"a": float("inf")}],
    "menos-infinito": [{"a": float("-inf")}],
}

# --- eixo RAIZ (P4b): o json faz RT, o TCF aceita só list[dict] hoje ---
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
def test_paridade_json_tcf(nome):
    """Os dois caminhos fazem RT. Se o TCF quebrar aqui = regressão de capacidade."""
    docs = PARIDADE[nome]
    assert j_rt_tx(docs), f"{nome}: o caminho JSON parou de fazer RT (mudou o ambiente?)"
    assert t_rt_tx(docs), f"{nome}: REGRESSÃO — o json faz RT e o TCF não"


@pytest.mark.parametrize("nome", list(LACUNAS))
@pytest.mark.xfail(strict=True, reason="lacuna de capacidade conhecida (escala E3/E5/E7) — "
                                       "quando implementar, mover o caso p/ PARIDADE")
def test_lacuna_de_capacidade(nome):
    """O json faz RT (e é I-JSON-conforme); o TCF ainda não.

    strict=True de propósito: fechar a lacuna faz o teste dar XPASS e FALHAR a suíte —
    obrigando a promover o caso para PARIDADE. A lacuna não fecha em silêncio.
    """
    docs = LACUNAS[nome]
    assert j_rt_tx(docs), f"{nome}: premissa — o json faz RT"
    assert t_rt_tx(docs), f"{nome}: TCF ainda não faz (esperado)"


@pytest.mark.parametrize("nome", list(TCF_ESTRITO))
def test_tcf_estrito_onde_json_sai_da_norma(nome):
    """±Infinity: o CPython emite 'Infinity' (RFC 8259 §6 NÃO permite; allow_nan=True é default).

    O TCF recusa. Isto NÃO é lacuna — é o json fora da norma. Pinado para que ninguém
    'conserte' o TCF afrouxando: copiar aqui seria importar um bug de interoperabilidade.
    """
    docs = TCF_ESTRITO[nome]
    assert j_rt_tx(docs), f"{nome}: premissa — o CPython round-trip'a (fora da RFC)"
    assert not t_rt_tx(docs), f"{nome}: o TCF passou a ACEITAR não-finito — decisão de formato?"


@pytest.mark.parametrize("nome", list(RAIZ_LACUNAS))
def test_raiz_generalizada_ainda_fail_loud(nome):
    """P4b: o json faz RT de qualquer valor na raiz; o TCF aceita só list[dict].

    Pino do estado atual (fail-loud declarado, 0 corrupção silenciosa). Quando o P4b
    for decidido/implementado, este teste muda junto — de propósito.
    """
    v = RAIZ_LACUNAS[nome]
    assert j_rt_tx(v), f"{nome}: premissa — o json faz RT na raiz"
    assert not t_rt_tx(v), f"{nome}: raiz passou a ser aceita — P4b implementado? atualizar pino"


def test_criterio_global_nao_regrediu():
    """O critério agregado: nenhum caso de PARIDADE pode virar lacuna sem alarme."""
    quebrados = [n for n, d in PARIDADE.items() if j_rt_tx(d) and not t_rt_tx(d)]
    assert not quebrados, f"regressão do critério J-RT ⟹ T-RT em: {quebrados}"

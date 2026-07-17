"""Sinteticos de CONTROLE do fluxo hierarquico (.8H) — pins de NAVEGACAO.

Complementa test_hierarchical_rt.py (correcao: RT + fail-loud) com a dimensao que
faltava: PRA ONDE OS BYTES VAO (buckets meta/controle/folhas) e QUAIS mecanismos
disparam (mask omitida quando uniforme; counts colapsam; emask densa; seq-RLE).
Antes desta suite o .8H nao tinha NENHUM pino de bytes — uma regressao de
eficiencia de fluxo seria invisivel (o flat tem D1-D9/real-world; o hierarquico
so tinha RT).

Pins = marcadores de dev re-pinaveis (ADR-0024 git-as-compat): mudanca consciente
de representacao re-pina COM investigacao; mudanca silenciosa = alarme.

Fonte unica dos casos: tests/fixtures/control_synthetics_h.py (mesmo gerador do
lab experiments/lab/dirty/2026-07-17-0014-sinteticos-controle-fluxo-hierarquia/,
que produz os .tcf inspecionaveis e a tabela de navegacao).
"""
from __future__ import annotations

import json

import pytest

from tcf import decode, encode_hierarchical

from fixtures.control_synthetics_h import (
    KEY_ORDER_EXPECTED_BACK,
    KEY_ORDER_PROBE,
    decompose,
    gen_cases,
)

# (total, meta, controle, folhas, n_cols_controle) — medidos 2026-07-17 no weld P4a (suite 754).
PINS = {
    "c01-uniforme":          (798,  30,   0,  768, 0),
    "c02-telemetria-array":  (3134, 26,   8, 3100, 1),
    "c03-telemetria-split":  (2836, 43,   0, 2793, 0),
    "c04-ragged":            (685,  31,  78,  576, 1),
    "c05-null-campo":        (842,  33,  90,  719, 1),
    "c06-null-elemento":     (1422, 40, 409,  973, 2),
    "c07-arrays-vazios":     (467,  25, 201,  241, 1),
    "c08-matriz":            (646,  27,  14,  605, 2),
    "c09-espinha":           (3219, 57, 238, 2924, 1),
    "c10-tipos-cadenciados": (1317, 34,   0, 1283, 0),
    "c11-categorico":        (1688, 21,   0, 1667, 0),
    "c12-compose-total":     (1459, 75, 436,  948, 5),
}

_CASES = gen_cases()


@pytest.fixture(scope="module")
def wires():
    """Encoda cada caso 1x por sessao de teste (RT validado aqui mesmo)."""
    out = {}
    for key, (_desc, _mec, docs) in _CASES.items():
        wire = encode_hierarchical(docs)
        assert decode(wire) == docs, f"RT falhou em {key}"
        out[key] = wire
    return out


@pytest.mark.parametrize("key", list(PINS))
def test_navegacao_pinada(wires, key):
    """Buckets byte-exatos por caso — o pino de comportamento do fluxo."""
    d = decompose(wires[key])
    got = (d["total"], d["meta"], d["controle"], d["folhas"], d["n_cols_controle"])
    assert got == PINS[key], (
        f"{key}: navegacao mudou {PINS[key]} -> {got}. Se a mudanca de representacao "
        f"foi CONSCIENTE, re-pinar com investigacao (ADR-0024); senao, regressao de fluxo.")


def test_uniforme_nao_paga_controle(wires):
    """Principio 'nao expandir o obvio': campo sempre-presente/nunca-null nao tem mask."""
    assert decompose(wires["c01-uniforme"])["n_cols_controle"] == 0


def test_counts_uniformes_colapsam(wires):
    """Fan-out fixo: a coluna de count de 200 instancias colapsa em poucos bytes (RLE)."""
    cols = {(p, k): b for p, k, b in decompose(wires["c02-telemetria-array"])["cols"]}
    assert cols[("v", "count")] <= 10   # medido 8 B para 200 instancias


def test_par_fanout_split(wires):
    """H-HIER-FANOUT-SPLIT-01, par de controle: MESMOS dados, array vs campos irmaos.

    Com serie realista (random-walk) o split ganha ~9.5%; com folhas de baixa
    entropia o ganho e' muito maior (ver revisao 2026-07-16 §2.2c: 96.5% do wire
    em folhas no caso constante). O pino aqui e' o SINAL (split < array), nao o
    tamanho do ganho.
    """
    array = decompose(wires["c02-telemetria-array"])["total"]
    split = decompose(wires["c03-telemetria-split"])["total"]
    assert split < array


def test_sintoma_emask_densa(wires):
    """H-HIER-EMASK-SPARSE-01: null esparso em elemento liga emask O(total-elementos).

    Pino do SINTOMA (controle >= 25% do wire) — se um dia a emask ficar
    por-instancia/esparsa, este teste avisa para re-pinar PINS junto.
    """
    d = decompose(wires["c06-null-elemento"])
    assert d["controle"] * 4 >= d["total"]


def test_ordem_de_chaves_ragged_e_do_schema():
    """FRONTEIRA OBSERVADA (achado 2026-07-17 da suite de controle; NAO consertar
    sem decisao de contrato do owner): chave opcional que aparece pela 1a vez
    DEPOIS do 1o registro volta na ordem do SCHEMA (uniao por 1a aparicao) — ao
    FIM do dict — nao na posicao por-registro. Igualdade semantica (dict) passa;
    byte-igualdade do json.dumps nao. Registro: T-API-BOUNDARY-CONTRACTS +
    T-CODE-TCF8H-JSON-PARITY. O contrato S0 do DatasetH (lab 2026-07-16-1708)
    preserva ordem por-registro — gap S0 x .8H a decidir no S6/P4b.
    """
    back = decode(encode_hierarchical(KEY_ORDER_PROBE))
    assert back == KEY_ORDER_PROBE                      # semantica preservada
    assert [list(d) for d in back] == [list(d) for d in KEY_ORDER_EXPECTED_BACK]
    assert json.dumps(back) != json.dumps(KEY_ORDER_PROBE)   # byte-igualdade NAO


def test_geracao_deterministica():
    """Os casos sao seedados — duas geracoes = mesmos documentos (pins estaveis)."""
    a, b = gen_cases(), gen_cases()
    assert {k: v[2] for k, v in a.items()} == {k: v[2] for k, v in b.items()}

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
lab experiments/lab/dirty/2026-07/2026-07-17/2026-07-17-0014-sinteticos-controle-fluxo-hierarquia/,
que produz os .tcf inspecionaveis e a tabela de navegacao).
"""
from __future__ import annotations

import json

import pytest

from tcf import decode, encode
from tcf.hierarchical import _encode_hierarchical

from fixtures.control_synthetics_h import (
    KEY_ORDER_EXPECTED_BACK,
    KEY_ORDER_PROBE,
    decompose,
    gen_cases,
)

# (total, meta, controle, folhas, n_cols_controle) — medidos 2026-07-17 no weld P4a (suite 754).
# ADR-0024: o seq-RLE ganhou FLOOR (so' compacta se ENCOLHER). 6 casos
# DIMINUIRAM (c02/c03/c06/c07/c09/c12) porque em trechos sem cadencia o marcador `*N+d|`
# custava mais que as linhas cruas. Melhora pura -- nenhum pino subiu.
# RE-PIN 2026-08-28 (divergencia #6 da auditoria de consistencia, ADR-0024): coluna
# ESCALAR densa-com-nulos passou a declarar '?0:' (emask 2-estados) em vez de '?:'
# (mask 3-estados de campo opcional). +1 byte de META por coluna assim, controle e
# folhas byte-identicos: c05 842->843 e c12 1453->1454, os UNICOS dois casos com nulo
# denso. Motivo: a view distinguir tabela-com-nulos (consultavel) de ragged pelo header.
PINS = {
    "c01-uniforme":          (798,  30,   0,  768, 0),
    "c02-telemetria-array":  (3132, 26,   8, 3098, 1),
    "c03-telemetria-split":  (2830, 43,   0, 2787, 0),
    "c04-ragged":            (685,  31,  78,  576, 1),
    "c05-null-campo":        (843,  34,  90,  719, 1),
    "c06-null-elemento":     (1420, 40, 407,  973, 2),
    "c07-arrays-vazios":     (465,  25, 199,  241, 1),
    "c08-matriz":            (646,  27,  14,  605, 2),
    "c09-espinha":           (3218, 57, 237, 2924, 1),
    "c10-tipos-cadenciados": (1317, 34,   0, 1283, 0),
    "c11-categorico":        (1688, 21,   0, 1667, 0),
    "c12-compose-total":     (1454, 76, 434,  944, 5),
}

_CASES = gen_cases()


# Os 5 casos que sao TABELA RETANGULAR e que o ADR-0049 passou a rotear pro `#TCF.8R`.
# Eles nunca foram hierarquicos: eram tabelas planas que caiam no `.8H` porque era pra la'
# que uma lista de dicionarios ia. Continuam aqui, e continuam pinando a navegacao do `.8H`,
# porque o SUJEITO desta suite e' o fluxo `.8H` e nao a rota que o `encode` publico escolhe.
ROTEADOS_PRO_R = {
    "c01-uniforme": 436,
    "c03-telemetria-split": 1495,
    "c05-null-campo": 537,
    "c10-tipos-cadenciados": 423,
    "c11-categorico": 664,
}


@pytest.fixture(scope="module")
def wires():
    """A rota PUBLICA de cada caso, 1x por sessao (RT validado aqui mesmo).

    Depois do ADR-0049 nem todo caso sai em `.8H` por aqui: os retangulares saem em
    `#TCF.8R`. Este fixture e' o gate de ROUND-TRIP da rota que o usuario de fato pega.
    """
    out = {}
    for key, (_desc, _mec, docs) in _CASES.items():
        wire = encode(docs)
        assert decode(wire) == docs, f"RT falhou em {key}"
        out[key] = wire
    return out


@pytest.fixture(scope="module")
def wires_h():
    """O wire `.8H` de cada caso, que e' o SUJEITO dos pinos de navegacao.

    Chama o encoder hierarquico direto porque a rota publica deixou de mandar os casos
    retangulares pra ca' (ADR-0049). Sem isso os pinos perderiam o objeto que medem: o
    `decompose` separa meta/controle/folhas, buckets que so' existem no `.8H`.
    """
    out = {}
    for key, (_desc, _mec, docs) in _CASES.items():
        wire = _encode_hierarchical(docs)
        assert decode(wire) == docs, f"RT .8H falhou em {key}"
        out[key] = wire
    return out


def test_retangulares_agora_roteiam_pro_r_e_encolhem(wires):
    """ADR-0049: os casos que sao TABELA saem do `.8H` e ganham o `min()` por coluna.

    Pina os dois lados da mudanca. Os retangulares mudam de familia e encolhem; os
    genuinamente hierarquicos (aninhado, ragged, array) ficam BYTE-IDENTICOS ao que ja'
    emitiam, que e' a prova de que a solda nao vazou pra fora do seu escopo.
    """
    for key, esperado in ROTEADOS_PRO_R.items():
        assert wires[key].startswith("#TCF.8R"), f"{key} deveria rotear pro .8R"
        assert len(wires[key].encode("utf-8")) == esperado, (
            f"{key}: {len(wires[key].encode('utf-8'))} B, pino {esperado} B (ADR-0024)")
        assert len(wires[key].encode("utf-8")) < PINS[key][0], (
            f"{key}: rotear deveria encolher, e nao encolheu")
    for key in PINS:
        if key in ROTEADOS_PRO_R:
            continue
        assert wires[key].startswith("#TCF.8H"), f"{key} deveria continuar no .8H"
        assert len(wires[key].encode("utf-8")) == PINS[key][0], (
            f"{key}: caso hierarquico mudou de tamanho, a solda vazou")


@pytest.mark.parametrize("key", list(PINS))
def test_navegacao_pinada(wires_h, key):
    """Buckets byte-exatos por caso — o pino de comportamento do fluxo."""
    d = decompose(wires_h[key])
    got = (d["total"], d["meta"], d["controle"], d["folhas"], d["n_cols_controle"])
    assert got == PINS[key], (
        f"{key}: navegacao mudou {PINS[key]} -> {got}. Se a mudanca de representacao "
        f"foi CONSCIENTE, re-pinar com investigacao (ADR-0024); senao, regressao de fluxo.")


def test_uniforme_nao_paga_controle(wires_h):
    """Principio 'nao expandir o obvio': campo sempre-presente/nunca-null nao tem mask."""
    assert decompose(wires_h["c01-uniforme"])["n_cols_controle"] == 0


def test_counts_uniformes_colapsam(wires_h):
    """Fan-out fixo: a coluna de count de 200 instancias colapsa em poucos bytes (RLE)."""
    cols = {(p, k): b for p, k, b in decompose(wires_h["c02-telemetria-array"])["cols"]}
    assert cols[("v", "count")] <= 10   # medido 8 B para 200 instancias


def test_par_fanout_split(wires_h):
    """H-HIER-FANOUT-SPLIT-01, par de controle: MESMOS dados, array vs campos irmaos.

    Com serie realista (random-walk) o split ganha ~9.5%; com folhas de baixa
    entropia o ganho e' muito maior (ver revisao 2026-07-16 §2.2c: 96.5% do wire
    em folhas no caso constante). O pino aqui e' o SINAL (split < array), nao o
    tamanho do ganho.
    """
    array = decompose(wires_h["c02-telemetria-array"])["total"]
    split = decompose(wires_h["c03-telemetria-split"])["total"]
    assert split < array


def test_sintoma_emask_densa(wires_h):
    """H-HIER-EMASK-SPARSE-01: null esparso em elemento liga emask O(total-elementos).

    Pino do SINTOMA (controle >= 25% do wire) — se um dia a emask ficar
    por-instancia/esparsa, este teste avisa para re-pinar PINS junto.
    """
    d = decompose(wires_h["c06-null-elemento"])
    assert d["controle"] * 4 >= d["total"]


def test_ordem_de_chaves_schema_order_e_CANONICA():
    """BORDA 2 — DECIDIDA 2026-07-17 (owner: "fechar as duas bordas").

    DECISAO: no `.8H` a ordem de chaves e' a do SCHEMA (uniao por 1a aparicao) — CANONICA,
    nao um bug. Fundamento: (a) o `.8H` e' um codec COLUNAR-shredded — como Arrow/Parquet, as
    colunas sao COMPARTILHADAS entre registros, entao ordem por-registro e' inexpressivel por
    construcao; (b) JSON/ECMA-404: "does not assign any significance to the ordering of
    name/value pairs" — ordem de chave NAO e' significativa; (c) dict-equality (a igualdade
    SEMANTICA) e' sempre preservada. So' a byte-ordem de um json.dumps re-serializado pode
    diferir, o que a RFC PERMITE. Quem precisa de byte-ordem por-registro usa outra camada
    (o modelo S0 do DatasetH preserva preorder; o flat/adaptador tambem). NAO e' gap de
    capacidade — e' propriedade declarada do contrato colunar.
    """
    back = decode(encode(KEY_ORDER_PROBE))
    assert back == KEY_ORDER_PROBE                      # semantica (dict) preservada — SEMPRE
    assert [list(d) for d in back] == [list(d) for d in KEY_ORDER_EXPECTED_BACK]  # ordem = schema
    assert json.dumps(back) != json.dumps(KEY_ORDER_PROBE)   # byte-ordem difere (RFC permite)


def test_borda1_contagem_vazio_fail_loud_que_ensina():
    """BORDA 1 — DECIDIDA 2026-07-17 (RATIFICAR): objeto cujas folhas sao TODAS objetos-vazios
    nao tem coluna p/ contar registros (problema B). Fail-loud que ENSINA o workaround; a
    representacao plena (schema-declare/registro-'0') e' O-FMT-20 (armazenamento, pre-1.0)."""
    from tcf.hierarchical import HierarchicalError
    for degenerado in ({"a": {}}, {"a": {}, "b": {}}, [{"a": {}}], [{"a": {}}, {"a": {}}],
                       {"a": {"b": {}}}):
        with pytest.raises(HierarchicalError, match="contagem-vazio|folhas s.o objetos-vazios"):
            encode(degenerado)


def test_borda1_workarounds_funcionam():
    """A assimetria e' declarada: campo array-vazio funciona (count e' coluna); campo real
    junto resolve; ragged vazio-depois-cheio resolve. So' o all-empty-object e' fail-loud."""
    for ok in ({"a": []}, {"a": [], "b": []}, [{"a": []}], {"a": {}, "b": 1},
               [{"a": {}}, {"a": {"x": 1}}]):
        assert decode(encode(ok)) == ok


def test_geracao_deterministica():
    """Os casos sao seedados — duas geracoes = mesmos documentos (pins estaveis)."""
    a, b = gen_cases(), gen_cases()
    assert {k: v[2] for k, v in a.items()} == {k: v[2] for k, v in b.items()}

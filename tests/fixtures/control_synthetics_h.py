"""Sinteticos de CONTROLE do fluxo hierarquico (.8H) — fonte unica.

12 casos, cada um isolando UM mecanismo do fluxo (mask, counts, emask, seq-RLE,
refs, framing, tipos). Proposito: observar a NAVEGACAO do fluxo (pra onde os
bytes vao; quais mecanismos disparam), nao ganhar bytes. Vies declarado:
sinteticos de design construidos pra observacao, com valores realistas e seed
fixa (geracao deterministica).

Consumidores:
  - tests/test_hierarchical_control_synthetics.py (pins de comportamento)
  - experiments/lab/dirty/2026-07-17-0014-sinteticos-controle-fluxo-hierarquia/

decompose() usa _parse_meta (interno, LEITURA diagnostica apenas): a regra de
classificacao controle/dado e' a MESMA do decode do core (mask | count* | emask*).
"""
from __future__ import annotations

import random

SEED = 20260717

_NOMES = ["Ana Souza", "Bruno Lima", "Carla Mota", "Diego Alves", "Elisa Prado",
          "Fabio Nunes", "Gilda Ramos", "Hugo Teles", "Iara Campos", "Jonas Dias",
          "Karen Melo", "Lucas Viana"]
_CIDADES = ["Curitiba", "Recife", "Manaus", "Niteroi", "Santos"]
_TAGS = ["urgente", "fiscal", "revisado", "interno", "cliente"]
_STATUS = ["ativo", "inativo", "pendente"]
_UFS = ["PR", "SP", "AM", "RJ", "PE"]
_OBS = ["reentrega", "aguardando doc", "ok", "verificar cadastro"]


def _telemetria(rng, n=200):
    """Leituras com deriva (random walk) — mesma serie alimenta C02 e C03."""
    temp, hum, pres = 21.0, 58.0, 1013.0
    out = []
    for i in range(n):
        temp = round(temp + rng.uniform(-0.4, 0.4), 1)
        hum = round(hum + rng.uniform(-1.0, 1.0), 1)
        pres = round(pres + rng.uniform(-0.6, 0.6), 1)
        out.append((1700000000 + i * 60, temp, hum, pres))
    return out


def gen_cases() -> dict:
    """{chave: (descricao, mecanismo_alvo, docs)} — ordem estavel, geracao deterministica."""
    rng = random.Random(SEED)
    leituras = _telemetria(rng)
    cases: dict[str, tuple[str, str, list]] = {}

    cases["c01-uniforme"] = (
        "baseline flat-like: todo campo presente, sem arrays",
        "zero colunas de controle (mask so' quando opcional/null)",
        [{"id": i + 1, "nome": _NOMES[i % 12], "cidade": _CIDADES[i % 5]} for i in range(100)])

    cases["c02-telemetria-array"] = (
        "fan-out FIXO 3 como array (fraqueza conhecida: folha periodica)",
        "counts colapsam; folhas periodicas NAO colapsam (seq-RLE e' adjacente)",
        [{"t": t, "v": [a, b, c]} for t, a, b, c in leituras])

    cases["c03-telemetria-split"] = (
        "MESMOS dados do c02 como 3 campos irmaos (par de controle do fan-out-split)",
        "cada serie vira coluna propria -> L1 ve a deriva por coluna",
        [{"t": t, "temp": a, "hum": b, "pres": c} for t, a, b, c in leituras])

    cases["c04-ragged"] = (
        "campo opcional presente em ~10% (P1)",
        "mask 2-estados com runs longas de '-' -> RLE colapsa",
        [{"id": i + 1, "nome": _NOMES[i % 12],
          **({"obs": _OBS[i % 4]} if rng.random() < 0.10 else {})} for i in range(120)])

    cases["c05-null-campo"] = (
        "campo com ~8% null (P3a)",
        "mask 3-estados; '0' esparso quebra runs da mask",
        [{"id": i + 1, "nome": _NOMES[i % 12],
          "email": (None if rng.random() < 0.08 else f"user{i}@mail.com")} for i in range(120)])

    cases["c06-null-elemento"] = (
        "null esparso EM ELEMENTO (~15%, nao-adjacente) — sintoma da emask densa",
        "1 null liga emask O(total-elementos); padrao esparso nao colapsa",
        [{"id": i + 1,
          "leituras": [(None if rng.random() < 0.15 else round(20 + rng.random() * 5, 1))
                       for _ in range(rng.randint(3, 5))]} for i in range(60)])

    cases["c07-arrays-vazios"] = (
        "60% arrays vazios (repeticao de vazio ESTRUTURAL)",
        "count \\0 em runs -> RLE colapsa; body de dados minimo",
        [{"id": i + 1,
          "tags": ([] if rng.random() < 0.60 else
                   rng.sample(_TAGS, rng.randint(1, 3)))} for i in range(100)])

    cases["c08-matriz"] = (
        "matriz 2x2 regular por registro (P4a raso)",
        "counts de 2 niveis, ambos constantes -> colapsam",
        [{"grade": [[i, i + 1], [i + 2, i + 3]]} for i in range(40)])

    cases["c09-espinha"] = (
        "1:N classico com fan-out VARIAVEL 0..4 (espinha TPC-H-like)",
        "counts variaveis (nao colapsam inteiros) + folhas de filho densas",
        [{"id": i + 1, "nome": _NOMES[i % 12],
          "pedidos": [{"num": f"P{i:03d}-{j}", "valor": round(50 + rng.random() * 900, 2)}
                      for j in range(rng.randint(0, 4))]} for i in range(80)])

    cases["c10-tipos-cadenciados"] = (
        "int sequencial + bool quase-constante + float cadenciado (P2 x seq-RLE)",
        "seq-RLE deve pegar as 3 colunas tipadas",
        [{"seq": i, "ok": (i % 7 != 0), "temp": round(20.0 + i * 0.5, 1)} for i in range(150)])

    cases["c11-categorico"] = (
        "2 colunas categoricas repetitivas (dict/refs do L1)",
        "refs/aliases dominam; folhas ~O(cardinalidade), nao O(N)",
        [{"status": _STATUS[rng.randrange(3)], "uf": _UFS[rng.randrange(5)]} for i in range(300)])

    # NOTA (achado 2026-07-17): campo opcional vai por ULTIMO de proposito — o .8H devolve
    # chaves na ordem do SCHEMA (uniao por 1a aparicao), nao na ordem por-registro; com a
    # chave opcional no fim, ordem-por-registro == ordem-do-schema e o roundtrip fica
    # byte-diffavel. O comportamento em si e' pinado a parte (KEY_ORDER_PROBE).
    cases["c12-compose-total"] = (
        "P1+P2+P3a+P3b+P4a juntos, moderado",
        "todos os mecanismos ao mesmo tempo (integracao)",
        [{"id": i + 1, "nome": _NOMES[i % 12],
          "email": (None if rng.random() < 0.1 else f"c{i}@mail.com"),
          "m": [[i, (None if rng.random() < 0.2 else i + 1)], [i + 2]],
          "ok": (i % 3 != 0),
          **({"obs": _OBS[i % 4]} if rng.random() < 0.2 else {})} for i in range(40)])

    return cases


# Fronteira OBSERVADA (2026-07-17, achado da suite de controle): chave opcional que
# aparece pela 1a vez DEPOIS do 1o registro volta ao FIM do dict (ordem do schema),
# nao na posicao original. Igualdade semantica (dict) preservada; byte-igualdade JSON
# do dump NAO. Pinado em tests/test_hierarchical_control_synthetics.py; registro em
# T-API-BOUNDARY-CONTRACTS + T-CODE-TCF8H-JSON-PARITY. NAO "consertar" sem decisao de
# contrato do owner (ordem por-registro custaria wire; contrato S0 do DatasetH preserva).
KEY_ORDER_PROBE = [{"a": "1", "c": "x"}, {"a": "2", "obs": "o", "c": "y"}]
KEY_ORDER_EXPECTED_BACK = [{"a": "1", "c": "x"}, {"a": "2", "c": "y", "obs": "o"}]


def decompose(wire: str) -> dict:
    """Decompoe um wire .8H em buckets: meta / controle / folhas (bytes).

    Classificacao IDENTICA a do decode do core: kind mask | count* | emask* =
    controle; resto = dado (folhas). Sizes vem do proprio header; a soma tem
    de bater com o corpo inteiro (mesma exaustao que o decode exige).
    """
    from tcf.hierarchical import MAGIC, _parse_meta

    line1 = wire.split("\n", 1)[0]
    _schema, order = _parse_meta(line1[len(MAGIC):])
    raw = wire[len(line1) + 1:].encode("utf-8")
    meta_b = len(line1.encode("utf-8")) + 1                      # header + \n
    buckets = {"meta": meta_b, "controle": 0, "folhas": 0}
    per_col = []
    off = 0
    for path, kind, size in order:
        b = size if size is not None else len(raw) - off
        off += b
        is_ctrl = kind == "mask" or kind.startswith("count") or kind.startswith("emask")
        buckets["controle" if is_ctrl else "folhas"] += b
        per_col.append(("/".join(path) or "<raiz>", kind, b))
    assert off == len(raw), f"decomposicao nao exauriu o corpo ({off}/{len(raw)})"
    total = len(wire.encode("utf-8"))
    assert meta_b + buckets["controle"] + buckets["folhas"] == total
    return {"total": total, **buckets,
            "n_cols_controle": sum(1 for _, k, _b in per_col
                                   if k == "mask" or k.startswith(("count", "emask"))),
            "cols": per_col}

"""Testes do gadget tcf_lazy (view lazy/consultável sobre blob TCF).

Gadget auxiliar em scripts/tcf_lazy/ (não TCF-CORE; lê #TCF.7, não toca src/tcf).
"""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from tcf import encode, decode            # noqa: E402
from tcf_lazy import view                 # noqa: E402


TABLE = {
    "cliente": ["Ana", "Bruno", "Carla", "Diego", "Ana", "Bruno"],
    "cidade":  ["Sao Paulo", "Sao Paulo", "Rio de Janeiro",
                "Sao Paulo", "Rio de Janeiro", "Sao Paulo"],
    "plano":   ["Premium", "Basic", "Premium", "Premium", "Basic", "Premium"],
    "valor":   ["120", "80", "200", "120", "80", "150"],
}


@pytest.fixture
def blob():
    return encode(TABLE)


def test_columns_e_nrows(blob):
    v = view(blob)
    assert v.columns == list(TABLE)
    assert v.nrows == 6


def test_count_total(blob):
    assert view(blob).count() == 6


def test_agregadores_globais(blob):
    v = view(blob)
    assert v.sum("valor") == 750.0
    assert v.min("valor") == 80.0
    assert v.max("valor") == 200.0
    assert v.avg("valor") == 125.0


def test_filtro_mais_agregacao(blob):
    v = view(blob)
    f = v.where("cidade", "Sao Paulo")
    assert f.count() == 4
    assert f.sum("valor") == 470.0          # 120+80+120+150
    assert f.avg("valor") == 117.5


def test_alinhamento_de_linha(blob):
    # where em cidade -> índices; select traz a MESMA linha em outra coluna
    rows = view(blob).where("cidade", "Rio de Janeiro").select(["cliente", "valor"])
    assert rows == [{"cliente": "Carla", "valor": "200"},
                    {"cliente": "Ana", "valor": "80"}]


def test_filtro_encadeado_and(blob):
    f = view(blob).where("cidade", "Sao Paulo").where("plano", "Premium")
    assert f.count() == 3                    # Ana, Diego, Bruno(150)
    assert f.sum("valor") == 390.0           # 120+120+150


def test_filtro_por_predicado(blob):
    f = view(blob).where("valor", pred=lambda x: int(x) >= 120)
    assert sorted(f.indices) == [0, 2, 3, 5]
    assert f.count() == 4


def test_seletividade_count_toca_uma_coluna(blob):
    v = view(blob)
    v.count()
    rep = v.report()
    assert len(rep["touched"]) == 1          # count toca só a coluna mais barata
    assert rep["n_cols"] == 4


def test_seletividade_filtro_agrega_duas(blob):
    v = view(blob)
    v.where("cidade", "Sao Paulo").sum("valor")
    rep = v.report()
    assert set(rep["touched"]) == {"cidade", "valor"}   # nunca tocou cliente/plano
    assert rep["materialized_bytes"] < rep["total_bytes"]


def test_correto_vs_decode_completo(blob):
    # a soma via lazy bate com a soma via decode() completo
    full = decode(blob)
    esperado = sum(float(x) for x in full["valor"])
    assert view(blob).sum("valor") == esperado


def test_nao_numerico_erra(blob):
    with pytest.raises(ValueError):
        view(blob).sum("cliente")            # "Ana" não é número


def test_vazios_sao_ignorados():
    t = {"id": ["1", "2", "3"], "v": ["10", "", "30"]}
    v = view(encode(t))
    assert v.sum("v") == 40.0                 # ignora o vazio
    assert v.avg("v") == 20.0                 # média sobre 2 valores


def test_coluna_inexistente(blob):
    with pytest.raises(KeyError):
        view(blob).sum("inexistente")


# --- L3: contar/agrupar sem expandir (via dict/raw) ---

def test_tem_coluna_dict(blob):
    # garante que o caminho estrutural (dicionario @) e' exercido neste fixture
    assert "dict" in view(blob)._mode.values()


def test_nrows_estrutural(blob):
    assert view(blob).nrows == 6


def test_group_count_cidade(blob):
    assert view(blob).group_count("cidade") == {"Sao Paulo": 4, "Rio de Janeiro": 2}


def test_group_count_correto_vs_decode(blob):
    full = decode(blob)
    for c in view(blob).columns:
        assert view(blob).group_count(c) == dict(Counter(full[c]))

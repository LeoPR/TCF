"""As amostras do EXP-019, todas pelo Shaper, todas estratificadas.

Oito tabelas de OITO fontes reais diferentes. A escolha nao e' por conveniencia: o que o
experimento verifica e' CONSISTENCIA, e consistencia so' se testa contra variedade. Cada
amostra traz uma forma de coluna que as outras nao tem.

A estratificacao e' obrigatoria (regra do projeto): amostra honesta pede representatividade,
dimensionamento e distribuicao, e o `Shaper` responde os tres e ainda grava as metricas
(TVD/JSD/Hellinger/chi2) no trace, que este lab persiste em `intermediates/`.
"""
from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[4]
for _p in ("src", "scripts"):
    _q = str(RAIZ / _p)
    if _q not in sys.path:
        sys.path.insert(0, _q)

from shaper import ShapeRequest, Shaper  # noqa: E402

VOLUME = 800
SEED = 42

# (rotulo, dataset, tabela, coluna de estrato, o que esta amostra traz de proprio)
AMOSTRAS = [
    ("adult-census", "adult-census", "adult", "education",
     "15 colunas, mistura de int e categorico de baixa cardinalidade, o classico de ML"),
    ("online-retail", "online-retail", "online_retail", "Country",
     "texto livre em Description, float de preco, e a cauda longa de 38 paises"),
    ("ibge-municipios", "ibge-municipios", "municipios", "uf_sigla",
     "nomes proprios com acento, hierarquia geografica redundante (uf/meso/micro)"),
    ("br-identidades", "br-identidades", "pessoas", "uf_sigla",
     "documento formatado (CPF), email, data ISO: o territorio das natures"),
    ("tpch-orders", "tpch-sf001", "orders", "o_orderstatus",
     "chave alta cardinalidade + status de 3 valores, o par que o dict adora"),
    ("tpch-lineitem", "tpch-sf001", "lineitem", "l_returnflag",
     "16 colunas, a tabela mais larga do conjunto, muitos decimais"),
    ("receita-cnpj", "receita-cnpj", "estabelecimentos", "situacao",
     "dado publico real, nome fantasia com ruido de digitacao"),
    ("wine-quality", "wine-quality", "wine", "quality",
     "13 colunas TODAS numericas, float denso: o pior caso do dicionario"),
]


def carrega(rotulo: str):
    """Devolve `(linhas, trace)` de uma amostra estratificada. `linhas` e' `list[dict]`."""
    _, dataset, tabela, estrato = next(a[:4] for a in AMOSTRAS if a[0] == rotulo)
    res = Shaper().apply(ShapeRequest(
        dataset=dataset, volume=VOLUME, seed=SEED,
        stratify_by=estrato, schema=[tabela]))
    return res.tables[tabela], res.trace


def colunas(linhas: list[dict]) -> dict[str, list]:
    """A MESMA tabela na outra grafia: dict de colunas."""
    return {k: [r[k] for r in linhas] for k in linhas[0]}

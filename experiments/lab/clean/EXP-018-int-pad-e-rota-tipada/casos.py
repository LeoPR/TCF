"""Os casos do EXP-018: sintéticos controlados + as colunas REAIS que mais importam.

Cada caso declara o PIN (`espera`): quem deve vencer o FLOOR. Divergência é falha do lab,
não nota de rodapé — é assim que o pin serve para alguma coisa.

O corpus real vem congelado de `inputs/fontes/`, extraído dos hubs de `Z:` pelo lab dirty
`2026-08-14-0112`. Aqui entram as colunas onde o PAD ganhou e, deliberadamente, também
colunas onde ele **perde** — um lab que só mostra o caso favorável não prova nunca-pior.
"""
from __future__ import annotations

import json
import pathlib
import random

RAIZ = pathlib.Path(__file__).parent
FONTES = RAIZ / "inputs" / "fontes"
rnd = random.Random(20260814)
N = 600


def real(rotulo):
    """Coluna REAL congelada. `None` se a fatia não está no disco (o lab roda sem Z:)."""
    def _gen():
        p = FONTES / f"{rotulo}.json"
        if not p.exists():
            return None
        return json.loads(p.read_text(encoding="utf-8"))
    return _gen


# (nome, familia, gerador, ideia, espera: 'spec' | 'core')
CASOS = [
    # ── sintéticos: o mecanismo isolado ────────────────────────────────────────
    ("sint-progressao-largura-varia", "sintetico", lambda: list(range(1, N + 1)),
     "1..600: a largura varia (1->2->3 digitos) e quebra o marcador em 3", "spec"),
    ("sint-passo7", "sintetico", lambda: [i * 7 for i in range(N)],
     "passo 7: largura de 1 a 4 digitos", "spec"),
    ("sint-largura-ja-fixa", "sintetico", lambda: [100000 + i for i in range(N)],
     "largura JA' uniforme: o pad e' no-op, o `dimensiona` nem oferece", "core"),
    ("sint-cardinalidade-5", "sintetico",
     lambda: [rnd.choice([10, 20, 30, 40, 50]) for _ in range(N)],
     "k=5: territorio do bN, o pad nao tem o que ativar", "core"),
    ("sint-aleatorio-largura-varia", "sintetico",
     lambda: [rnd.randrange(1, 99999) for _ in range(N)],
     "largura varia mas NAO ha' progressao: o pad paga e nao ativa nada", "core"),
    ("sint-com-nulos", "sintetico",
     lambda: [None if i % 37 == 0 else i for i in range(1, N + 1)],
     "slots NULOS no meio da progressao — o null e' do tipo, nao da grafia", "spec"),
    ("sint-negativos", "sintetico",
     lambda: [rnd.randrange(-500, 501) for _ in range(N)],
     "com sinal: o spec RECUSA (format_mismatch) e o FLOOR fica no core", "core"),
    ("sint-quase-constante", "sintetico", lambda: [42] * (N - 3) + [43, 44, 45],
     "k=4 desbalanceado: o RLE do nucleo resolve", "core"),

    # ── reais: onde o PAD ganhou no corpus (lab 2026-08-14-0112) ──────────────
    ("real-tpch-orderkey", "real", real("tpch-sf001-orders-o-orderkey.natural"),
     "chave de pedido 1..12000: o maior ganho medido (2,73x)", "spec"),
    ("real-tpch-partkey", "real", real("tpch-sf001-part-p-partkey.natural"),
     "chave de peca 1..2000 (1,72x)", "spec"),
    ("real-tpch-custkey", "real", real("tpch-sf001-customer-c-custkey.natural"),
     "chave de cliente 1..1500 (1,69x)", "spec"),
    # PIN CORRIGIDO 2026-08-14: eu esperava `spec` por ser "progressao com repeticao" —
    # ERRADO, e a expectativa era minha, nao do codigo. Medido: k=744 em 3000, monotona
    # mas com TRES passos distintos (1,1,1,1,1,1,2,3...). A repeticao QUEBRA a progressao
    # limpa, o marcador aritmetico nao ativa, e o padding so' custaria. O core resolve com
    # `#TCF.8n!!`. Lição: monotonia NAO basta — o gatilho do PAD precisa de progressao
    # limpa, e o `dimensiona` acerta ao oferecer (larguras 1..4) mas o FLOOR recusa.
    ("real-tpch-lineitem-orderkey", "real", real("tpch-sf001-lineitem-l-orderkey.natural"),
     "chave REPETIDA (k=744 em 3000, 3 passos distintos): a repeticao quebra a "
     "progressao e o FLOOR recusa o pad", "core"),

    # ── reais: onde o PAD PERDE — a prova de nunca-pior que importa ───────────
    ("real-tpch-linenumber", "real", real("tpch-sf001-lineitem-l-linenumber.natural"),
     "k=7, largura 1: nada a padear, o bN domina", "core"),
    ("real-wine-quality", "real", real("wine-quality-wine-quality.natural"),
     "nota 3..9: k=7, largura 1", "core"),
    ("real-retail-quantity", "real", real("online-retail-online-retail-quantity.natural"),
     "quantidade com NEGATIVOS (-24..600): o spec recusa os negativos", "core"),
    ("real-ibge-municipio-id", "real", real("ibge-municipios-municipios-id.natural"),
     "id de municipio: 7 digitos uniformes, sem progressao", "core"),
    ("real-tpch-availqty", "real", real("tpch-sf001-partsupp-ps-availqty.natural"),
     "quantidade 4..9998: largura varia, sem progressao", "core"),
    ("real-tpch-nationkey", "real", real("tpch-sf001-customer-c-nationkey.natural"),
     "k=25, largura 1-2: baixa cardinalidade", "core"),
]

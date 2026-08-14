# -*- coding: utf-8 -*-
"""Os casos — sinteticos PARTICULARES primeiro (pedido do owner: "mais lentamente").

Cada sintetico existe para ver UM efeito, e vem com o par de contra-prova quando faz
sentido perguntar "quanto disso e' do mecanismo e quanto ja' era do nucleo?".

Os dados sinteticos sao **viesados por construcao** — escolhidos para ver comportamento,
nao para vencer benchmark. Os reais estao em `datasets-provenance.md`.
"""
from __future__ import annotations

import sqlite3

TERCO12 = round(1 / 3, 12)          # 0.333333333333


def _diz(p, q, d=12):
    return round(p / q, d)


# ── SINTETICOS — cada um com a ideia e, quando cabe, o PAR de contra-prova ────
SINTETICOS = [
    ("owner-sujo-no-meio",
     [0.2, 0.4, 0.6, 0.333333333, 0.8, 1.0, 0.2, 0.4, 0.6, 0.2],
     "O CASO DO OWNER, literal: coluna de 1 casa com um sujo de 9 casas no meio.",
     "par: owner-sem-o-sujo"),

    ("owner-sem-o-sujo",
     [0.2, 0.4, 0.6, 0.6, 0.8, 1.0, 0.2, 0.4, 0.6, 0.2],
     "CONTRA-PROVA do anterior: a MESMA coluna com o sujo trocado por um limpo. "
     "Isola quanto UM valor sujo custa hoje.",
     "par: owner-sujo-no-meio"),

    ("dizima-uniforme",
     [TERCO12] * 10,
     "10x a MESMA dizima. O RLE de linha identica ja' resolve — aqui o mecanismo "
     "deve ganhar POUCO. E' a contra-prova contra a leitura ingenua de 'grafia menor "
     "sempre da' wire menor'.",
     "par: dizima-variada"),

    ("dizima-variada",
     [_diz(*pq) for pq in [(1, 3), (2, 3), (1, 7), (1, 6), (5, 6),
                           (2, 7), (1, 9), (4, 9), (1, 11), (2, 11)]],
     "10 dizimas DIFERENTES. O nucleo nao tem repeticao de linha para comer; e' onde "
     "a grafia fracional teria folga.",
     "par: dizima-uniforme"),

    ("rateio-terco",
     [_diz(100, 3)] * 3 + [_diz(200, 3)] * 3,
     "O PARCELAMENTO do owner: 100 dividido em 3. Liga M1 (grafia) com M4 (soma "
     "preservada) no mesmo dado.",
     "usado tambem em M4"),

    ("money-2casas",
     [round(v, 2) for v in
      [12.9, 3.5, 47.25, 8.0, 129.99, 4.5, 63.7, 21.15, 9.99, 250.0,
       17.45, 6.3, 88.8, 33.33, 5.55, 41.2, 74.6, 2.99, 19.9, 105.5]],
     "Dinheiro limpo, 2 casas, valores NAO em progressao (de proposito: uma "
     "progressao viraria seq-RLE e mediria o nucleo, nao a escala).",
     "onde a escala pura ja' deveria funcionar"),

    ("money-com-terco",
     [round(v, 2) for v in
      [12.9, 3.5, 47.25, 8.0, 129.99, 4.5, 63.7, 21.15, 9.99, 250.0,
       17.45, 6.3, 88.8, 33.33, 5.55, 41.2, 74.6, 2.99, 19.9]] + [_diz(100, 3)],
     "CONTRA-PROVA de money-2casas: a mesma coluna com UMA dizima no fim. E' o caso "
     "do owner em escala de dinheiro — mede o que 1 valor em 20 faz com a escala pura.",
     "par: money-2casas"),
]

SINTETICOS_POR_NOME = [(n, v) for n, v, _, _ in SINTETICOS]

# ── BORDAS — os mecanismos RECUSAM o que devem recusar? ──────────────────────
# Herdadas do fechamento do float (2026-08-14-1616): as mesmas bordas, agora
# perguntando de M1/M3 em vez do nucleo.
BORDAS = [
    ("borda-cientifica", [1e-5, 2e-5, 3e-5], "grafia sem 'casas' — M1 deve recusar"),
    ("borda-subnormal", [5e-324, 1e-323],
     "limit_denominator(5e-324) devolve 0 — M1 deve recusar ANTES disso"),
    ("borda-zero-negativo", [-0.0, 0.0, 1.0], "`==` nao distingue; M1 nao pode mexer"),
    ("borda-max-float", [1.7976931348623157e308, 1e308], "escala estoura 2^53"),
    ("borda-precisao-suja", [0.1 + 0.2, 1 / 3, 2 / 3],
     "0.30000000000000004 NAO e' dizima: M1 deve recusar, M3 deve tratar como excecao"),
    ("borda-com-nulo", [TERCO12, None, _diz(2, 3)], "o slot nulo atravessa"),
    ("borda-inteiro-em-float", [3.0, 4.0, 5.0], "sem casas uteis — M1 recusa, M2 vence"),
    ("borda-uniao-int-float", [1, TERCO12, 3],
     "a tag-UNIAO `n`: M1 so' pode tocar no elemento float"),
]

# ── REAIS — preenchido pela varredura do corpus (Z:/tcf-data) ────────────────
# (db, tabela, coluna, sql, ideia). `None` em sql = SELECT simples.
REAIS = [
    ("wine-quality", "wine", "alcohol",
     "SELECT alcohol FROM wine WHERE alcohol IS NOT NULL",
     "O CASO QUE QUEBROU A ESCALA no fechamento do float: 6 valores de 13-14 casas "
     "(medias sujas do dataset) derrubam a coluna inteira. E' o R1 do owner em dado real."),
    ("wine-quality", "wine", "density",
     "SELECT density FROM wine WHERE density IS NOT NULL",
     "3-5 casas, entre 0.99 e 1.04. A coluna do PoC de junho (M4)."),
    ("online-retail", "online_retail", "UnitPrice",
     "SELECT UnitPrice FROM online_retail WHERE UnitPrice IS NOT NULL",
     "Money-like real: preco unitario. Onde uma SOMA tem sentido semantico (M4)."),
    ("tpch-sf001", "lineitem", "l_discount",
     "SELECT l_discount FROM lineitem", "2 casas, entre 0.00 e 0.10 — escala pura facil."),
    ("tpch-sf001", "lineitem", "l_extendedprice",
     "SELECT l_extendedprice FROM lineitem", "Money-like de maior magnitude."),
]

AMOSTRA_MAX = 2000


def carrega_real(db, sql, amostra=AMOSTRA_MAX):
    """Le do corpus em modo read-only. Amostra ESPALHADA (rowid % k), nunca LIMIT puro.

    LIMIT puro degenera a amostra — ja' custou uma conclusao invertida neste projeto
    (o retail com LIMIT 600 devolveu 1 data distinta).
    """
    try:
        con = sqlite3.connect(f"file:Z:/tcf-data/interim/{db}.db?mode=ro", uri=True)
    except Exception:
        return None
    try:
        vals = [r[0] for r in con.execute(sql)]
    except Exception:
        return None
    finally:
        con.close()
    vals = [v for v in vals if v is not None]
    if len(vals) > amostra:
        passo = len(vals) // amostra
        vals = vals[::passo][:amostra]
    return vals

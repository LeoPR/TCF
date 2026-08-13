"""Os casos de DATA a inspecionar. Progressao: ilustrativo -> realista -> bordas.

Cada caso: (nome, familia, gerador, a IDEIA que ele mostra).
Gerador devolve `None` = caso pulado (fonte ausente) — o lab tem de rodar sem `Z:`.
"""
from __future__ import annotations

import datetime as dt
import json
import pathlib
import random

RAIZ = pathlib.Path(__file__).parent
# corpus REAL ja' extraido de `Z:/tcf-data/` pelo EXP-017 (nao re-extrai, nao baixa nada).
# parents: [0]=<dia> [1]=<mes> [2]=dirty [3]=lab -> lab/clean/EXP-017/...
FONTES = RAIZ.parents[3] / "clean" / "EXP-017-data-alvos-mensais" / "inputs" / "fontes"

BASE = dt.date(2026, 1, 1)


def _iso(d):
    return d.isoformat()


def diaria(n, base=BASE):
    return [_iso(base + dt.timedelta(days=i)) for i in range(n)]


def passo(n, p, base=BASE):
    return [_iso(base + dt.timedelta(days=p * i)) for i in range(n)]


def uteis(n, base=BASE):
    """Dias UTEIS: o delta cicla 1,1,1,1,3 (sex->seg pula o fim de semana).

    E' o caso que o seq-RLE aritmetico NAO pega (passo nao e' constante) e o
    PERIODICO pega (ADR-0040) — a diferenca visivel entre as duas grafias.
    """
    out, d = [], base
    while len(out) < n:
        if d.weekday() < 5:
            out.append(_iso(d))
        d += dt.timedelta(days=1)
    return out


def primeiro_do_mes(n, base=BASE):
    """Dia 1 de cada mes: passo IRREGULAR (31,28,31,30…) — nem constante nem ciclo curto.

    Mostra o LIMITE dos dois marcadores: o ciclo real tem periodo 48 (4 anos
    bissextos) e o teto `MAX_PERIODO=24` (ADR-0040) o exclui de proposito.
    """
    out, y, m = [], base.year, base.month
    for _ in range(n):
        out.append(_iso(dt.date(y, m, 1)))
        m += 1
        if m > 12:
            m, y = 1, y + 1
    return out


def agrupada(n, tam=20):
    return [_iso(BASE + dt.timedelta(days=i // tam)) for i in range(n)]


def aleatoria(n, seed=20260813, span=4000):
    r = random.Random(seed)
    return [_iso(BASE + dt.timedelta(days=r.randrange(span))) for _ in range(n)]


def suja(n, pct, seed=7):
    vals = diaria(n)
    r = random.Random(seed)
    for _ in range(n * pct // 100):
        vals[r.randrange(n)] = r.choice(["31/12/2025", "", "sem data", "2026-13-45", "20260101"])
    return vals


def com_nulos(n, pct=10):
    vals = diaria(n)
    for i in range(0, n, max(1, 100 // pct)):
        vals[i] = None
    return vals


def real(rotulo):
    """Coluna REAL do corpus ja' extraido (EXP-017). None se a fonte nao esta' no disco."""
    def _gen():
        p = FONTES / f"{rotulo}.json"
        if not p.exists():
            return None
        return json.loads(p.read_text(encoding="utf-8"))
    return _gen


# ── (nome, familia, gerador, a IDEIA que o caso mostra) ─────────────────────────
CASOS = [
    # A — o MECANISMO: como a data vira ordinal e o ordinal vira marcador
    ("a1-diaria-600", "mecanismo", lambda: diaria(600),
     "passo constante +1: o ordinal colapsa no seq-RLE aritmetico `*N+1|ancora`"),
    ("a2-mensal-600", "mecanismo", lambda: passo(600, 30),
     "passo constante +30: pro seq-RLE da' o MESMO trabalho que +1 (o passo nao importa)"),
    ("a3-uteis-600", "mecanismo", lambda: uteis(600),
     "dias UTEIS: delta cicla 1,1,1,1,3 -> so' o marcador PERIODICO pega (ADR-0040)"),
    ("a4-quinzenal-400", "mecanismo", lambda: passo(400, 15),
     "quinzenal: outro passo constante, p/ ver que a grafia nao muda"),
    ("a5-primeiro-do-mes-240", "mecanismo", lambda: primeiro_do_mes(240),
     "dia 1 de cada mes: passo IRREGULAR (31,28,31,30…) — o LIMITE dos dois marcadores"),

    # B — o FLIP do FLOOR: a mudanca de HOJE (ADR-0041)
    ("b1-diaria-n10", "flip-do-floor", lambda: diaria(10),
     "N=10: a nature PERDE o FLOOR -> o encoder emite o CORE (sem `:dt`)"),
    ("b2-diaria-n11", "flip-do-floor", lambda: diaria(11),
     "N=11: a nature VENCE — o flip que o id curto comprou (com `:data-iso` perdia)"),
    ("b3-diaria-n12", "flip-do-floor", lambda: diaria(12),
     "N=12: ja' consolidado do lado da nature"),

    # C — bordas: onde o FLOOR RECUSA (a invariante nunca-pior)
    ("c1-agrupada-400", "borda", lambda: agrupada(400),
     "datas repetidas em blocos: o RLE do nucleo ja' resolve -> o FLOOR RECUSA a nature"),
    ("c2-aleatoria-300", "borda", lambda: aleatoria(300),
     "sem estrutura temporal: nao ha' progressao p/ o seq-RLE morder"),
    ("c3-suja-30pct-300", "borda", lambda: suja(300, 30),
     "30% de grafias nao-canonicas: cada uma vira LITERAL (`_`), RT byte-exato"),
    ("c4-com-nulos-300", "borda", lambda: com_nulos(300),
     "slots NULOS no meio da progressao (o None do core, nao string vazia)"),
    ("c5-n1", "borda", lambda: diaria(1),
     "N=1: nao ha' delta nenhum p/ observar"),
    ("c6-descendente-300", "borda", lambda: [_iso(BASE - dt.timedelta(days=i)) for i in range(300)],
     "progressao DESCENDENTE: o passo e' -1 (o sinal viaja no marcador)"),

    # F — REAIS (corpus ja' extraido de Z: pelo EXP-017; nao baixa nada)
    ("f1-tpch-orderdate", "real", real("tpch-orderdate.natural"),
     "TPC-H orderdate como vem do banco (nao ordenado): o caso comum de coluna de data"),
    ("f2-tpch-orderdate-ord", "real", real("tpch-orderdate.ordenado"),
     "a MESMA coluna ordenada: o que a ordem sozinha muda"),
    ("f3-tpch-shipdate", "real", real("tpch-shipdate.natural"), "TPC-H shipdate"),
    ("f4-tpch-commitdate", "real", real("tpch-commitdate.natural"), "TPC-H commitdate"),
    ("f5-tpch-receiptdate", "real", real("tpch-receiptdate.natural"), "TPC-H receiptdate"),
    ("f6-tpch-sf01-orderdate", "real", real("tpch-sf01-orderdate.natural"),
     "TPC-H sf01 (escala maior)"),
    ("f7-br-cadastro", "real", real("br-data-cadastro.natural"), "br-identidades: data de cadastro"),
    ("f8-br-abertura", "real", real("br-data-abertura.natural"), "br-identidades: data de abertura"),
    ("f9-receita-inicio", "real", real("receita-data-inicio.natural"),
     "Receita: data de inicio de atividade (CNPJ real)"),
    ("f10-retail-invoicedate", "real", real("retail-invoicedate.natural"),
     "retail: data de fatura (muitas repeticoes por dia)"),
    ("f11-football-date", "real", real("football-date.natural"), "football: data de partida"),
    ("f12-receita-inicio-ord", "real", real("receita-data-inicio.ordenado"),
     "Receita ordenada: onde a progressao aparece"),
]

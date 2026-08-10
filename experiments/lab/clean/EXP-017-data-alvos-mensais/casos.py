"""Catálogo de casos — declarativo e auto-verificável (molde do EXP-016).

Cada caso declara **o que se espera antes de rodar**. O lab não descreve o que aconteceu:
afirma o que deve acontecer e falha quando não acontece.

    nome      identificador estável (vira nome de arquivo em outputs/)
    familia   agrupamento para o relatório
    fonte     'real:<arquivo em inputs/>' ou gerador determinístico
    porque    por que este caso existe — o que ele exerce/ataca
    espera    qual alvo deve VENCER o FLOOR:
                'ordinal'  o spec soldado (A1) ganha
                'mensal'   um dos alvos mensais (A4/A2f/YM) ganha
                'nenhum'   todos perdem do core sozinho — a válvula/FLOOR protege
                'qualquer' só nos casos em que a decisão não é o ponto

`espera` é um PIN, não uma descrição: quando um ticket mover a fronteira de propósito,
o lab quebra — que é o ponto.

**Os PINs dos casos reais foram fixados no que de fato acontece** (disciplina do EXP-016:
um caso `'qualquer'` não prova nada sobre o FLOOR — vira teste de RT com nome de teste de
decisão). Sobra `'qualquer'` em 1 caso só, e por construção.
"""
from __future__ import annotations

import calendar
import datetime as _dt
import hashlib
import json
import pathlib

INPUTS = pathlib.Path(__file__).parent / "inputs"
B = _dt.date(2026, 1, 1)


def _rnd(i, mod, salt=""):
    return int.from_bytes(hashlib.sha256(f"{salt}:{i}".encode()).digest()[:4], "big") % mod


# ─────────────────────────── geradores sintéticos ───────────────────────────

def mensal(n=600, dia=1):
    out, y, m = [], 2000, 1
    for _ in range(n):
        ult = calendar.monthrange(y, m)[1]
        d = ult if dia == "fim" else min(dia, ult)
        out.append(_dt.date(y, m, d).isoformat())
        m += 1
        if m == 13:
            m, y = 1, y + 1
    return out


def mensal_faltas(n=600):
    out, y, m, k = [], 2000, 1, 0
    while len(out) < n:
        k += 1
        if k % 7 != 0:
            out.append(_dt.date(y, m, 1).isoformat())
        m += 1
        if m == 13:
            m, y = 1, y + 1
    return out


def trimestral(n=400):
    out, y, m = [], 2000, 1
    for _ in range(n):
        out.append(_dt.date(y, m, 1).isoformat())
        m += 3
        while m > 12:
            m -= 12
            y += 1
    return out


def ano_mes(n=600):
    out, y, m = [], 2000, 1
    for _ in range(n):
        out.append(f"{y:04d}-{m:02d}")
        m += 1
        if m == 13:
            m, y = 1, y + 1
    return out


def diario(n=600):
    return [(B + _dt.timedelta(days=i)).isoformat() for i in range(n)]


def uteis(n=600):
    out, d = [], B
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d.isoformat())
        d += _dt.timedelta(days=1)
    return out


def mensal_sujo(n=600, pct=5):
    vals = mensal(n)
    for i in range(max(1, n * pct // 100)):
        vals[_rnd(i, n, "sujo")] = "s/d"
    return vals


def mensal_sujo_inicio(n=600):
    """UMA sujeira no indice 3 — dentro da janela de 20 do pre-pass (T-PENHASCO-INICIO)."""
    vals = mensal(n)
    vals[3] = "s/d"
    return vals


def mensal_com_null(n=600):
    vals = mensal(n)
    for i in (7, 100, 355, 599):
        vals[i] = None
    return vals


def misto_d01_d15(n=600):
    a, b = mensal(n // 2, 1), mensal(n // 2, 15)
    return [v for par in zip(a, b) for v in par]


def espalhado(n=600):
    ds, d = [], B
    for i in range(n):
        d += _dt.timedelta(days=_rnd(i, 40, "esp") + 1)
        ds.append(d.isoformat())
    return ds


def _real(arq):
    def _carrega():
        p = INPUTS / "fontes" / arq
        if not p.exists():
            return None
        return json.loads(p.read_text(encoding="utf-8"))
    return _carrega


# ─────────────────────────────── o catálogo ───────────────────────────────
# (nome, familia, gerador, porque, espera)

CASOS = [
    # ── SINTÉTICOS: o que o lab dirty 1853 mediu, agora pinado ──
    ("sint-mensal-dia1", "sintetico-mensal", lambda: mensal(600, 1),
     "o regime canônico do alvo mensal: dia constante, delta 28-31 no eixo do dia", "mensal"),
    ("sint-mensal-dia15", "sintetico-mensal", lambda: mensal(600, 15),
     "dia constante != 1: só o A4 (sem convenção) cobre", "mensal"),
    ("sint-mensal-fim", "sintetico-mensal", lambda: mensal(600, "fim"),
     "fecho contábil: o dia VARIA e é dedutível — o único caso do A2f", "mensal"),
    ("sint-mensal-faltas", "sintetico-mensal", mensal_faltas,
     "competência sem fato: mês pulado. No eixo do dia o spec recusa a coluna", "mensal"),
    ("sint-trimestral", "sintetico-mensal", trimestral,
     "passo de 3 meses: delta uniforme no eixo do mês", "mensal"),
    ("sint-ano-mes", "sintetico-mensal", ano_mes,
     "grafia YYYY-MM pura: o spec ISO recusa (não é data completa)", "mensal"),
    ("sint-misto-d01-d15", "sintetico-mensal", misto_d01_d15,
     "dois dias alternando: vira período 2 no eixo do mês", "mensal"),
    # ── CONTROLES: onde o mensal NÃO pode ganhar ──
    ("ctrl-diario", "controle", diario,
     "o ordinal-dia é ótimo aqui; se o mensal ganhar, algo está errado", "ordinal"),
    ("ctrl-uteis", "controle", uteis,
     "cadência de dias úteis: território do periódico no eixo do DIA", "ordinal"),
    ("ctrl-espalhado", "controle", espalhado,
     "passo irregular de 1-40 dias: nenhum eixo uniformiza", "ordinal"),
    # ── VÁLVULA: dado que não casa ──
    ("valv-mensal-sujo-5pct", "valvula", mensal_sujo,
     "5% de 's/d': a válvula segura. ATENÇÃO (caçada adversarial): o resultado é "
     "BIMODAL por semente — em 12 sementes o core vence 8; esta semente é do lado "
     "favorável. O pin fixa ESTA semente; a bimodalidade é o T-PENHASCO-INICIO", "mensal"),
    ("valv-sujeira-no-inicio", "valvula", lambda: mensal_sujo_inicio(),
     "UMA sujeira no índice 3 (<20): o penhasco do pre-pass (analyze_column "
     "sample_size=20 + Regra 2 do auto_cadence) — 95x decidido pela POSIÇÃO da "
     "primeira exceção; atinge o ordinal soldado igual", "qualquer"),
    ("valv-ym-unicode", "valvula", lambda: ano_mes(597) + ["２０００-０１", "٢٠٠٠-٠١", "2000-01"],
     "dígitos Unicode (fullwidth/árabe): `isdigit()`/`int()` os ACEITAM — sem o guard de "
     "re-emissão o payload colapsava grafias distintas (caçada adversarial, 4ª ocorrência "
     "da classe). Com o guard: viram literal e o RT fecha", "mensal"),
    ("valv-mensal-null", "valvula", mensal_com_null,
     "None no meio: passa pelo slot 0, fora do alvo", "mensal"),
    # ── REAIS: o que o lab dirty NÃO tinha ──
    ("real-tpch-orderdate-nat", "real-tpch", _real("tpch-orderdate.natural.json"),
     "TPC-H orders na ordem de armazenamento: data comercial, k alto", "ordinal"),
    ("real-tpch-orderdate-ord", "real-tpch", _real("tpch-orderdate.ordenado.json"),
     "a MESMA coluna ordenada: isola o efeito da ordem", "mensal"),
    ("real-tpch-shipdate-nat", "real-tpch", _real("tpch-shipdate.natural.json"),
     "lineitem embarque: a coluna de data mais medida do projeto", "ordinal"),
    ("real-tpch-shipdate-ord", "real-tpch", _real("tpch-shipdate.ordenado.json"),
     "idem ordenada", "ordinal"),
    ("real-tpch-commitdate-ord", "real-tpch", _real("tpch-commitdate.ordenado.json"),
     "coluna irmã (H7 da triagem morreu, mas a coluna sozinha vale medir)", "ordinal"),
    ("real-tpch-receiptdate-ord", "real-tpch", _real("tpch-receiptdate.ordenado.json"),
     "terceira irmã", "ordinal"),
    ("real-tpch-sf01-orderdate-ord", "real-tpch", _real("tpch-sf01-orderdate.ordenado.json"),
     "amostra DISTINTA da mesma fonte (OFFSET 90000 — a cacada pegou que LIMIT puro "
     "duplicava o sf001 byte a byte: dbgen deterministico). O A4 vence por 14 B em "
     "12.612 (0,1%): acidente estrutural do payload, NAO regime mensal — a coluna tem "
     "31 dias-do-mes uniformes", "mensal"),
    ("real-br-cadastro-nat", "real-br", _real("br-data-cadastro.natural.json"),
     "cadastro BR na ordem natural: k alto, span curto", "ordinal"),
    ("real-br-cadastro-ord", "real-br", _real("br-data-cadastro.ordenado.json"),
     "idem ordenada", "ordinal"),
    ("real-br-abertura-ord", "real-br", _real("br-data-abertura.ordenado.json"),
     "abertura de empresas: span longo", "ordinal"),
    ("real-receita-yyyymmdd", "real-grafia", _real("receita-data-inicio.natural.json"),
     "YYYYMMDD COMPACTO: o spec ISO recusa por design (guard de re-emissão)", "nenhum"),
    ("real-retail-datetime", "real-grafia", _real("retail-invoicedate.natural.json"),
     "DATETIME com hora: não é date puro — a válvula tem de segurar tudo", "nenhum"),
    ("real-football", "real-span", _real("football-date.natural.json"),
     "1872..hoje: o maior span do corpus; ja' ordenado na origem (a variante .ordenado "
     "e' byte-identica — cacada adversarial, md5)", "ordinal"),
]

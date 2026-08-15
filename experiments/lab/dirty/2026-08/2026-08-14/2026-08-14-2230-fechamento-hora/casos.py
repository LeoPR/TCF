# -*- coding: utf-8 -*-
"""Os casos do fechamento da HORA.

O owner pediu explicitamente os sintéticos:

> *"precisamos fazer testes sintéticos porque campos com hora existem, mas concordo que se não
> é comum, podemos deixar pro fim."*

Eles existem porque o corpus **não tem** hora pura — a avaliação de 2026-08-14 varreu todos os
bancos e achou UMA coluna com hora, e ela é datetime. Então os regimes onde a hora tem
comportamento próprio (telemetria, batimento, expediente) precisam ser construídos.

**Viés declarado**: sintético é viesado por construção. Cada regime existe para ver UM
comportamento, e vem com o par de contra-prova quando faz sentido perguntar "quanto disso é do
mecanismo e quanto o núcleo já fazia?".
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, time, timedelta


def _hhmmss(seg: int) -> str:
    """Segundos desde meia-noite -> `HH:MM:SS`. Sem wrap: `seg` deve ser 0..86399."""
    return f"{seg // 3600:02d}:{(seg % 3600) // 60:02d}:{seg % 60:02d}"


def batimento(passo_s: int, n: int, inicio_s: int = 0, ciclico: bool = True):
    """Batimento regular. `ciclico=True` volta a zero à meia-noite (é o que a hora FAZ)."""
    fora = []
    for i in range(n):
        s = inicio_s + i * passo_s
        fora.append(_hhmmss(s % 86400) if ciclico else _hhmmss(s))
    return fora


def expediente(n: int, semente: int = 7):
    """Horários espalhados em 08:00–18:00, deterministicamente (sem random)."""
    fora, x = [], semente
    for _ in range(n):
        x = (x * 1103515245 + 12345) % 2147483648      # LCG — reprodutível, sem `random`
        fora.append(_hhmmss(8 * 3600 + x % (10 * 3600)))
    return fora


# ── SINTÉTICOS por REGIME (o que o corpus não tem) ───────────────────────────
SINTETICOS = [
    ("regime-batimento-15min", batimento(900, 96),
     "telemetria: 1 dia inteiro a cada 15 min (96 pontos). O regime onde a hora é regular.",
     "par: regime-batimento-15min-2dias"),

    ("regime-batimento-15min-2dias", batimento(900, 192),
     "CONTRA-PROVA: o MESMO batimento por 2 dias — passa pela meia-noite. Aqui a "
     "CICLICIDADE morde: a sequência volta a zero e o seq-RLE vê um salto negativo.",
     "par: regime-batimento-15min"),

    ("regime-batimento-1min", batimento(60, 600),
     "batimento de 1 min, 600 pontos (10 h) — não passa da meia-noite.", ""),

    ("regime-batimento-1s", batimento(1, 600),
     "batimento de 1 s — o caso mais regular possível.", ""),

    ("regime-expediente", expediente(200),
     "200 horários espalhados em 08:00–18:00 — irregular mas com faixa estreita.", ""),

    ("regime-constante", ["00:00:00"] * 200,
     "tudo meia-noite. É o regime do `InvoiceDate` quando a hora não é usada — e o caso "
     "onde o RLE de linha resolve sozinho.", ""),

    ("regime-so-hora-e-minuto", [h[:5] for h in batimento(900, 96)],
     "a MESMA sequência em `HH:MM` — a grafia mais curta. Contra-prova de grafia.",
     "par: regime-batimento-15min"),
]

# ── BORDAS — o que a norma permite e o que quebra canonicidade ───────────────
BORDAS = [
    ("borda-meia-noite", ["00:00:00", "00:00:01", "23:59:59"],
     "os extremos do dia"),
    ("borda-24h", ["23:59:59", "24:00:00"],
     "`24:00:00` é VÁLIDO em ISO 8601 (fim do dia) e o Python RECUSA — grafia legal que "
     "não sobrevive ao `time.fromisoformat`"),
    ("borda-leap-second", ["23:59:59", "23:59:60"],
     "segundo bissexto: existe em UTC, não existe em `datetime.time`"),
    ("borda-fracao", ["12:00:00.5", "12:00:00.500000", "12:00:00.000001"],
     "frações: `.5` e `.500000` são o MESMO instante com grafias distintas — armadilha "
     "de canonicidade"),
    ("borda-hhmm-x-hhmmss", ["12:00", "12:00:00"],
     "duas grafias do mesmo instante — se um spec normalizasse, o RT quebraria"),
    ("borda-12h", ["01:30 PM", "13:30"],
     "12h com sufixo — grafia comum em relatório, não é ISO"),
    ("borda-compacta", ["120000", "235959"],
     "`HHMMSS` sem separador (forma básica da ISO) — indistinguível de um inteiro"),
    ("borda-com-nulo", ["08:00:00", None, "09:00:00"],
     "o slot nulo atravessa"),
    ("borda-timezone", ["12:00:00Z", "12:00:00+03:00", "12:00:00-00:00"],
     "com offset — e o `-00:00` tem semântica própria na RFC 3339"),
]

SINTETICOS_POR_NOME = {n: v for n, v, _, _ in SINTETICOS}


# ── REAL — a única hora do corpus, dentro de um datetime ─────────────────────
def carrega_hora_real(amostra=2000):
    """A parte de HORA do `online-retail.InvoiceDate`. Devolve (horas, ideia) ou None."""
    try:
        con = sqlite3.connect("file:Z:/tcf-data/interim/online-retail.db?mode=ro", uri=True)
        vals = [r[0] for r in con.execute(
            "SELECT InvoiceDate FROM online_retail WHERE InvoiceDate IS NOT NULL")]
        con.close()
    except Exception:
        return None
    passo = max(1, len(vals) // amostra)
    vals = vals[::passo][:amostra]
    horas = []
    for v in vals:
        s = str(v)
        parte = s.split(" ")[1] if " " in s else (s.split("T")[1] if "T" in s else None)
        if parte:
            horas.append(parte)
    return horas or None

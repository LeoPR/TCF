"""Geradores de coluna de DATA — quatro eixos, sem RNG (tudo determinístico).

Data é o primeiro tipo que a gente olha *como tipo*, e não como pretexto pra exercer o bN.
Por isso os eixos são os que fazem uma coluna de data ser diferente de outra:

    FORMATO    a mesma data, grafias diferentes (ISO, BR, US, compacto, epoch, extenso…)
    PRECISÃO   ano → ano-mês → data → datetime → +ms → +tz
    REGIME     como os valores se distribuem: incremental, repetido, espalhado, agrupado
    ESCALA     n = 12 · 120 · 1200

O eixo REGIME é o que o owner chamou de "a parte serializada, variada": uma coluna de datas
sequenciais e uma de datas espalhadas têm o MESMO tipo e comportamentos opostos.

Nada de RNG: o "espalhado" usa um LCG com semente fixa, pra rodar igual sempre.
`src/tcf` NÃO é tocado.
"""
from __future__ import annotations

import datetime as _dt

BASE = _dt.date(2026, 1, 1)
BASE_TS = _dt.datetime(2026, 1, 1, 8, 30, 0)


def _lcg(n: int, mod: int, semente: int = 12345):
    """Sequência pseudo-aleatória determinística — sem `random`, roda igual sempre."""
    x, out = semente, []
    for _ in range(n):
        x = (1103515245 * x + 12345) % (1 << 31)
        out.append(x % mod)
    return out


# ─────────────────────────────────────────────────────── EIXO FORMATO
#: A MESMA sequência de datas, escrita de jeitos diferentes. Isola a grafia do regime.
FORMATOS = {
    "iso": lambda d: d.isoformat(),                          # 2026-01-01
    "br": lambda d: d.strftime("%d/%m/%Y"),                  # 01/01/2026
    "us": lambda d: d.strftime("%m/%d/%Y"),                  # 01/01/2026
    "compacto": lambda d: d.strftime("%Y%m%d"),              # 20260101
    "ponto": lambda d: d.strftime("%d.%m.%Y"),               # 01.01.2026
    "extenso": lambda d: d.strftime("%d-%b-%Y"),             # 01-Jan-2026
    "ano-mes": lambda d: d.strftime("%Y-%m"),                # 2026-01
    "ano": lambda d: d.strftime("%Y"),                       # 2026
    "epoch-dia": lambda d: str(d.toordinal()),               # 739618
    "iso-invertido": lambda d: d.strftime("%d-%m-%Y"),       # 01-01-2026
}

#: Precisão crescente sobre o MESMO instante — mede o custo de cada campo a mais.
PRECISOES = {
    "P1-ano": lambda t: t.strftime("%Y"),
    "P2-ano-mes": lambda t: t.strftime("%Y-%m"),
    "P3-data": lambda t: t.strftime("%Y-%m-%d"),
    "P4-data-hora": lambda t: t.strftime("%Y-%m-%dT%H:%M"),
    "P5-data-hora-seg": lambda t: t.strftime("%Y-%m-%dT%H:%M:%S"),
    "P6-milissegundo": lambda t: t.strftime("%Y-%m-%dT%H:%M:%S") + f".{t.microsecond // 1000:03d}",
    "P7-tz-Z": lambda t: t.strftime("%Y-%m-%dT%H:%M:%S") + "Z",
    "P8-tz-offset": lambda t: t.strftime("%Y-%m-%dT%H:%M:%S") + "-03:00",
}


# ─────────────────────────────────────────────────────── EIXO REGIME
def regime(nome: str, n: int) -> list[_dt.date]:
    """Como os valores se distribuem — o eixo 'serializada × variada'."""
    if nome == "R1-diario":                       # 1 dia por linha, sem repetir
        return [BASE + _dt.timedelta(days=i) for i in range(n)]
    if nome == "R2-semanal":                      # passo 7
        return [BASE + _dt.timedelta(days=7 * i) for i in range(n)]
    if nome == "R3-mensal":                       # passo ~30, vira ano novo
        return [BASE + _dt.timedelta(days=30 * i) for i in range(n)]
    if nome == "R4-repetido-k5":                  # 5 datas distintas, cicladas
        base = [BASE + _dt.timedelta(days=90 * i) for i in range(5)]
        return [base[i % 5] for i in range(n)]
    if nome == "R5-agrupado":                     # blocos de iguais (o RLE adora)
        return [BASE + _dt.timedelta(days=i // 10) for i in range(n)]
    if nome == "R6-espalhado":                    # 10 anos, sem ordem
        return [BASE + _dt.timedelta(days=d) for d in _lcg(n, 3650)]
    if nome == "R7-espalhado-ordenado":           # o mesmo, mas ordenado
        return sorted(BASE + _dt.timedelta(days=d) for d in _lcg(n, 3650))
    if nome == "R8-descendente":                  # tempo pra trás
        return [BASE + _dt.timedelta(days=n - i) for i in range(n)]
    raise ValueError(nome)


REGIMES = ["R1-diario", "R2-semanal", "R3-mensal", "R4-repetido-k5",
           "R5-agrupado", "R6-espalhado", "R7-espalhado-ordenado", "R8-descendente"]


def timestamps(nome: str, n: int) -> list[_dt.datetime]:
    """Regimes de TIMESTAMP — o caso de log, onde a data repete e a hora varia."""
    if nome == "T1-log-mesmo-dia":                # mesma data, segundos correndo
        return [BASE_TS + _dt.timedelta(seconds=i) for i in range(n)]
    if nome == "T2-log-esparso":                  # mesma data, saltos irregulares
        return [BASE_TS + _dt.timedelta(seconds=s) for s in sorted(_lcg(n, 86400))]
    if nome == "T3-varios-dias":                  # dias e horas variando juntos
        return [BASE_TS + _dt.timedelta(days=i // 24, hours=i % 24) for i in range(n)]
    if nome == "T4-hora-redonda":                 # só horas cheias
        return [BASE_TS.replace(minute=0, second=0) + _dt.timedelta(hours=i)
                for i in range(n)]
    raise ValueError(nome)


REGIMES_TS = ["T1-log-mesmo-dia", "T2-log-esparso", "T3-varios-dias", "T4-hora-redonda"]

ESCALAS = [12, 120, 1200]

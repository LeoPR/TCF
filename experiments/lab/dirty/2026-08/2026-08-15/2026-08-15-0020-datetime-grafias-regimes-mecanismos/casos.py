# -*- coding: utf-8 -*-
"""Os casos do datetime — GRAFIAS prováveis × REGIMES de distribuição.

Direção do owner (2026-08-15):

> *"é absolutamente fácil achar um corpus com datetime… e mesmo o sintético é muito simples e
> na maioria das vezes os tipos são comportados, já que têm origem em bancos de dados que já
> tratam esse tipo de dado como canônico, seria muito raro ter misturas, e mesmo nessas
> condições provavelmente seriam corrupções de transmissão. Gere uma variedade PROVÁVEL de
> datetimes, com os tipos e variações de formato, para ver o comportamento do que se tem do
> TCF."*

Isso fixa o desenho: **a grafia é uniforme por coluna** (é o que um banco emite), e o eixo
interessante é *qual grafia* × *qual distribuição* — não robustez a lixo misturado.

## Os dois eixos, separados de propósito

- **GRAFIA** — como o produtor escreve. Fixa o regime e varia a forma: 13 grafias que sistemas
  reais emitem por default.
- **REGIME** — como o dado se distribui. Fixa a grafia canônica e varia a distribuição: 8
  regimes que produzem estruturas diferentes no wire.

Cruzar os dois daria 104 colunas e esconderia qual eixo explica o quê. Separados, cada tabela
tem uma variável.
"""
from __future__ import annotations

from datetime import datetime, timedelta

BASE = datetime(2026, 3, 2, 8, 26, 0)          # segunda-feira, 08:26


# ── as 13 GRAFIAS (todas sobre a MESMA sequência de instantes) ───────────────
def g_sql_espaco(d):                            # SQLite / MySQL DATETIME — o do corpus
    return d.strftime("%Y-%m-%d %H:%M:%S")


def g_iso_t(d):                                 # ISO 8601 / JSON / .NET
    return d.strftime("%Y-%m-%dT%H:%M:%S")


def g_rfc3339_z(d):                             # RFC 3339 UTC
    return d.strftime("%Y-%m-%dT%H:%M:%SZ")


def g_rfc3339_off(d):                           # RFC 3339 com offset (Brasil)
    return d.strftime("%Y-%m-%dT%H:%M:%S-03:00")


def g_pg_micro(d):                              # PostgreSQL timestamp
    return d.strftime("%Y-%m-%d %H:%M:%S.") + f"{d.microsecond:06d}"


def g_ms_milli(d):                              # SQL Server datetime2(3) / Java
    return d.strftime("%Y-%m-%d %H:%M:%S.") + f"{d.microsecond // 1000:03d}"


def g_sem_segundo(d):                           # formulário / relatório
    return d.strftime("%Y-%m-%d %H:%M")


def g_compacta(d):                              # mainframe / COBOL / chave
    return d.strftime("%Y%m%d%H%M%S")


def g_iso_basica(d):                            # ISO 8601 forma BÁSICA
    return d.strftime("%Y%m%dT%H%M%S")


def g_br(d):                                    # pt-BR
    return d.strftime("%d/%m/%Y %H:%M:%S")


def g_us_ampm(d):                               # US 12h
    return d.strftime("%m/%d/%Y %I:%M:%S ") + ("AM" if d.hour < 12 else "PM")


def g_epoch_s(d):                               # Unix segundos
    return str(int(d.timestamp()))


def g_epoch_ms(d):                              # Java / JavaScript
    return str(int(d.timestamp() * 1000))


GRAFIAS = [
    ("g01-sql-espaco", g_sql_espaco, "`YYYY-MM-DD HH:MM:SS` — SQLite/MySQL; **a do corpus**"),
    ("g02-iso-t", g_iso_t, "`...T...` — ISO 8601 / JSON / .NET"),
    ("g03-rfc3339-z", g_rfc3339_z, "com `Z` — RFC 3339 UTC"),
    ("g04-rfc3339-offset", g_rfc3339_off, "com `-03:00` — offset explícito"),
    ("g05-pg-microssegundo", g_pg_micro, "`.ffffff` — PostgreSQL timestamp"),
    ("g06-sqlserver-milli", g_ms_milli, "`.fff` — SQL Server datetime2(3) / Java"),
    ("g07-sem-segundo", g_sem_segundo, "`HH:MM` — formulário, sem segundo"),
    ("g08-compacta", g_compacta, "`YYYYMMDDHHMMSS` — mainframe, sem separador"),
    ("g09-iso-basica", g_iso_basica, "`YYYYMMDDTHHMMSS` — ISO forma básica"),
    ("g10-br", g_br, "`DD/MM/YYYY HH:MM:SS` — pt-BR"),
    ("g11-us-ampm", g_us_ampm, "`MM/DD/YYYY hh:mm:ss AM/PM` — US 12h"),
    ("g12-epoch-s", g_epoch_s, "epoch em segundos — Unix"),
    ("g13-epoch-ms", g_epoch_ms, "epoch em milissegundos — Java/JS"),
]


# ── os 8 REGIMES (a distribuição dos instantes) ─────────────────────────────
def _lcg(semente=42):
    x = semente
    while True:
        x = (x * 1103515245 + 12345) % 2147483648
        yield x


def r_comercial(n=2000):
    """Transacional: horário comercial, segundo `00`, muita repetição adjacente.

    É o regime do corpus (`online_retail.InvoiceDate`): 97,61% em 08–18h, sem sábado,
    segundo constante, 95,71% de linhas repetindo a anterior.
    """
    g, fora, atual = _lcg(7), [], BASE
    for _ in range(n):
        x = next(g)
        if x % 100 < 4:                          # 4% das vezes avança o instante
            passo = 1 + x % 40
            atual += timedelta(minutes=passo)
            if atual.hour >= 18:                 # pula pro dia seguinte, 08:00
                atual = atual.replace(hour=8, minute=next(g) % 60) + timedelta(days=1)
                if atual.weekday() == 5:         # sem sábado
                    atual += timedelta(days=1)
        fora.append(atual.replace(second=0, microsecond=0))
    return fora


def r_log_alta_card(n=2000):
    """Log: cada linha um instante distinto, segundo variando, milissegundo variando."""
    g, fora, atual = _lcg(11), [], BASE
    for _ in range(n):
        atual += timedelta(seconds=1 + next(g) % 7, microseconds=next(g) % 1000000)
        fora.append(atual)
    return fora


def r_batimento_5min(n=2000):
    """Telemetria: exatamente a cada 5 minutos, sem falha."""
    return [BASE + timedelta(minutes=5 * i) for i in range(n)]


def r_batimento_1s(n=2000):
    """Telemetria de alta taxa: 1 por segundo."""
    return [BASE + timedelta(seconds=i) for i in range(n)]


def r_esparso_multi_ano(n=2000):
    """Eventos raros espalhados por 5 anos — muitas datas, poucas por dia."""
    g, fora, atual = _lcg(13), [], BASE
    for _ in range(n):
        atual += timedelta(days=next(g) % 3, hours=next(g) % 24, minutes=next(g) % 60)
        fora.append(atual.replace(second=next(g) % 60, microsecond=0))
    return fora


def r_um_dia_so(n=2000):
    """Tudo no mesmo dia — a data é constante, só a hora varia."""
    g, fora = _lcg(17), []
    for _ in range(n):
        x = next(g)
        fora.append(BASE.replace(hour=x % 24, minute=(x // 24) % 60, second=(x // 60) % 60))
    return fora


def r_constante(n=2000):
    """Todos iguais — o caso degenerado que o RLE de linha resolve sozinho."""
    return [BASE] * n


def r_comercial_embaralhado(n=2000):
    """O regime comercial SEM a repetição adjacente — o par de contra-prova.

    Mesmos instantes, mesma cardinalidade; só a ORDEM muda. Isola quanto do ganho é do
    `*N|` (RLE de linha adjacente) e quanto é do mecanismo em teste.
    """
    vals = r_comercial(n)
    g = _lcg(23)
    v = list(vals)
    for i in range(len(v) - 1, 0, -1):            # Fisher-Yates determinístico
        j = next(g) % (i + 1)
        v[i], v[j] = v[j], v[i]
    return v


REGIMES = [
    ("r1-comercial", r_comercial,
     "transacional: 08–18h, sem sábado, segundo `00`, muita repetição adjacente — "
     "**o regime do corpus**", "par: r8-comercial-embaralhado"),
    ("r2-log-alta-card", r_log_alta_card,
     "log: todo instante distinto, com microssegundo — a pior cardinalidade", ""),
    ("r3-batimento-5min", r_batimento_5min,
     "telemetria regular: exatamente 5 em 5 minutos", "par: r4-batimento-1s"),
    ("r4-batimento-1s", r_batimento_1s, "telemetria de alta taxa: 1/s", ""),
    ("r5-esparso-multi-ano", r_esparso_multi_ano,
     "eventos raros por 5 anos — muitas datas distintas", ""),
    ("r6-um-dia-so", r_um_dia_so, "a data é CONSTANTE, só a hora varia", ""),
    ("r7-constante", r_constante, "todos iguais — o degenerado", ""),
    ("r8-comercial-embaralhado", r_comercial_embaralhado,
     "**CONTRA-PROVA do r1**: os mesmos instantes, embaralhados — isola o `*N|`",
     "par: r1-comercial"),
]

REGIMES_POR_NOME = {n: f for n, f, _, _ in REGIMES}
GRAFIAS_POR_NOME = {n: f for n, f, _ in GRAFIAS}

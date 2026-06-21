"""Pos-tx decoder pra datas YYYY-MM-DD, resolucao dia.

Inverso de `pretx_dia.encode`.
"""

from __future__ import annotations

from datetime import date, timedelta


def parse_iso_day(s: str) -> date:
    return date.fromisoformat(s)


def format_iso_day(d: date) -> str:
    return d.isoformat()


def decode(linhas: list[str]) -> list[str]:
    """Decodifica (base, deltas_em_dias) em datas YYYY-MM-DD.

    Args:
        linhas: saida de `pretx_dia.encode` — primeiro elemento e'
            data, demais sao deltas em dias.

    Returns:
        Lista de datas reconstruidas no formato `YYYY-MM-DD`.
    """
    if not linhas:
        return []
    current = parse_iso_day(linhas[0])
    out = [linhas[0]]
    for i in range(1, len(linhas)):
        delta = int(linhas[i])
        current = current + timedelta(days=delta)
        out.append(format_iso_day(current))
    return out

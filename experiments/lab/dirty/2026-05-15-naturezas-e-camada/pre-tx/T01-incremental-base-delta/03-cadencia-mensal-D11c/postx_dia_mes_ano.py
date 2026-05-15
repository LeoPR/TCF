"""Pos-tx decoder v1 pra datas YYYY-MM-DD com escalas dia/mes/ano.

Inverso de `pretx_dia_mes_ano.encode`. Parse delta `<sinal><N><escala>`
e aplica calendar arithmetic apropriado.
"""

from __future__ import annotations

from datetime import date, timedelta


def parse_iso_day(s: str) -> date:
    return date.fromisoformat(s)


def format_iso_day(d: date) -> str:
    return d.isoformat()


def _parse_delta(s: str) -> tuple[str, int]:
    """Retorna (escala, n) onde escala in {'Y', 'M', 'd'} e n e' signed int."""
    if not s:
        return ("d", 0)
    if s[-1] == "Y":
        return ("Y", int(s[:-1]))
    if s[-1] == "M":
        return ("M", int(s[:-1]))
    return ("d", int(s))


def _add_months(d: date, n: int) -> date:
    """Adiciona n meses (pode ser negativo) a d. Preserva dia."""
    total = d.year * 12 + (d.month - 1) + n
    new_year = total // 12
    new_month = total % 12 + 1
    return date(new_year, new_month, d.day)


def _apply_delta(d: date, scale: str, n: int) -> date:
    if scale == "d":
        return d + timedelta(days=n)
    if scale == "M":
        return _add_months(d, n)
    if scale == "Y":
        return date(d.year + n, d.month, d.day)
    raise ValueError(f"Escala desconhecida: {scale!r}")


def decode(linhas: list[str]) -> list[str]:
    """Decodifica (base, deltas com escala) em datas YYYY-MM-DD."""
    if not linhas:
        return []
    current = parse_iso_day(linhas[0])
    out = [linhas[0]]
    for i in range(1, len(linhas)):
        scale, n = _parse_delta(linhas[i])
        current = _apply_delta(current, scale, n)
        out.append(format_iso_day(current))
    return out

"""Pre-tx encoder pra datas YYYY-MM-DD, resolucao dia.

Linguagem v0:
- Linha 0: data base intocada (`YYYY-MM-DD`).
- Linhas 1+: delta em dias (inteiro como string) em relacao a
  linha imediatamente anterior.

Permite delta 0 (data repetida) e delta negativo (data anterior).
"""

from __future__ import annotations

from datetime import date


def parse_iso_day(s: str) -> date:
    return date.fromisoformat(s)


def encode(linhas: list[str]) -> list[str]:
    """Codifica datas YYYY-MM-DD em (base, deltas_em_dias).

    Args:
        linhas: lista de datas no formato `YYYY-MM-DD`.

    Returns:
        Lista de mesmo tamanho:
        - [0] = primeira data (base, intocada);
        - [i] para i>=1 = delta em dias entre linhas[i] e linhas[i-1].
    """
    if not linhas:
        return []
    dates = [parse_iso_day(l) for l in linhas]
    out = [linhas[0]]
    for i in range(1, len(dates)):
        delta = (dates[i] - dates[i - 1]).days
        out.append(str(delta))
    return out

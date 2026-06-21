"""Pre-tx encoder v1 pra datas YYYY-MM-DD com escalas dia/mes/ano.

Linguagem v1:
- Linha 0: data base intocada (`YYYY-MM-DD`).
- Linhas 1+: <sinal><quantidade><escala>
  - sinal: implicito positivo; explicito "-" pra negativo
  - quantidade: inteiro nao-negativo
  - escala: "Y" = ano, "M" = mes, "" (vazio) = dia (default)

Estrategia (maior escala exata possivel):
1. Se delta e' multiplo exato de anos (mes e dia iguais aos da
   linha anterior) e ano difere: emite "{N}Y" / "-{N}Y".
2. Se delta e' multiplo exato de meses (dia igual; mes/ano diferem)
   e meses difere: emite "{N}M" / "-{N}M".
3. Caso contrario: emite delta em dias.

Notas:
- "Exato" significa que adicionar N anos/meses a previa produz
  exatamente a data atual (sem ajuste de dia tipo Feb 29).
- Year diff e' tentado primeiro porque codifica mais info em
  menos bytes (1 inteiro + Y) que months (mesma quantidade de
  bytes mas Y representa mais tempo).
"""

from __future__ import annotations

from datetime import date


def parse_iso_day(s: str) -> date:
    return date.fromisoformat(s)


def _try_years(prev: date, curr: date) -> int | None:
    """Se curr = prev + N anos exatos, retorna N. Senao, None."""
    if prev.month != curr.month or prev.day != curr.day:
        return None
    n = curr.year - prev.year
    if n == 0:
        return None
    return n


def _try_months(prev: date, curr: date) -> int | None:
    """Se curr = prev + N meses exatos, retorna N. Senao, None."""
    if prev.day != curr.day:
        return None
    n = (curr.year * 12 + curr.month) - (prev.year * 12 + prev.month)
    if n == 0:
        return None
    return n


def _format_delta(n: int, scale: str) -> str:
    """Format `N<scale>` com sinal implicito."""
    sign = "-" if n < 0 else ""
    return f"{sign}{abs(n)}{scale}"


def encode(linhas: list[str]) -> list[str]:
    """Codifica datas YYYY-MM-DD em (base, deltas com escala).

    Para cada delta, tenta na ordem: ano exato → mes exato → dias.
    """
    if not linhas:
        return []
    dates = [parse_iso_day(l) for l in linhas]
    out = [linhas[0]]
    for i in range(1, len(dates)):
        prev, curr = dates[i - 1], dates[i]
        n_y = _try_years(prev, curr)
        if n_y is not None:
            out.append(_format_delta(n_y, "Y"))
            continue
        n_m = _try_months(prev, curr)
        if n_m is not None:
            out.append(_format_delta(n_m, "M"))
            continue
        n_d = (curr - prev).days
        out.append(_format_delta(n_d, ""))
    return out

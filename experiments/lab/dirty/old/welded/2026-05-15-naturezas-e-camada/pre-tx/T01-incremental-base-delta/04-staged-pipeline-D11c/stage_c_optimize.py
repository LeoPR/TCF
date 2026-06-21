"""Estagio C: otimizacao de escala.

Recebe saida do estagio B (deltas em unidade base) + metadata.
Tenta substituir deltas por **escalas maiores** (ano, mes) onde
a substituicao e' **exata** (reconstroi a mesma data).

Sintaxe da escala:
- `<N>` (sem letra) = N na unidade base (ex: dias)
- `<N>M` = N meses
- `<N>Y` = N anos
- Sinal `-` explicito so' pra negativos

Regras de "exato":
- N anos: data atual = data anterior + N anos, **mesmo mes e dia**.
- N meses: data atual = data anterior + N meses, **mesmo dia**.

Strategy: tenta Y primeiro (escala maior), depois M, depois mantem
unidade base.

Para verificar exatidao, o estagio C **reconstroi a sequencia de
datas** a partir da base + deltas em dias do estagio B. Stage C
e' auto-suficiente a partir do output do stage B.
"""

from __future__ import annotations

from datetime import date, timedelta


def _try_years(prev: date, curr: date) -> int | None:
    """Se curr = prev + N anos exatos, retorna N (signed)."""
    if prev.month != curr.month or prev.day != curr.day:
        return None
    n = curr.year - prev.year
    return n if n != 0 else None


def _try_months(prev: date, curr: date) -> int | None:
    """Se curr = prev + N meses exatos, retorna N (signed)."""
    if prev.day != curr.day:
        return None
    n = (curr.year * 12 + curr.month) - (prev.year * 12 + prev.month)
    return n if n != 0 else None


def _format(n: int, scale: str) -> str:
    sign = "-" if n < 0 else ""
    return f"{sign}{abs(n)}{scale}"


def optimize_scales(stage_b: list[str], meta: dict) -> list[str]:
    """Forward: [base, deltas em dias] -> [base, deltas com escala otimizada]."""
    if meta.get("type") != "date" or meta.get("granularity") != "day":
        # Tipo nao suportado: no-op
        return list(stage_b)
    if len(stage_b) <= 1:
        return list(stage_b)

    out = [stage_b[0]]
    current = date.fromisoformat(stage_b[0])
    for i in range(1, len(stage_b)):
        n_days = int(stage_b[i])
        next_d = current + timedelta(days=n_days)
        n_y = _try_years(current, next_d)
        if n_y is not None:
            out.append(_format(n_y, "Y"))
        else:
            n_m = _try_months(current, next_d)
            if n_m is not None:
                out.append(_format(n_m, "M"))
            else:
                out.append(stage_b[i])  # mantem dias
        current = next_d
    return out


def deoptimize_scales(stage_c: list[str], meta: dict) -> list[str]:
    """Reverse: [base, deltas com escala] -> [base, deltas em dias].

    Apos isso, denormalize_from_unit do stage B reconstroi as datas.
    """
    if meta.get("type") != "date" or meta.get("granularity") != "day":
        return list(stage_c)
    if len(stage_c) <= 1:
        return list(stage_c)

    out = [stage_c[0]]
    current = date.fromisoformat(stage_c[0])
    for i in range(1, len(stage_c)):
        s = stage_c[i]
        if s.endswith("Y"):
            n = int(s[:-1])
            next_d = date(current.year + n, current.month, current.day)
        elif s.endswith("M"):
            n = int(s[:-1])
            total = current.year * 12 + (current.month - 1) + n
            next_d = date(total // 12, total % 12 + 1, current.day)
        else:
            n = int(s)
            next_d = current + timedelta(days=n)
        delta_days = (next_d - current).days
        out.append(str(delta_days))
        current = next_d
    return out

"""Estagio B: normalizacao a unidade base.

Recebe linhas + metadata. Converte deltas a **unica unidade**
detectada em A. **NAO otimiza escala** — saida e' "naive" em uma
unidade so'.

Para data com granularidade dia:
- Output[0] = primeira linha (base intocada)
- Output[i] (i>=1) = delta em **dias** vs linha anterior

Versoes futuras: lidar com granularidade hora/segundo/etc., e
naturezas nao-date.
"""

from __future__ import annotations

from datetime import date, timedelta


def normalize_to_unit(linhas: list[str], meta: dict) -> list[str]:
    """Forward: linhas brutas -> [base, deltas em unidade base]."""
    if meta.get("type") != "date" or meta.get("granularity") != "day":
        raise NotImplementedError(
            f"Stage B forward suporta apenas type=date, "
            f"granularity=day; recebi type={meta.get('type')!r}, "
            f"granularity={meta.get('granularity')!r}."
        )
    if not linhas:
        return []
    dates = [date.fromisoformat(s) for s in linhas]
    out = [linhas[0]]
    for i in range(1, len(dates)):
        delta_days = (dates[i] - dates[i - 1]).days
        out.append(str(delta_days))
    return out


def denormalize_from_unit(unit_lines: list[str], meta: dict) -> list[str]:
    """Reverse: [base, deltas em dias] -> linhas brutas (datas)."""
    if meta.get("type") != "date" or meta.get("granularity") != "day":
        raise NotImplementedError(
            f"Stage B reverse suporta apenas type=date, "
            f"granularity=day; recebi type={meta.get('type')!r}, "
            f"granularity={meta.get('granularity')!r}."
        )
    if not unit_lines:
        return []
    current = date.fromisoformat(unit_lines[0])
    out = [unit_lines[0]]
    for i in range(1, len(unit_lines)):
        delta_days = int(unit_lines[i])
        current = current + timedelta(days=delta_days)
        out.append(current.isoformat())
    return out

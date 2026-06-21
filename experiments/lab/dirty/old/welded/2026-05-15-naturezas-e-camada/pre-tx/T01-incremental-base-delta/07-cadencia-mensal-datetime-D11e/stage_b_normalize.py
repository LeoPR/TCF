"""Estagio B: normalizacao a unidade base.

Versao estendida (sub-exp 06): suporta granularidade `day` (deltas
em dias) e `second` (deltas em segundos). Forma "naive" — uma unica
unidade.

Datetime: parser aceita separador `T` ou ` `; reformatacao usa o
separador detectado em A (campo `meta['separator']`).
"""

from __future__ import annotations

from datetime import date, datetime, timedelta


def _parse_datetime(s: str) -> datetime:
    return datetime.fromisoformat(s.replace(" ", "T"))


def _format_datetime(dt: datetime, sep: str) -> str:
    iso = dt.isoformat(sep=sep, timespec="seconds")
    return iso


def normalize_to_unit(linhas: list[str], meta: dict) -> list[str]:
    """Forward: linhas -> [base, deltas na unidade base]."""
    if meta.get("type") != "date":
        raise NotImplementedError(
            f"Stage B forward suporta apenas type=date; "
            f"recebi type={meta.get('type')!r}."
        )
    gran = meta.get("granularity")
    if not linhas:
        return []

    if gran == "day":
        dates = [date.fromisoformat(s) for s in linhas]
        out = [linhas[0]]
        for i in range(1, len(dates)):
            out.append(str((dates[i] - dates[i - 1]).days))
        return out

    if gran == "second":
        dts = [_parse_datetime(s) for s in linhas]
        out = [linhas[0]]
        for i in range(1, len(dts)):
            delta_s = int((dts[i] - dts[i - 1]).total_seconds())
            out.append(str(delta_s))
        return out

    raise NotImplementedError(
        f"Stage B forward nao suporta granularity={gran!r}."
    )


def denormalize_from_unit(unit_lines: list[str], meta: dict) -> list[str]:
    """Reverse: [base, deltas em unidade base] -> linhas (reformat)."""
    if meta.get("type") != "date":
        raise NotImplementedError(
            f"Stage B reverse suporta apenas type=date."
        )
    gran = meta.get("granularity")
    if not unit_lines:
        return []

    if gran == "day":
        current = date.fromisoformat(unit_lines[0])
        out = [unit_lines[0]]
        for i in range(1, len(unit_lines)):
            current = current + timedelta(days=int(unit_lines[i]))
            out.append(current.isoformat())
        return out

    if gran == "second":
        sep = meta.get("separator", " ")
        current = _parse_datetime(unit_lines[0])
        out = [unit_lines[0]]
        for i in range(1, len(unit_lines)):
            current = current + timedelta(seconds=int(unit_lines[i]))
            out.append(_format_datetime(current, sep))
        return out

    raise NotImplementedError(
        f"Stage B reverse nao suporta granularity={gran!r}."
    )

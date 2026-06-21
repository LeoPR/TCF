"""Estagio B: normalizacao estendida pra granularidades day/second/ms/us/ns.

Para sub-second (ms/us/ns), uso integer counting:
- granularity=ms: deltas em ms (int)
- granularity=us: deltas em us (int)
- granularity=ns: deltas em ns (int)

Python datetime suporta us nativamente. Pra ns, separamos o ns_extra
(digitos 7-9 do fractional) e somamos no total.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta


_EPOCH_DT = datetime(1, 1, 1)  # referencia interna pra integer counts


def _parse_dt_and_ns(s: str) -> tuple[datetime, int]:
    """Parse string -> (datetime up to us, ns_extra 0-999)."""
    if "." in s:
        main, frac = s.rsplit(".", 1)
        # ns: 9 digitos; us: 6; ms: 3
        frac_padded = frac.ljust(9, "0")[:9]
        us_str = frac_padded[:6]
        ns_extra = int(frac_padded[6:9])
        iso = main.replace(" ", "T") + "." + us_str
        return datetime.fromisoformat(iso), ns_extra
    dt = datetime.fromisoformat(s.replace(" ", "T"))
    return dt, 0


def _to_total_us(dt: datetime) -> int:
    """Microseconds desde _EPOCH_DT (integer)."""
    delta = dt - _EPOCH_DT
    return delta.days * 86_400_000_000 + delta.seconds * 1_000_000 + delta.microseconds


def _to_total_ns(dt: datetime, ns_extra: int) -> int:
    return _to_total_us(dt) * 1000 + ns_extra


def _from_total_us(total_us: int) -> datetime:
    return _EPOCH_DT + timedelta(microseconds=total_us)


def _format_dt(dt: datetime, ns_extra: int, granularity: str, sep: str) -> str:
    """Formata datetime de volta no formato detectado em A."""
    base = dt.strftime(f"%Y-%m-%d{sep}%H:%M:%S")
    if granularity == "second":
        return base
    if granularity == "ms":
        # microsecond -> ms (primeiros 3 digitos)
        ms = dt.microsecond // 1000
        return f"{base}.{ms:03d}"
    if granularity == "us":
        return f"{base}.{dt.microsecond:06d}"
    if granularity == "ns":
        return f"{base}.{dt.microsecond:06d}{ns_extra:03d}"
    raise ValueError(f"Unknown granularity: {granularity!r}")


def normalize_to_unit(linhas: list[str], meta: dict) -> list[str]:
    if meta.get("type") != "date":
        raise NotImplementedError(
            f"Stage B suporta apenas type=date; "
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
        dts = [_parse_dt_and_ns(s)[0] for s in linhas]
        out = [linhas[0]]
        for i in range(1, len(dts)):
            delta_s = int((dts[i] - dts[i - 1]).total_seconds())
            out.append(str(delta_s))
        return out

    if gran == "ms":
        dts = [_parse_dt_and_ns(s)[0] for s in linhas]
        out = [linhas[0]]
        for i in range(1, len(dts)):
            td = dts[i] - dts[i - 1]
            delta_us = td.days * 86_400_000_000 + td.seconds * 1_000_000 + td.microseconds
            out.append(str(delta_us // 1000))  # ms
        return out

    if gran == "us":
        dts = [_parse_dt_and_ns(s)[0] for s in linhas]
        out = [linhas[0]]
        for i in range(1, len(dts)):
            td = dts[i] - dts[i - 1]
            delta_us = td.days * 86_400_000_000 + td.seconds * 1_000_000 + td.microseconds
            out.append(str(delta_us))
        return out

    if gran == "ns":
        parsed = [_parse_dt_and_ns(s) for s in linhas]
        totals = [_to_total_ns(dt, ns) for dt, ns in parsed]
        out = [linhas[0]]
        for i in range(1, len(totals)):
            out.append(str(totals[i] - totals[i - 1]))
        return out

    raise NotImplementedError(f"Stage B granularity={gran!r}")


def denormalize_from_unit(unit_lines: list[str], meta: dict) -> list[str]:
    if meta.get("type") != "date":
        raise NotImplementedError("Stage B reverse suporta apenas type=date.")
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

    sep = meta.get("separator", " ")
    base_dt, base_ns = _parse_dt_and_ns(unit_lines[0])

    if gran == "second":
        current = base_dt
        out = [unit_lines[0]]
        for i in range(1, len(unit_lines)):
            current = current + timedelta(seconds=int(unit_lines[i]))
            out.append(_format_dt(current, 0, "second", sep))
        return out

    if gran == "ms":
        current = base_dt
        out = [unit_lines[0]]
        for i in range(1, len(unit_lines)):
            current = current + timedelta(milliseconds=int(unit_lines[i]))
            out.append(_format_dt(current, 0, "ms", sep))
        return out

    if gran == "us":
        current = base_dt
        out = [unit_lines[0]]
        for i in range(1, len(unit_lines)):
            current = current + timedelta(microseconds=int(unit_lines[i]))
            out.append(_format_dt(current, 0, "us", sep))
        return out

    if gran == "ns":
        current_total_ns = _to_total_ns(base_dt, base_ns)
        out = [unit_lines[0]]
        for i in range(1, len(unit_lines)):
            current_total_ns += int(unit_lines[i])
            dt = _from_total_us(current_total_ns // 1000)
            ns_extra = current_total_ns % 1000
            out.append(_format_dt(dt, ns_extra, "ns", sep))
        return out

    raise NotImplementedError(f"Stage B reverse granularity={gran!r}")

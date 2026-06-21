"""Estagio C: otimizacao de escala estendida pra ms/us/ns.

Sufixos suportados (longest-first parsing pra distinguir `ms` de `s`):

| Sufixo | Significado | Valido em granularidade |
|---|---|---|
| (none) | unidade base detectada em A | sempre |
| `Y` | ano | sempre |
| `M` | mes | sempre |
| `D` | dia | second, ms, us, ns |
| `h` | hora | second, ms, us, ns |
| `m` | minuto | second, ms, us, ns |
| `s` | segundo | ms, us, ns |
| `ms` | milissegundo | us, ns |
| `us` | microssegundo | ns |
| (sinal `-`) | negativo | sempre |

"Exato" pra cada escala = todos os componentes ABAIXO da escala
identicos entre prev e curr.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

import stage_b_normalize as _sb


# ---- Tentativas de escala pra cada granularidade ----
# Cada helper retorna n se exato, None caso contrario.

def _try_year_dt(prev: datetime, prev_ns: int,
                  curr: datetime, curr_ns: int) -> int | None:
    if (prev.month, prev.day, prev.hour, prev.minute, prev.second,
        prev.microsecond, prev_ns) != \
       (curr.month, curr.day, curr.hour, curr.minute, curr.second,
        curr.microsecond, curr_ns):
        return None
    n = curr.year - prev.year
    return n if n != 0 else None


def _try_month_dt(prev: datetime, prev_ns: int,
                   curr: datetime, curr_ns: int) -> int | None:
    if (prev.day, prev.hour, prev.minute, prev.second,
        prev.microsecond, prev_ns) != \
       (curr.day, curr.hour, curr.minute, curr.second,
        curr.microsecond, curr_ns):
        return None
    n = (curr.year * 12 + curr.month) - (prev.year * 12 + prev.month)
    return n if n != 0 else None


def _try_day_dt(prev: datetime, prev_ns: int,
                 curr: datetime, curr_ns: int) -> int | None:
    if (prev.hour, prev.minute, prev.second,
        prev.microsecond, prev_ns) != \
       (curr.hour, curr.minute, curr.second,
        curr.microsecond, curr_ns):
        return None
    delta = curr - prev
    if delta.seconds != 0 or delta.microseconds != 0 or curr_ns != prev_ns:
        return None
    return delta.days if delta.days != 0 else None


def _try_hour_dt(prev: datetime, prev_ns: int,
                  curr: datetime, curr_ns: int) -> int | None:
    if (prev.minute, prev.second,
        prev.microsecond, prev_ns) != \
       (curr.minute, curr.second,
        curr.microsecond, curr_ns):
        return None
    delta = curr - prev
    if delta.microseconds != 0 or curr_ns != prev_ns:
        return None
    total_s = delta.days * 86400 + delta.seconds
    if total_s % 3600 != 0:
        return None
    n = total_s // 3600
    return n if n != 0 else None


def _try_minute_dt(prev: datetime, prev_ns: int,
                    curr: datetime, curr_ns: int) -> int | None:
    if (prev.second, prev.microsecond, prev_ns) != \
       (curr.second, curr.microsecond, curr_ns):
        return None
    delta = curr - prev
    if delta.microseconds != 0 or curr_ns != prev_ns:
        return None
    total_s = delta.days * 86400 + delta.seconds
    if total_s % 60 != 0:
        return None
    n = total_s // 60
    return n if n != 0 else None


def _try_second_dt(prev: datetime, prev_ns: int,
                    curr: datetime, curr_ns: int) -> int | None:
    if (prev.microsecond, prev_ns) != (curr.microsecond, curr_ns):
        return None
    delta = curr - prev
    if delta.microseconds != 0 or curr_ns != prev_ns:
        return None
    total_s = delta.days * 86400 + delta.seconds
    return total_s if total_s != 0 else None


def _try_ms_dt(prev: datetime, prev_ns: int,
                curr: datetime, curr_ns: int) -> int | None:
    # Pra exato ms: ns_extra igual + us_field mod 1000 igual
    if prev_ns != curr_ns:
        return None
    if (prev.microsecond % 1000) != (curr.microsecond % 1000):
        return None
    # delta total em ms
    delta_us = (_sb._to_total_us(curr) - _sb._to_total_us(prev))
    if delta_us % 1000 != 0:
        return None
    n = delta_us // 1000
    return n if n != 0 else None


def _try_us_dt(prev: datetime, prev_ns: int,
                curr: datetime, curr_ns: int) -> int | None:
    if prev_ns != curr_ns:
        return None
    delta_us = _sb._to_total_us(curr) - _sb._to_total_us(prev)
    return delta_us if delta_us != 0 else None


def _fmt(n: int, scale: str) -> str:
    sign = "-" if n < 0 else ""
    return f"{sign}{abs(n)}{scale}"


# ---- Scales validos por granularidade ----

_SCALES_PER_GRAN = {
    "day":    [("Y", _try_year_dt), ("M", _try_month_dt)],
    "second": [("Y", _try_year_dt), ("M", _try_month_dt),
                ("D", _try_day_dt), ("h", _try_hour_dt), ("m", _try_minute_dt)],
    "ms":     [("Y", _try_year_dt), ("M", _try_month_dt),
                ("D", _try_day_dt), ("h", _try_hour_dt), ("m", _try_minute_dt),
                ("s", _try_second_dt)],
    "us":     [("Y", _try_year_dt), ("M", _try_month_dt),
                ("D", _try_day_dt), ("h", _try_hour_dt), ("m", _try_minute_dt),
                ("s", _try_second_dt), ("ms", _try_ms_dt)],
    "ns":     [("Y", _try_year_dt), ("M", _try_month_dt),
                ("D", _try_day_dt), ("h", _try_hour_dt), ("m", _try_minute_dt),
                ("s", _try_second_dt), ("ms", _try_ms_dt), ("us", _try_us_dt)],
}


# ---- Stage C forward ----

def optimize_scales(stage_b: list[str], meta: dict) -> list[str]:
    if meta.get("type") != "date":
        return list(stage_b)
    gran = meta.get("granularity")
    if len(stage_b) <= 1:
        return list(stage_b)

    if gran == "day":
        return _optimize_day(stage_b)

    # Sub-second e' tudo dispatch generico via _optimize_dt_based
    if gran in ("second", "ms", "us", "ns"):
        return _optimize_dt_based(stage_b, gran)

    return list(stage_b)


def _optimize_day(stage_b: list[str]) -> list[str]:
    out = [stage_b[0]]
    current = date.fromisoformat(stage_b[0])
    for i in range(1, len(stage_b)):
        n_days = int(stage_b[i])
        next_d = current + timedelta(days=n_days)
        # Day-granularity: testa Y, M
        if next_d.month == current.month and next_d.day == current.day:
            n_y = next_d.year - current.year
            if n_y != 0:
                out.append(_fmt(n_y, "Y"))
                current = next_d
                continue
        if next_d.day == current.day:
            n_m = (next_d.year * 12 + next_d.month) - \
                  (current.year * 12 + current.month)
            if n_m != 0:
                out.append(_fmt(n_m, "M"))
                current = next_d
                continue
        out.append(stage_b[i])
        current = next_d
    return out


def _optimize_dt_based(stage_b: list[str], gran: str) -> list[str]:
    out = [stage_b[0]]
    base_dt, base_ns = _sb._parse_dt_and_ns(stage_b[0])
    cur_dt, cur_ns = base_dt, base_ns

    for i in range(1, len(stage_b)):
        n = int(stage_b[i])
        next_dt, next_ns = _advance(cur_dt, cur_ns, n, gran)

        emitted = None
        for scale, fn in _SCALES_PER_GRAN[gran]:
            val = fn(cur_dt, cur_ns, next_dt, next_ns)
            if val is not None:
                emitted = _fmt(val, scale)
                break
        out.append(emitted if emitted is not None else stage_b[i])
        cur_dt, cur_ns = next_dt, next_ns
    return out


def _advance(dt: datetime, ns_extra: int, n: int, gran: str) -> tuple[datetime, int]:
    """Avanca dt por n unidades da granularidade. Retorna (dt, ns_extra)."""
    if gran == "second":
        return dt + timedelta(seconds=n), ns_extra
    if gran == "ms":
        return dt + timedelta(milliseconds=n), ns_extra
    if gran == "us":
        return dt + timedelta(microseconds=n), ns_extra
    if gran == "ns":
        # Avanca em ns. ns_extra rolaria em us.
        total_ns = _sb._to_total_ns(dt, ns_extra) + n
        new_dt = _sb._from_total_us(total_ns // 1000)
        new_ns = total_ns % 1000
        return new_dt, new_ns
    raise ValueError(gran)


# ---- Stage C reverse ----

# Sufixos multi-char primeiro!
_KNOWN_SUFFIXES = ("ms", "us", "ns")
_KNOWN_SINGLE = ("Y", "M", "D", "h", "m", "s")


def _parse_delta(s: str) -> tuple[str, int]:
    """Retorna (scale, n). Scale in {Y,M,D,h,m,s,ms,us,ns,@default}."""
    if not s:
        return ("@default", 0)
    # Multi-char primeiro
    for sfx in _KNOWN_SUFFIXES:
        if s.endswith(sfx) and len(s) > len(sfx) and s[-len(sfx) - 1] in "0123456789-":
            return (sfx, int(s[:-len(sfx)]))
    # Single-char
    if s[-1] in _KNOWN_SINGLE:
        return (s[-1], int(s[:-1]))
    return ("@default", int(s))


def deoptimize_scales(stage_c: list[str], meta: dict) -> list[str]:
    if meta.get("type") != "date":
        return list(stage_c)
    gran = meta.get("granularity")
    if len(stage_c) <= 1:
        return list(stage_c)

    if gran == "day":
        return _deoptimize_day(stage_c)

    if gran in ("second", "ms", "us", "ns"):
        return _deoptimize_dt_based(stage_c, gran)

    return list(stage_c)


def _deoptimize_day(stage_c: list[str]) -> list[str]:
    out = [stage_c[0]]
    current = date.fromisoformat(stage_c[0])
    for i in range(1, len(stage_c)):
        scale, n = _parse_delta(stage_c[i])
        if scale == "Y":
            next_d = date(current.year + n, current.month, current.day)
        elif scale == "M":
            total = current.year * 12 + (current.month - 1) + n
            next_d = date(total // 12, total % 12 + 1, current.day)
        else:
            next_d = current + timedelta(days=n)
        out.append(str((next_d - current).days))
        current = next_d
    return out


def _deoptimize_dt_based(stage_c: list[str], gran: str) -> list[str]:
    out = [stage_c[0]]
    cur_dt, cur_ns = _sb._parse_dt_and_ns(stage_c[0])

    for i in range(1, len(stage_c)):
        scale, n = _parse_delta(stage_c[i])
        next_dt, next_ns = _apply_scale(cur_dt, cur_ns, scale, n, gran)

        # Converte delta pra unidade da granularidade
        delta_str = _delta_in_unit(cur_dt, cur_ns, next_dt, next_ns, gran)
        out.append(delta_str)

        cur_dt, cur_ns = next_dt, next_ns
    return out


def _apply_scale(dt: datetime, ns_extra: int, scale: str, n: int,
                  gran: str) -> tuple[datetime, int]:
    if scale == "Y":
        return dt.replace(year=dt.year + n), ns_extra
    if scale == "M":
        total = dt.year * 12 + (dt.month - 1) + n
        return dt.replace(year=total // 12, month=total % 12 + 1), ns_extra
    if scale == "D":
        return dt + timedelta(days=n), ns_extra
    if scale == "h":
        return dt + timedelta(hours=n), ns_extra
    if scale == "m":
        return dt + timedelta(minutes=n), ns_extra
    if scale == "s":
        return dt + timedelta(seconds=n), ns_extra
    if scale == "ms":
        return dt + timedelta(milliseconds=n), ns_extra
    if scale == "us":
        return dt + timedelta(microseconds=n), ns_extra
    if scale == "ns":
        total_ns = _sb._to_total_ns(dt, ns_extra) + n
        return _sb._from_total_us(total_ns // 1000), total_ns % 1000
    # @default: gran-unit
    return _advance(dt, ns_extra, n, gran)


def _delta_in_unit(prev_dt: datetime, prev_ns: int,
                    curr_dt: datetime, curr_ns: int,
                    gran: str) -> str:
    if gran == "second":
        return str(int((curr_dt - prev_dt).total_seconds()))
    if gran == "ms":
        td = curr_dt - prev_dt
        delta_us = td.days * 86_400_000_000 + td.seconds * 1_000_000 + td.microseconds
        return str(delta_us // 1000)
    if gran == "us":
        td = curr_dt - prev_dt
        delta_us = td.days * 86_400_000_000 + td.seconds * 1_000_000 + td.microseconds
        return str(delta_us)
    if gran == "ns":
        total_ns_prev = _sb._to_total_ns(prev_dt, prev_ns)
        total_ns_curr = _sb._to_total_ns(curr_dt, curr_ns)
        return str(total_ns_curr - total_ns_prev)
    raise ValueError(gran)

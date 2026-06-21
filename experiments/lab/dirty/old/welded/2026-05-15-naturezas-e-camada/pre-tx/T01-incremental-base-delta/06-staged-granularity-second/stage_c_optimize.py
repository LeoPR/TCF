"""Estagio C: otimizacao de escala.

Versao estendida (sub-exp 06): suporta granularidade `day` e
`second`. Aplica a maior escala exata possivel.

Escalas suportadas (ordem de tentativa, maior pra menor):
- `Y` = ano
- `M` = mes
- `D` = dia (so' pra granularity=second; pra granularity=day, default e' dia sem letra)
- `h` = hora (so' pra second)
- `m` = minuto (so' pra second)
- (default) = unidade base (dia ou segundo conforme granularity)

"Exato" significa que todos os componentes menores que a escala
sao iguais entre prev e curr. Ex: `+1Y` exato exige mesmo mes,
dia, hora, minuto, segundo.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta


def _parse_datetime(s: str) -> datetime:
    return datetime.fromisoformat(s.replace(" ", "T"))


def _fmt(n: int, scale: str) -> str:
    sign = "-" if n < 0 else ""
    return f"{sign}{abs(n)}{scale}"


# ---- Helpers de "exato" pra granularity=day ----

def _try_year_day(prev: date, curr: date) -> int | None:
    if (prev.month, prev.day) != (curr.month, curr.day):
        return None
    n = curr.year - prev.year
    return n if n != 0 else None


def _try_month_day(prev: date, curr: date) -> int | None:
    if prev.day != curr.day:
        return None
    n = (curr.year * 12 + curr.month) - (prev.year * 12 + prev.month)
    return n if n != 0 else None


# ---- Helpers de "exato" pra granularity=second ----

def _ymd_hms(dt: datetime) -> tuple:
    return (dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second)


def _try_year_sec(prev: datetime, curr: datetime) -> int | None:
    if (prev.month, prev.day, prev.hour, prev.minute, prev.second) != \
       (curr.month, curr.day, curr.hour, curr.minute, curr.second):
        return None
    n = curr.year - prev.year
    return n if n != 0 else None


def _try_month_sec(prev: datetime, curr: datetime) -> int | None:
    if (prev.day, prev.hour, prev.minute, prev.second) != \
       (curr.day, curr.hour, curr.minute, curr.second):
        return None
    n = (curr.year * 12 + curr.month) - (prev.year * 12 + prev.month)
    return n if n != 0 else None


def _try_day_sec(prev: datetime, curr: datetime) -> int | None:
    if (prev.hour, prev.minute, prev.second) != \
       (curr.hour, curr.minute, curr.second):
        return None
    delta = curr - prev
    if delta.seconds != 0 or delta.microseconds != 0:
        return None
    return delta.days if delta.days != 0 else None


def _try_hour_sec(prev: datetime, curr: datetime) -> int | None:
    if (prev.minute, prev.second) != (curr.minute, curr.second):
        return None
    delta = curr - prev
    if delta.microseconds != 0:
        return None
    total_s = delta.days * 86400 + delta.seconds
    if total_s % 3600 != 0:
        return None
    n = total_s // 3600
    return n if n != 0 else None


def _try_minute_sec(prev: datetime, curr: datetime) -> int | None:
    if prev.second != curr.second:
        return None
    delta = curr - prev
    if delta.microseconds != 0:
        return None
    total_s = delta.days * 86400 + delta.seconds
    if total_s % 60 != 0:
        return None
    n = total_s // 60
    return n if n != 0 else None


# ---- Stage C forward ----

def optimize_scales(stage_b: list[str], meta: dict) -> list[str]:
    if meta.get("type") != "date":
        return list(stage_b)
    gran = meta.get("granularity")
    if len(stage_b) <= 1:
        return list(stage_b)

    if gran == "day":
        return _optimize_day(stage_b)
    if gran == "second":
        return _optimize_second(stage_b)
    return list(stage_b)


def _optimize_day(stage_b: list[str]) -> list[str]:
    out = [stage_b[0]]
    current = date.fromisoformat(stage_b[0])
    for i in range(1, len(stage_b)):
        n_days = int(stage_b[i])
        next_d = current + timedelta(days=n_days)
        n_y = _try_year_day(current, next_d)
        if n_y is not None:
            out.append(_fmt(n_y, "Y"))
        else:
            n_m = _try_month_day(current, next_d)
            if n_m is not None:
                out.append(_fmt(n_m, "M"))
            else:
                out.append(stage_b[i])
        current = next_d
    return out


def _optimize_second(stage_b: list[str]) -> list[str]:
    out = [stage_b[0]]
    current = _parse_datetime(stage_b[0])
    for i in range(1, len(stage_b)):
        n_sec = int(stage_b[i])
        next_dt = current + timedelta(seconds=n_sec)
        emitted = None
        for scale, fn in [
            ("Y", _try_year_sec),
            ("M", _try_month_sec),
            ("D", _try_day_sec),
            ("h", _try_hour_sec),
            ("m", _try_minute_sec),
        ]:
            n = fn(current, next_dt)
            if n is not None:
                emitted = _fmt(n, scale)
                break
        out.append(emitted if emitted is not None else stage_b[i])
        current = next_dt
    return out


# ---- Stage C reverse ----

def _parse_delta(s: str) -> tuple[str, int]:
    """Retorna (escala, n) onde escala in {"Y","M","D","h","m","@default"}."""
    if not s:
        return ("@default", 0)
    if s[-1] in ("Y", "M", "D", "h", "m"):
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
    if gran == "second":
        return _deoptimize_second(stage_c)
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
        else:  # @default = dia
            next_d = current + timedelta(days=n)
        out.append(str((next_d - current).days))
        current = next_d
    return out


def _deoptimize_second(stage_c: list[str]) -> list[str]:
    out = [stage_c[0]]
    current = _parse_datetime(stage_c[0])
    for i in range(1, len(stage_c)):
        scale, n = _parse_delta(stage_c[i])
        if scale == "Y":
            next_dt = current.replace(year=current.year + n)
        elif scale == "M":
            total = current.year * 12 + (current.month - 1) + n
            next_dt = current.replace(year=total // 12,
                                       month=total % 12 + 1)
        elif scale == "D":
            next_dt = current + timedelta(days=n)
        elif scale == "h":
            next_dt = current + timedelta(hours=n)
        elif scale == "m":
            next_dt = current + timedelta(minutes=n)
        else:  # @default = segundo
            next_dt = current + timedelta(seconds=n)
        delta_s = int((next_dt - current).total_seconds())
        out.append(str(delta_s))
        current = next_dt
    return out

r"""templated_marker.py — proof of concept de marker `?` no template.

Conceito: template carrega "parte estatica" da string com marker `?`
(um ou mais consecutivos) na posicao que varia. Deltas operam na
unidade do field marcado, sem precisar sufixo.

**Convencao adotada nesta POC**: marker `?` representa um field que
varia, e o **valor inicial** e' o **minimo do field** (month=01,
day=01, hour=00, minute=00, ms=000, etc.). Para datasets D11c, D11g,
D11i isso funciona porque eles comecam no minimo.

Para uso geral, futuro: encoder ou template precisaria carregar
initial value explicitamente (ex: `2010-?01?-01` com `01` embutido).
Fora do escopo da POC.

Suporta:
- Single-position cadence: template + deltas no field
- Multi-position com corrections: template + deltas no marker field
  + correcoes em outros fields (formato `marker|correctionField`)
"""

from __future__ import annotations

import re
from datetime import date, datetime


# === Helpers ========================================================

def _format_date(year: int, month: int, day: int) -> str:
    return f"{year:04d}-{month:02d}-{day:02d}"


def _add_months(year: int, month: int, n: int) -> tuple[int, int]:
    """Add n months. Returns (new_year, new_month)."""
    total = year * 12 + (month - 1) + n
    return total // 12, total % 12 + 1


# === Encoder pra D11c (monthly cadence em data YYYY-MM-DD) ===========

def encode_d11c(rows: list[str]) -> list[str]:
    """Encode D11c-style: month cadence, day fixo em template.

    Template: `YYYY-??-DD` (marker em month, year/day fixos do row 0).
    Deltas: meses incrementados desde inicial.
    """
    if not rows:
        return []
    # Parse row 0
    base = rows[0]
    y0, m0, d0 = int(base[0:4]), int(base[5:7]), int(base[8:10])

    # Template: substitui month por `??`
    template = f"{y0:04d}-??-{d0:02d}"

    out = [template]
    prev_m_total = y0 * 12 + (m0 - 1)
    for row in rows[1:]:
        y, m, d = int(row[0:4]), int(row[5:7]), int(row[8:10])
        cur_m_total = y * 12 + (m - 1)
        delta = cur_m_total - prev_m_total
        out.append(str(delta))
        prev_m_total = cur_m_total
    return out


def decode_d11c(lines: list[str]) -> list[str]:
    """Decode template-marker D11c.

    Convention: row 0 reconstructed from template at month=01 (MIN).
    Subsequent rows from accumulated deltas.
    """
    template = lines[0]
    m_template = re.fullmatch(r"(\d{4})-\?\?-(\d{2})", template)
    if not m_template:
        raise ValueError(f"Bad template: {template}")
    y0, d0 = int(m_template.group(1)), int(m_template.group(2))

    cur_m_total = y0 * 12 + 0  # MIN month = 01
    rows = [_format_date(y0, 1, d0)]  # row 0
    for delta_str in lines[1:]:
        cur_m_total += int(delta_str)
        y = cur_m_total // 12
        m = cur_m_total % 12 + 1
        rows.append(_format_date(y, m, d0))
    return rows


# === Encoder pra D11g (ms cadence em datetime us-precision) ==========

def encode_d11g(rows: list[str]) -> list[str]:
    """Encode D11g-style: ms cadence em YYYY-MM-DD HH:MM:SS.ffffff.

    Template: `YYYY-MM-DD HH:MM:SS.???000` (marker em ms positions).
    Deltas: ms incrementados.

    Identifica quantos `?` precisa: depende do range max de ms.
    """
    base = rows[0]
    fixed_part = base[:20]  # "YYYY-MM-DD HH:MM:SS."

    # Compute max ms value
    ms_values = []
    for row in rows:
        # us-fraction = row[20:26]
        us = int(row[20:26])
        ms = us // 1000
        ms_values.append(ms)

    max_ms = max(ms_values)
    n_marker = max(1, len(str(max_ms)))

    # Template: fixed_part + `?` * n_marker + remaining zeros (full ffffff)
    # ms fica nas primeiras 3 posicoes do us-fraction.
    # `?` cobre as posicoes que variam (= n_marker chars, alinhadas a direita do ms-field)
    # Ex: ms=0..12 -> n_marker=2 -> template `....00??000` (`?` em positions 21,22)
    n_zeros_left = 3 - n_marker  # zeros antes do marker (ms-field tem 3 chars)
    n_zeros_right = 3  # us-only digits (sempre 3)
    template = (
        fixed_part
        + "0" * n_zeros_left
        + "?" * n_marker
        + "0" * n_zeros_right
    )

    out = [template]
    prev_ms = ms_values[0]
    for ms in ms_values[1:]:
        delta = ms - prev_ms
        out.append(str(delta))
        prev_ms = ms
    return out


def decode_d11g(lines: list[str]) -> list[str]:
    """Decode D11g template-marker. Row 0 = template at ms=0 (MIN)."""
    template = lines[0]
    fixed_prefix = template[:20]
    cur_ms = 0  # MIN
    rows = [fixed_prefix + f"{cur_ms * 1000:06d}"]
    for delta_str in lines[1:]:
        cur_ms += int(delta_str)
        us = cur_ms * 1000
        rows.append(fixed_prefix + f"{us:06d}")
    return rows


# === Encoder pra D11i (mensal com correcao de dia) ===================

def encode_d11i(rows: list[str]) -> list[str]:
    """Encode D11i-style: month cadence + day corrections.

    Template: `YYYY-??-DD` (marker em month, DD = day_template padrao).
    Deltas:
    - `N` = +N months, day = template_default (no correction)
    - `N|Cd` = +N months, day = template_default + C
    """
    if not rows:
        return []
    base = rows[0]
    y0, m0, d_template = int(base[0:4]), int(base[5:7]), int(base[8:10])
    template = f"{y0:04d}-??-{d_template:02d}"

    out = [template]
    prev_m_total = y0 * 12 + (m0 - 1)
    for row in rows[1:]:
        y, m, d = int(row[0:4]), int(row[5:7]), int(row[8:10])
        cur_m_total = y * 12 + (m - 1)
        delta_m = cur_m_total - prev_m_total
        day_correction = d - d_template
        if day_correction == 0:
            out.append(str(delta_m))
        else:
            out.append(f"{delta_m}|{day_correction:+d}d")
        prev_m_total = cur_m_total
    return out


def decode_d11i(lines: list[str]) -> list[str]:
    """Decode D11i template-marker com corrections."""
    template = lines[0]
    m_template = re.fullmatch(r"(\d{4})-\?\?-(\d{2})", template)
    if not m_template:
        raise ValueError(f"Bad template: {template}")
    y0, d_template = int(m_template.group(1)), int(m_template.group(2))

    cur_m_total = y0 * 12 + 0  # initial month = 01 (min)
    rows = [_format_date(y0, 1, d_template)]  # row 0 at MIN
    for delta_str in lines[1:]:
        if "|" in delta_str:
            marker_str, correction = delta_str.split("|", 1)
            cur_m_total += int(marker_str)
            # Parse correction: `+Nd` or `-Nd`
            m_corr = re.fullmatch(r"([+-]?\d+)d", correction)
            if not m_corr:
                raise ValueError(f"Bad correction: {correction}")
            day_offset = int(m_corr.group(1))
        else:
            cur_m_total += int(delta_str)
            day_offset = 0
        y = cur_m_total // 12
        m = cur_m_total % 12 + 1
        d = d_template + day_offset
        rows.append(_format_date(y, m, d))
    return rows


# === Dispatcher (manual por dataset) =================================

ENCODERS = {
    "D11c-datas-mensal":        encode_d11c,
    "D11g-datetime-us":         encode_d11g,
    "D11i-datas-mensal-com-correcao": encode_d11i,
}

DECODERS = {
    "D11c-datas-mensal":        decode_d11c,
    "D11g-datetime-us":         decode_d11g,
    "D11i-datas-mensal-com-correcao": decode_d11i,
}

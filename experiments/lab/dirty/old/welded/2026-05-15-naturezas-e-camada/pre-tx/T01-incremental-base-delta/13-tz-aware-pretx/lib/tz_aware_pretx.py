r"""tz_aware_pretx.py — engenhoca: timezone-aware pre-tx para datetime+tz.

Conceito:
- Detecta tz suffix (`Z`, `+HH:MM`, `-HH:MM`) por linha
- Se tz e' constante across rows -> extrai pro template (uma vez),
  aplica pipeline template-marker em minute-cadence sobre o stripped
- Se tz varia -> fallback: nao extrai (deixa linhas como sao)

Sintaxe ilustrativa adotada (engenhoca, nao definitiva):
- Template: `YYYY-MM-DD HH:??:SS<tz>` com `??` indicando minuto variavel
  (formato 2-char zero-padded preservado pela escolha de `??`)
- Deltas: int (minutos relativos ao anterior)
- tz colado ao template (parte estatica)

Importante: a sintaxe `??` aqui e' meramente uma escolha demonstrativa
da POC do sub-exp 12 (marker = field variavel + hint de formato).
"""

from __future__ import annotations

import re


TZ_PATTERN = re.compile(r"^(.*?)(Z|[+-]\d{2}:\d{2})$")


def split_tz(row: str) -> tuple[str, str | None]:
    """Stage A: separa (datetime_part, tz_suffix). tz=None se nao detectada."""
    m = TZ_PATTERN.match(row)
    if m:
        return m.group(1), m.group(2)
    return row, None


def detect_mode(rows: list[str]) -> str:
    """Retorna 'constant_tz', 'variable_tz', ou 'no_tz'."""
    tzs = [split_tz(r)[1] for r in rows]
    if all(t is None for t in tzs):
        return "no_tz"
    if any(t is None for t in tzs):
        # Mistura — tratamos como variable
        return "variable_tz"
    if len(set(tzs)) == 1:
        return "constant_tz"
    return "variable_tz"


# === Encoder/decoder: constant_tz =====================================

def encode_constant_tz(rows: list[str]) -> list[str]:
    """Template-marker minute cadence + tz suffix colado ao template.

    Template: `YYYY-MM-DD HH:??:SS<tz>`
    Deltas: int minutos (relativos ao anterior).
    Assume cadence single-hour (no carry/overflow).
    """
    stripped = [split_tz(r)[0] for r in rows]
    tz = split_tz(rows[0])[1]
    base = stripped[0]
    fixed_prefix = base[:14]   # "YYYY-MM-DD HH:"
    second_suffix = base[16:]  # ":SS"
    template = f"{fixed_prefix}??{second_suffix}{tz}"

    out = [template]
    prev_min = int(base[14:16])
    for row in stripped[1:]:
        cur_min = int(row[14:16])
        delta = cur_min - prev_min
        out.append(str(delta))
        prev_min = cur_min
    return out


def decode_constant_tz(lines: list[str]) -> list[str]:
    template = lines[0]
    # Match: prefix + `??` + rest. `??` e' unico no template.
    m = re.match(r"^(.+?)\?\?(.+)$", template)
    if not m:
        raise ValueError(f"Bad template (no `??` marker): {template!r}")
    fixed_prefix = m.group(1)
    rest = m.group(2)

    cur_min = 0  # MIN (convencao da POC sub-exp 12)
    rows = [f"{fixed_prefix}{cur_min:02d}{rest}"]
    for delta_str in lines[1:]:
        cur_min += int(delta_str)
        rows.append(f"{fixed_prefix}{cur_min:02d}{rest}")
    return rows


# === Encoder/decoder: variable_tz =====================================

def encode_variable_tz(rows: list[str]) -> list[str]:
    """Fallback: tz varia, sem extracao. Pre-tx == rows."""
    return list(rows)


def decode_variable_tz(lines: list[str]) -> list[str]:
    return list(lines)


# === Auto dispatcher ==================================================

def auto_encode(rows: list[str]) -> tuple[str, list[str]]:
    mode = detect_mode(rows)
    if mode == "constant_tz":
        return mode, encode_constant_tz(rows)
    if mode == "variable_tz":
        return mode, encode_variable_tz(rows)
    raise ValueError(f"Unsupported mode: {mode}")


def auto_decode(mode: str, lines: list[str]) -> list[str]:
    if mode == "constant_tz":
        return decode_constant_tz(lines)
    if mode == "variable_tz":
        return decode_variable_tz(lines)
    raise ValueError(f"Unknown mode: {mode}")

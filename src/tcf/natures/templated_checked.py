"""TemplatedCheckedSpec — categoria "Templated + Checked + Unique-Discrete".

Welded canonical 2026-05-24 via ADR-0015.
Origem: experiments/lab/dirty/2026-05-24-cpf-templated-checked/07-generalizar-CNPJ/

Categoria abstrata: identificadores unicos com:
1. Layout fixo (template regex)
2. Digito verificador derivavel (check_fn)
3. Sem ordem entre instancias (Unique-Discrete)

Mesma maquina parametrica serve CPF, CNPJ, e potencialmente IBAN/Luhn
(nao welded — registrar SPEC novo quando dataset real existir).

Filosofia opt-in per-value (sub-exp 05):
- compressible -> base-94 encoded (5-7 chars)
- format_padded / check_invalid / format_mismatch / etc. -> literal fallback
- Marker prefix `_` distingue literal vs compressed
- RT byte-canonical preservado SEMPRE

Implementa Protocol NatureSpec (encode_value / decode_value /
classify_value como methods). Encoder/decoder polimorfico, zero
`isinstance` check.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable


# === Alfabeto base-94 safe pra TCF textual ===
# Exclui: \n \r \t (control), space, , ~ * \ # = [ ] < > " ' ` _ (TCF reserved + marker)
_RESERVED = set('\n\r\t ,~*\\#=[]<>"\'`_')
BASE94 = ''.join(chr(c) for c in range(33, 127) if chr(c) not in _RESERVED)
assert len(BASE94) >= 50, f"base alphabet only {len(BASE94)} chars"

MARKER_LITERAL = '_'


@dataclass(frozen=True)
class TemplatedCheckedSpec:
    """Spec parametrico pra encoder generico Templated+Checked+Unique.

    Attributes:
        name: identificador ("cpf" / "cnpj" / etc.)
        regex: padrao re.compile pra validar formato
        body_length: numero digitos no corpo (sem check)
        check_length: numero digitos check
        check_fn: dado lista[int] body, retorna lista[int] checks
        formatter: dado lista[int] (body+check), retorna string formatada
        encoded_length: chars pra encodar 10^body_length em BASE94
    """
    name: str
    regex: re.Pattern
    body_length: int
    check_length: int
    check_fn: Callable[[list[int]], list[int]]
    formatter: Callable[[list[int]], str]
    encoded_length: int

    # === Protocol NatureSpec methods ===

    def classify_value(self, v: str) -> str:
        """Classifica valor: 'compressible' ou razao Kim 2003 taxonomy."""
        if not v:
            return 'empty_value'
        expected_total = self.body_length + self.check_length
        if len(v) == expected_total and v.isdigit():
            return 'format_unmasked'
        if not self.regex.match(v):
            return 'format_mismatch' if len(v) > 5 else 'length_wrong'
        digits_str = ''.join(c for c in v if c.isdigit())
        if len(digits_str) != expected_total:
            return 'length_wrong'
        body = [int(d) for d in digits_str[:self.body_length]]
        actual_check = [int(d) for d in digits_str[self.body_length:]]
        expected_check = self.check_fn(body)
        if expected_check != actual_check:
            return 'check_invalid'
        return 'compressible'

    def encode_value(self, v: str) -> tuple[str, str]:
        """Encode generico. Retorna (payload, status)."""
        status = self.classify_value(v)
        if status != 'compressible':
            return MARKER_LITERAL + v, status
        digits_str = ''.join(c for c in v if c.isdigit())
        body_int = int(digits_str[:self.body_length])
        chars = []
        n = body_int
        for _ in range(self.encoded_length):
            chars.append(BASE94[n % len(BASE94)])
            n //= len(BASE94)
        return ''.join(reversed(chars)), status

    def decode_value(self, payload: str) -> str:
        """Decode generico — reverte encode_value."""
        if payload.startswith(MARKER_LITERAL):
            return payload[1:]
        if len(payload) == self.encoded_length and all(c in BASE94 for c in payload):
            n = 0
            for c in payload:
                n = n * len(BASE94) + BASE94.index(c)
            body_str = str(n).zfill(self.body_length)
            digits = [int(d) for d in body_str]
            digits.extend(self.check_fn(digits))
            return self.formatter(digits)
        return payload


# === Standalone functions (backward compat wrappers — delegam pra methods) ===

def classify_value(spec, v: str) -> str:
    """Compat wrapper — delega a spec.classify_value(v)."""
    return spec.classify_value(v)


def encode_value(spec, v: str) -> tuple[str, str]:
    """Compat wrapper — delega a spec.encode_value(v)."""
    return spec.encode_value(v)


def decode_value(spec, payload: str) -> str:
    """Compat wrapper — delega a spec.decode_value(payload)."""
    return spec.decode_value(payload)


# ===========================================================================
# SPEC_CPF (Brazilian individual taxpayer ID)
# ===========================================================================

_CPF_RE = re.compile(r'^(\d{3})\.(\d{3})\.(\d{3})-(\d{2})$')


def _cpf_check_fn(body: list[int]) -> list[int]:
    """Mod-11 CPF: 2 check digits."""
    s1 = sum(d * w for d, w in zip(body, range(10, 1, -1)))
    d1 = (s1 * 10) % 11
    if d1 == 10:
        d1 = 0
    s2 = sum(d * w for d, w in zip(body + [d1], range(11, 1, -1)))
    d2 = (s2 * 10) % 11
    if d2 == 10:
        d2 = 0
    return [d1, d2]


def _cpf_formatter(digits: list[int]) -> str:
    s = ''.join(str(d) for d in digits)
    return f"{s[:3]}.{s[3:6]}.{s[6:9]}-{s[9:]}"


SPEC_CPF = TemplatedCheckedSpec(
    name="cpf",
    regex=_CPF_RE,
    body_length=9,
    check_length=2,
    check_fn=_cpf_check_fn,
    formatter=_cpf_formatter,
    encoded_length=5,  # 80^5 = 3.3*10^9 > 10^9 ✓
)


# ===========================================================================
# SPEC_CNPJ (Brazilian company taxpayer ID)
# ===========================================================================

_CNPJ_RE = re.compile(r'^(\d{2})\.(\d{3})\.(\d{3})/(\d{4})-(\d{2})$')

_W1_CNPJ = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
_W2_CNPJ = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]


def _cnpj_check_fn(body: list[int]) -> list[int]:
    """Mod-11 CNPJ: 2 check digits (pesos diferentes de CPF)."""
    s1 = sum(d * w for d, w in zip(body, _W1_CNPJ))
    rem1 = s1 % 11
    d1 = 0 if rem1 < 2 else 11 - rem1
    s2 = sum(d * w for d, w in zip(body + [d1], _W2_CNPJ))
    rem2 = s2 % 11
    d2 = 0 if rem2 < 2 else 11 - rem2
    return [d1, d2]


def _cnpj_formatter(digits: list[int]) -> str:
    s = ''.join(str(d) for d in digits)
    return f"{s[:2]}.{s[2:5]}.{s[5:8]}/{s[8:12]}-{s[12:]}"


SPEC_CNPJ = TemplatedCheckedSpec(
    name="cnpj",
    regex=_CNPJ_RE,
    body_length=12,
    check_length=2,
    check_fn=_cnpj_check_fn,
    formatter=_cnpj_formatter,
    encoded_length=7,  # 80^7 = 2.1*10^13 > 10^12 ✓
)

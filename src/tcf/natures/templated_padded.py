"""TemplatedPaddedSpec — categoria TCU-NoCheckVarLength.

Welded canonical 2026-05-24 via extensao ADR-0015.
Origem: experiments/lab/dirty/old/welded/2026-05-24-cpf-templated-checked/08-IP-tcu-delta/
variante C (1.71% em D-IP-subnet via padding 12-digit).

Categoria: identificadores templated com slots de comprimento variavel
SEM check digit. Padding zero-leading torna slots fixed-width pra
ativar HCC seq-RLE digit-only.

Diferenca vs TemplatedCheckedSpec:
- Sem check_fn (sem digito verificador)
- Sem base94 encoding (preserva digit visibility pra HCC)
- Slots de width variavel padronizados via padding

Caso canonico: IPv4 com slots [3,3,3,3] separador `.`.
Comportamento: `192.168.1.1` -> `192168001001` (12 digit padded).

Implementa mesmo Protocol que TemplatedCheckedSpec
(encode_value / decode_value / classify_value como methods) —
encoder.py polimorfico, zero `isinstance` check.

Validacao real-world (sub-exp 08 variante C):
- D-IP-subnet 1000: **1.71% ratio** (vs M10 puro 117%) — speedup 68x
- D-IP-uniform 1000: 102% (worse — sem cadence cross-IPs aleatorios)
- HCC seq-RLE detecta cadence dramatic quando IPs em subnet
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from tcf.natures.templated_checked import MARKER_LITERAL


@dataclass(frozen=True)
class TemplatedPaddedSpec:
    """Spec pra Templated + Padded slots (sem check, sem base encoding).

    Attributes:
        name: identificador (ex: "ip")
        regex: pattern com grupos = slots
        slot_widths: tupla com width fixo de cada slot apos padding
        separator: char separador entre slots (ex: '.')

    Total padded length = sum(slot_widths). Strings padded sao
    digit-only -> HCC seq-RLE digit-centric ativa.

    Decodificacao: split por slot_widths, reformat com separador.
    """
    name: str
    regex: re.Pattern
    slot_widths: tuple[int, ...]
    separator: str

    @property
    def total_padded_length(self) -> int:
        return sum(self.slot_widths)

    # === Protocol methods ===

    def classify_value(self, v: str) -> str:
        """Kim 2003 taxonomy aplicado a templated-padded."""
        if not v:
            return 'empty_value'
        m = self.regex.match(v)
        if not m:
            return 'format_mismatch'
        slots = m.groups()
        if len(slots) != len(self.slot_widths):
            return 'format_mismatch'
        # Cada slot deve ser parseavel como int >= 0
        for slot_str, width in zip(slots, self.slot_widths):
            try:
                val = int(slot_str)
            except ValueError:
                return 'format_mismatch'
            if val >= 10 ** width:
                return 'range_invalid'
            # Detect padded zeros: se str(int) != slot_str -> non-canonical
            if str(val) != slot_str:
                return 'format_padded_zeros'
        return 'compressible'

    def encode_value(self, v: str) -> tuple[str, str]:
        """Encode: canonical -> padded string. Retorna (payload, status)."""
        status = self.classify_value(v)
        if status != 'compressible':
            return MARKER_LITERAL + v, status
        m = self.regex.match(v)
        slots = m.groups()
        padded = ''.join(
            slot_str.zfill(width)
            for slot_str, width in zip(slots, self.slot_widths)
        )
        return padded, status

    def decode_value(self, payload: str) -> str:
        """Decode: padded -> canonical via split + format."""
        if payload.startswith(MARKER_LITERAL):
            return payload[1:]
        if (len(payload) == self.total_padded_length
                and payload.isdigit()):
            # Split per slot_widths
            parts = []
            cursor = 0
            for width in self.slot_widths:
                slot_str = payload[cursor:cursor + width]
                parts.append(str(int(slot_str)))  # remove leading zeros
                cursor += width
            return self.separator.join(parts)
        return payload  # fallback inesperado


# === SPEC_IP (IPv4 canonical) ===

_IPV4_RE = re.compile(r'^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$')

SPEC_IP = TemplatedPaddedSpec(
    name="ip",
    regex=_IPV4_RE,
    slot_widths=(3, 3, 3, 3),
    separator='.',
)

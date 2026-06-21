"""BaseAlphabet — descritor puro de uma base (data class sem logica).

Separacao de responsabilidades:
- BaseAlphabet eh APENAS data (nome, chars, base int).
- Logica de parsing/formatting vive em SeqRLEEngine (que recebe alphabet).
- Zero condicionais "if base == X" — engine eh polimorfica via alphabet.

Inspirado em:
- PFOR-DELTA (Zukowski 2006): integer delta encoding
- VByte/Varint: integer encoding
- BaseAlphabet eh extensao text-oriented desses paradigmas
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BaseAlphabet:
    """Descritor de uma base numerica + alfabeto de chars.

    Args:
        name: identificador human-readable (ex: "decimal", "hex_lower")
        chars: chars que compoem o alfabeto, em ordem (chars[0]=0, chars[1]=1, ...)
        base: tamanho do alfabeto (len(chars))

    Invariante: base == len(chars).
    """
    name: str
    chars: str
    base: int

    def __post_init__(self):
        assert self.base == len(self.chars), \
            f"base ({self.base}) != len(chars) ({len(self.chars)})"


# === Alfabetos pre-definidos ===

DECIMAL = BaseAlphabet(
    name="decimal",
    chars="0123456789",
    base=10,
)

HEX_LOWER = BaseAlphabet(
    name="hex_lower",
    chars="0123456789abcdef",
    base=16,
)

HEX_UPPER = BaseAlphabet(
    name="hex_upper",
    chars="0123456789ABCDEF",
    base=16,
)

# Marker character em syntax HCC seq-RLE pra distinguir base no marker
# (Default = decimal, sem marker. Outras bases marker explicit.)
BASE_MARKER = {
    DECIMAL: '',           # default, compat M10
    HEX_LOWER: 'h',
    HEX_UPPER: 'H',
}

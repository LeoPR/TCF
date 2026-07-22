"""boolean_spec — protótipo da spec BINÁRIA (domínio-2) com VARIANTES e AUTORIDADE.

Insight (owner): 'boolean' é uma spec de DOMÍNIO-2. A superfície é uma VARIANTE (1/0, t/f, true/false,
True/False, Y/N…). Semanticamente-bool = variante conhecida; enum-2 arbitrário (Male/Female) = mesma
ESTRUTURA (2 símbolos = 1 bit), superfície é dado.

AUTORIDADE decide a liberdade de canonicalizar:
- deduzido (CSV cru): preserva a superfície EXATA (sanidade) — guarda a variante/os 2 valores.
- mandatório/typed: livre pra canonicalizar (saída pode sair 'true'/'false' minúsculo — vemos o DADO).

GABARITO-DA-SPEC: se a variante é padrão (registry), os 2 valores VÊM da spec — a coluna não guarda
gabarito, só o id da variante + 1 bit/linha. Não toca src/tcf.
"""
from __future__ import annotations

# registry de variantes padrão: nome -> (surface_false, surface_true)
VARIANTS = {
    "true/false": ("false", "true"),
    "True/False": ("False", "True"),
    "1/0": ("0", "1"),
    "t/f": ("f", "t"),
    "T/F": ("F", "T"),
    "yes/no": ("no", "yes"),
    "Y/N": ("N", "Y"),
    "sim/nao": ("nao", "sim"),
}
_SURFACE_TO_VARIANT = {frozenset(v): k for k, v in VARIANTS.items()}


class BinarySpec:
    """Spec de domínio-2. Guarda (surface_false, surface_true) + se é variante padrão.
    encode: bitstring '0'/'1' (false/true). decode: mapa bit->superfície (RT exato)."""

    def __init__(self, s_false: str, s_true: str, variant: str | None = None):
        self.s_false, self.s_true = s_false, s_true
        self.variant = variant                       # nome no registry, ou None (enum-2 arbitrário)

    @classmethod
    def induce(cls, values):
        """induz do dado. None se domínio != 2. Ordena por variante padrão; senão 1ª-vista=false."""
        distinct = list(dict.fromkeys(str(v) for v in values))   # ordem de aparição
        if len(distinct) != 2:
            return None
        ds = frozenset(distinct)
        variant = _SURFACE_TO_VARIANT.get(ds)
        if variant:
            s_false, s_true = VARIANTS[variant]
        else:
            s_false, s_true = distinct[0], distinct[1]            # enum-2: 1ª-vista = false
        return cls(s_false, s_true, variant)

    def header(self, authority="deduzido") -> str:
        """o que precisa ir no cabeçalho pra reconstruir. Variante padrão = só o id (gabarito-da-spec)."""
        if self.variant:
            return f"@bool:{self.variant}"            # gabarito vem da spec — 2 valores implícitos
        return f"@bin:{self.s_false}|{self.s_true}"   # enum-2: guarda os 2 (gabarito na coluna)

    def encode_bits(self, values) -> str:
        return "".join("1" if str(v) == self.s_true else "0" for v in values)

    def decode_bits(self, bits) -> list:
        return [self.s_true if b == "1" else self.s_false for b in bits]


def rt_ok(values):
    """round-trip da spec binária sobre uma coluna."""
    spec = BinarySpec.induce(values)
    if spec is None:
        return None, "não é domínio-2"
    back = spec.decode_bits(spec.encode_bits(values))
    return back == [str(v) for v in values], spec

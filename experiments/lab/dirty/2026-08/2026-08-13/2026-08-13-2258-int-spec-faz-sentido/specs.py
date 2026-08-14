"""Protótipos de spec de INTEIRO. Fork de laboratório — `src/tcf` NÃO é tocado.

Cada alvo implementa o mesmo Protocol das natures welded (`classify_value` /
`encode_value` / `decode_value`), então o `encode(vals, nature=alvo)` real os aceita.

As três ideias vêm do que o projeto JÁ soldou para outros tipos — é o "percurso de
revisão desde bN, bool, date" generalizando:

  A. PAD    zero-pad p/ largura fixa      <- `TemplatedPaddedSpec` (IP, ADR-0015)
  B. B94    base-94 densa                 <- `TemplatedCheckedSpec` (CPF, ADR-0015)
  C. OFF    offset p/ o mínimo, depois pad <- ideia do ordinal (data-iso, T-DATA-LAZY-ISO)

O alvo NÃO decide sozinho: o `encode()` real faz o FLOOR (compete contra o core e só
vence se reduzir). É o mesmo contrato de toda nature.
"""
from __future__ import annotations

from dataclasses import dataclass

from tcf.natures.templated_checked import BASE94, MARKER_LITERAL

_B94 = {c: i for i, c in enumerate(BASE94)}
_R = len(BASE94)


def _digitos(v: str) -> bool:
    return bool(v) and v.isdigit()


@dataclass(frozen=True)
class IntPad:
    """A. Zero-pad para largura fixa.

    Motivo (medido): o marcador aritmético do seq-RLE compara LINHAS, e a progressão
    quebra quando o número muda de dígito (9->10, 99->100). `1..600` sai em TRÊS
    marcadores; com pad vira UM. É exatamente o que o IP já faz ("padding zero-leading
    torna slots fixed-width pra ativar HCC seq-RLE digit-only").
    """

    largura: int
    name: str = "int-pad"
    wire_id: str = "xipad"

    def classify_value(self, v: str) -> str:
        if not v:
            return "empty_value"
        if not _digitos(v):
            return "format_mismatch"
        if len(v) > self.largura:
            return "length_wrong"
        if v != str(int(v)):
            return "format_noncanonical"      # '007' != '7' — RT byte-exato exige recusa
        return "compressible"

    def encode_value(self, v: str) -> tuple[str, str]:
        s = self.classify_value(v)
        if s != "compressible":
            return MARKER_LITERAL + v, s
        return v.zfill(self.largura), s

    def decode_value(self, p: str) -> str:
        if p.startswith(MARKER_LITERAL):
            return p[1:]
        return str(int(p))


@dataclass(frozen=True)
class IntB94:
    """B. Base-94 densa, largura fixa de saída.

    Motivo: uma coluna de ids de largura fixa não ganha NADA hoje (600 ids de 6 dígitos
    = 4209 B contra ~4200 crus). O CPF já resolve isso: 11 dígitos -> 5 chars BASE94.
    """

    digitos: int
    name: str = "int-b94"
    wire_id: str = "xib94"

    @property
    def saida(self) -> int:
        n, w = 10 ** self.digitos, 0
        while _R ** w < n:
            w += 1
        return w

    def classify_value(self, v: str) -> str:
        if not v:
            return "empty_value"
        if not _digitos(v):
            return "format_mismatch"
        if len(v) > self.digitos:
            return "length_wrong"
        if v != str(int(v)):
            return "format_noncanonical"
        return "compressible"

    def encode_value(self, v: str) -> tuple[str, str]:
        s = self.classify_value(v)
        if s != "compressible":
            return MARKER_LITERAL + v, s
        n, out = int(v), []
        for _ in range(self.saida):
            n, r = divmod(n, _R)
            out.append(BASE94[r])
        return "".join(reversed(out)), s

    def decode_value(self, p: str) -> str:
        if p.startswith(MARKER_LITERAL):
            return p[1:]
        n = 0
        for c in p:
            n = n * _R + _B94[c]
        return str(n)


@dataclass(frozen=True)
class IntOffPad:
    """C. Offset para o mínimo, depois pad.

    Motivo: negativos e faixas deslocadas (ex.: 1..600 com base 1e9) gastam dígitos que
    não informam. É a mesma ideia do ordinal de data: trocar a grafia por uma em que a
    aritmética fica visível e curta. O `base` viaja no PRÓPRIO spec (out-of-band), que é
    o que torna isto um protótipo e não uma proposta de wire.
    """

    base: int
    largura: int
    name: str = "int-offpad"
    wire_id: str = "xioff"

    def classify_value(self, v: str) -> str:
        if not v:
            return "empty_value"
        try:
            n = int(v)
        except ValueError:
            return "format_mismatch"
        if v != str(n):
            return "format_noncanonical"
        d = n - self.base
        if d < 0 or len(str(d)) > self.largura:
            return "length_wrong"
        return "compressible"

    def encode_value(self, v: str) -> tuple[str, str]:
        s = self.classify_value(v)
        if s != "compressible":
            return MARKER_LITERAL + v, s
        return str(int(v) - self.base).zfill(self.largura), s

    def decode_value(self, p: str) -> str:
        if p.startswith(MARKER_LITERAL):
            return p[1:]
        return str(int(p) + self.base)


def alvos_para(vals: list[str]) -> list:
    """Instancia os 3 alvos DIMENSIONADOS pela coluna (o que um auto-detector faria)."""
    nums = [int(v) for v in vals if v and (v.lstrip("-").isdigit())]
    if not nums:
        return []
    largura = max(len(str(abs(n))) for n in nums)
    base = min(nums)
    span = max(nums) - base
    out = [IntPad(largura=largura)]
    if largura <= 12:
        out.append(IntB94(digitos=largura))
    if base != 0 and span >= 0:
        out.append(IntOffPad(base=base, largura=max(1, len(str(span)))))
    return out

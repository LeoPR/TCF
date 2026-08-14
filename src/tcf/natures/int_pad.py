"""IntPadSpec — inteiro decimal -> zero-pad a largura fixa. Categoria TCU-Padded.

Weld 2026-08-14 (EXP-018). Implementa o mesmo Protocol das outras natures
(`classify_value` / `encode_value` / `decode_value`), entao o encoder segue polimorfico.

## Por que zero-pad, e por que ele é AUTO-CONTIDO

O marcador aritmético do seq-RLE compara LINHAS do corpo, e a progressão quebra quando o
número muda de dígito. Medido: `1..600` sai em TRÊS marcadores (`*9+1|1`, `*90+1|10`,
`*501+1|100`); com largura fixa vira UM. É o mesmo fenômeno que a docstring do `data_iso`
descreve para ISO (*"2026-01-31 → 2026-02-01 não é '+1' em campo nenhum isolado"*), e a
mesma solução que o `TemplatedPaddedSpec` (IP) já usa: *"padding zero-leading torna slots
fixed-width pra ativar HCC seq-RLE digit-only"*.

**A largura NÃO precisa viajar**: ela é o comprimento das linhas do corpo, visível no corpo
expandido. É o que separa este spec do `OFFPAD` descartado, cuja base era informação perdida
— e é a mesma propriedade que faz `data-iso`/`cpf`/`cnpj`/`ip` serem auto-contidos.

## O guard de canonicidade

`'007'` **não é** o inteiro `7`. Aceitar os dois colapsaria duas grafias no mesmo valor e o
round-trip byte-exato quebraria. Mesma técnica de canonicidade por re-emissão que o
`data_iso` introduziu: **re-emite e compara; se diferiu, é literal.**

## Medido

39 colunas numericas reais dos hubs de `Z:` (lab dirty `2026-08-14-0112`): ganho real em 21
medicoes, mediana 1,72x, maximo 2,73x, zero empates. Prototipo probatorio: EXP-018, 18 casos,
0 falhas, 7 provas por caso — o spec vence em 6 (mediana 1,79x, max 2,80x) e RECUSA nos outros
12, com wire byte-identico ao do nucleo. Vies declarado: o corpus e' majoritariamente TPC-H,
que favorece progressao densa; o lab sustenta o comportamento (ganha onde o gatilho dispara,
recusa onde nao), nao o valor absoluto como previsao universal.
"""

from __future__ import annotations

from dataclasses import dataclass

from tcf.natures.templated_checked import MARKER_LITERAL


@dataclass(frozen=True)
class IntPadSpec:
    """Inteiro decimal -> zero-pad à largura fixa da coluna. Categoria TCU-Padded.

    Attributes:
        largura: nº de dígitos da grafia padded. Dimensionada pela coluna no encode e
            DEDUZÍVEL do corpo no decode — por isso o wire é auto-contido.
        name: identificador de CÓDIGO (nunca viaja) — ADR-0041.
        wire_id: identificador de DADO (o `:id` do header) — ADR-0041.
    """

    largura: int
    name: str = "int-pad"
    wire_id: str = "ipad"

    def __post_init__(self):
        if not isinstance(self.largura, int) or self.largura < 1 or self.largura > 38:
            # 38 = maior largura decimal representável em 128 bits; acima disso a coluna
            # não é "inteiro tabular", é bignum, e o pad custaria mais do que informa.
            raise ValueError(
                f"IntPadSpec.largura deve ser int em 1..38; got {self.largura!r}")

    # ── classificacao ────────────────────────────────────────────────────────
    def classify_value(self, v: str) -> str:
        """`'compressible'` ou o motivo. Mesmo vocabulario das outras natures."""
        if not v:
            return "empty_value"
        if not v.isdigit():
            # negativo, decimal, sinal, espaco, notacao cientifica — tudo literal.
            # Medido: offset p/ acomodar negativos PIORA (0,89x), entao nem se tenta.
            return "format_mismatch"
        if len(v) > self.largura:
            return "length_wrong"
        if v != str(int(v)):
            # CANONICIDADE POR RE-EMISSAO: '007' != '7'. Sem este guard, duas grafias
            # colapsariam no mesmo ordinal e o RT byte-exato quebraria.
            return "format_noncanonical"
        return "compressible"

    # ── transformacao ────────────────────────────────────────────────────────
    def encode_value(self, v: str) -> "tuple[str, str]":
        status = self.classify_value(v)
        if status != "compressible":
            return MARKER_LITERAL + v, status
        return v.zfill(self.largura), status

    def decode_value(self, payload: str) -> str:
        if payload.startswith(MARKER_LITERAL):
            return payload[1:]
        if not payload.isdigit():
            # Fail-loud: o encoder canonico so' emite digitos ou literal marcado.
            raise ValueError(
                f"nature {self.name} (header :{self.wire_id}): payload "
                f"{payload[:16]!r} nao e' decimal nem literal marcado — corpo nao-canonico"
            )
        return str(int(payload))


def int_pad_para(vals) -> "IntPadSpec | None":
    """A largura que um auto-detector escolheria: a do maior inteiro puro da coluna.

    Devolve `None` quando não há o que padear (nenhum inteiro, ou largura já uniforme —
    caso em que o pad é no-op e só custaria a tag). É o gatilho medido em corpus real:
    `gat_PAD` disparou 11/39 e acertou 9.
    """
    puros = [v for v in vals if v is not None and str(v).isdigit()]
    if not puros:
        return None
    larguras = {len(str(v)) for v in puros}
    if len(larguras) < 2:
        return None                     # largura ja' uniforme: padding nao muda nada
    return IntPadSpec(largura=max(larguras))

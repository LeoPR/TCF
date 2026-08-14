"""`IntPadSpec` — o candidato a WELD. Protótipo em forma de destino.

Diferente dos alvos do lab dirty, este arquivo é escrito como o código que iria para
`src/tcf/natures/int_pad.py`: mesmo Protocol das natures welded, mesmas convenções, mesmo
estilo de guarda. O `run.py` o exercita pela API pública real, então o FLOOR de verdade
decide se ele vence.

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

## Medido em corpus real

39 colunas numéricas dos hubs de `Z:` (lab `2026-08-14-0112`): vence com ganho real em 21
medições, **mediana 1,72×, máximo 2,73×, zero empates**. Viés declarado: 25 das 39 colunas
são TPC-H, que favorece este regime.
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


def dimensiona(vals) -> "IntPadSpec | None":
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

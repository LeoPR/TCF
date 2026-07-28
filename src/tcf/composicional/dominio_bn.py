"""bN de DOMINIO — densidade por cardinalidade, nao por tipo declarado.

Com `k` valores distintos numa coluna, bastam `w = ceil(log2(k))` bits por linha. O dominio
viaja uma vez; os indices viajam empacotados.

    #TCF.8                    #TCF.8B178
    \\0                        false
    \\1                        true
    ^1                        =CIhmASAEyQvAQQZokA
    ^2
    ...  (609 B)              (57 B)

## Duas grafias, escolhidas pelo TRANSPORTE

    B   dominio PRIMEIRO, `=` abre o bloco de bits    default -- STREAMA nos dois lados
    C   dominio por ULTIMO, sem marcador               lote fechado -- ~1 B/coluna menor

Com o dominio no fim (`C`) o leitor **nao emite valor nenhum antes do payload inteiro
chegar**: o comprimento do b64 e' deduzivel de `n` e `w`, mas o significado dos indices so'
aparece depois. Medido no lab `2026-07-27-2211`: numa coluna de 2000 linhas o `B` bufferiza
~100 B e o `C` ~1760 B — 17x — para 1 byte de diferenca.

## O marcador `=` e o escape

O `=` abre o bloco de bits. Uma linha de DOMINIO que comece com `=` ganha `\\` na frente.
Isso e' inequivoco porque **o core nunca emite `\\` seguido de char fora de `* 0-9 \\ ^ ~`**
(medido, varrendo os 95 imprimiveis, no lab `2026-07-27-2231`).

Custo: **1 B** de marcador, mais 1 B por valor de dominio que comece com `=` — em 145 colunas
categoricas reais das fixtures, esse segundo termo foi **zero**. E o caso patologico (dominio
cheio de `=`) e' absorvido pelo FLOOR externo: se o bN inchar, o core vence.

## O slot nulo

`null` nao e' caso especial: e' mais um valor do dominio, e ocupa o **slot 0**, que o formato
ja' reserva pra ele. A grafia do dominio e' a do core: `0` cru = null, `\\0` = o literal `"0"`.
Essa assimetria (grafar mais do que se desfaz) ja' custou 4 bugs no projeto — por isso
`_le_grafia` desfaz exatamente `_grafa`, nem mais.

## Onde NAO se aplica

    k <= 1    o core ja' e' otimo com RLE (`*N|valor`)
    k > 256   `w` passaria de 8; fora do namespace
    n pequeno o cabecalho + dominio nao se pagam (o FLOOR recusa sozinho)

Referencias: labs `experiments/lab/dirty/2026-07/2026-07-27/` — `1608` (a escada), `1647`
(dominio comprimido + alinhamento), `2211` (o eixo de streaming), `2231` (marcador por
escape), `2247` (o espaco completo de delimitacao).
"""
from __future__ import annotations

import base64
import math

from tcf.bitpack import pack_w, unpack_w

MAGIC = "#TCF.8"
BS = chr(92)

#: Discriminadores. `B` = dominio primeiro (streaming); `C` = dominio por ultimo (lote).
DISC_STREAM = "B"
DISC_LOTE = "C"
DISCS = frozenset({DISC_STREAM, DISC_LOTE})

#: O char que abre o bloco de bits no modo `B`.
MARCADOR = "="

#: Teto do namespace: `w` de 1 a 8 -> ate' 256 valores distintos.
MAX_W = 8


def _largura(k: int) -> int:
    return 0 if k <= 1 else max(1, math.ceil(math.log2(k)))


def _grafa(v: "str | None") -> str:
    """`0` cru = slot nulo; `\\0` = o literal `"0"`. SO' esse valor e' escapado aqui."""
    return "0" if v is None else (BS + v if v == "0" else v)


def _le_grafia(s: str) -> "str | None":
    """Desfaz `_grafa`, e SO' ela. Desfazer mais mutila dado que ja' vem com `\\`."""
    if s == "0":
        return None
    return "0" if s == BS + "0" else s


def dominio(valores: "list[str | None]") -> "list[str | None]":
    """Dominio canonico: `null` no slot 0 (pre-alocado), resto por PRIMEIRA APARICAO."""
    tem_nulo = False
    vistos: "dict[str, bool]" = {}
    for v in valores:
        if v is None:
            tem_nulo = True
        elif v not in vistos:
            vistos[v] = True
    return ([None] if tem_nulo else []) + list(vistos.keys())    # type: ignore[list-item]


def candidatos(valores, encode_col, decode_col):
    """Wires bN para `valores`, ou `[]` se a coluna nao se qualifica.

    `encode_col`/`decode_col` sao injetados pra evitar import circular com o encoder.
    Devolve os dois modos (`B` e `C`) — quem decide e' o `min()` de quem chamou.
    """
    dom = dominio(valores)
    k = len(dom)
    w = _largura(k)
    if w == 0 or w > MAX_W:
        return []
    idx = {v: i for i, v in enumerate(dom)}
    b64 = base64.b64encode(pack_w([idx[v] for v in valores], w)).decode("ascii").rstrip("=")
    bloco = encode_col([_grafa(v) for v in dom]).rstrip("\n")
    n = len(valores)
    escapado = "\n".join(BS + ln if ln.startswith(MARCADOR) else ln
                         for ln in bloco.split("\n"))
    return [
        f"{MAGIC}{DISC_STREAM}{w}{n:x}\n{escapado}\n{MARCADOR}{b64}",
        f"{MAGIC}{DISC_LOTE}{w}{n:x}\n{b64}\n{bloco}",
    ]


def _b64_len(n: int, w: int) -> int:
    """Comprimento do bloco base64 SEM padding — deduzivel de `n` e `w`."""
    return (((n * w + 7) // 8) * 8 + 5) // 6


def decode_bn(tcf_text: str, disc: str, decode_col) -> "list[str | None]":
    """Le um wire `#TCF.8B…`/`#TCF.8C…`. Fail-loud em cabecalho ou fronteira nao-canonicos."""
    cab, sep, resto = tcf_text.partition("\n")
    if not sep:
        raise ValueError(f"wire bN sem corpo: {cab[:24]!r}")
    campos = cab[len(MAGIC) + 1:]
    if not campos or not campos[0].isdigit():
        raise ValueError(f"cabecalho bN sem largura: {cab[:24]!r}")
    w = int(campos[0])
    if not 1 <= w <= MAX_W:
        raise ValueError(f"largura bN fora de 1..{MAX_W}: {w}")
    try:
        n = int(campos[1:], 16)
    except ValueError:
        raise ValueError(f"contagem bN nao-hexadecimal: {campos[1:]!r}") from None

    if disc == DISC_LOTE:
        nb = _b64_len(n, w)
        b64, bloco = resto[:nb], resto[nb + 1:]
    else:
        linhas = resto.split("\n")
        alvo = next((j for j, ln in enumerate(linhas) if ln.startswith(MARCADOR)), None)
        if alvo is None:
            raise ValueError(
                f"wire bN sem o marcador {MARCADOR!r} que separa dominio e bits "
                f"— corpo nao-canonico (truncado ou editado a mao)"
            )
        b64 = linhas[alvo][1:]
        bloco = "\n".join(ln[1:] if ln.startswith(BS + MARCADOR) else ln
                          for ln in linhas[:alvo])

    dom = [_le_grafia(s) for s in decode_col(bloco + "\n")]
    if not dom:
        raise ValueError("dominio bN vazio — corpo nao-canonico")
    if len(dom) > (1 << w):
        raise ValueError(f"dominio bN com {len(dom)} valores nao cabe em {w} bits")
    raw = base64.b64decode(b64 + "=" * (-len(b64) % 4))
    saida = []
    for i in unpack_w(raw, w, n):
        if i >= len(dom):
            # `w` bits enderecam 2^w slots, mas o dominio pode ter menos. Indice fora da
            # faixa e' wire adulterado — fail-loud, nao IndexError cru.
            raise ValueError(
                f"indice {i} fora do dominio bN de {len(dom)} valores — corpo nao-canonico"
            )
        saida.append(dom[i])
    return saida

"""Protótipo do `T-BN-TIPADO` — o bN de domínio na rota TIPADA.

O bN de domínio está soldado (ADR-0036) **só na rota flat** (`list[str]`). A rota tipada
(`#TCF.8<tag>`, tags `b`/`n`) não o alcança, porque o wire `#TCF.8B…` devolve **string** e ali
o tipo tem de ser preservado — um `bool` voltando `"true"` seria corrupção silenciosa.

## A grafia proposta — o slot JÁ existe

    #TCF.8 b B 2 c8
           │ │ │ └── n em hex
           │ │ └──── w = largura em bits
           │ └────── modo, INDICE 7
           └──────── tag de tipo, INDICE 6

`decoder._decode_typed` já faz `resto = line1[7:]` e `modo_c = resto[:1]`, com
`_LARGURA_MODO = {'1','2','4','8'}` (as larguras do denso). Acrescentar `B` é **um ramo no
dispatch que já existe** — o mesmo idioma posicional do ADR-0029, não gramática nova.

## O que este módulo é

Protótipo de **fiação**, não de mecanismo: ele injeta a tag no candidato que
`dominio_bn.candidatos()` já produz, e no decode chama `dominio_bn.decode_bn` seguido de
`decoder._cast_tipo`. **Ambas as funções são do `src/tcf`** — nenhuma reimplementação, o que
torna a medição honesta: o que se mede aqui é o que a solda produziria.

`src/tcf` intocado.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[6] / "src"))

from tcf.composicional.dominio_bn import DISC_STREAM, candidatos, decode_bn  # noqa: E402
from tcf.decoder import _cast_tipo, _decode_column  # noqa: E402
from tcf.encoder import _encode_column, _tipo_single_col  # noqa: E402

MAGIC = "#TCF.8"


def proto_encode(dados):
    """`(wire, tag, w)` do candidato bN TIPADO, ou `(None, tag, 0)` se nao se qualifica."""
    t = _tipo_single_col(dados)
    if t is None:
        return None, None, 0
    tag, render = t
    strs = [None if x is None else render(x) for x in dados]
    cands = candidatos(strs, lambda vs: _encode_column(vs, header="val"), None)
    if not cands:
        return None, tag, 0
    # o candidato `B` (dominio primeiro), com a TAG injetada no indice 6
    corpo = cands[0][len(MAGIC):]
    w = int(corpo[1])
    return MAGIC + tag + corpo, tag, w


def proto_decode(wire):
    """Le o wire tipado bN. Usa `decode_bn` e `_cast_tipo` do `src/tcf` — sem reimplementar."""
    line1 = wire.partition("\n")[0]
    tag = line1[6]
    disc = line1[7]
    if disc != DISC_STREAM:
        raise ValueError(f"esperado modo {DISC_STREAM!r} no indice 7: {line1[:12]!r}")
    # remove a tag pra reconstituir o wire que o `decode_bn` sabe ler
    sem_tag = MAGIC + wire[7:]
    strs = decode_bn(sem_tag, disc, lambda b: _decode_column(b))
    return _cast_tipo(strs, tag)

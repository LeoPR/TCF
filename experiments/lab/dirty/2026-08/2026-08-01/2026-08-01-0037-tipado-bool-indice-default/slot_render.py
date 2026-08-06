"""Protótipo do `T-TIPADO-BOOL-INDICE` — slots congelados como grafia DEFAULT da tag `b`.

Hoje a rota tipada bool renderiza `true`/`false` como NOMES no corpo core; o null já viaja
como `0` cru (slot 0 pré-alocado). A proposta aprovada pelo owner: o render da tag `b` vira
**slots congelados** — o MESMO domínio do denso b2 (ADR-0037): `null=0` (já é a grafia core),
`false=1`, `true=2` — emitidos pelo core como literais escapados (`\\1`/`\\2`, via o
`_escape_lit` de sempre). O decode aceita slots (canônico, único emitido) E nomes
(decodável-não-emitido — mesmo contrato do modo `C` da ADR-0036: preserva wires antigos).

Fecha o caso que escapava do b2: o candidato CORE/RLE (ex.: `[True]*200` = 1 run).

## O que este módulo é

Protótipo de **fiação**: replica a rota tipada bool do `encoder.py` trocando SÓ o render, e
no decode usa o `_decode_column`/`despolariza`/`_decode_typed` do `src/tcf` — só o cast de
slots é novo. `src/tcf` intocado.
"""
import base64
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[6] / "src"))

from tcf.bitpack import pack_w  # noqa: E402
from tcf.composicional.polaridade import despolariza, polariza  # noqa: E402
from tcf.decoder import _decode_column, _separa_sufixo_polaridade, decode  # noqa: E402
from tcf.encoder import _encode_column, _tipo_single_col  # noqa: E402

MAGIC = "#TCF.8"


def _render_slot(v):
    return None if v is None else ("2" if v else "1")   # dominio CONGELADO: null=0, false=1, true=2


def proto_encode(dados):
    """`(wire, tag)` da rota tipada bool com render SLOT, ou `(None, tag)` se não é bool."""
    t = _tipo_single_col(dados)
    if t is None:
        return None, None
    tag, _render_nomes = t
    if tag != "b":
        return None, tag
    tem_nulo = any(x is None for x in dados)
    strs = [_render_slot(x) for x in dados]
    corpo_core = _encode_column(strs, header="val")
    _suf, _corpo_pol = polariza(corpo_core)
    candidatos = [f"{MAGIC}b\n{corpo_core}"]
    if _suf:
        candidatos.append(f"{MAGIC}b{_suf}\n{_corpo_pol}")
    if not tem_nulo:
        idx = [1 if x else 0 for x in dados]             # b1: dominio implicito false=0/true=1
        b64 = base64.b64encode(pack_w(idx, 1)).decode("ascii")
        candidatos.append(f"{MAGIC}b1{len(dados):x}\n{b64}")
    else:
        idx = [0 if x is None else (2 if x else 1) for x in dados]  # b2: null=0/false=1/true=2
        b64 = base64.b64encode(pack_w(idx, 2)).decode("ascii")
        candidatos.append(f"{MAGIC}b2{len(dados):x}\n{b64}")
    # FLOOR: argmin; empate fica no 1o (core, mais inspecionavel) — igual ao encoder real
    return min(candidatos, key=lambda w: len(w.encode("utf-8"))), tag


def cast_slots(strs):
    """Camada explicita->tipo com slots. Slots = canônico; nomes = decodável-não-emitido
    (contrato do modo `C` da ADR-0036). FAIL-LOUD no resto (`'0'`, `'3'`, `'15'`, ...)."""
    MAPA = {"1": False, "2": True, "false": False, "true": True}
    out = []
    for s in strs:
        if s is None:
            out.append(None)                             # slot 0 atravessa qualquer tag
        elif s in MAPA:
            out.append(MAPA[s])
        else:
            raise ValueError(f"#TCF.8b: valor fora do dominio bool (slots 1/2): {s!r}")
    return out


def proto_decode(wire):
    """Decode real pra TUDO menos o cast. Denso b1/b2 -> `decode` público (já soldado);
    core/polaridade -> despolariza + `_decode_column` do `src/tcf` + `cast_slots` daqui."""
    line1, _sep, body = wire.partition("\n")
    _tag, sufixo = _separa_sufixo_polaridade(line1[6:])
    if sufixo:                                           # polaridade -> corpo canonico primeiro
        body = despolariza(body, sufixo)
        resto = line1[7:-len(sufixo)]
    else:
        resto = line1[7:]
    if resto == "":                                      # modo CORE: cast novo (slots + nomes)
        return cast_slots(_decode_column(body) if body else [])
    return decode(wire)                                  # modo DENSO b1/b2: ja' soldado no src/tcf

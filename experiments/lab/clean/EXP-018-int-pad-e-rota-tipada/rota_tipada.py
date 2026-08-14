"""Protótipo da ABERTURA da rota tipada a specs — sem tocar `src/tcf`.

## O que falta hoje, medido

A rota tipada (`#TCF.8n`, `#TCF.8b`) recusa os DOIS mecanismos que o inteiro precisa:

    encode([1,2,3], nature=SPEC)    -> ValueError: kwargs ['nature']  so' valem no flat de STRING
    encode([1,2,3], min_len=12)     -> ValueError: kwargs ['min_len'] so' valem no flat de STRING

E o `.8H`/multi recusam com a mensagem gêmea (*"é coluna TIPADA (number/bool), não string"*).
Resultado: *"entra int, o spec é int, devolve int"* não é expressável em rota nenhuma.

## O desenho, e onde ele encaixaria no weld

Localizado na investigação de 2026-08-13/14:

| ponto | arquivo | o que entra |
|---|---|---|
| encode | `encoder.py:539` | o spec **depois** do `render` (que para `n` é a builtin `str`) |
| FLOOR | `encoder.py:549-600` | um `candidatos.append` — o spec compete, como toda nature |
| decode | `decoder.py:410-411` | o spec **antes** do `_cast_tipo` |
| header | slot do índice 7 | `#TCF.8n [nome]:id` — verificado livre |

O bool é o precedente exato: ele não tem rota própria, tem **um candidato a mais** no mesmo
`min()`. O int seguiria o mesmo caminho.

## O que este protótipo faz

Reproduz esse fluxo **por fora**, usando só a API pública: aplica o `render` (int→str),
passa o spec, encoda pela rota string, e recompõe o header tipado. No decode, o inverso. O
wire produzido é **exatamente** o que o weld emitiria — e o `run.py` prova o round-trip com
TIPO e a invariante nunca-pior contra o que o encoder emite hoje.

**Não é candidato a weld como está**: é a forma do destino, para medir e validar antes de
tocar no núcleo.
"""

from __future__ import annotations

from tcf import decode as _decode
from tcf import encode as _encode

#: O `render` de cada família tipada, como `_tipo_single_col` os define (encoder.py:98-131).
#: `n` usa a builtin `str`; o `b` usa a tabela congelada. Só `n` interessa aqui.
_RENDER = {"n": str}


def _tag_de(vals) -> "str | None":
    """A tag que `_tipo_single_col` daria — replicada, não importada (é interna)."""
    v = [x for x in vals if x is not None]
    if not v:
        return None
    if all(type(x) is bool for x in v):
        return "b"
    if all(type(x) is int or type(x) is float for x in v):
        from math import isfinite
        if any(type(x) is float and not isfinite(x) for x in v):
            return None
        return "n"
    return None


def encode_tipado_com_spec(vals, spec, *, min_len=None):
    """O wire que o weld emitiria: `#TCF.8n :id` + corpo do spec.

    Devolve `(wire, venceu)` — `venceu=False` quando o FLOOR fica com o núcleo, e aí o
    wire é o que `encode(vals)` já produz hoje, byte a byte.
    """
    tag = _tag_de(vals)
    if tag != "n":
        raise ValueError(f"prototipo cobre so' a familia 'n'; tag={tag!r}")
    base = _encode(vals)                                  # o que o encoder emite HOJE
    grafias = [None if v is None else _RENDER["n"](v) for v in vals]
    kw = {"min_len": min_len} if min_len else {}
    try:
        w_spec = _encode(grafias, nature=spec, **kw)
    except Exception:
        return base, False
    l0, _, corpo = w_spec.partition("\n")
    if ":" not in l0:
        return base, False                                # o FLOOR ja' recusou na rota string
    # recompoe o header TIPADO: `#TCF.8` + tag + o resto do meta da rota string
    cand = "#TCF.8" + tag + l0[len("#TCF.8"):] + "\n" + corpo
    # FLOOR: o spec so' vence se reduzir o que seria emitido
    if len(cand.encode("utf-8")) < len(base.encode("utf-8")):
        return cand, True
    return base, False


def decode_tipado_com_spec(wire, spec):
    """O inverso: aplica o spec ANTES do cast de tipo (o ponto `decoder.py:410-411`)."""
    l0, _, corpo = wire.partition("\n")
    if not l0.startswith("#TCF.8n") or ":" not in l0:
        return _decode(wire)                              # sem spec: o decode de hoje basta
    meta = l0[len("#TCF.8n"):]                            # ' [nome]:id'
    # O spec vai OUT-OF-BAND porque `ipad` ainda nao esta' no registry core — resolucao
    # ESTRITA do ADR-0041. Depois do weld ele estaria la', e o decode resolveria sozinho:
    # e' a diferenca entre prototipo e destino, e ela e' de UMA linha.
    grafias = _decode("#TCF.8" + meta + "\n" + corpo, nature=spec)
    return [None if g is None else int(g) for g in grafias]   # o `_cast_tipo` da familia `n`

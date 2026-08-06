"""Protótipo do `T-DENSO-B2` — denso ternário `#TCF.8b2<n>` com domínio IMPLÍCITO.

`true`/`false`/`null` são tipos PUROS do JSON — o domínio é conhecido a priori, então
declarar o domínio (como o bN tipado `#TCF.8bB2c8` do lab vizinho `2026-07-28-0829`) é
redundante. A proposta estende o denso b1 (bool puro SEM null, já soldado) para o ternário:

    #TCF.8 b 2 c8
           │ │ └── n em hex
           │ └──── modo = 2 bits/símbolo, ÍNDICE 7 (o slot posicional do ADR-0029)
           └──────── tag de tipo, ÍNDICE 6

Domínio implícito CONGELADO: `0=null, 1=false, 2=true`; símbolo **3 = reservado**,
fail-loud no decode. Payload = base64 do `pack_w(idx, 2)` — o MESMO `pack_w`/`unpack_w`
soldado do b1 (`src/tcf/bitpack.py`), nenhuma reimplementação do mecanismo.

## O que este módulo é

Protótipo de **fiação**: `proto_encode` só aceita coluna com tag `b` (via
`_tipo_single_col` do `src/tcf`) E com algum `None` (sem null, o b1 é estritamente menor e
o b2 não se aplica). `proto_decode` faz parse posicional estrito e **fail-loud** em:
símbolo 3, payload de tamanho errado, base64 não-canônico — o `unpack_w` ainda recusa
payload curto e padding não-zero.

`src/tcf` intocado.
"""
import base64
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[6] / "src"))

from tcf.bitpack import pack_w, unpack_w  # noqa: E402
from tcf.encoder import _tipo_single_col  # noqa: E402

MAGIC = "#TCF.8"
DOMINIO = (None, False, True)            # 0=null, 1=false, 2=true — CONGELADO
W = 2


def proto_encode(dados):
    """`(wire, tag, w)` do denso b2, ou `(None, tag, 0)` se não se aplica.

    Aplica-se SÓ a coluna tipada bool COM null. Bool puro sem null -> `None` (o denso b1,
    já soldado, é estritamente menor — o b2 não compete lá).
    """
    t = _tipo_single_col(dados)
    if t is None:
        return None, None, 0
    tag, _render = t
    if tag != "b":
        return None, tag, 0
    if not any(x is None for x in dados):
        return None, tag, 0                          # sem null: o b1 domina, recusa
    idx = [0 if x is None else (2 if x else 1) for x in dados]
    b64 = base64.b64encode(pack_w(idx, W)).decode("ascii")
    # n em HEX: mesma propriedade do b1 — len(hex) <= len(dec) p/ todo n >= 0, e o parse
    # e' posicional (modo = 1o char), entao hex nao colide com o namespace do <modo>.
    return f"{MAGIC}b2{len(dados):x}\n{b64}", tag, W


def proto_decode(wire):
    """Lê o wire denso b2. FAIL-LOUD: símbolo 3, payload de tamanho errado, b64 inválido."""
    line1, sep, payload = wire.partition("\n")
    if not sep:
        raise ValueError(f"wire denso b2 sem corpo: {line1[:12]!r}")
    if line1[:6] != MAGIC or line1[6:7] != "b":
        raise ValueError(f"esperado prefixo {MAGIC}b: {line1[:12]!r}")
    if line1[7:8] != "2":
        raise ValueError(f"esperado modo '2' no indice 7: {line1[:12]!r}")
    try:
        n = int(line1[8:], 16)
    except ValueError:
        raise ValueError(f"n nao-hex no cabecalho: {line1[:12]!r}") from None
    raw = base64.b64decode(payload, validate=True)     # estrito: b64 nao-canonico rejeita
    esperado = (n * W + 7) // 8
    if len(raw) != esperado:                           # tamanho EXATO: truncado/sobra rejeita
        raise ValueError(
            f"payload denso b2 de tamanho errado: {len(raw)} bytes, esperado {esperado}")
    idx = unpack_w(raw, W, n)                          # fail-loud: curto, padding nao-zero
    if 3 in idx:
        raise ValueError("simbolo 3 no denso b2: RESERVADO, wire invalido")
    return [DOMINIO[i] for i in idx]

"""Protótipo do `T-LAZYTYPE-BOOL` — lazytype bool: cabeça congelada + extras declarados.

Coluna concentrada em null/true/false mas COM exceções string ("other", "xxxxx") — hoje a
união bool+str expulsa a coluna pro `.8H`. A proposta: os slots congelados da `TABELA_B2`
(`tipos_internos.py`: null=0, false=1, true=2) + **extras declarados no arquivo a partir do
slot 3**, por primeira aparição, índices empacotados — a mecânica do `dominio_bn`
(ADR-0036), mas com a cabeça bool IMPLÍCITA.

Grafia: `#TCF.8bB<w><n-hex>` — tag `b` no índice 6, `B` (domínio-primeiro, streaming) no
índice 7, como o slot posicional que o `tipado_bn.py` do lab `2026-07-28-0829` já parseava.
O domínio declarado carrega **SÓ os extras** (bool/null não viajam — são conhecidos a
priori). Só modo `B`; `C` fora.

    #TCF.8bB3c8
    other
    xxxxx
    =AbCdEf...        <- índices a w bits: 0=null, 1=false, 2=true, 3+=extras

`src/tcf` intocado — reusa `pack_w`/`unpack_w`, `_encode_column`, `_grafa`/`_le_grafia`/
`dominio`/`candidatos`/`decode_bn` do `dominio_bn`.
"""
import base64
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[6] / "src"))

from tcf.bitpack import pack_w, unpack_w  # noqa: E402
from tcf.composicional.dominio_bn import (  # noqa: E402
    DISC_STREAM, MARCADOR, MAX_W, _grafa, _le_grafia,
)
from tcf.decoder import _decode_column  # noqa: E402
from tcf.encoder import _encode_column  # noqa: E402

MAGIC = "#TCF.8"
BS = chr(92)

#: Cabeça congelada — a MESMA `TABELA_B2` do `tipos_internos.py` (declarada aqui pra o lab
#: não depender de import do módulo novo; consistência verificada no run.py).
CABECA = (None, False, True)                           # null=0, false=1, true=2


def _eh_lazy(dados):
    """Coluna lazytype: união de {bool, None, str} com pelo menos um bool/None E um extra str."""
    if not isinstance(dados, list) or not dados:
        return False
    tipos = {type(x) for x in dados}
    if not tipos <= {bool, type(None), str}:
        return False                                  # int/float/etc. fora do lazytype bool
    return str in tipos and (bool in tipos or type(None) in tipos)


def proto_encode(dados):
    """`(wire, w, extras)` do lazy `bB`, ou `(None, 0, extras)` se não se aplica / recusa."""
    extras = []
    for x in dados:
        if isinstance(x, str) and x not in extras:
            extras.append(x)
    if not extras:
        return None, 0, extras                        # 0 extras -> o b2/core cobrem
    k_total = len(CABECA) + len(extras)
    w = max(2, math.ceil(math.log2(k_total)))
    if w > MAX_W:
        return None, 0, extras                        # recusa: extras > 253 (w>8)
    idx = {None: 0, False: 1, True: 2}
    idx.update({e: 3 + i for i, e in enumerate(extras)})
    b64 = base64.b64encode(pack_w([idx[x] for x in dados], w)).decode("ascii").rstrip("=")
    # dominio = SO' extras, na grafia do core, COMPRIMIDO pelo proprio core (como o dominio_bn)
    _bl = _encode_column([_grafa(e) for e in extras], header="val")
    bloco = _bl[:-1] if _bl.endswith("\n") else _bl
    escapado = "\n".join(BS + ln if ln.startswith(MARCADOR) else ln
                         for ln in bloco.split("\n"))
    return f"{MAGIC}b{DISC_STREAM}{w}{len(dados):x}\n{escapado}\n{MARCADOR}{b64}", w, extras


def proto_decode(wire):
    """Lê o wire lazy `bB`. Fail-loud alinhado ao `decode_bn`: header hex mínimo canônico,
    domínio mal-formado, índice fora da tabela, conteúdo após o bloco de bits."""
    cab, sep, resto = wire.partition("\n")
    if not sep:
        raise ValueError(f"wire lazy bN sem corpo: {cab[:24]!r}")
    if not cab.startswith(MAGIC + "b" + DISC_STREAM):
        raise ValueError(f"esperado prefixo {MAGIC}b{DISC_STREAM}: {cab[:12]!r}")
    campos = cab[len(MAGIC) + 2:]
    if len(campos) < 2 or campos[0] not in "12345678":
        raise ValueError(f"cabecalho bN nao-canonico: largura {campos[:1]!r} fora de 1..{MAX_W}")
    w = int(campos[0])
    nhex = campos[1:]
    if any(c not in "0123456789abcdef" for c in nhex):
        raise ValueError(f"contagem bN nao-hexadecimal-canonica: {nhex!r}")
    n = int(nhex, 16)
    if f"{n:x}" != nhex:                              # grafia MINIMA: sem zero a esquerda
        raise ValueError(f"contagem bN nao-canonica: {nhex!r} (canonico: {n:x})")
    linhas = resto.split("\n")
    alvo = next((j for j, ln in enumerate(linhas) if ln.startswith(MARCADOR)), None)
    if alvo is None:
        raise ValueError(f"wire bN sem o marcador {MARCADOR!r} — corpo nao-canonico")
    if any(ln for ln in linhas[alvo + 1:]):
        raise ValueError(f"conteudo apos o bloco de bits do bN — corpo nao-canonico")
    b64 = linhas[alvo][1:]
    bloco = "\n".join(ln[1:] if ln.startswith(BS + MARCADOR) else ln
                      for ln in linhas[:alvo])
    if not bloco:
        raise ValueError("dominio lazy vazio — a cabeça congelada não se declara")
    extras = [_le_grafia(s) for s in _decode_column(bloco + "\n")]
    tabela = list(CABECA) + extras
    if len(tabela) > (1 << w):
        raise ValueError(f"tabela lazy com {len(tabela)} valores nao cabe em {w} bits")
    raw = base64.b64decode(b64 + "=" * (-len(b64) % 4))
    saida = []
    for i in unpack_w(raw, w, n):
        if i >= len(tabela):
            raise ValueError(
                f"indice {i} fora da tabela lazy de {len(tabela)} valores — corpo nao-canonico")
        saida.append(tabela[i])
    return saida

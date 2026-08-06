"""Fiação do lazy bool na rota real — detector, FLOOR, dispatch, decode estrito.

Reusa `lazy_bn.py` do lab vizinho `2026-08-01-0229` (importado, não copiado) e responde às
6 perguntas da fiação. `src/tcf` intocado.
"""
import sys
from pathlib import Path

RAIZ = Path(__file__).parent
VIZINHO = RAIZ.parents[1] / "2026-08-01" / "2026-08-01-0229-lazytype-bool-extras"
sys.path.insert(0, str(VIZINHO))
sys.path.insert(0, str(RAIZ.parents[6] / "src"))

from lazy_bn import proto_encode  # noqa: E402

from tcf.composicional.dominio_bn import DISC_STREAM, MARCADOR, _le_grafia  # noqa: E402
from tcf.decoder import _decode_column  # noqa: E402

MAGIC = "#TCF.8"
BS = chr(92)


def detecta_lazy(dados):
    """Detector da rota lazy: união bool+str com tipo preservável.

    Entra: vals ⊆ {bool, str, None} com >=1 bool E >=1 str.
    NÃO entra: str+null SEM bool (flat); bool±null sem str (tipado puro b1/b2/core);
    qualquer outro tipo no mix (bool+str+int -> lazytype-numérico é OUTRO ticket).
    """
    if not isinstance(dados, list) or not dados:
        return False
    tipos = {type(x) for x in dados}
    if not tipos <= {bool, str, type(None)}:
        return False
    return bool in tipos and str in tipos


def proto_encode_checked(dados):
    """`proto_encode` do lab 0229 + o check que o caminho do domínio NÃO herda de graça:
    LF embutido num EXTRA. O fail-loud de LF mora no `encode` público flat, NÃO no
    `_encode_column` (medido neste lab: `_encode_column(['a\\nb'])` devolve 'a\\nb\\n'
    calado) — um extra com LF corromperia o parse do domínio. O weld DEVE adicionar este
    check explicitamente."""
    extras = [x for x in dados if isinstance(x, str)]
    if any("\n" in e for e in extras):
        raise ValueError("extra lazy com LF embutido nao e' representavel "
                         "(LF delimita linhas do dominio)")
    return proto_encode(dados)


def decode_estrito(wire):
    """Decode lazy com a checagem de canonicidade que o lab 0229 ainda não tinha:
    o domínio declarado NÃO pode redeclarar a cabeça congelada — linha `0` cru (que
    `_le_grafia` lê como None) = grafia INVÁLIDA, fail-loud."""
    cab, sep, resto = wire.partition("\n")
    if not sep or not cab.startswith(MAGIC + "b" + DISC_STREAM):
        raise ValueError(f"esperado prefixo {MAGIC}b{DISC_STREAM}: {cab[:12]!r}")
    linhas = resto.split("\n")
    alvo = next((j for j, ln in enumerate(linhas) if ln.startswith(MARCADOR)), None)
    if alvo is None:
        raise ValueError(f"wire bN sem o marcador {MARCADOR!r} — corpo nao-canonico")
    bloco = "\n".join(ln[1:] if ln.startswith(BS + MARCADOR) else ln
                      for ln in linhas[:alvo])
    # `_decode_column` ja' devolve o `0` cru como None (slot 0) — None aqui = cabeça redeclarada.
    # Domínio VAZIO de linhas so' acontece com o extra "" (string vazia): o bloco e' a linha
    # vazia e `_decode_column("\n")` devolve [""] — VALIDO, espelhando o bugfix `[:-1]` do
    # `dominio_bn` (lab 2026-07-28). Rejeita-se lista vazia de VERDADE, nao a linha vazia.
    decod = _decode_column(bloco + "\n")
    if not decod:
        raise ValueError("dominio lazy vazio — corpo nao-canonico")
    if any(s is None for s in decod):
        raise ValueError(
            "dominio lazy redeclara a cabeça congelada (slot 0 = null) — grafia "
            "nao-canonica; a cabeça 0/1/2 é implícita e NUNCA se declara")
    extras = [_le_grafia(s) for s in decod]
    # --- payload: header + bits (espelho do lazy_bn, com os extras ja' validados acima)
    import base64

    from tcf.bitpack import unpack_w
    from tcf.composicional.dominio_bn import MAX_W
    campos = cab[len(MAGIC) + 2:]
    if len(campos) < 2 or campos[0] not in "12345678":
        raise ValueError(f"cabecalho bN nao-canonico: largura {campos[:1]!r} fora de 1..{MAX_W}")
    w = int(campos[0])
    nhex = campos[1:]
    if any(c not in "0123456789abcdef" for c in nhex):
        raise ValueError(f"contagem bN nao-hexadecimal-canonica: {nhex!r}")
    n = int(nhex, 16)
    if f"{n:x}" != nhex:
        raise ValueError(f"contagem bN nao-canonico: {nhex!r} (canonico: {n:x})")
    if any(ln for ln in linhas[alvo + 1:]):
        raise ValueError("conteudo apos o bloco de bits do bN — corpo nao-canonico")
    b64 = linhas[alvo][1:]
    tabela = [None, False, True] + extras
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


def encode_com_lazy(dados, **kw):
    """Simula a rota INSERIDA: detector lazy primeiro, senão o encode real de sempre."""
    from tcf import encode
    if detecta_lazy(dados):
        wire, _w, _x = proto_encode(dados)
        if wire is not None:
            return wire
    return encode(dados, **kw)

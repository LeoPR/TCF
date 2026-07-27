"""Domínio comprimido pelo core + alinhamento de bits — refino da escada bN.

    "se temos um início com RLE + referências (…) dá pra pegar a lista e comprimir ela
     internamente. `M*ale / Fem2 / CIhmASAEyQvAQQZokA==` — é uma compressão boba, mas parece
     que é aproveitando os índices inter tipos. (…) ver se a expansão está OK quando ela não
     casa com o número de bits, se a lista é ímpar, essas coisas."

## As três perguntas

1. **Dá pra comprimir o domínio com o que já existe?** Sim, literalmente: o domínio é uma
   mini-coluna, então `_encode_column(dom)` serve. `Male\\nFemale\\n` (12 B) vira
   `M*ale\\nFem2\\n` (11 B), reusando a tabela de fragmentos do próprio core.

2. **Onde o domínio termina e o b64 começa?** Aqui mora a armadilha: o **seq-RLE colapsa
   linhas**. `['100','101','102','103']` vira `*4+1|\\100` — **1 linha para 4 valores**. Logo
   "leia k linhas" **não funciona**. Duas saídas medidas aqui:

       V-len   declara o tamanho do bloco de domínio no cabeçalho (custa bytes)
       V-b64   põe o b64 PRIMEIRO — o comprimento dele e' DEDUZIVEL de `n` e `w`,
               que ja' estao no cabecalho. Custo ZERO.

   `V-b64` é a materialização mínima: deduz em vez de declarar.

3. **O alinhamento fecha?** `n*w` raramente é múltiplo de 8, e o base64 ainda arredonda para
   múltiplos de 3 bytes. Os bits do rabo são lixo. O leitor **tem de parar em `n`**, e `n` já
   viaja no cabeçalho. Este módulo varre isso exaustivamente em vez de assumir.

`src/tcf` intocado — estudo, não solda.
"""
import base64
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[6] / "src"))

from tcf.bitpack import pack_w  # noqa: E402
from tcf.encoder import _encode_column  # noqa: E402

MAGIC = "#TCF.8"
BS = chr(92)


def largura(k):
    return 0 if k <= 1 else max(1, math.ceil(math.log2(k)))


def dominio(valores):
    """Domínio canônico: null no slot 0 (pré-alocado pelo formato), resto por 1ª aparição."""
    tem_nulo = any(v is None for v in valores)
    vistos = {}
    for v in valores:
        if v is not None and v not in vistos:
            vistos[v] = True
    return ([None] if tem_nulo else []) + list(vistos.keys())


def _grafa(v):
    """`0` cru = slot nulo; `\\0` = o literal `"0"`. A grafia do core, não uma nova.

    Terceira aparição desta colisão no projeto (weld do slot nulo, lab `2026-07-26-2126`,
    lab `2026-07-27-1608`). Invariante: quem grafa valores ao lado do slot nulo usa a grafia
    do core.
    """
    if v is None:
        return "0"
    return BS + v if v == "0" else v


def _le_grafia(s):
    if s == "0":
        return None
    return s[1:] if s.startswith(BS) else s


def _b64_len(n, w):
    """Comprimento do bloco base64 — **deduzível** de `n` e `w`, que já estão no cabeçalho."""
    nbytes = (n * w + 7) // 8
    return 4 * ((nbytes + 2) // 3)


# ------------------------------------------------------------------ as 3 grafias do domínio
def dom_cru(dom):
    """Uma linha por valor, sem compressão. É o que o lab `1608` fazia."""
    return "\n".join(_grafa(v) for v in dom)


def dom_core(dom):
    """O domínio passado pelo **core** — reusa OBAT/HCC/seq-RLE, zero código novo."""
    return _encode_column([_grafa(v) for v in dom]).rstrip("\n")


# ------------------------------------------------------------------ as 2 montagens
def monta_v_len(valores, comprimir):
    """`#TCF.8B<w><n_hex>:<len_dom_hex>\\n<dominio>\\n<b64>` — declara o tamanho do domínio."""
    dom = dominio(valores)
    k = len(dom)
    w = largura(k)
    if w == 0:
        return None, 0, k
    idx = {v: i for i, v in enumerate(dom)}
    b64 = base64.b64encode(pack_w([idx[v] for v in valores], w)).decode("ascii")
    bloco = dom_core(dom) if comprimir else dom_cru(dom)
    nb = len(bloco.encode())
    return f"{MAGIC}B{w}{len(valores):x}:{nb:x}\n{bloco}\n{b64}", w, k


def monta_v_b64(valores, comprimir):
    """`#TCF.8B<w><n_hex>\\n<b64>\\n<dominio>` — o b64 vem PRIMEIRO.

    O comprimento dele é deduzível de `n` e `w`; o que sobra é o domínio. **Custo zero** de
    declaração — é o padrão de materialização mínima do projeto.
    """
    dom = dominio(valores)
    k = len(dom)
    w = largura(k)
    if w == 0:
        return None, 0, k
    idx = {v: i for i, v in enumerate(dom)}
    b64 = base64.b64encode(pack_w([idx[v] for v in valores], w)).decode("ascii")
    bloco = dom_core(dom) if comprimir else dom_cru(dom)
    return f"{MAGIC}B{w}{len(valores):x}\n{b64}\n{bloco}", w, k


# ------------------------------------------------------------------ leitores INDEPENDENTES
def _desempacota(b64, n, w):
    """Desempacota exatamente `n` índices de largura `w`. Ignora o rabo de padding."""
    dados = base64.b64decode(b64)
    saida, acc, nbits = [], 0, 0
    for byte in dados:
        acc = (acc << 8) | byte
        nbits += 8
        while nbits >= w and len(saida) < n:
            nbits -= w
            saida.append((acc >> nbits) & ((1 << w) - 1))
        acc &= (1 << nbits) - 1
    return saida


def _dom_de_bloco(bloco, comprimido):
    if comprimido:
        from tcf.decoder import _decode_column

        return [_le_grafia(s) for s in _decode_column(bloco + "\n")]
    return [_le_grafia(s) for s in bloco.split("\n")]


def le_v_len(wire, comprimido):
    cab, _, resto = wire.partition("\n")
    corpo = cab[len(MAGIC) + 1:]
    w = int(corpo[0])
    n_hex, _, len_hex = corpo[1:].partition(":")
    n, nb = int(n_hex, 16), int(len_hex, 16)
    bloco = resto.encode()[:nb].decode()
    b64 = resto.encode()[nb + 1:].decode()
    dom = _dom_de_bloco(bloco, comprimido)
    return [dom[i] for i in _desempacota(b64, n, w)]


def le_v_b64(wire, comprimido):
    cab, _, resto = wire.partition("\n")
    corpo = cab[len(MAGIC) + 1:]
    w = int(corpo[0])
    n = int(corpo[1:], 16)
    nb64 = _b64_len(n, w)                    # DEDUZIDO, nao declarado
    b64 = resto[:nb64]
    bloco = resto[nb64 + 1:]
    dom = _dom_de_bloco(bloco, comprimido)
    return [dom[i] for i in _desempacota(b64, n, w)]

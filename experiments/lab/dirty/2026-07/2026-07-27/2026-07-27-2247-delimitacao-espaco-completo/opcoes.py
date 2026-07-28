"""Sete formas de delimitar o domínio — o espaço completo, com escape explorado de verdade.

    "queria discordar com `=` colidir: se por acaso alguém da lista tiver `=`, obviamente
     poderíamos fazer escape nele. Também dá pra adotar algum caractere como default e
     desambiguar se alguém na lista tiver ele (…) a gente já tem muita ferramenta e técnicas
     que estudamos nos últimos meses pra desambiguar, só precisamos escolher as mais baratas.
     (…) lembre que colocar a marcação no cabeçalho gasta bytes de qualquer forma, então tem
     que ver onde jogar de forma inteligente."

Discordância procedente. Eu tratei colisão como veredito quando é **custo condicional**: o
escape resolve, e só se paga onde ocorre.

## O espaço

    M1  `\\|`            marcador da CLASSE DE ESCAPE (o core nunca emite)     2 B fixos
    M2  `=` + escape    default; `\\=` escapa a linha de dado que colide       1 B + 1/colisao
    M3  char ELEITO     do complemento do alfabeto do dominio, declarado       2 B fixos
    M4  padding a 2^w   delimitacao DEDUZIVEL de `w`; sem seq-RLE no dominio   (2^w - k) B
    M5  `L<hex>`        contagem de linhas no cabecalho                        2-3 B
    M6  `:<hex>`        tamanho em BYTES (a convencao do multi-col)            3-5 B
    M7  dominio ULTIMO  o b64 tem tamanho deduzivel; nada a delimitar          0 B, sem stream

## Onde jogar o byte

Header e corpo custam o mesmo byte, mas **não a mesma coisa**: marcação no corpo não precisa
ser conhecida antes de escrever, então o *encoder* também streama. Marcação no cabeçalho
obriga a bufferizar ou voltar atrás. É o eixo que separa M1/M2/M3 de M5/M6.

## Sobre reusar o multi-col

O `.8M` já declara tamanho por coluna em hex (`multi/core.py:_serialize`), então M6 reusa
convenção existente. Mas o single-col **não pode depender do multi** para se ler — M6 aqui é
a mesma ideia reimplementada, não uma dependência.

`src/tcf` intocado.
"""
import base64
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[6] / "src"))

from tcf.bitpack import pack_w  # noqa: E402
from tcf.decoder import _decode_column  # noqa: E402
from tcf.encoder import _encode_column  # noqa: E402

MAGIC = "#TCF.8"
BS = chr(92)

#: Chars que o core PODE emitir logo após um `\` (medido no lab 2026-07-27-2231).
SEGUEM_ESCAPE = frozenset("*0123456789" + BS + "^~")

#: Pontuação fora da gramática — o mesmo critério de classe da polaridade (ADR-0035).
FAIXA = tuple(c for c in (chr(i) for i in range(0x21, 0x7F))
              if c not in set("*~^,|" + BS) and not c.isdigit() and not c.isalpha())

PADRAO = "="          # o char default do M2 — a sua proposta


def largura(k):
    return 0 if k <= 1 else max(1, math.ceil(math.log2(k)))


def dominio(valores):
    tem_nulo = any(v is None for v in valores)
    vistos = {}
    for v in valores:
        if v is not None and v not in vistos:
            vistos[v] = True
    return ([None] if tem_nulo else []) + list(vistos.keys())


def _grafa(v):
    """`0` cru = slot nulo; `\\0` = o literal `"0"`. SÓ esse valor é escapado aqui."""
    return "0" if v is None else (BS + v if v == "0" else v)


def _le_grafia(s):
    """Desfaz `_grafa`, e só ela — a assimetria já custou 4 bugs no projeto."""
    if s == "0":
        return None
    return "0" if s == BS + "0" else s


def bloco(dom, seq_rle=True):
    """Domínio pelo core. `seq_rle=False` garante 1 linha por valor (necessário no M4)."""
    from tcf.pipeline import PipelineConfig

    cfg = None if seq_rle else PipelineConfig(hcc_seq_rle=False)
    txt = _encode_column([_grafa(v) for v in dom], cfg=cfg) if cfg else \
        _encode_column([_grafa(v) for v in dom])
    return txt.rstrip("\n")


def _bits(valores, dom, w):
    idx = {v: i for i, v in enumerate(dom)}
    return base64.b64encode(pack_w([idx[v] for v in valores], w)).decode("ascii").rstrip("=")


def _desempacota(b64, dom, n, w):
    raw = base64.b64decode(b64 + "=" * (-len(b64) % 4))
    saida, acc, nbits = [], 0, 0
    for byte in raw:
        acc = (acc << 8) | byte
        nbits += 8
        while nbits >= w and len(saida) < n:
            nbits -= w
            saida.append(dom[(acc >> nbits) & ((1 << w) - 1)])
        acc &= (1 << nbits) - 1
    return saida


def _cab(w, n, extra=""):
    return f"{MAGIC}B{w}{n:x}{extra}"


def _le_cab(cab):
    corpo = cab[len(MAGIC) + 1:]
    w = int(corpo[0])
    return w, corpo[1:]


def _prep(valores, seq_rle=True):
    dom = dominio(valores)
    k = len(dom)
    w = largura(k)
    if w == 0:
        return None
    return dom, k, w, bloco(dom, seq_rle), _bits(valores, dom, w)


# ================================================================ M1 — classe de escape
def m1(valores):
    p = _prep(valores)
    if p is None:
        return None
    dom, k, w, bl, b64 = p
    return f"{_cab(w, len(valores))}\n{bl}\n{BS}|{b64}"


def le_m1(wire):
    cab, _, resto = wire.partition("\n")
    w, n_hex = _le_cab(cab)
    n = int(n_hex, 16)
    linhas = resto.split("\n")
    i = next(j for j, ln in enumerate(linhas) if ln.startswith(BS + "|"))
    dom = [_le_grafia(s) for s in _decode_column("\n".join(linhas[:i]) + "\n")]
    return _desempacota(linhas[i][2:], dom, n, w)


# ================================================================ M2 — default + escape
def m2(valores, char=PADRAO):
    """Marcador de 1 char. Linha de dado que comece com ele ganha `\\` na frente."""
    p = _prep(valores)
    if p is None:
        return None
    dom, k, w, bl, b64 = p
    linhas = [(BS + ln if ln.startswith(char) else ln) for ln in bl.split("\n")]
    return f"{_cab(w, len(valores))}\n" + "\n".join(linhas) + f"\n{char}{b64}"


def le_m2(wire, char=PADRAO):
    cab, _, resto = wire.partition("\n")
    w, n_hex = _le_cab(cab)
    n = int(n_hex, 16)
    linhas = resto.split("\n")
    i = next(j for j, ln in enumerate(linhas) if ln.startswith(char))
    dom_l = [(ln[1:] if ln.startswith(BS + char) else ln) for ln in linhas[:i]]
    dom = [_le_grafia(s) for s in _decode_column("\n".join(dom_l) + "\n")]
    return _desempacota(linhas[i][1:], dom, n, w)


def escapes_m2(valores, char=PADRAO):
    p = _prep(valores)
    return 0 if p is None else sum(1 for ln in p[3].split("\n") if ln.startswith(char))


# ================================================================ M3 — char eleito
def elege(bl):
    """Menor char da FAIXA que o bloco do domínio não usa — o critério da polaridade."""
    usados = set(bl)
    for c in FAIXA:
        if c not in usados:
            return c
    return None


def m3(valores):
    p = _prep(valores)
    if p is None:
        return None
    dom, k, w, bl, b64 = p
    c = elege(bl)
    if c is None:
        return None
    return f"{_cab(w, len(valores), c)}\n{bl}\n{c}{b64}"


def le_m3(wire):
    cab, _, resto = wire.partition("\n")
    w, sufixo = _le_cab(cab)
    n_hex, c = sufixo[:-1], sufixo[-1]
    n = int(n_hex, 16)
    linhas = resto.split("\n")
    i = next(j for j, ln in enumerate(linhas) if ln.startswith(c))
    dom = [_le_grafia(s) for s in _decode_column("\n".join(linhas[:i]) + "\n")]
    return _desempacota(linhas[i][1:], dom, n, w)


# ================================================================ M4 — padding a 2^w
def m4(valores):
    """Domínio preenchido até `2^w` linhas. A fronteira sai de `w` — **0 B de declaração**."""
    p = _prep(valores, seq_rle=False)
    if p is None:
        return None
    dom, k, w, bl, b64 = p
    linhas = bl.split("\n")
    if len(linhas) != k:                       # sem seq-RLE deve ser 1 linha por valor
        return None
    linhas += [""] * ((1 << w) - k)            # slots nao usados = linha vazia
    return f"{_cab(w, len(valores))}\n" + "\n".join(linhas) + f"\n{b64}"


def le_m4(wire):
    cab, _, resto = wire.partition("\n")
    w, n_hex = _le_cab(cab)
    n = int(n_hex, 16)
    linhas = resto.split("\n")
    nl = 1 << w                                # DEDUZIDO de w
    dom_l = [ln for ln in linhas[:nl]]
    while dom_l and dom_l[-1] == "":
        dom_l.pop()
    dom = [_le_grafia(s) for s in _decode_column("\n".join(dom_l) + "\n")]
    return _desempacota(linhas[nl], dom, n, w)


# ================================================================ M5 — contagem de linhas
def m5(valores):
    p = _prep(valores)
    if p is None:
        return None
    dom, k, w, bl, b64 = p
    return f"{_cab(w, len(valores), 'L' + format(len(bl.split(chr(10))), 'x'))}\n{bl}\n{b64}"


def le_m5(wire):
    cab, _, resto = wire.partition("\n")
    w, sufixo = _le_cab(cab)
    n_hex, _, nl_hex = sufixo.partition("L")
    n, nl = int(n_hex, 16), int(nl_hex, 16)
    linhas = resto.split("\n")
    dom = [_le_grafia(s) for s in _decode_column("\n".join(linhas[:nl]) + "\n")]
    return _desempacota(linhas[nl], dom, n, w)


# ================================================================ M6 — tamanho em bytes
def m6(valores):
    """A convenção do `.8M` (tamanho em hex). Reimplementada — o single-col não depende dele."""
    p = _prep(valores)
    if p is None:
        return None
    dom, k, w, bl, b64 = p
    return f"{_cab(w, len(valores), ':' + format(len(bl.encode()), 'x'))}\n{bl}\n{b64}"


def le_m6(wire):
    cab, _, resto = wire.partition("\n")
    w, sufixo = _le_cab(cab)
    n_hex, _, nb_hex = sufixo.partition(":")
    n, nb = int(n_hex, 16), int(nb_hex, 16)
    b = resto.encode()
    dom = [_le_grafia(s) for s in _decode_column(b[:nb].decode() + "\n")]
    return _desempacota(b[nb + 1:].decode(), dom, n, w)


# ================================================================ M7 — domínio por último
def m7(valores):
    p = _prep(valores)
    if p is None:
        return None
    dom, k, w, bl, b64 = p
    return f"{_cab(w, len(valores))}\n{b64}\n{bl}"


def le_m7(wire):
    cab, _, resto = wire.partition("\n")
    w, n_hex = _le_cab(cab)
    n = int(n_hex, 16)
    nbytes = (n * w + 7) // 8
    nb64 = (nbytes * 8 + 5) // 6                # DEDUZIDO (sem padding)
    dom = [_le_grafia(s) for s in _decode_column(resto[nb64 + 1:] + "\n")]
    return _desempacota(resto[:nb64], dom, n, w)


OPCOES = [("M1", m1, le_m1, "`\\|` classe de escape", "corpo"),
          ("M2", m2, le_m2, "`=` default + escape", "corpo"),
          ("M3", m3, le_m3, "char eleito, declarado", "ambos"),
          ("M4", m4, le_m4, "padding a 2^w", "corpo"),
          ("M5", m5, le_m5, "`L<hex>` linhas", "cabeçalho"),
          ("M6", m6, le_m6, "`:<hex>` bytes (multi-col)", "cabeçalho"),
          ("M7", m7, le_m7, "domínio por último", "nenhum")]

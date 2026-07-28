"""Quatro montagens do bloco bN — e a métrica que faltava: **quanto se bufferiza**.

    "na questão do b64 primeiro é uma questão de ponto de vista, infelizmente teríamos que
     gastar algo pra deixar a lista antes, isso porque se deixar a lista depois e a transmissão
     for em stream, tem que esperar carregar tudo pra saber que é a lista. (…) a lista no final
     é só pra uma questão de lote total. Eu gostei desse formato, poderíamos ter os dois, e esse
     como formato de compressão extra. (…) o marcador `==`, se o arquivo estiver íntegro,
     poderia ser dispensado e colocado na hora de decodificar, mas ele poderia ser usado no
     começo pra diferenciar da lista também."

O lab anterior (`2026-07-27-1647`) escolheu **b64 primeiro** porque custa 0 B de declaração.
Isso mediu o eixo errado sozinho: com o domínio no fim, **nenhum valor sai antes de o payload
inteiro chegar**. Aqui a métrica de streaming entra ao lado dos bytes.

## As quatro

    F1  dominio primeiro + CONTAGEM DE LINHAS do bloco no cabecalho
    F2  dominio primeiro + MARCADOR `=` abrindo o b64, e o padding `=` DROPADO
    F3  b64 primeiro, dominio no fim                    (o do lab anterior)
    F4  dominio primeiro + TAMANHO EM BYTES no cabecalho

## Por que a contagem de linhas, e não `k`

O seq-RLE **colapsa** o domínio: `['100','101','102','103']` vira **1 linha** (`*4+1|\\100`).
Então `k` não diz quantas linhas ler. A contagem de linhas emitidas, sim.

## O `=` é DEDUZÍVEL

O padding do base64 sai do número de bytes, que sai de `n` e `w` — ambos no cabeçalho.
Verificado: dropar e recolocar reconstrói byte a byte. Economiza 0-2 B, e libera o `=` para
ser **marcador de abertura** em vez de terminador, que foi a sua ideia.

`src/tcf` intocado — estudo.
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
    """`0` cru = slot nulo; `\\0` = o literal `"0"`. A grafia do core."""
    if v is None:
        return "0"
    return BS + v if v == "0" else v


def _le_grafia(s):
    if s == "0":
        return None
    return s[1:] if s.startswith(BS) else s


def bloco_dominio(dom):
    """O domínio pelo core — a mini-coluna. Pode ter MENOS linhas que `k` (seq-RLE)."""
    return _encode_column([_grafa(v) for v in dom]).rstrip("\n")


def le_bloco_dominio(bloco):
    return [_le_grafia(s) for s in _decode_column(bloco + "\n")]


def _bits(valores, dom, w):
    idx = {v: i for i, v in enumerate(dom)}
    return pack_w([idx[v] for v in valores], w)


def _b64_len_com_pad(n, w):
    nbytes = (n * w + 7) // 8
    return 4 * ((nbytes + 2) // 3)


def _b64_len_sem_pad(n, w):
    """Sem o `=`: 4/3 arredondado pra cima, sem completar o quarteto."""
    nbytes = (n * w + 7) // 8
    return (nbytes * 8 + 5) // 6


def _prep(valores):
    dom = dominio(valores)
    k = len(dom)
    w = largura(k)
    if w == 0:
        return None
    return dom, k, w, bloco_dominio(dom), _bits(valores, dom, w)


# ------------------------------------------------------------------ F1: contagem de linhas
def monta_f1(valores):
    p = _prep(valores)
    if p is None:
        return None
    dom, k, w, bloco, raw = p
    nl = len(bloco.split("\n"))
    b64 = base64.b64encode(raw).decode("ascii")
    return f"{MAGIC}B{w}{len(valores):x}L{nl:x}\n{bloco}\n{b64}"


def le_f1(wire):
    cab, _, resto = wire.partition("\n")
    corpo = cab[len(MAGIC) + 1:]
    w = int(corpo[0])
    n_hex, _, nl_hex = corpo[1:].partition("L")
    n, nl = int(n_hex, 16), int(nl_hex, 16)
    linhas = resto.split("\n")
    dom = le_bloco_dominio("\n".join(linhas[:nl]))
    return _expande(base64.b64decode(linhas[nl]), dom, n, w)


# ------------------------------------------------------------------ F2: marcador `=`
def monta_f2(valores):
    """O `=` abre o b64 (a sua ideia) e o padding some — ele e' deduzivel."""
    p = _prep(valores)
    if p is None:
        return None
    dom, k, w, bloco, raw = p
    b64 = base64.b64encode(raw).decode("ascii").rstrip("=")
    return f"{MAGIC}B{w}{len(valores):x}\n{bloco}\n={b64}"


def le_f2(wire):
    cab, _, resto = wire.partition("\n")
    corpo = cab[len(MAGIC) + 1:]
    w, n = int(corpo[0]), int(corpo[1:], 16)
    linhas = resto.split("\n")
    # o bloco do b64 e' a linha que ABRE com `=`; o resto antes dela e' o dominio
    i = next(j for j, ln in enumerate(linhas) if ln.startswith("="))
    dom = le_bloco_dominio("\n".join(linhas[:i]))
    b64 = linhas[i][1:]
    raw = base64.b64decode(b64 + "=" * (-len(b64) % 4))
    return _expande(raw, dom, n, w)


# ------------------------------------------------------------------ F3: b64 primeiro
def monta_f3(valores):
    p = _prep(valores)
    if p is None:
        return None
    dom, k, w, bloco, raw = p
    b64 = base64.b64encode(raw).decode("ascii")
    return f"{MAGIC}B{w}{len(valores):x}\n{b64}\n{bloco}"


def le_f3(wire):
    cab, _, resto = wire.partition("\n")
    corpo = cab[len(MAGIC) + 1:]
    w, n = int(corpo[0]), int(corpo[1:], 16)
    nb = _b64_len_com_pad(n, w)
    return _expande(base64.b64decode(resto[:nb]), le_bloco_dominio(resto[nb + 1:]), n, w)


# ------------------------------------------------------------------ F4: tamanho em bytes
def monta_f4(valores):
    p = _prep(valores)
    if p is None:
        return None
    dom, k, w, bloco, raw = p
    nb = len(bloco.encode())
    b64 = base64.b64encode(raw).decode("ascii")
    return f"{MAGIC}B{w}{len(valores):x}:{nb:x}\n{bloco}\n{b64}"


def le_f4(wire):
    cab, _, resto = wire.partition("\n")
    corpo = cab[len(MAGIC) + 1:]
    w = int(corpo[0])
    n_hex, _, nb_hex = corpo[1:].partition(":")
    n, nb = int(n_hex, 16), int(nb_hex, 16)
    b = resto.encode()
    return _expande(base64.b64decode(b[nb + 1:]), le_bloco_dominio(b[:nb].decode()), n, w)


# ------------------------------------------------------------------ comum
def _expande(raw, dom, n, w):
    """Desempacota EXATAMENTE `n` indices. O rabo de padding e' ignorado por construcao."""
    saida, acc, nbits = [], 0, 0
    for byte in raw:
        acc = (acc << 8) | byte
        nbits += 8
        while nbits >= w and len(saida) < n:
            nbits -= w
            saida.append(dom[(acc >> nbits) & ((1 << w) - 1)])
        acc &= (1 << nbits) - 1
    return saida


def prefixo_ate_1o_valor(wire, variante):
    """**Quantos bytes o leitor precisa bufferizar antes de emitir o 1º valor.**

    É a métrica que o eixo de bytes escondia. Com o domínio no FIM, o leitor não sabe o que
    os bits significam até o payload inteiro chegar — logo o prefixo é o wire todo.
    """
    cab, _, resto = wire.partition("\n")
    if variante == "F3":
        return len(wire.encode())                      # dominio no fim: espera tudo
    # dominio primeiro: cabecalho + bloco de dominio + 1 quarteto de b64
    linhas = resto.split("\n")
    if variante == "F1":
        nl = int(cab.partition("L")[2], 16)
        pre = "\n".join(linhas[:nl])
    elif variante == "F2":
        i = next(j for j, ln in enumerate(linhas) if ln.startswith("="))
        pre = "\n".join(linhas[:i])
    else:                                              # F4
        nb = int(cab.rpartition(":")[2], 16)
        pre = resto.encode()[:nb].decode()
    return len((cab + "\n" + pre + "\n").encode()) + 4

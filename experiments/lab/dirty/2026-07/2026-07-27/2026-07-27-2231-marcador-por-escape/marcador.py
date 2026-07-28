"""O marcador de fronteira pelo ESCAPE que já existe.

    "o `=` foi meramente um exemplo ilustrativo, obviamente eu estava falando de um caracter
     de diferenciação, teoricamente qualquer um que dê escape — a gente já trabalhou com
     escape, não tem como usar o mesmo ou um escape diferente?"

Eu tinha travado no `=` literal e concluído que o marcador colide com dado. A pergunta certa
era outra, e a resposta está na própria gramática.

## O que o core NUNCA emite

Num corpo canônico, `\\` só aparece seguido de:

    *  0 1 2 3 4 5 6 7 8 9  \\  ^  ~

Medido, varrendo os 95 imprimíveis: `_escape_lit` escapa corrida de dígito, `*`, `\\` e `~`;
o `^`-líder é escapado à parte. **Mais nada.**

Logo `\\` + qualquer outro char é uma sequência que o core **não consegue produzir**. Não é
"raro" — é **impossível pela gramática**. Um valor de dado com `\\` vira `\\\\` (dois), com `|`
fica `|` cru, com `=` fica `=` cru.

## Por que isso é melhor do que as duas tentativas anteriores

    F2  `=` cru        colide com dado que comece com `=`        (medido: falha)
    F1  contagem de linhas no cabecalho                          robusto, MAS...
    F5  `\\|` marcador  impossivel de colidir, por construcao      2 B

O detalhe do F1 que só aparece pensando em stream: **o encoder precisa terminar o bloco do
domínio para contar as linhas antes de escrever o cabeçalho**. Com o marcador, ele escreve
cabeçalho → domínio → marcador → bits, sem voltar atrás. Streaming dos **dois** lados.

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

#: Chars que o core PODE emitir logo depois de um `\`. Medido, não suposto.
SEGUEM_ESCAPE = frozenset("*0123456789" + BS + "^~")

#: O marcador. `\|` — `|` nunca segue um `\` num corpo canônico.
MARCADOR = BS + "|"


def marcador_valido(m):
    """Um marcador de 2 chars só é seguro se o 2º char nunca seguir um `\\` no core."""
    return len(m) == 2 and m[0] == BS and m[1] not in SEGUEM_ESCAPE


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
    """`0` cru = slot nulo; `\\0` = o literal `"0"`. Só ESSE valor é escapado."""
    if v is None:
        return "0"
    return BS + v if v == "0" else v


def _le_grafia(s):
    """Desfaz `_grafa` — e SÓ ela.

    **Bug corrigido aqui.** A primeira versão tirava QUALQUER `\\` inicial, mas `_grafa` só
    escapa o valor `"0"`. Um dado que já começa com `\\` (ex.: `\\temp`) vem do core intacto e
    era mutilado para `temp`; o valor `\\|` virava `|`. Assimetria minha, não do core — que
    faz o próprio escape e o desfaz sozinho antes de chegar aqui.

    É a mesma classe do bug do slot nulo (3ª aparição): quem grafa ao lado do slot 0 tem de
    desfazer exatamente o que fez, nem mais.
    """
    if s == "0":
        return None
    return "0" if s == BS + "0" else s


def monta(valores, marcador=MARCADOR, sem_padding=True):
    """`#TCF.8B<w><n_hex>\\n<dominio>\\n<marcador><b64>`.

    O domínio vem PRIMEIRO (streaming de leitura), o marcador abre os bits, e o padding `=`
    do base64 é dropado — ele é deduzível de `n` e `w`.
    """
    dom = dominio(valores)
    k = len(dom)
    w = largura(k)
    if w == 0:
        return None
    idx = {v: i for i, v in enumerate(dom)}
    raw = pack_w([idx[v] for v in valores], w)
    b64 = base64.b64encode(raw).decode("ascii")
    if sem_padding:
        b64 = b64.rstrip("=")
    bloco = _encode_column([_grafa(v) for v in dom]).rstrip("\n")
    return f"{MAGIC}B{w}{len(valores):x}\n{bloco}\n{marcador}{b64}"


def le(wire, marcador=MARCADOR):
    """LEITOR INDEPENDENTE — acha a fronteira pelo marcador, sem receber `k` nem contagem."""
    cab, _, resto = wire.partition("\n")
    corpo = cab[len(MAGIC) + 1:]
    w, n = int(corpo[0]), int(corpo[1:], 16)
    linhas = resto.split("\n")
    i = next(j for j, ln in enumerate(linhas) if ln.startswith(marcador))
    dom = [_le_grafia(s) for s in _decode_column("\n".join(linhas[:i]) + "\n")]
    b64 = linhas[i][len(marcador):]
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


def prefixo_leitura(wire, marcador=MARCADOR):
    """Bytes a bufferizar antes do 1º valor: cabeçalho + domínio + marcador + 1 quarteto."""
    cab, _, resto = wire.partition("\n")
    linhas = resto.split("\n")
    i = next(j for j, ln in enumerate(linhas) if ln.startswith(marcador))
    return len((cab + "\n" + "\n".join(linhas[:i]) + "\n").encode()) + len(marcador) + 4

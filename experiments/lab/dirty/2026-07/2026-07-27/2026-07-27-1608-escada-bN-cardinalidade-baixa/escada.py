"""A escada bN — representação densa por CARDINALIDADE, não por tipo declarado.

    "não entendi porque a versão binária não ficou compacta. (…) se ao buscar os elementos
     eles tiverem só 1, já lança um binário/boolean previamente com b64 como default, se
     entrar 2, mesma coisa, se tiver null, aí também vai escalando, com 4 etc. (…) acho que o
     binário/bool é um bom candidato à escolha automática do tipo, assim como o `n`."

## O que a observação acertou

`['0','1'] * 100` custa **609 B**; a mesma informação como `bool` custa **47 B**. A diferença
não é de conteúdo, é de **rota**: `list[str]` cai no `_lista_flat` (rota 1) e nunca chega no
`_tipo_single_col` (rota 3), que é onde o modo denso mora. E o denso é **bool sem null** por
construção (`encoder.py`: `if tag == "b" and not tem_nulo`), então `bool + null` também cai
no core — 546 B.

Ou seja: a oportunidade é de **cardinalidade da coluna**, não do tipo Python da entrada.

## A escada

Com `k` valores distintos, bastam `w = ceil(log2(k))` bits por linha. O domínio viaja uma
vez; os índices viajam empacotados.

    k=1   0 bits    -- o core JA' resolve com RLE (`*200|v0` = 16 B). NAO mexer.
    k=2   1 bit     -- e' o `b1` de hoje, mas so' alcançavel via bool nativo
    k<=4  2 bits
    k<=8  3 bits
    k<=16 4 bits    ...

`null` **não é caso especial**: é mais um valor do domínio. E o formato já reserva o **slot 0**
para ele (ADR do weld do null), então a escada e a pré-alocação se encaixam sem gambiarra.

## Onde isto cai no mapa do `.9`

Categoria **A (FLOOR de bytes)** — mais um candidato do `min()` — com um **gate C** de
cardinalidade. O insumo da decisão (`n_unicas`, `avg_len`) **já é computado** hoje por
`analyze_column`, então a decisão é `[stream]` no eixo do guia: nada de materializar para
comparar.

Relacionado, mas **não é o mesmo**: a decisão pendente de `bN-dense` no `STATUS.md` é de
escopo **multi-col `.8M`**. Este lab é o lado single-col.

`src/tcf` intocado — isto é proposta, não solda.
"""
import base64
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[6] / "src"))

from tcf.bitpack import pack_w  # noqa: E402

MAGIC = "#TCF.8"


def largura(k):
    """Bits por linha para um domínio de `k` valores. `k<=1` -> 0 (o core faz melhor)."""
    return 0 if k <= 1 else max(1, math.ceil(math.log2(k)))


def dominio(valores):
    """Domínio canônico: ordem de PRIMEIRA APARIÇÃO, com `null` no slot 0 se existir.

    O slot 0 já é reservado ao null pelo formato — a escada só o reaproveita, em vez de
    inventar sentinela nova.
    """
    tem_nulo = any(v is None for v in valores)
    vistos = {}
    for v in valores:
        if v is not None and v not in vistos:
            vistos[v] = True
    return ([None] if tem_nulo else []) + list(vistos.keys())


def para_bn(valores):
    """`(wire, w, k)` da proposta. Wire = `#TCF.8B<w><n_hex>\\n<dominio>\\n<b64>`.

    O `<w>` é a largura; o domínio vai uma linha por valor, com o slot nulo grafado `0`
    (a mesma grafia otimizada que o core já usa para `^0`).
    """
    dom = dominio(valores)
    k = len(dom)
    w = largura(k)
    if w == 0:
        return None, 0, k                       # k<=1: o core resolve com RLE
    idx = {v: i for i, v in enumerate(dom)}
    fluxo = [idx[v] for v in valores]
    b64 = base64.b64encode(pack_w(fluxo, w)).decode("ascii")
    linhas_dom = "\n".join(_grafa(v) for v in dom)
    return f"{MAGIC}B{w}{len(valores):x}\n{linhas_dom}\n{b64}", w, k


BS = chr(92)


def _grafa(v):
    """Grafia de UM valor do domínio. Mesma convenção do corpo canônico.

    **Bug achado pelo leitor independente nesta rodada** — e é a TERCEIRA aparição da mesma
    colisão (weld do slot nulo, lab `2026-07-26-2126`, e agora aqui): se o domínio escreve o
    null como `0` cru e um valor de DADO também é `"0"`, os dois ficam indistinguíveis e a
    coluna volta com `None` no lugar da string.

    A saída não é regra nova — é a MESMA do core: `0` cru = slot nulo, `\\0` = o literal.
    """
    if v is None:
        return "0"
    return BS + v if v == "0" else v


def _le_grafia(s):
    if s == "0":
        return None
    return s[1:] if s.startswith(BS) else s


def soma_dominio(dom):
    """Soma de comprimentos que a fórmula do FLOOR consome — já na grafia emitida."""
    return sum(len(_grafa(v)) for v in dom)


def le_bn(wire, n_dom=None):
    """LEITOR INDEPENDENTE — reimplementa a semântica, não é a inversa de `para_bn`.

    Lê o cabeçalho posicionalmente (`B` + largura + n em hex), fatia o domínio pelo número de
    linhas que a largura permite, e desempacota. É lição do lab `2026-07-26-0038`: validar
    pela inversa é circular.
    """
    cab, _, resto = wire.partition("\n")
    assert cab.startswith(MAGIC + "B"), cab
    w = int(cab[len(MAGIC) + 1])
    n = int(cab[len(MAGIC) + 2:], 16)
    linhas = resto.split("\n")
    k = n_dom if n_dom is not None else _k_do_dominio(linhas, w)
    dom = [_le_grafia(s) for s in linhas[:k]]
    b64 = linhas[k]
    dados = base64.b64decode(b64)
    saida, acc, nbits = [], 0, 0
    for byte in dados:
        acc = (acc << 8) | byte
        nbits += 8
        while nbits >= w and len(saida) < n:
            nbits -= w
            saida.append(dom[(acc >> nbits) & ((1 << w) - 1)])
        acc &= (1 << nbits) - 1
    return saida


def _k_do_dominio(linhas, w):
    """O domínio tem no máximo 2^w linhas; a última linha do bloco é o b64."""
    return min(1 << w, len(linhas) - 1)


def custo_bn(k, n, soma_len_dominio):
    """O custo em bytes, CALCULADO — sem materializar. É a forma que o FLOOR usaria.

    cabecalho + dominio (valores + LF) + base64(ceil(n*w/8))
    """
    w = largura(k)
    if w == 0:
        return None
    bits = n * w
    nbytes = (bits + 7) // 8
    b64 = 4 * ((nbytes + 2) // 3)
    cab = len(MAGIC) + 1 + 1 + len(f"{n:x}") + 1
    return cab + soma_len_dominio + k + b64

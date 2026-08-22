"""bN de DOMINIO — densidade por cardinalidade, nao por tipo declarado.

Com `k` valores distintos numa coluna, bastam `w = ceil(log2(k))` bits por linha. O dominio
viaja uma vez; os indices viajam empacotados.

    #TCF.8                    #TCF.8B178
    \\0                        false
    \\1                        true
    ^1                        =CIhmASAEyQvAQQZokA
    ^2
    ...  (609 B)              (57 B)

## Duas grafias, escolhidas pelo TRANSPORTE

    B   dominio PRIMEIRO, `=` abre o bloco de bits    default -- STREAMA nos dois lados
    C   dominio por ULTIMO, sem marcador               lote fechado -- ~1 B/coluna menor

Com o dominio no fim (`C`) o leitor **nao emite valor nenhum antes do payload inteiro
chegar**: o comprimento do b64 e' deduzivel de `n` e `w`, mas o significado dos indices so'
aparece depois. Medido no lab `2026-07-27-2211`: numa coluna de 2000 linhas o `B` bufferiza
~100 B e o `C` ~1760 B — 17x — para 1 byte de diferenca.

## O marcador `=` e o escape

O `=` abre o bloco de bits. Uma linha de DOMINIO que comece com `=` ganha `\\` na frente.
Isso e' inequivoco porque **o core nunca emite `\\` seguido de char fora de `* 0-9 \\ ^ ~`**
(medido, varrendo os 95 imprimiveis, no lab `2026-07-27-2231`).

Custo: **1 B** de marcador, mais 1 B por valor de dominio que comece com `=` — em 145 colunas
categoricas reais das fixtures, esse segundo termo foi **zero**. E o caso patologico (dominio
cheio de `=`) e' absorvido pelo FLOOR externo: se o bN inchar, o core vence.

## O slot nulo

`null` nao e' caso especial: e' mais um valor do dominio, e ocupa o **slot 0**, que o formato
ja' reserva pra ele. A grafia do dominio e' a do core: `0` cru = null, `\\0` = o literal `"0"`.
Essa assimetria (grafar mais do que se desfaz) ja' custou 4 bugs no projeto — por isso
`_le_grafia` desfaz exatamente `_grafa`, nem mais.

## Onde NAO se aplica

    k <= 1    o core ja' e' otimo com RLE (`*N|valor`)
    k > 256   `w` passaria de 8; fora do namespace
    n pequeno o cabecalho + dominio nao se pagam (o FLOOR recusa sozinho)

Referencias: labs `experiments/lab/dirty/2026-07/2026-07-27/` — `1608` (a escada), `1647`
(dominio comprimido + alinhamento), `2211` (o eixo de streaming), `2231` (marcador por
escape), `2247` (o espaco completo de delimitacao).
"""
from __future__ import annotations

import base64
import binascii as _binascii
import math

from tcf.bitpack import pack_w, unpack_w

MAGIC = "#TCF.8"
BS = chr(92)

#: Discriminadores. `B` = dominio primeiro (streaming); `C` = dominio por ultimo (lote).
DISC_STREAM = "B"
DISC_LOTE = "C"
DISCS = frozenset({DISC_STREAM, DISC_LOTE})

#: O char que abre o bloco de bits no modo `B`.
MARCADOR = "="

#: Teto do namespace: `w` de 1 a 8 -> ate' 256 valores distintos.
MAX_W = 8


def _largura(k: int) -> int:
    return 0 if k <= 1 else max(1, math.ceil(math.log2(k)))


def _grafa(v: "str | None") -> str:
    """`0` cru = slot nulo; `\\0` = o literal `"0"`. INJETIVA.

    **corrupcao SILENCIOSA no weld
    ADR-0036.** A primeira versao escapava so' o valor `"0"` e devolvia o resto intacto:

        _grafa("0")   -> "\\0"
        _grafa("\\0")  -> "\\0"      <- MESMA saida, valores DIFERENTES

    Quem escapa tem de escapar tambem o proprio char de escape, senao a funcao deixa de ser
    injetiva. `encode(['\\0','x']*30)` devolvia `['0','x',...]` — sem excecao, pela API
    publica, com `list[str]` trivial. A rota core preservava; era regressao do bN.

    5a aparicao da mesma familia de assimetria no projeto. A regra, agora sem excecao:
    **escapa o `\\` inicial E o `0` solitario; nada mais.**
    """
    if v is None:
        return "0"
    return BS + v if (v == "0" or v.startswith(BS)) else v


def _le_grafia(s: str) -> "str | None":
    """Inversa exata de `_grafa`."""
    if s == "0":
        return None
    return s[1:] if s.startswith(BS) else s


def dominio(valores: "list[str | None]") -> "list[str | None]":
    """Dominio canonico: `null` no slot 0 (pre-alocado), resto por PRIMEIRA APARICAO."""
    tem_nulo = False
    vistos: "dict[str, bool]" = {}
    for v in valores:
        if v is None:
            tem_nulo = True
        elif v not in vistos:
            vistos[v] = True
    return ([None] if tem_nulo else []) + list(vistos.keys())    # type: ignore[list-item]


def candidatos(valores, encode_col, decode_col):
    """Wires bN para `valores`, ou `[]` se a coluna nao se qualifica.

    `encode_col`/`decode_col` sao injetados pra evitar import circular com o encoder.
    Devolve os dois modos (`B` e `C`) — quem decide e' o `min()` de quem chamou.
    """
    dom = dominio(valores)
    k = len(dom)
    w = _largura(k)
    if w == 0 or w > MAX_W:
        return []
    idx = {v: i for i, v in enumerate(dom)}
    b64 = base64.b64encode(pack_w([idx[v] for v in valores], w)).decode("ascii").rstrip("=")
    # `[:-1]` e NAO `rstrip("\n")`: o corpo
    # canonico termina em EXATAMENTE um `\n`, mas `rstrip` come TODOS — e um dominio cujo
    # ULTIMO valor e' a string vazia acaba em `\n\n`. `['a','b','']` perdia o 3o valor, e o
    # `decode` estourava com "indice 2 fora do dominio de 2 valores": RT quebrado pela API
    # publica. Cortar um so' preserva a linha vazia final.
    _bl = encode_col([_grafa(v) for v in dom])
    bloco = _bl[:-1] if _bl.endswith("\n") else _bl
    n = len(valores)
    escapado = "\n".join(BS + ln if ln.startswith(MARCADOR) else ln
                         for ln in bloco.split("\n"))
    return [
        f"{MAGIC}{DISC_STREAM}{w}{n:x}\n{escapado}\n{MARCADOR}{b64}",
        f"{MAGIC}{DISC_LOTE}{w}{n:x}\n{b64}\n{bloco}",
    ]


def valida_payload_b64(b64: str, n: int, w: int, rotulo: str,
                       padded: bool = False) -> bytes:
    """Payload base64 -> bytes. TRES checagens, nenhuma redundante (T-BN-B64-VALIDATE).

    Fonte unica de validacao de payload denso do formato — o `decode_bn` (bN `B`/`C`) e o
    `decoder._decode_lazy_bool` (lazy `bB`) chamam esta funcao; o `_decode_denso` ja' fazia
    o equivalente inline desde sempre e serviu de modelo.

    Medido no lab `2026-08-06-2104` (9 sondas x 5 rotas, 45 celulas): **nenhuma das tres
    subsome as outras.**

        1. validate=True        char fora do alfabeto, espaco, padding em lugar errado
        2. re-codifica+compara  padding a mais, caixa trocada -> grafia dupla dos MESMOS bytes
        3. tamanho exato        extensao com bytes ZERO e truncamento

    A (2) e' a MESMA tecnica que o cabecalho ja' usa pro hex (`f"{n:x}" != nhex`, ADR-0036):
    canonicidade por re-emissao. A (3) e' o que o `_decode_denso` ja' fazia — e e' a unica
    que pega `payload + "AAAA"`, porque bytes zero atravessam ate' a checagem de
    bits-de-padding do `unpack_w`.

    `padded` diz a forma canonica DESTA rota: o denso emite com `=`, o bN e o lazy sem.
    """
    try:
        raw = base64.b64decode(b64 + "=" * (-len(b64) % 4), validate=True)
    except (ValueError, _binascii.Error) as e:
        raise ValueError(f"{rotulo}: payload nao e' base64 canonico: {e}") from e

    volta = base64.b64encode(raw).decode("ascii")
    if not padded:
        volta = volta.rstrip("=")
    if volta != b64:
        raise ValueError(
            f"{rotulo}: payload base64 nao-canonico — recebido {b64[:20]!r}…, canonico "
            f"{volta[:20]!r}… (duas grafias para os mesmos bytes)"
        )

    esperado = -(-n * w // 8)                    # ceil(n*w/8) — a mesma conta do _decode_denso
    if len(raw) != esperado:
        raise ValueError(
            f"{rotulo}: payload = {len(raw)} bytes, esperado {esperado} p/ n={n} w={w} "
            f"(wire truncado, estendido ou concatenado)"
        )
    return raw


def _b64_len(n: int, w: int) -> int:
    """Comprimento do bloco base64 SEM padding — deduzivel de `n` e `w`."""
    return (((n * w + 7) // 8) * 8 + 5) // 6


def decode_bn(tcf_text: str, disc: str, decode_col,
              rotulo: "str | None" = None) -> "list[str | None]":
    """Le um wire `#TCF.8B…`/`#TCF.8C…`. Fail-loud em cabecalho ou fronteira nao-canonicos.

    `rotulo` nomeia o wire NAS MENSAGENS DE ERRO. Default = `#TCF.8<disc>`. Quem delega pra
    ca' com o cabecalho reescrito (a rota tipada `#TCF.8nB`) passa o rotulo original, senao
    o erro sai assinado com a forma interna e aponta pro mecanismo errado.
    """
    cab, sep, resto = tcf_text.partition("\n")
    if not sep:
        raise ValueError(f"wire bN sem corpo: {cab[:24]!r}")
    campos = cab[len(MAGIC) + 1:]
    # CANONICIDADE DO CABECALHO —.
    # A 1a versao usava `campos[0].isdigit()` e `int(campos[1:], 16)` CRUS. `str.isdigit()`
    # aceita digito Unicode (`٢`), e `int(x, 16)` aceita zero a esquerda, maiuscula,
    # underscore (PEP 515), prefixo `0x` e sinal — uma familia INFINITA de grafias para o
    # mesmo valor. O irmao no MESMO indice 7 (modo denso, `decoder.py`) ja' rejeitava tudo
    # isso, e `test_typed_singlecol.py::test_grafia_nao_canonica_fail_loud` ja' travava o
    # invariante ("duas grafias, mesmo valor, violaria S1.2"). O bN o violava.
    if len(campos) < 2 or campos[0] not in "12345678":
        raise ValueError(
            f"cabecalho bN nao-canonico: largura {campos[:1]!r} fora de 1..{MAX_W}"
        )
    w = int(campos[0])
    nhex = campos[1:]
    if any(c not in "0123456789abcdef" for c in nhex):
        raise ValueError(f"contagem bN nao-hexadecimal-canonica: {nhex!r}")
    n = int(nhex, 16)
    if f"{n:x}" != nhex:                      # grafia MINIMA: sem zero a esquerda
        raise ValueError(
            f"contagem bN nao-canonica: {nhex!r} (canonico: {n:x}) — duas grafias para o "
            f"mesmo valor violariam a canonicidade do wire"
        )

    if disc == DISC_LOTE:
        nb = _b64_len(n, w)
        b64, bloco = resto[:nb], resto[nb + 1:]
    else:
        linhas = resto.split("\n")
        alvo = next((j for j, ln in enumerate(linhas) if ln.startswith(MARCADOR)), None)
        if alvo is None:
            raise ValueError(
                f"wire bN sem o marcador {MARCADOR!r} que separa dominio e bits "
                f"— corpo nao-canonico (truncado ou editado a mao)"
            )
        # Nada pode vir DEPOIS do bloco de bits: linha extra era
        # ignorada CALADA, enquanto o irmao no mesmo indice 7 (modo denso) falha alto na
        # mesma sonda. Silencio aqui esconde wire truncado, concatenado ou editado a mao.
        if any(ln for ln in linhas[alvo + 1:]):
            raise ValueError(
                f"conteudo apos o bloco de bits do bN: {linhas[alvo + 1:][:1]!r} "
                f"— corpo nao-canonico (wire concatenado ou editado a mao)"
            )
        b64 = linhas[alvo][1:]
        bloco = "\n".join(ln[1:] if ln.startswith(BS + MARCADOR) else ln
                          for ln in linhas[:alvo])

    # O rotulo das mensagens de erro identifica o wire QUE O USUARIO MANDOU, nao a forma
    # interna pra qual ele foi reescrito. A rota tipada (`#TCF.8nB`) chega aqui com o
    # cabecalho ja' reescrito pra `#TCF.8B` — sem `rotulo` explicito, o erro sairia assinado
    # como o irmao de STRING, que tem contrato de retorno diferente (auditoria,
    # achado [4]). Diagnostico que aponta pro mecanismo errado custa depuracao.
    rotulo = rotulo or f"{MAGIC}{disc}"
    dom = [_le_grafia(s) for s in decode_col(bloco + "\n")]
    if not dom:
        raise ValueError("dominio bN vazio — corpo nao-canonico")
    if len(dom) > (1 << w):
        raise ValueError(f"dominio bN com {len(dom)} valores nao cabe em {w} bits")
    raw = valida_payload_b64(b64, n, w, rotulo)
    saida = []
    maior = -1
    for i in unpack_w(raw, w, n):
        if i >= len(dom):
            # `w` bits enderecam 2^w slots, mas o dominio pode ter menos. Indice fora da
            # faixa e' wire adulterado — fail-loud, nao IndexError cru.
            raise ValueError(
                f"{rotulo}: indice {i} fora do dominio bN de {len(dom)} valores "
                f"— corpo nao-canonico"
            )
        if i > maior:
            maior = i
        saida.append(dom[i])
    # TODO SLOT DO DOMINIO E' REFERENCIADO (invariante, medido em 35/35 colunas canonicas
    # incluindo com null): `dominio()` monta a lista a partir da PRIMEIRA APARICAO de cada
    # valor distinto, entao todo indice 0..k-1 aparece no corpo. Slot sobrando = wire
    # adulterado.
    #
    # Sem isto os DOIS modos aceitavam calados uma entrada extra no dominio (achado da
    # varredura). No `B` ela entra antes do marcador; no `C`, no fim — e o
    # guard `len(dom) > 2^w` so' pegava por acaso, quando a largura nao tinha folga.
    # E' a MESMA classe do "conteudo apos o bloco de bits": aceitar em silencio o que o
    # encoder canonico nunca produz.
    if maior + 1 != len(dom):
        raise ValueError(
            f"{rotulo}: dominio bN tem {len(dom)} valores mas so' {maior + 1} sao "
            f"referenciados — corpo nao-canonico (o encoder nunca emite slot sobrando)"
        )
    return saida

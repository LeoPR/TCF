"""Online-ness: **de quanto do fio o valor `j` depende?** — sem reimplementar o decoder.

## Duas tentativas jogadas fora antes desta

1. **Leitor mínimo por rota.** Mentiu em ~1/3 das células. Ler o corpo do core exige a
   tabela de apelidos do OBAT (`^N` é índice de APELIDO, não de linha: em `S/N/^1/^2/^1` o
   `^1` é o apelido 1) e a compressão de afixo (`b*eta`, `z3`). Um leitor mínimo correto
   **é** o decoder — e reimplementar o decoder num lab contraria a filosofia do projeto e
   produz números errados com cara de medição.

2. **Mutação de cauda.** Mutar `wire[p:]` e ver se o valor `j` muda. Deu **100% em tudo** —
   não porque o formato seja sequencial, mas porque quase toda mutação invalida o FIO, o
   `decode` levanta, e o método (conservador de propósito) empurra `p` pra cima. Método
   sólido, discriminação zero. Descartado por inútil, não por errado.

## O que ficou: dois métodos construtivos, cada um no seu domínio

**TRUNCAMENTO** (rotas em que o decoder tolera fio curto — o core e a polaridade).
Menor `p` tal que `decode(wire[:p])` devolve ao menos `j+1` valores **e** o valor `j` está
certo. Corta só em fronteira de linha. Usa o decoder real; é prova construtiva de
suficiência, não estimativa.

**EXTRAÇÃO ARITMÉTICA** (bN modo `B`). Truncar não serve aqui: a checagem de tamanho exato
do payload b64 recusa fio curto — é o CÓDIGO sendo estrito, não o formato sendo sequencial.
Então o valor `j` é extraído de exatamente três pedaços (cabeçalho + bloco de domínio + o
quarteto base64 que contém o bit `j*w`) e conferido contra `decode(wire)[j]`. Se bater, os
outros bytes provadamente não foram necessários.

**Modo `C`**: nenhum dos dois se aplica, e não por limitação do método — o domínio vem
DEPOIS do payload, então o valor `j` depende de bytes no fim do fio. É estrutural.

`src/tcf` NÃO é tocado.
"""
from __future__ import annotations

import base64

BS = chr(92)


# ────────────────────────────────────────────────────────── método 1: truncar
def _fronteiras(wire: str) -> list[int]:
    """Posições logo após cada `\\n` — os únicos cortes que podem dar fio válido."""
    return [i + 1 for i, c in enumerate(wire) if c == "\n"] + [len(wire)]


def _basta(decode, wire: str, p: int, j: int, esperado) -> bool:
    try:
        saida = decode(wire[:p])
    except Exception:
        return False
    return len(saida) > j and saida[j] == esperado


def prefixo_por_truncamento(decode, wire: str, j: int, esperado) -> "int | None":
    """Menor prefixo (em fronteira de linha) que já determina o valor `j`. `None` se a
    rota não tolera truncamento (o bN recusa por causa da checagem de tamanho exato)."""
    fr = _fronteiras(wire)
    if not _basta(decode, wire, fr[-1], j, esperado):
        return None
    lo, hi = 0, len(fr) - 1                       # invariante: fr[hi] basta
    while lo < hi:
        meio = (lo + hi) // 2
        if _basta(decode, wire, fr[meio], j, esperado):
            hi = meio
        else:
            lo = meio + 1
    return len(wire[:fr[hi]].encode())


# ─────────────────────────────────────────── método 2: extração aritmética bN
def _desescapa(s: str) -> str:
    out, i = [], 0
    while i < len(s):
        if s[i] == BS and i + 1 < len(s):
            out.append(s[i + 1])
            i += 2
        else:
            out.append(s[i])
            i += 1
    return "".join(out)


def extrai_bn(wire: str, j: int, dom_linhas: list[str]) -> "tuple[object, int]":
    """`(valor_j, bytes_tocados)` no modo `B`, tocando só cabeçalho + domínio + 1 quarteto.

    `dom_linhas` vem de fora (o bloco de domínio é um corpo TCF e quem o expande é o
    `_decode_column` do próprio `src/tcf` — não se reimplementa nada aqui).
    """
    fim_cab = wire.index("\n")
    w = int(wire[7])
    pos_marc = wire.index("\n=", fim_cab)
    tocado = len(wire[:pos_marc + 2].encode())     # cabeçalho + domínio + "\n="
    b64 = wire[pos_marc + 2:]
    bit = j * w
    c0 = bit // 6
    ini = c0 - (c0 % 4)
    quarteto = b64[ini:ini + 4]
    brutos = base64.b64decode(quarteto + "=" * ((4 - len(quarteto) % 4) % 4))
    desloc = (c0 % 4) * 6 + (bit % 6)
    idx = 0
    for k in range(w):
        b = desloc + k
        idx = (idx << 1) | ((brutos[b // 8] >> (7 - b % 8)) & 1)
    grafado = dom_linhas[idx]
    valor = None if grafado == "0" else _desescapa(
        grafado[1:] if grafado.startswith(BS) else grafado)
    return valor, tocado + len(quarteto)

"""Decompoe um wire TCF de DATA em partes explicadas. E' a peca de inspecao do lab.

Nao adivinha: explica o que RECONHECE (magic, spec, marcadores do seq-RLE, dict, bN,
polaridade) e chama de "corpo OBAT/HCC" o que nao souber. Erro de leitura aqui seria pior
que silencio — a ideia e' o owner ABRIR o arquivo e conferir o que o codigo emitiu.
"""
from __future__ import annotations

import re

# Marcadores do corpo. As grafias vem do codigo real:
#   `*{count}{sign}{passo}|{ancora}`         seq-RLE aritmetico  (hcc_seqrle.py:364)
#   `*{count}~{d1,d2,...}|{ancora}`          seq-RLE PERIODICO   (hcc_seqrle.py:275, ADR-0040)
#   `*{count}{sinais}{deltas}|{ancora}`      seq-RLE multi-digito(hcc_seqrle.py:372)
_ARIT = re.compile(r"^\*(\d+)([+-])(\d+)\|(.*)$")
_PERI = re.compile(r"^\*(\d+)~([\d,+-]+)\|(.*)$")
_RLE = re.compile(r"^\*(\d+)\|(.*)$")


def _explica_header(l0: str) -> list[tuple[str, str]]:
    """[(pedaco, o que significa)] da primeira linha."""
    out = []
    if not l0.startswith("#TCF.8"):
        return [(l0, "SEM header — wire orfao (corpo puro; contrato vive nas pontas)")]
    disc = l0[6:7]
    if disc == "M":
        out.append(("#TCF.8M", "magic MULTI-COLUNA; o meta das colunas vem inline"))
        meta = l0[7:]
        out.append((meta, "meta inline: `size` `nome`:`spec` por coluna "
                          "(`@`=modo dict; a ULTIMA sem size = corpo ate' EOF)"))
        if ":dt" in meta:
            out.append((":dt", "spec de data ISO — wire_id CURTO (ADR-0041; era `:data-iso`)"))
    elif disc == "H":
        out.append(("#TCF.8H", "magic HIERARQUICO (.8H); meta = `campo:size:spec` por folha"))
        out.append((l0[7:], "meta das folhas"))
        if ":dt" in l0:
            out.append((":dt", "spec de data ISO na folha (ADR-0041)"))
    elif disc == " ":
        nome, _, spec = l0[7:].partition(":")
        out.append(("#TCF.8", "magic single-col"))
        if nome:
            out.append((nome, "rotulo opcional da coluna"))
        out.append((f":{spec}", f"spec `{spec}`"
                    + (" — data ISO -> ordinal decimal (ADR-0041: id curto `dt`)"
                       if spec == "dt" else "")))
    elif disc == "":
        out.append(("#TCF.8", "magic de versao (carimbo); a nature NAO venceu o FLOOR "
                              "-> corpo do nucleo, sem spec"))
    else:
        out.append((l0, f"header com sufixo de rota `{l0[6:]}` "
                        "(ex.: `!`=polaridade ADR-0035, `B..`=bN de dominio ADR-0036)"))
    return out


def _explica_linha_corpo(ln: str) -> str:
    m = _PERI.match(ln)
    if m:
        count, deltas, ancora = m.groups()
        ds = deltas.replace("+", "").split(",")
        return (f"seq-RLE PERIODICO (ADR-0040): {count} linhas cujo delta CICLA em "
                f"[{', '.join(ds)}] (periodo {len(ds)}), ancoradas em {ancora!r}. "
                f"O ciclo paga UMA vez — custo O(1) no numero de linhas")
    m = _ARIT.match(ln)
    if m:
        count, sinal, passo, ancora = m.groups()
        return (f"seq-RLE aritmetico: {count} linhas com passo constante {sinal}{passo}, "
                f"ancoradas em {ancora!r}")
    m = _RLE.match(ln)
    if m:
        count, linha = m.groups()
        return f"RLE de linha: {count} linhas IDENTICAS a {linha!r}"
    if ln.startswith("_"):
        return "valor LITERAL (a nature recusou este valor; fallback byte-exato)"
    return ""


#: `\` antes de um run de digitos e' o ESCAPE do nucleo (OBAT) — grafia interna, nao
#: parte do ordinal. Verificado: `encode(['739617','739618','739619'])` sozinho ja' sai
#: `\73961*\7 / 1\8 / 1\9`, sem spec nenhum no meio.
_NOTA_ESCAPE = (r"  nota: o `\` antes dos digitos e' o escape do nucleo (OBAT) para run "
                r"de digitos — grafia interna, nao faz parte do ordinal")


def anatomia(wire: str, *, titulo: str = "", amostra_corpo: int = 6) -> str:
    """Texto inspecionavel: header explicado + corpo com os marcadores traduzidos."""
    linhas = wire.split("\n")
    L = []
    if titulo:
        L.append(titulo)
        L.append("=" * len(titulo))
    L.append(f"WIRE COMPLETO ({len(wire.encode('utf-8'))} bytes):")
    L.append(repr(wire) if len(wire) <= 400 else repr(wire[:400]) + f"  …(+{len(wire) - 400} chars)")
    L.append("")
    L.append("HEADER")
    for pedaco, sentido in _explica_header(linhas[0]):
        L.append(f"  {pedaco!r:<30} {sentido}")
    corpo = linhas[1:] if len(linhas) > 1 else []
    L.append("")
    L.append(f"CORPO ({len(corpo)} linha(s))")
    if not corpo:
        L.append("  (vazio)")
    for i, ln in enumerate(corpo[:amostra_corpo]):
        expl = _explica_linha_corpo(ln)
        L.append(f"  [{i}] {ln[:110]!r}")
        if expl:
            L.append(f"      -> {expl}")
    if len(corpo) > amostra_corpo:
        L.append(f"  … (+{len(corpo) - amostra_corpo} linhas)")
    if any("\\" in ln for ln in corpo[:amostra_corpo]):
        L.append(_NOTA_ESCAPE)
    return "\n".join(L)

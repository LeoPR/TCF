"""TCF encoder — API publica (welding step 3, 2026-05-17).

Wrapper de alto nivel do pipeline:
  values → alg16 (tokenizacao online) → M8.A composicional → TCF text

Uso minimo:

    from tcf import encode

    tcf_text = encode(["joao@gmail.com", "maria@gmail.com", ...])

Internamente:
1. Deduplicacao preservando ordem de aparicao
2. `tcf.core.online.processar(unicas)` — alg16 tokeniza
3. `tcf.composicional.syntax.M8AVirtualRefsSyntax()` — Compactacao
   composicional (detector unificado + emit `~`/`,`)
4. Saida: texto TCF (sem brackets, LF only)

Esta API e' single-column. Multi-column / multi-dataset sera
adicionado em fase posterior (organizer/orquestrador).
"""

from __future__ import annotations
from collections import OrderedDict

from tcf.core.online import processar
from tcf.composicional.syntax import M8AVirtualRefsSyntax


def encode(values: list[str], header: str = "val") -> str:
    """Encode lista de strings em texto TCF compacto.

    Parametros:
        values: lista de strings (com repeticoes preservadas para RLE).
        header: nome opcional da "coluna" (passado a syntax; M8.A
            atual ignora este campo).

    Retorna: texto TCF (sem brackets, LF only).
    """
    seen: OrderedDict[str, bool] = OrderedDict()
    for s in values:
        seen[s] = True
    unicas = list(seen.keys())
    tokens, _ = processar(unicas, min_len=3)
    syn = M8AVirtualRefsSyntax()
    return syn.encode(values, unicas, tokens, header)

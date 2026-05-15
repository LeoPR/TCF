"""TCF encoder — API publica.

Pipeline:
  values → OBAT (tokenizacao) → HCC (compactacao composicional) → TCF text

Uso minimo:

    from tcf import encode

    tcf_text = encode(["joao@gmail.com", "maria@gmail.com", ...])

Internamente:
1. Deduplicacao preservando ordem de aparicao
2. `tcf.core.online.processar(unicas)` — **OBAT** tokeniza
3. `tcf.composicional.syntax.M8AVirtualRefsSyntax()` — **HCC**
   Compactacao composicional
4. Saida: texto TCF (sem brackets, LF only)

Esta API e' single-column. Multi-column / multi-dataset sera
adicionado em fase posterior (organizer/orquestrador).

Para detalhamento dos algoritmos:
- `docs/algorithms/OBAT.md`
- `docs/algorithms/HCC.md`
"""

from __future__ import annotations
from collections import OrderedDict

from tcf.core.online import processar
from tcf.composicional.syntax import M8AVirtualRefsSyntax


def encode(values: list[str], header: str = "val") -> str:
    """Encode lista de strings em texto TCF compacto.

    Parametros:
        values: lista de strings (com repeticoes preservadas para RLE).
        header: nome opcional da "coluna" (passado a syntax HCC;
            implementacao atual ignora este campo, futuro multi-col
            podera usar).

    Retorna: texto TCF (sem brackets, LF only).
    """
    seen: OrderedDict[str, bool] = OrderedDict()
    for s in values:
        seen[s] = True
    unicas = list(seen.keys())
    tokens, _ = processar(unicas, min_len=3)
    syn = M8AVirtualRefsSyntax()
    return syn.encode(values, unicas, tokens, header)

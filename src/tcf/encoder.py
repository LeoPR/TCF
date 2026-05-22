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

from tcf.auto_min_len import detect_min_len
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

    min_len: auto-detectado via `tcf.auto_min_len.detect_min_len`
    (ADR-0010, H-DA-11). Datasets pequenos (n<100) usam ml=3 default
    (preserva M9 baseline 1615B exato); datasets >=100 rows usam
    heuristica v3 (captura ~9% weighted real-world Adult+TPC-H).
    """
    seen: OrderedDict[str, bool] = OrderedDict()
    for s in values:
        seen[s] = True
    unicas = list(seen.keys())
    min_len = detect_min_len(values)
    tokens, _ = processar(unicas, min_len=min_len)
    syn = M8AVirtualRefsSyntax()
    return syn.encode(values, unicas, tokens, header)

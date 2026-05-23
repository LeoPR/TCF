"""TCF encoder — API publica.

Pipeline canonical delta-aware (M10, ADR-0011, T-CODE-PACOTE1-WELD-CANONICAL):

    values
      → analyze_column (features pre-pass O(N))
      → detect_cadence_from_features (regras 1+2, ADR-0008)
      → detect_min_len_from_features (heur v3, ADR-0010)
      → OBAT tokeniza (processar_with_hint se cadence, senao processar)
      → HCCSeqRLE compacta body (com seq-RLE near-identical `*N+delta|`)
      → texto TCF

Uso minimo:

    from tcf import encode

    tcf_text = encode(["joao@gmail.com", "maria@gmail.com", ...])

Para detalhamento dos algoritmos:
- `docs/algorithms/OBAT.md`
- `docs/algorithms/HCC.md`
- `docs/adr/0011-pacote1-weld-canonical.md` — welding rationale
"""

from __future__ import annotations
from collections import OrderedDict

from tcf.auto_cadence import detect_cadence_from_features
from tcf.auto_min_len import detect_min_len_from_features
from tcf.column_features import analyze_column
from tcf.composicional.hcc_seqrle import HCCSeqRLE
from tcf.core.online import processar
from tcf.obat_shape import processar_with_hint


def encode(values: list[str], header: str = "val") -> str:
    """Encode lista de strings em texto TCF compacto.

    Parametros:
        values: lista de strings (com repeticoes preservadas para RLE).
        header: nome opcional da "coluna" (passado a syntax HCC;
            implementacao atual ignora este campo, futuro multi-col
            podera usar).

    Retorna: texto TCF (sem brackets, LF only).

    Pipeline canonical:
    1. Dedup preservando ordem
    2. `analyze_column(values)` — pre-pass features (1 passada O(N))
    3. `detect_cadence_from_features(features, unicas)` — hint pra OBAT
       (ADR-0008: regra 1 wrapper+counter ou regra 2 numeric+high-card)
    4. `detect_min_len_from_features(features)` — ADR-0010, gating n>=100
    5. OBAT tokeniza:
       - se cadence: `processar_with_hint(unicas, min_len, True)`
       - senao: `processar(unicas, min_len)` canonical
    6. HCC: `HCCSeqRLE().encode(...)` — M8A + seq-RLE near-identical
       (compacta runs `linha_a, linha_b=shift(linha_a, delta), ...` em
       `*N+delta|<template>`)
    """
    seen: OrderedDict[str, bool] = OrderedDict()
    for s in values:
        seen[s] = True
    unicas = list(seen.keys())

    features = analyze_column(values)
    cadence_detected, _info = detect_cadence_from_features(features, unicas)
    min_len = detect_min_len_from_features(features)

    if cadence_detected:
        tokens, _log = processar_with_hint(
            unicas, min_len=min_len, prefer_shape_consistency=True
        )
    else:
        tokens, _log = processar(unicas, min_len=min_len)

    syn = HCCSeqRLE()
    return syn.encode(values, unicas, tokens, header)

"""TCF decoder — API publica.

Wrapper de alto nivel: TCF text → lista de strings originais.

Uso minimo:

    from tcf import decode

    values = decode(tcf_text)

Internamente delega ao decoder de HCC com seq-RLE near-identical
(`HCCSeqRLE`, M10/ADR-0011): expande markers `*N+delta|<template>` em
N linhas, depois chama `M8AVirtualRefsSyntax.decode` no resultado.

Backward compat com M9 puro (`*N|<linha>` simples + literais): HCCSeqRLE
chama super().decode pra qualquer linha que NAO seja `*N+delta|`, entao
M9 outputs sao lidos sem mudanca. Outputs gerados por `encode()` desta
lib (M10) requerem decoder M10 (esta funcao).

Para detalhamento:
- `docs/algorithms/HCC.md`
- `docs/adr/0011-pacote1-weld-canonical.md`
"""

from __future__ import annotations

from tcf.composicional.hcc_seqrle import HCCSeqRLE


def decode(tcf_text: str) -> list[str]:
    """Decode texto TCF compacto de volta para lista de strings.

    Parametros:
        tcf_text: conteudo TCF (texto). Aceita:
            - M10 canonical: com markers `*N+delta|template` near-identical
            - M9 canonical: sem markers near-identical (sub-set de M10)
            - Com ou sem brackets `[`/`]` (back-compat pre-M7)

    Retorna: lista de strings na ordem original (com repeticoes).
    """
    syn = HCCSeqRLE()
    return syn.decode(tcf_text)

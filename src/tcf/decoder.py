"""TCF decoder — API publica.

Wrapper de alto nivel: TCF text → lista de strings originais.

Uso minimo:

    from tcf import decode

    values = decode(tcf_text)

Internamente delega ao decoder de **HCC** (Hierarchical Compositional
Coding). Suporta TCFs gerados por:
- `encode()` desta lib
- Dirty lab macros M8.A, M9, M10, M11, M12, M13, M14 (mesma sintaxe
  canonica)

Para detalhamento dos algoritmos:
- `docs/algorithms/HCC.md`
"""

from __future__ import annotations

from tcf.composicional.syntax import M8AVirtualRefsSyntax


def decode(tcf_text: str) -> list[str]:
    """Decode texto TCF compacto de volta para lista de strings.

    Parametros:
        tcf_text: conteudo TCF (texto). Aceita com ou sem brackets
            `[`/`]` (decoder mantem skip pra back-compat com versoes
            ate' M7).

    Retorna: lista de strings na ordem original (com repeticoes).
    """
    syn = M8AVirtualRefsSyntax()
    return syn.decode(tcf_text)

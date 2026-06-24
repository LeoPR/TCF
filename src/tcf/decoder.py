"""TCF decoder — API publica unificada (ADR-0014).

Wrapper de alto nivel: TCF text -> lista de strings OU dict de colunas.

Dispatch automatico pelo shebang:
- `#TCF.7 M\\n` (vivo) ou `#TCF.6 M\\n` (LEGADO, leitura ate' o 1.0) -> multi-column,
  retorna `dict[str, list[str]]`
- caso contrario -> single-column, retorna `list[str]`

Uso minimo:

    from tcf import encode, decode

    # Single
    text = encode(["abc", "abcd"])
    values = decode(text)              # -> list[str]

    # Multi
    text = encode({"id": [...], "name": [...]})
    table = decode(text)               # -> dict[str, list[str]]

    # Identidade: decode(encode(x)) == x sempre, tanto pra list quanto dict

Internamente delega ao decoder de HCC com seq-RLE near-identical
(`HCCSeqRLE`, M10/ADR-0011) pra single-col e a `_decode_multi`
(ADR-0013) pra multi-col.

Backward compat:
- M9 puro (sem markers near-identical): lido sem mudanca (subset de M10)
- Outputs de versoes anteriores que nao tinham shebang multi: tratados
  como single-col (comportamento atual)

Detalhes:
- `docs/algorithms/HCC.md`, `docs/algorithms/output-convention.md`
  (convencao sem-brackets / LF-unico implementada aqui e em hcc_seqrle.py)
- `docs/adr/0011-pacote1-weld-canonical.md`
- `docs/adr/0013-multi-column-canonical-api.md`
- `docs/adr/0014-unified-api-side-outputs.md`

Invariante `decode(encode(x)) == x` guardado por `tests/test_core_rt.py`
(single) + `tests/test_multi_col_rt.py` (multi) +
`tests/test_real_world_snapshots.py` (real-world).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from tcf.composicional.hcc_seqrle import HCCSeqRLE

if TYPE_CHECKING:
    from tcf.natures.templated_checked import TemplatedCheckedSpec


# #TCF.7 = formato VIVO (default). #TCF.6 = LEGADO de leitura — remover no 1.0
# (T-CODE-LEGACY-PRUNE-PRE-07; ADR-0024 git-as-compat reproduz blobs antigos).
_MULTI_MAGIC = "#TCF.7 M"
_MULTI_MAGIC_LEGACY_V6 = "#TCF.6 M"   # LEGADO — leitura ate' o 1.0


def decode(
    tcf_text: str,
    *,
    nature: "TemplatedCheckedSpec | None" = None,
    nature_per_col: "dict[str, TemplatedCheckedSpec] | None" = None,
) -> list[str] | dict[str, list[str]]:
    """Decode texto TCF. Roteia pelo shebang.

    Args:
        tcf_text: conteudo TCF (texto). Aceita:
            - Multi-col: comeca com `#TCF.7 M\\n` (vivo) ou `#TCF.6 M\\n`
              (LEGADO, leitura ate' o 1.0) + meta line + bodies
              -> retorna `dict[str, list[str]]`
            - Single-col: body puro (sem shebang)
              -> retorna `list[str]` (com repeticoes preservadas)
        nature: spec usado no encode pra pre-tx (ADR-0015). Se fornecido,
            aplica decode_value reverse apos M10 decode.
        nature_per_col: dict pra reverse multi-col pre-tx.

    Returns:
        list[str] OU dict[str, list[str]] dependendo do formato.

    Raises:
        ValueError: multi-col malformado (sem magic, sem meta line).
    """
    if tcf_text.startswith(_MULTI_MAGIC) or tcf_text.startswith(_MULTI_MAGIC_LEGACY_V6):
        from tcf.multi import _decode_multi
        result = _decode_multi(tcf_text)
        if nature_per_col:
            from tcf.natures.templated_checked import decode_value
            result = {
                name: ([decode_value(nature_per_col[name], v) for v in vals]
                       if name in nature_per_col else vals)
                for name, vals in result.items()
            }
        return result
    values = _decode_column(tcf_text)
    if nature is not None:
        from tcf.natures.templated_checked import decode_value
        values = [decode_value(nature, v) for v in values]
    return values


def _decode_column(tcf_text: str) -> list[str]:
    """Decode body single-col. Cf. _encode_column no encoder."""
    syn = HCCSeqRLE()
    return syn.decode(tcf_text)

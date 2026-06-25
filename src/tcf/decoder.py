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


# #TCF.7 = formato VIVO (default). #TCF.8 = self-describing natures (ADR-0027,
# opt-in SSE ha nature). #TCF.6 = LEGADO de leitura — remover no 1.0
# (T-CODE-LEGACY-PRUNE-PRE-07; ADR-0024 git-as-compat reproduz blobs antigos).
_MULTI_MAGIC = "#TCF.7 M"
_MULTI_MAGIC_V8 = "#TCF.8 M"          # multi self-describing (:id no meta-line)
_SINGLE_MAGIC_V8 = "#TCF.8"           # single-col self-describing (SEM M); shebang
                                      # '#TCF.8\\n[nome]:spec\\n<body>' (ADR-0027)
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
    if (tcf_text.startswith(_MULTI_MAGIC)
            or tcf_text.startswith(_MULTI_MAGIC_V8)
            or tcf_text.startswith(_MULTI_MAGIC_LEGACY_V6)):
        from tcf.multi import _decode_multi_impl
        result, header_ids = _decode_multi_impl(tcf_text)
        # Natures auto-descritas no header (#TCF.8, ADR-0027): resolve+aplica.
        # PRECEDENCIA: header vence pros 3 ids core; o usuario completa o resto
        # via nature_per_col. Sem isso, encode(nature)+decode(nature) aplicaria
        # DUAS vezes (header + usuario) e quebraria o RT.
        header_resolved: set[str] = set()
        if header_ids:
            from tcf.natures import _resolve_nature_id
            for name, nat_id in header_ids.items():
                spec = _resolve_nature_id(nat_id)
                if spec is not None:
                    result[name] = [spec.decode_value(v) for v in result[name]]
                    header_resolved.add(name)
                else:
                    # forward-compat: id desconhecido -> valor CRU + aviso (nao
                    # silencioso, nao KeyError). Usuario pode completar via param.
                    import warnings
                    warnings.warn(
                        f"nature-id desconhecido no header: {nat_id!r} "
                        f"(coluna {name!r}) -> valor mantido cru",
                        stacklevel=2,
                    )
        if nature_per_col:
            from tcf.natures.templated_checked import decode_value
            result = {
                name: ([decode_value(nature_per_col[name], v) for v in vals]
                       if (name in nature_per_col and name not in header_resolved)
                       else vals)
                for name, vals in result.items()
            }
        return result
    if tcf_text.startswith(_SINGLE_MAGIC_V8 + "\n"):
        # Single-col self-describing (#TCF.8 SEM M, ADR-0027): linha 1 '#TCF.8',
        # linha 2 '[nome]:spec_id' (nome opcional, so' rotulo -> descartado),
        # resto = body. Retorna LIST (single-col).
        nl1 = tcf_text.index("\n")
        nl2 = tcf_text.index("\n", nl1 + 1)
        meta = tcf_text[nl1 + 1:nl2]
        body = tcf_text[nl2 + 1:]
        _name, _, nat_id = meta.partition(":")
        values = _decode_column(body)
        from tcf.natures import _resolve_nature_id
        spec = _resolve_nature_id(nat_id)
        if spec is not None:
            # header vence: resolve+aplica e ignora um `nature=` redundante do
            # usuario (evita dupla aplicacao no RT).
            return [spec.decode_value(v) for v in values]
        # forward-compat: id desconhecido -> valor CRU + aviso (nao silencioso,
        # nao KeyError). Usuario pode completar via `nature=`.
        import warnings
        warnings.warn(
            f"nature-id desconhecido no header single-col: {nat_id!r} "
            f"-> valor mantido cru",
            stacklevel=2,
        )
        if nature is not None:
            from tcf.natures.templated_checked import decode_value
            values = [decode_value(nature, v) for v in values]
        return values
    values = _decode_column(tcf_text)
    if nature is not None:
        from tcf.natures.templated_checked import decode_value
        values = [decode_value(nature, v) for v in values]
    return values


def _decode_column(tcf_text: str) -> list[str]:
    """Decode body single-col. Cf. _encode_column no encoder."""
    syn = HCCSeqRLE()
    return syn.decode(tcf_text)

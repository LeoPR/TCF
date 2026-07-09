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


# #TCF.8 = formato VIVO/DEFAULT (ADR-0032). O char logo apos '#TCF.8' discrimina:
# 'M'=multi (#TCF.8M, meta inline), ' '=single+spec (#TCF.8 [nome]:spec),
# ''=single version-stamp (#TCF.8, magic-number p/ file), 'H'=hierarquico RESERVADO
# (ADR-0031, codec no lab -> fail-loud). Legado #TCF.6/#TCF.7 CORTADO (git-as-compat).
_V8_MAGIC = "#TCF.8"                  # base do #TCF.8; o disc (char no indice 6) decide


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
    line1 = tcf_text.split("\n", 1)[0]
    # Legado #TCF.6/#TCF.7 CORTADO (ADR-0032, 2026-07-09): nao decodavel no 0.8.
    # git-as-compat (ADR-0024) — recupere a era pra ler/comparar.
    if line1.startswith("#TCF.6") or line1.startswith("#TCF.7"):
        raise ValueError(
            f"formato legado {line1[:8]!r} nao suportado no 0.8 (ADR-0032: #TCF.6/.7 "
            f"cortados). git checkout <commit pre-0.8> pra ler, ou re-encode com o 0.8."
        )
    # Discriminador #TCF.8 (ADR-0029): char logo apos '#TCF.8'. 'M'=multi (#TCF.8M),
    # ' '=single+spec (#TCF.8 ...), ''=version-stamp (line1 == '#TCF.8').
    disc8 = line1[6:7] if line1.startswith(_V8_MAGIC) else None
    # FAIL-LOUD (ADR-0032 §6): discriminador reservado/desconhecido apos '#TCF.8' NAO
    # pode degradar pra decode orfao silencioso (corrompe). 'H' = hierarquico reservado
    # (ADR-0031), codec ainda no lab.
    if disc8 is not None and disc8 not in ("M", " ", ""):
        detalhe = ("'H' = multi-col hierarquico RESERVADO (ADR-0031); codec no lab, "
                   "nao implementado" if disc8 == "H" else f"discriminador {disc8!r} desconhecido")
        raise ValueError(f"#TCF.8: {detalhe} — nao decodavel.")

    # MULTI: #TCF.8M (disc 'M', meta inline).
    if disc8 == "M":
        from tcf.multi import _decode_multi_impl
        result, header_ids = _decode_multi_impl(tcf_text)
        # Natures auto-descritas no header (#TCF.8): resolve+aplica. PRECEDENCIA:
        # header vence pros 3 ids core; o usuario completa o resto via
        # nature_per_col. Sem isso, encode(nature)+decode(nature) aplicaria DUAS
        # vezes (header + usuario) e quebraria o RT.
        header_resolved: set[str] = set()
        if header_ids:
            from tcf.natures import _resolve_nature_id
            for name, nat_id in header_ids.items():
                spec = _resolve_nature_id(nat_id)
                if spec is not None:
                    result[name] = [spec.decode_value(v) for v in result[name]]
                    header_resolved.add(name)
                else:
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

    # SINGLE + SPEC: '#TCF.8 [nome]:spec' (disc espaco). Retorna LIST.
    if disc8 == " ":
        meta = line1[len(_V8_MAGIC) + 1:]          # apos "#TCF.8 "
        body = tcf_text[len(line1) + 1:]           # apos a 1a '\n'
        _name, _, nat_id = meta.partition(":")     # nome opcional, descartado
        values = _decode_column(body)
        from tcf.natures import _resolve_nature_id
        spec = _resolve_nature_id(nat_id)
        if spec is not None:
            return [spec.decode_value(v) for v in values]   # header vence
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

    # SINGLE version-stamp: line1 == '#TCF.8' (disc vazio). Carimbo de versao
    # (magic-number p/ file/libmagic, ADR-0029) — body single-col puro segue.
    if disc8 == "":
        body = tcf_text[len(line1) + 1:]           # apos "#TCF.8\n"
        values = _decode_column(body)
        if nature is not None:
            from tcf.natures.templated_checked import decode_value
            values = [decode_value(nature, v) for v in values]
        return values

    # ORFAO: single-col body puro (sem shebang) — camada 1 (ADR-0029).
    values = _decode_column(tcf_text)
    if nature is not None:
        from tcf.natures.templated_checked import decode_value
        values = [decode_value(nature, v) for v in values]
    return values


def _decode_column(tcf_text: str) -> list[str]:
    """Decode body single-col. Cf. _encode_column no encoder."""
    syn = HCCSeqRLE()
    return syn.decode(tcf_text)

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
_V8_MAGIC = "#TCF.8"  # base do #TCF.8; o disc (char no indice 6) decide


def _resolve_header_spec(nature_id: str, supplied, *, where: str):
    """Resolve um ID do header pelo registry core ou por spec declarado fora dele."""
    from tcf.natures import _resolve_nature_id

    spec = _resolve_nature_id(nature_id)
    if spec is not None:
        return spec
    if supplied is not None and getattr(supplied, "name", None) == nature_id:
        return supplied
    if supplied is not None:
        raise ValueError(
            f"nature-id {nature_id!r} no header {where} nao coincide com o spec "
            f"out-of-band {getattr(supplied, 'name', None)!r}"
        )
    raise ValueError(
        f"nature-id desconhecido no header {where}: {nature_id!r} — registry core "
        "fechado; forneca o spec correspondente out-of-band para decodificar"
    )


def decode(
    tcf_text: str,
    *,
    nature: "TemplatedCheckedSpec | None" = None,
    nature_per_col: "dict[str, TemplatedCheckedSpec] | None" = None,
) -> list[str] | dict[str, list[str]]:
    """Decode texto TCF. Roteia pela assinatura de formato (magic).

    Args:
        tcf_text: conteudo TCF (texto). Aceita (ADR-0032, #TCF.8 default):
            - Multi-col: `#TCF.8M<meta>\\n<bodies>` -> `dict[str, list[str]]`
            - Single + spec: `#TCF.8 [nome]:id\\n<body>` -> `list[str]`
            - Version-stamp: `#TCF.8\\n<body>` -> `list[str]`
            - Orfao: body puro (sem magic) -> `list[str]`
            Legado `#TCF.6/.7` e versoes desconhecidas `#TCF.<N>` -> ValueError
            (git-as-compat, ADR-0024).
        nature: spec usado no encode pra pre-tx (ADR-0015). Se fornecido,
            aplica decode_value reverse apos M10 decode.
        nature_per_col: dict pra reverse multi-col pre-tx.

    Returns:
        list[str] OU dict[str, list[str]] dependendo do formato.

    Raises:
        ValueError: multi-col malformado (sem magic, sem meta line).
    """
    if not isinstance(tcf_text, str):
        # BUG-10d (lote 3): fronteira clara em vez de AttributeError fundo.
        raise TypeError(
            f"decode espera str (conteudo TCF em texto); got {type(tcf_text).__name__}"
        )
    line1 = tcf_text.split("\n", 1)[0]
    # BUG-04 (T-QA-8 F0 lote 2): a VERSAO e' deduzivel do proprio magic —
    # '#TCF.' + run de digitos DECLARA a versao. Le o run COMPLETO (senao
    # '#TCF.85M' viraria .8 + disc '5'). Subversoes pre-1.0 sao controle de
    # dev (ADR-0024); compat real so' no 1.0 (visao owner 2026-07-10: um
    # '#TCF1M' final fecha tudo — sem 'if .7'/'if .6').
    _ver = ""
    if line1.startswith("#TCF."):
        for _ch in line1[5:]:
            if _ch in "0123456789":
                _ver += _ch
            else:
                break
    # Legado #TCF.6/#TCF.7 CORTADO (ADR-0032, 2026-07-09): nao decodavel no 0.8.
    # git-as-compat (ADR-0024) — recupere a era pra ler/comparar.
    if _ver in ("6", "7"):
        raise ValueError(
            f"formato legado {line1[:8]!r} nao suportado no 0.8 (ADR-0032: #TCF.6/.7 "
            f"cortados). git checkout <commit pre-0.8> pra ler, ou re-encode com o 0.8."
        )
    if _ver and _ver != "8":
        # Fail-loud claro (antes caia no decode orfao -> KeyError criptico do HCC).
        raise ValueError(
            f"blob #TCF.{_ver}: versao desconhecida deste decoder (formato atual = "
            f"#TCF.8, ADR-0032). Versoes de dev vivem no git (ADR-0024); "
            f"compatibilidade real so' a partir do 1.0."
        )
    # Discriminador #TCF.8 (ADR-0029): char logo apos '#TCF.8'. 'M'=multi (#TCF.8M),
    # ' '=single+spec (#TCF.8 ...), ''=version-stamp (line1 == '#TCF.8').
    disc8 = line1[6:7] if _ver == "8" else None
    # HIER: #TCF.8H (disc 'H', ADR-0031) — codec hierarquico (weld T-CODE-TCF8H-WELD).
    # Camada L2 aditiva: dispatch O(1) pelo char; L1 (compressor de coluna) reusado.
    if disc8 == "H":
        from tcf.hierarchical import decode_hierarchical

        return decode_hierarchical(tcf_text)
    # FAIL-LOUD (ADR-0032 §6): discriminador reservado/desconhecido apos '#TCF.8' NAO
    # pode degradar pra decode orfao silencioso (corrompe).
    if disc8 is not None and disc8 not in ("M", " ", ""):
        raise ValueError(f"#TCF.8: discriminador {disc8!r} desconhecido — nao decodavel.")

    # MULTI: #TCF.8M (disc 'M', meta inline).
    if disc8 == "M":
        from tcf.multi import _decode_multi_impl

        result, header_ids = _decode_multi_impl(tcf_text)
        # Natures auto-descritas no header (#TCF.8M e' SELF-DESCRIBING): o header e'
        # AUTORITATIVO — resolve+aplica os :id. Pos-FLOOR (T-SPEC-DEEPDIVE §5.1), uma
        # coluna SEM :id significa DEFINITIVAMENTE valores ORIGINAIS (a nature perdeu
        # o min() ou nao foi passada). Logo o `nature_per_col` out-of-band do decode
        # NAO deve tocar colunas nao-marcadas — fazia isso e CORROMPIA silenciosamente
        # valores que casassem a forma base-94 (achado da verificacao adversarial do
        # FLOOR, 2026-07-12). Para IDs fora do registry core, o spec out-of-band so'
        # entra se o nome coincidir exatamente com o ID do header.
        header_resolved: set[str] = set()
        if header_ids:
            for name, nat_id in header_ids.items():
                supplied = nature_per_col.get(name) if nature_per_col else None
                spec = _resolve_header_spec(
                    nat_id, supplied, where=f"multi-col coluna {name!r}"
                )
                result[name] = [spec.decode_value(v) for v in result[name]]
                header_resolved.add(name)
        # Colunas sem :id continuam definitivamente originais; o parâmetro
        # out-of-band não pode inferir uma nature perdida pelo FLOOR.
        return result

    # SINGLE + SPEC: '#TCF.8 [nome]:spec' (disc espaco). Retorna LIST.
    if disc8 == " ":
        meta = line1[len(_V8_MAGIC) + 1 :]  # apos "#TCF.8 "
        body = tcf_text[len(line1) + 1 :]  # apos a 1a '\n'
        _name, _, nat_id = meta.partition(":")  # nome opcional, descartado
        values = _decode_column(body)
        spec = _resolve_header_spec(nat_id, nature, where="single-col")
        return [spec.decode_value(v) for v in values]  # header vence

    # SINGLE version-stamp: line1 == '#TCF.8' (disc vazio). Carimbo de versao
    # (magic-number p/ file/libmagic, ADR-0029) — body single-col puro segue.
    # Out-of-band `nature=` NAO aplicado: pos-FLOOR (T-SPEC-DEEPDIVE §5.1) uma nature
    # que VENCE emite '#TCF.8 :id' (self-describing); stamp/orfao = valores ORIGINAIS
    # (a nature perdeu OU nao foi passada). Aplicar o spec aqui corromperia originais
    # que casassem a forma base-94 (mesma classe do achado multi-col; o param fica na
    # assinatura por compat, mas #TCF.8 e' self-describing e manda).
    if disc8 == "":
        return _decode_column(tcf_text[len(line1) + 1 :])  # apos "#TCF.8\n"

    # ORFAO: single-col body puro (sem shebang) — camada 1 (ADR-0029).
    return _decode_column(tcf_text)


def _decode_column(tcf_text: str) -> list[str]:
    """Decode body single-col. Cf. _encode_column no encoder."""
    syn = HCCSeqRLE()
    return syn.decode(tcf_text)

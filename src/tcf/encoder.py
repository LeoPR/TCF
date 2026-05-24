"""TCF encoder — API publica unificada (ADR-0014).

Pipeline canonical M10 (ADR-0011, T-CODE-PACOTE1-WELD-CANONICAL):

    values (por coluna)
      -> analyze_column (features pre-pass O(N))
      -> detect_cadence_from_features (regras 1+2, ADR-0008)
      -> detect_min_len_from_features (heur v3, ADR-0010)
      -> OBAT tokeniza (processar_with_hint se cadence, senao processar)
      -> HCCSeqRLE compacta body (com seq-RLE near-identical `*N+delta|`)
      -> texto TCF

API publica unificada (ADR-0014):

    from tcf import encode, SideOutputs

    text = encode(["a", "b", "c"])              # single -> body puro
    text = encode({"id": [...], "name": [...]}) # multi -> #TCF.6 M + bodies

    # Captura opcional de side outputs (debug, stats, schema)
    side = SideOutputs()
    text = encode(data, side_outputs=side)
    print(side.hcc_trace)        # trace detector HCC
    print(side.column_features)  # features pre-pass
    # ... etc

Detalhes:
- `docs/algorithms/OBAT.md`, `docs/algorithms/HCC.md`
- `docs/adr/0011-pacote1-weld-canonical.md` — pipeline M10
- `docs/adr/0013-multi-column-canonical-api.md` — header multi-col
- `docs/adr/0014-unified-api-side-outputs.md` — unificacao + side outputs
"""

from __future__ import annotations

from collections import OrderedDict

from tcf.auto_cadence import detect_cadence_from_features
from tcf.auto_min_len import detect_min_len_from_features
from tcf.column_features import analyze_column
from tcf.composicional.hcc_seqrle import HCCSeqRLE
from tcf.core.online import processar
from tcf.obat_shape import processar_with_hint
from tcf.side_outputs import SideOutputs


def encode(
    data: list[str] | dict[str, list[str]],
    *,
    side_outputs: SideOutputs | None = None,
) -> str:
    """Encode lista de strings OU dict de colunas em texto TCF.

    Args:
        data:
            - `list[str]`: single-column. Output = body puro (sem shebang).
            - `dict[str, list[str]]`: multi-column. Output = `#TCF.6 M\\n`
              + meta line + bodies concatenados byte-precise.
        side_outputs: opcional. Se fornecido, captura logs/info interna
            (column_features, cadence_info, OBAT log, HCC trace/rede,
            seq_rle_runs, multi_info, per_col). Sem ele: descartado
            (comportamento pre-existente, overhead zero).

    Returns:
        Texto TCF (str, sempre UTF-8, LF only).

    Raises:
        TypeError: se data nao for list nem dict.
        ValueError: (multi) table vazia, lengths divergentes,
            ou nomes com `,` / `=`.
    """
    if isinstance(data, list):
        return _encode_column(data, header="val", side=side_outputs)
    if isinstance(data, dict):
        from tcf.multi import _encode_multi
        return _encode_multi(data, side_outputs=side_outputs)
    raise TypeError(
        f"encode espera list[str] ou dict[str, list[str]], "
        f"recebeu {type(data).__name__}"
    )


def _encode_column(
    values: list[str],
    *,
    header: str = "val",
    side: SideOutputs | None = None,
) -> str:
    """Pipeline canonical M10 por coluna. Capta side outputs se fornecido.

    Esta eh a "encode unit" (cf. plano v0.4 D13 EncodeManager). O
    dispatcher `encode()` chama esta funcao 1+ vezes (1 pra list, N
    pra dict).
    """
    seen: OrderedDict[str, bool] = OrderedDict()
    for s in values:
        seen[s] = True
    unicas = list(seen.keys())

    features = analyze_column(values)
    cadence_detected, cadence_info = detect_cadence_from_features(features, unicas)
    min_len = detect_min_len_from_features(features)

    if cadence_detected:
        tokens, obat_log = processar_with_hint(
            unicas, min_len=min_len, prefer_shape_consistency=True
        )
        used_hint = True
    else:
        tokens, obat_log = processar(unicas, min_len=min_len)
        used_hint = False

    syn = HCCSeqRLE()
    body = syn.encode(values, unicas, tokens, header)

    if side is not None:
        side.column_features = features
        side.cadence_detected = cadence_detected
        side.cadence_info = cadence_info
        side.min_len = min_len
        side.obat_log = obat_log
        side.obat_used_hint = used_hint
        side.hcc_trace = syn.get_trace()
        side.hcc_rede = syn.get_rede()
        side.seq_rle_runs = syn.get_seq_info()
        side.body_bytes = len(body.encode("utf-8"))

    return body

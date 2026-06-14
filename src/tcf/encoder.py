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

Invariantes byte-canonical guardados por `tests/test_core_rt.py` +
`tests/test_regression_v1_baseline.py` (D1-D9=1523B, D17a=322B) e
`tests/test_real_world_snapshots.py` (bytes reais; GATE de qualquer mudanca
em pre-pass/OBAT/HCC). Identidade decode(encode(x))==x: ver decoder.py.
"""

from __future__ import annotations

from collections import OrderedDict
from typing import TYPE_CHECKING

from tcf.auto_cadence import detect_cadence_from_features
from tcf.auto_min_len import detect_min_len_from_features
from tcf.column_features import analyze_column
from tcf.composicional.hcc_seqrle import HCCSeqRLE
from tcf.composicional.syntax import M8AVirtualRefsSyntax
from tcf.core.online import processar
from tcf.obat_shape import processar_with_hint
from tcf.pipeline import DEFAULT_PIPELINE, PipelineConfig
from tcf.side_outputs import SideOutputs

if TYPE_CHECKING:
    from tcf.natures.templated_checked import TemplatedCheckedSpec


def encode(
    data: list[str] | dict[str, list[str]],
    *,
    side_outputs: SideOutputs | None = None,
    parallel: bool | int = False,
    nature: "TemplatedCheckedSpec | None" = None,
    nature_per_col: "dict[str, TemplatedCheckedSpec] | None" = None,
    layers: PipelineConfig | None = None,
    fallback: bool = True,
    min_header: bool = True,
    min_len: int | None = None,
) -> str:
    """Encode lista de strings OU dict de colunas em texto TCF.

    Multi-col sai no formato **0.7 / `#TCF.7`** por default (ADR-0024): por
    coluna escolhe min(TCF, raw) e usa o header minimo (sem prefixo, ultima
    coluna sem size). Single-col nao tem header — inalterado. Pra forcar o
    formato legado `#TCF.6` (comparacao/inspecao), passe
    `fallback=False, min_header=False`.

    Args:
        data:
            - `list[str]`: single-column. Output = body puro (sem shebang).
            - `dict[str, list[str]]`: multi-column. Output = `#TCF.7 M\\n`
              + meta line + bodies concatenados byte-precise.
        side_outputs: opcional. Se fornecido, captura logs/info interna
            (column_features, cadence_info, OBAT log, HCC trace/rede,
            seq_rle_runs, multi_info, per_col). Sem ele: descartado
            (comportamento pre-existente, overhead zero).
        parallel: paraleliza encode de colunas (multi-col so'). T-CODE-ENCODER-MANAGER Fase 1.
            - `False` (default): serial, comportamento atual
            - `True`: ProcessPoolExecutor com `os.cpu_count()` workers
            - `int N >= 1`: N workers explicitos
            - Para list (single-col): parametro ignorado (1 coluna)
            - Para dict com 1 coluna: ignorado (overhead nao compensa)
        nature: pre-tx por natureza (ADR-0015, CAMADA 0 do funil). Se
            fornecido, aplica `tcf.natures.encode_value(spec, v)` em cada
            valor antes do pipeline M10. Decoder precisa receber MESMO
            spec out-of-band. Pra list[str] apenas.
        nature_per_col: dict mapeando col_name -> spec. Pra dict input
            (multi-col); permite pre-tx natureza diferente por coluna.
        fallback: (multi-col) por coluna escolhe min(TCF, raw). **Default True**
            (0.7). False -> mantem TCF em toda coluna. Knob opt-out: o default
            zero-param continua 0.7; passe False so' pra modificar comportamento
            (ex: forcar #TCF.6 junto com `min_header=False`). Ignorado pra list.
        min_header: (multi-col) header minimo (meta sem prefixo, ultima coluna
            sem size). **Default True** (0.7). False -> header legado
            `# size=name,...`. Knob opt-out. Ignorado pra list.
        min_len: override manual do min_len do OBAT (afixos com `length <
            min_len` viram literal). **Default None -> auto** (detect_min_len
            por coluna; comportamento inalterado). int >= 1 aplica o mesmo
            min_len a TODAS as colunas (tuning manual). Muda os bytes — so'
            quando passado explicitamente.

    Returns:
        Texto TCF (str, sempre UTF-8, LF only). **Output byte-identico
        ao modo serial** (parallel apenas reordena computacao, nao bytes).

    Raises:
        TypeError: se data nao for list nem dict.
        ValueError: (multi) table vazia, lengths divergentes,
            ou nomes com `,` / `=`.
    """
    cfg = layers if layers is not None else DEFAULT_PIPELINE
    if min_len is not None and min_len < 1:
        raise ValueError(f"min_len deve ser >= 1 (ou None pra auto); got {min_len}")
    if isinstance(data, list):
        if nature is not None:
            from tcf.natures.templated_checked import encode_value
            data = [encode_value(nature, v)[0] for v in data]
        return _encode_column(data, header="val", side=side_outputs, cfg=cfg,
                              min_len=min_len)
    if isinstance(data, dict):
        from tcf.multi import _encode_multi
        if nature_per_col:
            from tcf.natures.templated_checked import encode_value
            data = {
                name: ([encode_value(nature_per_col[name], v)[0] for v in vals]
                       if name in nature_per_col else vals)
                for name, vals in data.items()
            }
        return _encode_multi(data, side_outputs=side_outputs, parallel=parallel,
                             cfg=cfg, fallback=fallback, min_header=min_header,
                             min_len=min_len)
    raise TypeError(
        f"encode espera list[str] ou dict[str, list[str]], "
        f"recebeu {type(data).__name__}"
    )


def _encode_column(
    values: list[str],
    *,
    header: str = "val",
    side: SideOutputs | None = None,
    cfg: PipelineConfig = DEFAULT_PIPELINE,
    min_len: int | None = None,
) -> str:
    """Pipeline canonical M10 por coluna. Capta side outputs se fornecido.

    Esta eh a "encode unit" (cf. plano v0.4 D13 EncodeManager). O
    dispatcher `encode()` chama esta funcao 1+ vezes (1 pra list, N
    pra dict).

    `cfg` controla quais camadas aplicar (T-CODE-LAYERED-PIPELINE Fase 1).
    Default = M10 canonical (todas camadas on).

    `min_len` (Segment 2): override manual do min_len do OBAT. None (default)
    -> auto (detect_min_len, ou 3 se pre_pass off). Comportamento inalterado
    no default.
    """
    seen: OrderedDict[str, bool] = OrderedDict()
    for s in values:
        seen[s] = True
    unicas = list(seen.keys())

    # CAMADA 1 — Pre-pass (toggleable)
    features = analyze_column(values)  # sempre computa (barato, util pra side)
    if cfg.pre_pass:
        cadence_detected, cadence_info = detect_cadence_from_features(features, unicas)
        auto_min_len = detect_min_len_from_features(features)
    else:
        cadence_detected = False
        cadence_info = {"rule_hit": None, "reason": "pre_pass disabled by cfg"}
        auto_min_len = 3  # default M9
    # Override explicito (Segment 2): min_len manual sobrepoe o auto/default.
    min_len = min_len if min_len is not None else auto_min_len

    # CAMADA 2 — OBAT (shape-preserve toggleable se cadence detected)
    if cadence_detected and cfg.obat_shape_preserve:
        tokens, obat_log = processar_with_hint(
            unicas, min_len=min_len, prefer_shape_consistency=True
        )
        used_hint = True
    else:
        tokens, obat_log = processar(unicas, min_len=min_len)
        used_hint = False

    # CAMADA 3 — HCC (seq-RLE toggleable; sem seq-RLE = M9 puro)
    if cfg.hcc_seq_rle:
        syn = HCCSeqRLE()
    else:
        syn = M8AVirtualRefsSyntax()
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
        # seq_rle_runs so' existe em HCCSeqRLE; M8AVirtualRefsSyntax nao tem
        side.seq_rle_runs = syn.get_seq_info() if hasattr(syn, 'get_seq_info') else []
        side.body_bytes = len(body.encode("utf-8"))

    return body

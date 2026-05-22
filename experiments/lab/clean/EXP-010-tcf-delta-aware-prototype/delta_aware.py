"""Delta-aware encoder/decoder — API publica do prototype EXP-010.

Pipeline single-column:
  Pre (auto-detect cadence) → OBAT (canonical OU shape-preserve) → HCC fork seq-RLE

API:
  encode_column(rows, ..., include_shebang=True) -> (text, info)
  decode_column(tcf_text, expect_shebang=True) -> list[str]

Header (uniformizado 2026-05-17):
  Default: emite shebang `#TCF.6` (versao 0.6, sem flags)
  Multi-column adiciona flag `M` no shebang (ver multi_col.py)
  Excecao: `include_shebang=False` quando caller garante formato
           out-of-band (caso raro)

Welded do pacote 1 (Delta-aware) do dirty lab:
- detect_cadence (auto_pre.py) ← sub-exp 09
- processar_with_hint (obat_shape.py) ← sub-exp 04
- HCCSeqRLE (hcc_seqrle.py) ← sub-exp 02 (post bug-fix do sub-exp 04)

Restricao: single-column. Multi-column expansao em EXP-011 (multi_col.py).
"""

from __future__ import annotations

from collections import OrderedDict

from tcf.core.online import processar

from auto_pre import detect_cadence
from auto_min_len import detect_min_len
from obat_shape import processar_with_hint
from hcc_seqrle import HCCSeqRLE


SHEBANG = "#TCF.6"  # versao 0.6 — regra: major 0 omite "0", escreve `.<minor>`


def _dedup_preserve_order(values: list[str]) -> list[str]:
    seen: OrderedDict[str, bool] = OrderedDict()
    for v in values:
        seen[v] = True
    return list(seen.keys())


def encode_column(rows: list[str], header: str = "val",
                    min_len: int | None = None,
                    detector_threshold: float = 0.7,
                    force_hint: bool | None = None,
                    include_shebang: bool = True) -> tuple[str, dict]:
    """Encode 1 coluna pra TCF delta-aware.

    Args:
        rows: linhas brutas (com possiveis duplicatas adjacentes)
        header: nome semantico (nao emitido em single-col)
        min_len: minimo LCP/LCS pra criar ref. None = auto-detect via
                 detect_min_len (ADR-0010, H-DA-11): gating n>=100 com
                 heur v3 (avg_len + cardinality + is_numeric). Datasets
                 pequenos (n<100) usam ml=3 default (preserva M9 baseline);
                 datasets >=100 rows usam heuristica (captura ~9.87%
                 weighted real-world).
        detector_threshold: limiar do auto-detect cadence (default 0.7)
        force_hint: se None, auto-detect decide. Se True/False, forca.
        include_shebang: default True (uniformizado). False so' em
                         caso excepcional (caller garante formato
                         out-of-band, ex: tabela multi-col que
                         emite shebang proprio).

    Returns:
        (tcf_text, info)
    """
    unicas = _dedup_preserve_order(rows)

    # Auto-detect min_len se nao especificado (ADR-0010)
    if min_len is None:
        min_len = detect_min_len(rows)
    min_len_auto = (min_len is not None)

    if force_hint is not None:
        cadence_detected = False
        detect_info = {"reason": "force_hint override"}
        hint_used = force_hint
    else:
        cadence_detected, detect_info = detect_cadence(
            unicas, threshold=detector_threshold
        )
        hint_used = cadence_detected

    if hint_used:
        tokens, _ = processar_with_hint(
            unicas, min_len=min_len, prefer_shape_consistency=True
        )
    else:
        tokens, _ = processar(unicas, min_len=min_len)

    syn = HCCSeqRLE()
    body = syn.encode(rows, unicas, tokens, header)

    if include_shebang:
        body = SHEBANG + "\n" + body

    info = {
        "cadence_detected": cadence_detected,
        "detect_info": detect_info,
        "hint_used": hint_used,
        "min_len": min_len,
        "min_len_auto": min_len_auto,
        "n_unicas": len(unicas),
        "n_rows": len(rows),
        "n_seq_runs": len(syn.get_seq_info()),
        "shebang": include_shebang,
    }
    return body, info


def decode_column(tcf_text: str, expect_shebang: bool = True) -> list[str]:
    """Decode TCF delta-aware pra lista de linhas.

    Args:
        tcf_text: conteudo TCF.
        expect_shebang: default True. False quando caller garante
                        que shebang foi omitido (ex: bodies dentro
                        de tabela multi-col).
    """
    if expect_shebang:
        if not tcf_text.startswith(SHEBANG + "\n"):
            raise ValueError(
                f"esperado shebang {SHEBANG!r}, got {tcf_text[:20]!r}"
            )
        tcf_text = tcf_text[len(SHEBANG) + 1:]
    syn = HCCSeqRLE()
    return syn.decode(tcf_text)

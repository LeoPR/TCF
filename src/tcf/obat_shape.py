"""OBAT com dica generica `prefer_shape_consistency`.

CAMADA-0/1 (limitrofe): recebe hint do pre-pass (detect_cadence) e estende
OBAT (core/online.py). Ordem do pipeline: pre-pass -> OBAT (core/) -> HCC
(composicional/). Irmaos pre-pass: auto_cadence, auto_min_len, column_features.

Welded canonical 2026-05-22 (T-CODE-PACOTE1-WELD-CANONICAL).
Origem: `experiments/lab/clean/EXP-010-tcf-delta-aware-prototype/obat_shape.py`
(welded 2026-05-17 do dirty lab `04-obat-shape-consistency-hint/obat_fork.py`).

Comportamento:
- Apos cada emissao, memoriza shape (p_src, p_len, has_L, s_src, s_len)
- Pra proxima string, tenta replicar shape se permitido pelo LCP/LCS
- Wider fallback: reduz lens pra max permitido se exato falhar
- Greedy fallback: cai pra OBAT canonical se nem o wider funciona

Atualizado pra nova assinatura indexed de `_escolher_par` (ADR-0009).
Mantem byte-canonical.

src/tcf/core/online.py intocado — importa e estende.
"""

from __future__ import annotations

from tcf.core.online import (
    TokLit,
    TokRefPref,
    TokRefSuf,
    Token,
    lcp_len,
    lcs_len,
    _escolher_par,
)


def _try_preserve_shape(s: str, strings: list[str], idx_limit: int,
                          last_shape: tuple, min_len: int
                          ) -> tuple[int, int, int, int] | None:
    """Tenta replicar last_shape. Retorna (p_id, p_len, s_id, s_len) ou None."""
    p_src, p_len_old, has_L, s_src, s_len_old = last_shape
    if not has_L:
        return None
    if p_src > idx_limit or s_src > idx_limit:
        return None
    prev_p = strings[p_src - 1]
    prev_s = strings[s_src - 1]

    lcp_avail = lcp_len(s, prev_p)
    lcs_avail = lcs_len(s, prev_s)

    # Exato
    if lcp_avail >= p_len_old and lcs_avail >= s_len_old:
        new_l = len(s) - p_len_old - s_len_old
        if new_l > 0:
            return (p_src, p_len_old, s_src, s_len_old)

    # Wider fallback
    new_p_len = min(p_len_old, lcp_avail)
    new_s_len = min(s_len_old, lcs_avail)
    if new_p_len >= min_len and new_s_len >= min_len:
        new_l = len(s) - new_p_len - new_s_len
        if new_l > 0:
            return (p_src, new_p_len, s_src, new_s_len)

    return None


def processar_with_hint(strings_unicas: list[str], min_len: int = 3,
                         prefer_shape_consistency: bool = False
                         ) -> tuple[list[list[Token]], str]:
    """Variante de processar() com dica opcional.

    Quando prefer_shape_consistency=False, comportamento equivalente
    ao processar() canonical de src/tcf/core/online.py.
    """
    log: list[str] = [f"min_len={min_len}",
                      f"prefer_shape_consistency={prefer_shape_consistency}",
                      ""]
    tokens_por_string: list[list[Token]] = []
    last_shape: tuple | None = None
    lens = [len(s) for s in strings_unicas]
    prefix_index: dict[str, list[int]] = {}
    suffix_index: dict[str, list[int]] = {}

    for idx, s in enumerate(strings_unicas):
        ls = lens[idx]
        if idx == 0:
            tokens_por_string.append([TokLit(s)])
            if ls >= min_len:
                prefix_index.setdefault(s[:3], []).append(idx)
                suffix_index.setdefault(s[-3:], []).append(idx)
            continue

        emitted = None
        if prefer_shape_consistency and last_shape is not None:
            tried = _try_preserve_shape(s, strings_unicas, idx, last_shape, min_len)
            if tried is not None:
                emitted = tried

        if emitted is None:
            emitted = _escolher_par(
                s, ls, strings_unicas, lens, prefix_index, suffix_index, min_len
            )

        bp_id, bp_len, bs_id, bs_len = emitted

        tokens: list[Token] = []
        if bp_len > 0:
            tokens.append(TokRefPref(bp_id, bp_len))
        meio = s[bp_len: ls - bs_len]
        if meio:
            tokens.append(TokLit(meio))
        if bs_len > 0:
            tokens.append(TokRefSuf(bs_id, bs_len))

        tokens_por_string.append(tokens)
        has_lit = bool(meio)
        last_shape = (bp_id, bp_len, has_lit, bs_id, bs_len)

        if ls >= min_len:
            prefix_index.setdefault(s[:3], []).append(idx)
            suffix_index.setdefault(s[-3:], []).append(idx)

    return tokens_por_string, "\n".join(log)

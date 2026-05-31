"""OBAT fork — aceita dica generica `prefer_shape_consistency`.

Quando ativada, prefere emitir mesma shape (P+L+S) que a anterior, se
LCP/LCS permitirem, mesmo que nao seja greedy maximo. Objetivo:
manter shape atraves de transicoes (ex: cardinalidade `\\9` → `\\10`),
permitindo seq-RLE no HCC.

Fallback duplo:
1. **Exato**: mesma source + lens
2. **Mais largo**: mesma source + lens reduzidos pra max permitido
3. **Greedy**: cai pra OBAT canonical

src/tcf/core/online.py intocado.
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


def _try_preserve_shape(s: str, anteriores: list[str], last_shape: tuple,
                          min_len: int) -> tuple[int, int, int, int] | None:
    """Tenta replicar shape memorizada. Retorna (p_id, p_len, s_id, s_len)
    ou None se nao for possivel.

    Estrategia:
    - Exato primeiro: mesmas sources, mesmos lens
    - Wider fallback: mesmas sources, lens = min(lens, max permitido)
    - Se nem o wider funcionar (lens < min_len ou L vazio), retorna None
    """
    p_src, p_len_old, has_L, s_src, s_len_old = last_shape
    if not has_L:
        return None  # so' replicamos shapes com Literal
    if p_src > len(anteriores) or s_src > len(anteriores):
        return None
    if p_src == s_src:
        prev_p = anteriores[p_src - 1]
        prev_s = prev_p
    else:
        prev_p = anteriores[p_src - 1]
        prev_s = anteriores[s_src - 1]

    lcp_avail = lcp_len(s, prev_p)
    lcs_avail = lcs_len(s, prev_s)

    # Exato
    if lcp_avail >= p_len_old and lcs_avail >= s_len_old:
        new_p_len = p_len_old
        new_s_len = s_len_old
        new_l = len(s) - new_p_len - new_s_len
        if new_l > 0:
            return (p_src, new_p_len, s_src, new_s_len)

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
    ao canonical.
    """
    log: list[str] = [
        f"min_len = {min_len}",
        f"prefer_shape_consistency = {prefer_shape_consistency}",
        ""
    ]
    tokens_por_string: list[list[Token]] = []
    last_shape: tuple | None = None  # (p_src, p_len, has_L, s_src, s_len)

    for idx, s in enumerate(strings_unicas):
        log.append(f"--- string {idx + 1}: {s!r} (len={len(s)}) ---")

        if idx == 0:
            tokens_por_string.append([TokLit(s)])
            log.append("  primeira string -> literal puro")
            log.append("")
            continue

        anteriores = strings_unicas[:idx]

        emitted = None
        emit_path = "greedy"

        if prefer_shape_consistency and last_shape is not None:
            tried = _try_preserve_shape(s, anteriores, last_shape, min_len)
            if tried is not None:
                emitted = tried
                emit_path = "shape-preserved"

        if emitted is None:
            bp_id, bp_len, bs_id, bs_len = _escolher_par(s, anteriores, min_len)
            emitted = (bp_id, bp_len, bs_id, bs_len)

        bp_id, bp_len, bs_id, bs_len = emitted
        log.append(f"  {emit_path}: pref(s{bp_id},{bp_len}) + suf(s{bs_id},{bs_len})")
        log.append(f"  cobertura: {bp_len + bs_len} de {len(s)}")

        tokens: list[Token] = []
        if bp_len > 0:
            tokens.append(TokRefPref(bp_id, bp_len))
        meio = s[bp_len: len(s) - bs_len]
        if meio:
            tokens.append(TokLit(meio))
        if bs_len > 0:
            tokens.append(TokRefSuf(bs_id, bs_len))

        tokens_por_string.append(tokens)
        log.append(f"  tokens: [{' + '.join(repr(t) for t in tokens)}]")

        # Update last_shape
        has_lit = bool(meio)
        last_shape = (bp_id, bp_len, has_lit, bs_id, bs_len)
        log.append(f"  last_shape: src_p={bp_id} p_len={bp_len} L={has_lit} src_s={bs_id} s_len={bs_len}")
        log.append("")

    return tokens_por_string, "\n".join(log)

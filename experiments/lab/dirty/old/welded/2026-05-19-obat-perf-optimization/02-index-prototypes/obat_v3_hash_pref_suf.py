"""v3 — v2 + hash de sufixos.

Suffix index analogo: chave = `s[-3:]`, busca candidatos para lcs.

Mesma garantia: iteracao em ordem de id ascendente preserva
byte-canonical.
"""

from __future__ import annotations

from obat_v0_baseline import TokLit, TokRefPref, TokRefSuf
from obat_v1_len_elim import lcp_len_capped, lcs_len_capped
from obat_v2_hash_pref import _melhor_pref_v2


def _melhor_suf_v3(s, ls, strings, lens, suffix_index, max_len, min_len):
    if ls < 3 or max_len < 3:
        return 0, 0
    bucket = suffix_index.get(s[-3:])
    if not bucket:
        return 0, 0
    best_id, best_len = 0, 0
    for idx in bucket:
        L = lcs_len_capped(s, strings[idx], ls, lens[idx], max_len)
        if L >= min_len and L > best_len:
            best_len, best_id = L, idx + 1
    return best_id, best_len


def _escolher_par_v3(s, ls, strings, lens, prefix_index, suffix_index, min_len):
    bp_id, bp_len = _melhor_pref_v2(s, ls, strings, lens, prefix_index, ls, min_len)
    bs_id, bs_len = _melhor_suf_v3(s, ls, strings, lens, suffix_index, ls, min_len)

    if bp_len + bs_len <= ls:
        return bp_id, bp_len, bs_id, bs_len

    novo_suf_id, novo_suf_len = _melhor_suf_v3(
        s, ls, strings, lens, suffix_index, ls - bp_len, min_len
    )
    cand_a = (bp_id, bp_len, novo_suf_id, novo_suf_len)

    novo_pref_id, novo_pref_len = _melhor_pref_v2(
        s, ls, strings, lens, prefix_index, ls - bs_len, min_len
    )
    cand_b = (novo_pref_id, novo_pref_len, bs_id, bs_len)

    if cand_a[1] + cand_a[3] > cand_b[1] + cand_b[3]:
        return cand_a
    if cand_b[1] + cand_b[3] > cand_a[1] + cand_a[3]:
        return cand_b
    if cand_a[1] >= cand_b[1]:
        return cand_a
    return cand_b


def processar(strings_unicas, min_len=3):
    tokens_por_string = []
    lens = [len(s) for s in strings_unicas]
    prefix_index = {}
    suffix_index = {}

    for idx, s in enumerate(strings_unicas):
        ls = lens[idx]
        if idx == 0:
            tokens_por_string.append([TokLit(s)])
            if ls >= 3:
                prefix_index.setdefault(s[:3], []).append(idx)
                suffix_index.setdefault(s[-3:], []).append(idx)
            continue

        bp_id, bp_len, bs_id, bs_len = _escolher_par_v3(
            s, ls, strings_unicas, lens, prefix_index, suffix_index, min_len
        )

        tokens = []
        if bp_len > 0:
            tokens.append(TokRefPref(bp_id, bp_len))
        meio = s[bp_len: ls - bs_len]
        if meio:
            tokens.append(TokLit(meio))
        if bs_len > 0:
            tokens.append(TokRefSuf(bs_id, bs_len))

        tokens_por_string.append(tokens)

        if ls >= 3:
            prefix_index.setdefault(s[:3], []).append(idx)
            suffix_index.setdefault(s[-3:], []).append(idx)

    return tokens_por_string, ""

"""v1 — len-elim + slice-elim.

Otimizacoes IDIOMATICAS (zero mudanca algoritmica):
1. Pre-computa comprimentos das strings em lista `lens`
2. Passa `(strings, idx_limit)` em vez de slicar `strings[:idx]`
3. `lcp_len`/`lcs_len` recebem `la`/`lb` ja' calculados
4. Substitui `min(max_len, lcp_len(...))` por cap interno

Garantia byte-canonical: mesma sequencia de comparacoes, mesma escolha
de tie-break (i+1 ordem ascendente). Empate sempre resolvido a favor
de menor id.
"""

from __future__ import annotations

from obat_v0_baseline import TokLit, TokRefPref, TokRefSuf


def lcp_len_capped(a, b, la, lb, cap):
    n = la if la < lb else lb
    if cap < n:
        n = cap
    i = 0
    while i < n and a[i] == b[i]:
        i += 1
    return i


def lcs_len_capped(a, b, la, lb, cap):
    n = la if la < lb else lb
    if cap < n:
        n = cap
    i = 0
    a_back = la - 1
    b_back = lb - 1
    while i < n and a[a_back - i] == b[b_back - i]:
        i += 1
    return i


def _melhor_pref_v1(s, ls, strings, lens, idx_limit, max_len, min_len):
    best_id, best_len = 0, 0
    for i in range(idx_limit):
        L = lcp_len_capped(s, strings[i], ls, lens[i], max_len)
        if L >= min_len and L > best_len:
            best_len, best_id = L, i + 1
    return best_id, best_len


def _melhor_suf_v1(s, ls, strings, lens, idx_limit, max_len, min_len):
    best_id, best_len = 0, 0
    for i in range(idx_limit):
        L = lcs_len_capped(s, strings[i], ls, lens[i], max_len)
        if L >= min_len and L > best_len:
            best_len, best_id = L, i + 1
    return best_id, best_len


def _escolher_par_v1(s, ls, strings, lens, idx_limit, min_len):
    bp_id, bp_len = _melhor_pref_v1(s, ls, strings, lens, idx_limit, ls, min_len)
    bs_id, bs_len = _melhor_suf_v1(s, ls, strings, lens, idx_limit, ls, min_len)

    if bp_len + bs_len <= ls:
        return bp_id, bp_len, bs_id, bs_len

    novo_suf_id, novo_suf_len = _melhor_suf_v1(
        s, ls, strings, lens, idx_limit, ls - bp_len, min_len
    )
    cand_a = (bp_id, bp_len, novo_suf_id, novo_suf_len)

    novo_pref_id, novo_pref_len = _melhor_pref_v1(
        s, ls, strings, lens, idx_limit, ls - bs_len, min_len
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

    for idx, s in enumerate(strings_unicas):
        if idx == 0:
            tokens_por_string.append([TokLit(s)])
            continue

        ls = lens[idx]
        bp_id, bp_len, bs_id, bs_len = _escolher_par_v1(
            s, ls, strings_unicas, lens, idx, min_len
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

    return tokens_por_string, ""

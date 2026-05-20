"""v0 — Copia EXATA de src/tcf/core/online.py (referencia canonical).

Reproduzido aqui pra isolamento: testes nao tocam src/tcf.
Qualquer mudanca em src/tcf precisa atualizar este arquivo manualmente.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class TokLit:
    text: str

    def __repr__(self) -> str:
        return f'L({self.text!r})'


@dataclass
class TokRefPref:
    string_id: int
    length: int

    def __repr__(self) -> str:
        return f'P({self.string_id},{self.length})'


@dataclass
class TokRefSuf:
    string_id: int
    length: int

    def __repr__(self) -> str:
        return f'S({self.string_id},{self.length})'


Token = TokLit | TokRefPref | TokRefSuf


def lcp_len(a: str, b: str) -> int:
    n = min(len(a), len(b))
    i = 0
    while i < n and a[i] == b[i]:
        i += 1
    return i


def lcs_len(a: str, b: str) -> int:
    n = min(len(a), len(b))
    i = 0
    while i < n and a[len(a) - 1 - i] == b[len(b) - 1 - i]:
        i += 1
    return i


def _melhor_pref(s, anteriores, max_len, min_len):
    best_id, best_len = 0, 0
    for i, prev in enumerate(anteriores):
        L = min(max_len, lcp_len(s, prev))
        if L >= min_len and L > best_len:
            best_len, best_id = L, i + 1
    return best_id, best_len


def _melhor_suf(s, anteriores, max_len, min_len):
    best_id, best_len = 0, 0
    for i, prev in enumerate(anteriores):
        L = min(max_len, lcs_len(s, prev))
        if L >= min_len and L > best_len:
            best_len, best_id = L, i + 1
    return best_id, best_len


def _escolher_par(s, anteriores, min_len):
    n = len(s)
    bp_id, bp_len = _melhor_pref(s, anteriores, n, min_len)
    bs_id, bs_len = _melhor_suf(s, anteriores, n, min_len)

    if bp_len + bs_len <= n:
        return bp_id, bp_len, bs_id, bs_len

    novo_suf_id, novo_suf_len = _melhor_suf(s, anteriores, n - bp_len, min_len)
    cand_a = (bp_id, bp_len, novo_suf_id, novo_suf_len)

    novo_pref_id, novo_pref_len = _melhor_pref(s, anteriores, n - bs_len, min_len)
    cand_b = (novo_pref_id, novo_pref_len, bs_id, bs_len)

    return max([cand_a, cand_b], key=lambda c: (c[1] + c[3], c[1]))


def processar(strings_unicas, min_len=3):
    log = [f"min_len = {min_len}", ""]
    tokens_por_string = []

    for idx, s in enumerate(strings_unicas):
        log.append(f"--- string {idx + 1}: {s!r} (len={len(s)}) ---")

        if idx == 0:
            tokens_por_string.append([TokLit(s)])
            log.append("  primeira string -> literal puro")
            log.append("")
            continue

        anteriores = strings_unicas[:idx]
        bp_id, bp_len, bs_id, bs_len = _escolher_par(s, anteriores, min_len)

        log.append(f"  pref: len={bp_len} de string {bp_id}")
        log.append(f"  suf:  len={bs_len} de string {bs_id}")

        tokens = []
        if bp_len > 0:
            tokens.append(TokRefPref(bp_id, bp_len))
        meio = s[bp_len: len(s) - bs_len]
        if meio:
            tokens.append(TokLit(meio))
        if bs_len > 0:
            tokens.append(TokRefSuf(bs_id, bs_len))

        tokens_por_string.append(tokens)
        log.append("")

    return tokens_por_string, "\n".join(log)

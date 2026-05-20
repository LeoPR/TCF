"""OBAT — Online Bidirectional Affix Tokenizer.

Camada 1 do TCF. Tokeniza strings via LCP + LCS contra anteriores
preservando byte-canonical.

Otimizacao 2026-05-19 (ADR-0009): hash de trigramas para reduzir
busca em `_melhor_pref` / `_melhor_suf` de O(N) anteriores para
O(B) bucket size.
- `prefix_index[s[:3]] → list[zero-indexed ids]`
- `suffix_index[s[-3:]] → list[zero-indexed ids]`
- Trigrama k=3 escolhido por igualar `min_len=3` (qualquer match
  valido implica s[:3] == prev[:3]).
- Bucket ordem = ordem de insercao = id ascendente. Iteracao
  preserva tie-break `>` strict (primeira ocorrencia ganha).
- Empirico: 5.4x speedup em lineitem 5k (sub-exp 02), bytes
  IDENTICOS em D1-D9 (1615B) + lineitem 1k/5k.

API publica preservada:
- `lcp_len(a, b)`, `lcs_len(a, b)` (usadas por auto_pre, obat_shape)
- `processar(strings_unicas, min_len=3)` retorna (tokens, log)
- `reconstroi(tokens, strings_unicas)`
- Dataclasses `TokLit`, `TokRefPref`, `TokRefSuf`, alias `Token`

Origem: refatoracao limpa do exp 15 (M0).
"""

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


def _lcp_len_capped(a, b, la, lb, cap):
    n = la if la < lb else lb
    if cap < n:
        n = cap
    i = 0
    while i < n and a[i] == b[i]:
        i += 1
    return i


def _lcs_len_capped(a, b, la, lb, cap):
    n = la if la < lb else lb
    if cap < n:
        n = cap
    i = 0
    a_back = la - 1
    b_back = lb - 1
    while i < n and a[a_back - i] == b[b_back - i]:
        i += 1
    return i


def _melhor_pref(s, ls, strings, lens, prefix_index, max_len, min_len):
    """Hash-indexed: busca so' candidatos com mesmo trigrama inicial.
    Bucket ordenado por ordem de insercao = id ascendente, preserva
    tie-break.
    """
    if ls < min_len or max_len < min_len:
        return 0, 0
    bucket = prefix_index.get(s[:3])
    if not bucket:
        return 0, 0
    best_id, best_len = 0, 0
    for idx in bucket:
        L = _lcp_len_capped(s, strings[idx], ls, lens[idx], max_len)
        if L >= min_len and L > best_len:
            best_len, best_id = L, idx + 1
    return best_id, best_len


def _melhor_suf(s, ls, strings, lens, suffix_index, max_len, min_len):
    if ls < min_len or max_len < min_len:
        return 0, 0
    bucket = suffix_index.get(s[-3:])
    if not bucket:
        return 0, 0
    best_id, best_len = 0, 0
    for idx in bucket:
        L = _lcs_len_capped(s, strings[idx], ls, lens[idx], max_len)
        if L >= min_len and L > best_len:
            best_len, best_id = L, idx + 1
    return best_id, best_len


def _escolher_par(s, ls, strings, lens, prefix_index, suffix_index, min_len):
    """Escolhe (pref_id, pref_len, suf_id, suf_len) maximizando
    cobertura sem overlap.

    Caminho rapido: melhor pref + melhor suf, se couberem sem overlap.
    Caso contrario: 2 candidatos.

    Tie -> mais pref (preservado de v0).
    """
    bp_id, bp_len = _melhor_pref(s, ls, strings, lens, prefix_index, ls, min_len)
    bs_id, bs_len = _melhor_suf(s, ls, strings, lens, suffix_index, ls, min_len)

    if bp_len + bs_len <= ls:
        return bp_id, bp_len, bs_id, bs_len

    # Overlap. Gera 2 candidatos.
    novo_suf_id, novo_suf_len = _melhor_suf(
        s, ls, strings, lens, suffix_index, ls - bp_len, min_len
    )
    cand_a = (bp_id, bp_len, novo_suf_id, novo_suf_len)

    novo_pref_id, novo_pref_len = _melhor_pref(
        s, ls, strings, lens, prefix_index, ls - bs_len, min_len
    )
    cand_b = (novo_pref_id, novo_pref_len, bs_id, bs_len)

    # Tie-break: maior cobertura; depois maior pref. Identico a v0.
    if cand_a[1] + cand_a[3] > cand_b[1] + cand_b[3]:
        return cand_a
    if cand_b[1] + cand_b[3] > cand_a[1] + cand_a[3]:
        return cand_b
    if cand_a[1] >= cand_b[1]:
        return cand_a
    return cand_b


def reconstroi(tokens: list[Token], strings_unicas: list[str]) -> str:
    """Reconstroi string a partir dos tokens. Usado para validacao
    de roundtrip dentro de processar()."""
    parts: list[str] = []
    for tok in tokens:
        if isinstance(tok, TokLit):
            parts.append(tok.text)
        elif isinstance(tok, TokRefPref):
            parts.append(strings_unicas[tok.string_id - 1][:tok.length])
        else:  # TokRefSuf
            parts.append(strings_unicas[tok.string_id - 1][-tok.length:])
    return "".join(parts)


def processar(strings_unicas: list[str], min_len: int = 3
              ) -> tuple[list[list[Token]], str]:
    log: list[str] = [f"min_len = {min_len}", ""]
    tokens_por_string: list[list[Token]] = []
    lens = [len(s) for s in strings_unicas]
    prefix_index: dict[str, list[int]] = {}
    suffix_index: dict[str, list[int]] = {}

    for idx, s in enumerate(strings_unicas):
        ls = lens[idx]
        log.append(f"--- string {idx + 1}: {s!r} (len={ls}) ---")

        if idx == 0:
            tokens_por_string.append([TokLit(s)])
            log.append("  primeira string -> literal puro")
            log.append("")
            if ls >= min_len:
                prefix_index.setdefault(s[:3], []).append(idx)
                suffix_index.setdefault(s[-3:], []).append(idx)
            continue

        bp_id, bp_len, bs_id, bs_len = _escolher_par(
            s, ls, strings_unicas, lens, prefix_index, suffix_index, min_len
        )

        log.append(f"  pref: len={bp_len} de string {bp_id}")
        log.append(f"  suf:  len={bs_len} de string {bs_id}")
        log.append(f"  cobertura: {bp_len + bs_len} de {ls}")

        tokens: list[Token] = []
        if bp_len > 0:
            tokens.append(TokRefPref(bp_id, bp_len))
        meio = s[bp_len: ls - bs_len]
        if meio:
            tokens.append(TokLit(meio))
        if bs_len > 0:
            tokens.append(TokRefSuf(bs_id, bs_len))

        tokens_por_string.append(tokens)
        log.append(f"  tokens: [{' + '.join(repr(t) for t in tokens)}]")
        log.append("")

        if ls >= min_len:
            prefix_index.setdefault(s[:3], []).append(idx)
            suffix_index.setdefault(s[-3:], []).append(idx)

    return tokens_por_string, "\n".join(log)

"""Online sem revisao — v2 com fix dos defeitos do exp 14.

Mudancas vs exp 14:
1. Quando ha overlap entre best_pref e best_suf, ao inves de
   descartar o menor, busca a melhor combinacao (pref_i, suf_j)
   que caiba SEM overlap.
2. Para isso, considera sufixos MENORES que o LCS maximo (e
   prefixos menores que o LCP maximo).

Algoritmo Patricia/Re-Pair nao usado aqui; segue 100% online.
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


def maior_pref_ate(s: str, prev_s: str, max_len: int, min_len: int) -> int:
    """Maior prefixo de s que e tambem prefixo de prev_s, com
    `min_len <= L <= max_len`. Retorna 0 se nao houver.
    """
    L = min(max_len, lcp_len(s, prev_s))
    return L if L >= min_len else 0


def maior_suf_ate(s: str, prev_s: str, max_len: int, min_len: int) -> int:
    L = min(max_len, lcs_len(s, prev_s))
    return L if L >= min_len else 0


def reconstroi(tokens: list[Token], strings_originais: list[str]) -> str:
    parts: list[str] = []
    for tok in tokens:
        if isinstance(tok, TokLit):
            parts.append(tok.text)
        elif isinstance(tok, TokRefPref):
            s = strings_originais[tok.string_id - 1]
            parts.append(s[:tok.length])
        elif isinstance(tok, TokRefSuf):
            s = strings_originais[tok.string_id - 1]
            parts.append(s[-tok.length:] if tok.length > 0 else "")
    return "".join(parts)


def _escolher_par(s: str, strings_anteriores: list[str],
                   min_len: int) -> tuple[int, int, int, int]:
    """Escolhe (pref_id, pref_len, suf_id, suf_len) maximizando
    cobertura (pref_len + suf_len) sem overlap.

    Estrategia:
      1. Calcula best_pref_max e best_suf_max (LCP/LCS sobre todas
         as anteriores)
      2. Se cabe sem overlap: usa direto
      3. Se overlap: gera 3 candidatos:
           (a) best_pref, melhor_suf <= (len(s)-best_pref)
           (b) melhor_pref <= (len(s)-best_suf), best_suf
           (c) best_pref, 0
           (d) 0, best_suf
         Escolhe maior cobertura. Tie -> mais pref.
    """
    n = len(s)

    # LCP/LCS maximo entre todas
    bp_id, bp_len = 0, 0
    bs_id, bs_len = 0, 0
    for i, prev in enumerate(strings_anteriores):
        lp = lcp_len(s, prev)
        if lp >= min_len and lp > bp_len:
            bp_len, bp_id = lp, i + 1
        ls = lcs_len(s, prev)
        if ls >= min_len and ls > bs_len:
            bs_len, bs_id = ls, i + 1

    if bp_len + bs_len <= n:
        return bp_id, bp_len, bs_id, bs_len

    # Overlap. Gera candidatos.
    candidatos: list[tuple[int, int, int, int]] = []

    # (a) mantem pref, reduz suf ao maior que caiba
    espaco_suf = n - bp_len
    if espaco_suf >= min_len:
        novo_suf_id, novo_suf_len = 0, 0
        for i, prev in enumerate(strings_anteriores):
            L = maior_suf_ate(s, prev, espaco_suf, min_len)
            if L > novo_suf_len:
                novo_suf_len, novo_suf_id = L, i + 1
        candidatos.append((bp_id, bp_len, novo_suf_id, novo_suf_len))
    else:
        candidatos.append((bp_id, bp_len, 0, 0))

    # (b) mantem suf, reduz pref
    espaco_pref = n - bs_len
    if espaco_pref >= min_len:
        novo_pref_id, novo_pref_len = 0, 0
        for i, prev in enumerate(strings_anteriores):
            L = maior_pref_ate(s, prev, espaco_pref, min_len)
            if L > novo_pref_len:
                novo_pref_len, novo_pref_id = L, i + 1
        candidatos.append((novo_pref_id, novo_pref_len, bs_id, bs_len))
    else:
        candidatos.append((0, 0, bs_id, bs_len))

    # (c) so pref
    candidatos.append((bp_id, bp_len, 0, 0))
    # (d) so suf
    candidatos.append((0, 0, bs_id, bs_len))

    # Escolhe maior cobertura, tie por maior pref
    candidatos.sort(key=lambda c: (-(c[1] + c[3]), -c[1]))
    return candidatos[0]


def processar(strings_unicas: list[str], min_len: int = 3
              ) -> tuple[list[list[Token]], str]:
    log: list[str] = []
    log.append(f"min_len = {min_len}")
    log.append("")
    tokens_por_string: list[list[Token]] = []

    for idx, s in enumerate(strings_unicas):
        log.append(f"--- string {idx + 1}: {s!r} (len={len(s)}) ---")
        if not tokens_por_string:
            tokens_por_string.append([TokLit(s)])
            log.append(f"  primeira string -> literal puro")
            log.append("")
            continue

        anteriores = strings_unicas[:idx]
        bp_id, bp_len, bs_id, bs_len = _escolher_par(s, anteriores, min_len)

        log.append(f"  pref: len={bp_len} de string {bp_id}")
        log.append(f"  suf:  len={bs_len} de string {bs_id}")
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
        log.append("")

    return tokens_por_string, "\n".join(log)

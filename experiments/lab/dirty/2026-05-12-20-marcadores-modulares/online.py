"""Online sem revisao — refatoracao limpa do exp 15.

Mudancas vs exp 15 (apenas estruturais, nao algoritmicas):
1. `_escolher_par` reduz 4 candidatos para 2 — (c) e (d) eram
   dominados por (a) e (b) respectivamente.
2. `reconstroi` sem guard `length>0` protetivo (algoritmo nunca
   emite ref com length=0).
3. Renomeacoes para consistencia.

Comportamento esperado: TCFs byte-identicos aos do exp 15.
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


def _melhor_pref(s: str, anteriores: list[str], max_len: int,
                  min_len: int) -> tuple[int, int]:
    """Retorna (id, length) do maior prefixo de s coincidente com
    alguma anterior, limitado por max_len e >= min_len.
    (0, 0) se nenhum vale.
    """
    best_id, best_len = 0, 0
    for i, prev in enumerate(anteriores):
        L = min(max_len, lcp_len(s, prev))
        if L >= min_len and L > best_len:
            best_len, best_id = L, i + 1
    return best_id, best_len


def _melhor_suf(s: str, anteriores: list[str], max_len: int,
                 min_len: int) -> tuple[int, int]:
    best_id, best_len = 0, 0
    for i, prev in enumerate(anteriores):
        L = min(max_len, lcs_len(s, prev))
        if L >= min_len and L > best_len:
            best_len, best_id = L, i + 1
    return best_id, best_len


def _escolher_par(s: str, anteriores: list[str],
                   min_len: int) -> tuple[int, int, int, int]:
    """Escolhe (pref_id, pref_len, suf_id, suf_len) maximizando
    cobertura sem overlap.

    Caminho rapido: melhor pref + melhor suf, se couberem sem
    overlap. Caso contrario: 2 candidatos.

    Candidatos em overlap:
      (a) manter pref maximo, buscar maior suf que caiba
      (b) manter suf maximo, buscar maior pref que caiba

    Escolhe maior cobertura. Tie -> mais pref.

    Nota: candidatos "so pref" e "so suf" sao dominados por (a) e
    (b) respectivamente, entao nao precisam ser avaliados
    separadamente.
    """
    n = len(s)
    bp_id, bp_len = _melhor_pref(s, anteriores, n, min_len)
    bs_id, bs_len = _melhor_suf(s, anteriores, n, min_len)

    if bp_len + bs_len <= n:
        return bp_id, bp_len, bs_id, bs_len

    # Overlap. Gera 2 candidatos.
    novo_suf_id, novo_suf_len = _melhor_suf(s, anteriores, n - bp_len, min_len)
    cand_a = (bp_id, bp_len, novo_suf_id, novo_suf_len)

    novo_pref_id, novo_pref_len = _melhor_pref(s, anteriores, n - bs_len, min_len)
    cand_b = (novo_pref_id, novo_pref_len, bs_id, bs_len)

    return max([cand_a, cand_b], key=lambda c: (c[1] + c[3], c[1]))


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

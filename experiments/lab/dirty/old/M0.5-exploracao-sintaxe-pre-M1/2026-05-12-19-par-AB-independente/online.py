"""Online sem revisao — par A+B independente (exp 19).

Mudanca vs exp 16:
- `_escolher_par` faz busca exaustiva sobre TODOS os pares
  (prev_a, prev_b) onde prev_a contribui o prefixo e prev_b o
  sufixo. Em exp 16, o algoritmo fixava uma das ancoras no maximo
  e procurava reducao na outra. Aqui ambas podem ter qualquer
  prev_id e qualquer tamanho >= min_len.

Custo: O(|prefs| * |sufs|) por string nova, onde |prefs| e
|sufs| sao o numero de anteriores com LCP/LCS >= min_len. Pior
caso O(N^2) por string, O(N^3) total. Em escala grande pode
ficar pesado — medir.

Comportamento esperado:
- Em datasets onde exp 16 ja atingia cobertura 100%, sem ganho.
- Em datasets com introducoes residuais (urls do exp 17, ips do
  exp 18), pode reduzir literais.
- TCFs podem diferir do exp 16: a escolha de (pref_id, suf_id) e
  diferente quando ha empate de cobertura mas IDs distintos.
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


def _coletar_disponiveis(s: str, anteriores: list[str],
                          min_len: int) -> tuple[list[tuple[int, int]],
                                                  list[tuple[int, int]]]:
    """Retorna (prefs, sufs) onde:
      prefs[k] = (id_anterior, max_lcp) com max_lcp >= min_len
      sufs[k]  = (id_anterior, max_lcs) com max_lcs >= min_len
    """
    prefs: list[tuple[int, int]] = []
    sufs: list[tuple[int, int]] = []
    for i, prev in enumerate(anteriores):
        lp = lcp_len(s, prev)
        if lp >= min_len:
            prefs.append((i + 1, lp))
        ls = lcs_len(s, prev)
        if ls >= min_len:
            sufs.append((i + 1, ls))
    return prefs, sufs


def _escolher_par(s: str, anteriores: list[str],
                   min_len: int) -> tuple[int, int, int, int]:
    """Busca exaustiva sobre todos os pares (prev_a, prev_b) com
    LCP/LCS >= min_len. Para cada par, considera:
      - tamanho maximo sem overlap (se couber)
      - reducao em uma das ancoras (se overlap)
    Retorna o par com maior cobertura. Tie por maior pref.

    Tambem considera "so pref" e "so suf" como casos degenerados.
    """
    n = len(s)
    prefs, sufs = _coletar_disponiveis(s, anteriores, min_len)

    # Caso degenerado: sem candidatos
    if not prefs and not sufs:
        return 0, 0, 0, 0

    # Candidato base: nada
    best = (0, 0, 0, 0)
    best_cov = 0
    best_pref_len = 0

    # 1. So pref
    for pid, pmax in prefs:
        cov = pmax
        if cov > best_cov or (cov == best_cov and pmax > best_pref_len):
            best = (pid, pmax, 0, 0)
            best_cov = cov
            best_pref_len = pmax

    # 2. So suf
    for sid, smax in sufs:
        cov = smax
        if cov > best_cov or (cov == best_cov and 0 > best_pref_len):
            best = (0, 0, sid, smax)
            best_cov = cov
            best_pref_len = 0

    # 3. Par A+B (pref de prev_a, suf de prev_b, ambos independentes)
    for pid, pmax in prefs:
        for sid, smax in sufs:
            if pmax + smax <= n:
                # cabe sem overlap, usar ambos no maximo
                pref_len, suf_len = pmax, smax
                cov = pmax + smax
            else:
                # overlap. Opcao A: manter pmax, reduzir suf
                cov_a = -1
                pref_a, suf_a = 0, 0
                if pmax <= n - min_len:
                    suf_len_a = min(smax, n - pmax)
                    if suf_len_a >= min_len:
                        pref_a, suf_a = pmax, suf_len_a
                        cov_a = pmax + suf_len_a
                # Opcao B: manter smax, reduzir pref
                cov_b = -1
                pref_b, suf_b = 0, 0
                if smax <= n - min_len:
                    pref_len_b = min(pmax, n - smax)
                    if pref_len_b >= min_len:
                        pref_b, suf_b = pref_len_b, smax
                        cov_b = pref_len_b + smax
                # Escolher entre A e B (A prioriza pref maior em empate)
                if cov_a >= cov_b and cov_a > 0:
                    pref_len, suf_len, cov = pref_a, suf_a, cov_a
                elif cov_b > 0:
                    pref_len, suf_len, cov = pref_b, suf_b, cov_b
                else:
                    continue
            if cov > best_cov or (cov == best_cov and pref_len > best_pref_len):
                best = (pid, pref_len, sid, suf_len)
                best_cov = cov
                best_pref_len = pref_len

    return best


def reconstroi(tokens: list[Token], strings_unicas: list[str]) -> str:
    parts: list[str] = []
    for tok in tokens:
        if isinstance(tok, TokLit):
            parts.append(tok.text)
        elif isinstance(tok, TokRefPref):
            parts.append(strings_unicas[tok.string_id - 1][:tok.length])
        else:
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

"""Algoritmo online incremental SEM revisao retroativa.

Processa strings unicas uma por vez. Para cada nova string:
  1. Compara com TODAS as strings ja processadas (por reconstrucao)
  2. Identifica o maior prefixo comum e maior sufixo comum (LCP/LCS)
     entre a nova e cada anterior
  3. Escolhe melhor par (maior cobertura sem overlap) entre todas as
     anteriores
  4. Codifica como [ref_pref + literal_meio + ref_suf]
  5. NAO modifica nada da estrutura ja codificada (sem revisao)

Permite streaming: a cada string processada, seu encoding pode ser
emitido imediatamente. Em troca, pode perder oportunidades de
fatoracao que apareceriam se revisitasse anteriores.

Memoria cresce com N strings unicas (sem janela limitada — essa
limitacao fica para exp 16).
"""

from dataclasses import dataclass


@dataclass
class TokLit:
    """Texto literal."""
    text: str

    def __repr__(self) -> str:
        return f'L({self.text!r})'


@dataclass
class TokRefPref:
    """Primeiros `length` chars da string anterior `string_id`."""
    string_id: int  # 1-indexed (1 = primeira string)
    length: int

    def __repr__(self) -> str:
        return f'P({self.string_id},{self.length})'


@dataclass
class TokRefSuf:
    """Ultimos `length` chars da string anterior `string_id`."""
    string_id: int
    length: int

    def __repr__(self) -> str:
        return f'S({self.string_id},{self.length})'


Token = TokLit | TokRefPref | TokRefSuf


def lcp_len(a: str, b: str) -> int:
    """Longest common prefix length."""
    n = min(len(a), len(b))
    i = 0
    while i < n and a[i] == b[i]:
        i += 1
    return i


def lcs_len(a: str, b: str) -> int:
    """Longest common suffix length."""
    n = min(len(a), len(b))
    i = 0
    while i < n and a[len(a) - 1 - i] == b[len(b) - 1 - i]:
        i += 1
    return i


def reconstroi(tokens: list[Token], strings_originais: list[str]) -> str:
    """Reconstroi a string dado os tokens e a lista de strings ja
    processadas (em ordem). string_id 1-indexed.
    """
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


def processar(strings_unicas: list[str], min_len: int = 3
              ) -> tuple[list[list[Token]], str]:
    """Processa strings em ordem. Retorna (tokens_por_string, log).

    Para cada nova string, busca em TODAS as anteriores o melhor par
    (pref_anterior, suf_anterior) que maximiza cobertura sem overlap.
    Critério tie: maior len(pref).
    """
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

        # Busca melhor pref e suf entre todas as anteriores
        melhor_pref_id = 0
        melhor_pref_len = 0
        melhor_suf_id = 0
        melhor_suf_len = 0

        for prev_idx, prev_s in enumerate(strings_unicas[:idx]):
            lp = lcp_len(s, prev_s)
            if lp >= min_len and lp > melhor_pref_len:
                melhor_pref_len = lp
                melhor_pref_id = prev_idx + 1
            ls = lcs_len(s, prev_s)
            if ls >= min_len and ls > melhor_suf_len:
                melhor_suf_len = ls
                melhor_suf_id = prev_idx + 1

        log.append(f"  melhor pref: len={melhor_pref_len} "
                   f"de string {melhor_pref_id}")
        log.append(f"  melhor suf:  len={melhor_suf_len} "
                   f"de string {melhor_suf_id}")

        # Overlap check
        if melhor_pref_len + melhor_suf_len > len(s):
            log.append(f"  OVERLAP: {melhor_pref_len} + {melhor_suf_len} "
                       f"> {len(s)}")
            if melhor_pref_len >= melhor_suf_len:
                log.append(f"  resolve: descarta suf")
                melhor_suf_len = 0
            else:
                log.append(f"  resolve: descarta pref")
                melhor_pref_len = 0

        # Construir tokens
        tokens: list[Token] = []
        if melhor_pref_len > 0:
            tokens.append(TokRefPref(melhor_pref_id, melhor_pref_len))
        meio = s[melhor_pref_len: len(s) - melhor_suf_len]
        if meio:
            tokens.append(TokLit(meio))
        if melhor_suf_len > 0:
            tokens.append(TokRefSuf(melhor_suf_id, melhor_suf_len))

        tokens_por_string.append(tokens)
        log.append(f"  tokens: [{' + '.join(repr(t) for t in tokens)}]")
        log.append("")

    return tokens_por_string, "\n".join(log)

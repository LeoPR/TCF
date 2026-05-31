"""Constroi 2 arvores Patricia (forward + reverse) e decompoe cada
string unica em (prefix_text, middle, suffix_text).

Regras de decomposicao:
  - prefix_text vem do pai imediato da folha na arvore forward
    (texto completo do pai, reconstruido). Se folha eh top-level
    (sem pai), prefix_text = "".
  - suffix_text vem do pai imediato da folha na arvore reverse,
    DES-invertido. Se folha eh top-level, suffix_text = "".
  - Ambos devem ter pelo menos `min_prefixo` chars para valer.
  - Em caso de overlap (len(p) + len(x) > len(s)): heuristica
    best-fragment-first de Fraenkel-Mor-Perl (1983) — escolhe o
    mais longo; descarta o outro. Tie -> prefere prefix.
  - middle = s[len(prefix):len(s)-len(suffix)].
"""

from dataclasses import dataclass

from patricia import (
    No,
    aplicar_patricia,
    construir_inicial,
    texto_completo,
)


@dataclass
class Decomposicao:
    s: str
    prefix_text: str
    middle: str
    suffix_text: str

    def reconstroi(self) -> str:
        return self.prefix_text + self.middle + self.suffix_text


def _prefix_de(s: str, fwd_arvore: dict[int, No],
               fwd_str_to_eid: dict[str, int]) -> str:
    eid = fwd_str_to_eid[s]
    no = fwd_arvore[eid]
    if no.pai_id is None:
        return ""
    return texto_completo(no.pai_id, fwd_arvore)


def _suffix_de(s: str, rev_arvore: dict[int, No],
               rev_str_to_eid: dict[str, int]) -> str:
    s_inv = s[::-1]
    eid = rev_str_to_eid[s_inv]
    no = rev_arvore[eid]
    if no.pai_id is None:
        return ""
    sufixo_inv = texto_completo(no.pai_id, rev_arvore)
    return sufixo_inv[::-1]


def construir_bidir(linhas: list[str], min_prefixo: int = 3):
    """Constroi forward e reverse Patricia. Retorna estruturas para uso
    por decompor_strings.
    """
    fwd_arvore, _, fwd_str_to_eid = construir_inicial(linhas)
    fwd_arvore = aplicar_patricia(fwd_arvore, min_prefixo=min_prefixo)

    linhas_inv = [s[::-1] for s in linhas]
    rev_arvore, _, rev_str_to_eid = construir_inicial(linhas_inv)
    rev_arvore = aplicar_patricia(rev_arvore, min_prefixo=min_prefixo)

    return fwd_arvore, fwd_str_to_eid, rev_arvore, rev_str_to_eid


def decompor_strings(strings_unicas: list[str], fwd_arvore, fwd_str_to_eid,
                     rev_arvore, rev_str_to_eid,
                     min_prefixo: int = 3) -> dict[str, Decomposicao]:
    resultado: dict[str, Decomposicao] = {}
    for s in strings_unicas:
        p = _prefix_de(s, fwd_arvore, fwd_str_to_eid)
        x = _suffix_de(s, rev_arvore, rev_str_to_eid)

        if len(p) < min_prefixo:
            p = ""
        if len(x) < min_prefixo:
            x = ""

        # Overlap resolution
        if p and x and len(p) + len(x) > len(s):
            # best-fragment-first: mais longo vence; tie -> prefix
            if len(p) >= len(x):
                x = ""
            else:
                p = ""

        middle = s[len(p): len(s) - len(x)] if x else s[len(p):]
        resultado[s] = Decomposicao(s=s, prefix_text=p, middle=middle,
                                    suffix_text=x)
    return resultado


def rle_strings(linhas: list[str]) -> list[tuple[str, int]]:
    if not linhas:
        return []
    res: list[tuple[str, int]] = []
    atual = linhas[0]
    rep = 1
    for x in linhas[1:]:
        if x == atual:
            rep += 1
        else:
            res.append((atual, rep))
            atual = x
            rep = 1
    res.append((atual, rep))
    return res

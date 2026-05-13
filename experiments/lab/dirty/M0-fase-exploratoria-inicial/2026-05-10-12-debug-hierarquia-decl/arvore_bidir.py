"""Decomposicao com escolha de nivel na cadeia de pais (forward + reverse).

Mudanca vs exp 08:
  - exp 08: usa SO o pai imediato de cada folha
  - exp 10: percorre a cadeia inteira de ancestrais (pai, avo, bisavo, ...)
            e escolhe a combinacao (pref, suf) de maior cobertura sem overlap

Heuristica de escolha: maior `len(p) + len(x)` que satisfaz
`len(p) + len(x) <= len(s)`. Tie -> maior `len(p)` (arbitrario,
determinista, alinhado com "best fragment first" de Fraenkel-Mor-Perl
1983 adaptado para o nosso problema com overlap).

Sempre inclui "sem pref" e "sem suf" como opcoes — degrada para os
casos do exp 08 quando nao ha hierarquia profunda.

Construcao das arvores Patricia (forward + reverse) eh identica ao
exp 08 — esta mudanca afeta apenas a fase de decomposicao.
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


def _cadeia_ancestrais_textos(eid: int, arvore: dict[int, No]) -> list[str]:
    """Textos completos dos ancestrais da folha, do pai imediato
    (mais longo) ate a raiz top-level (mais curto). Lista vazia
    se a folha for top-level (sem pai).
    """
    no = arvore[eid]
    resultado: list[str] = []
    while no.pai_id is not None:
        resultado.append(texto_completo(no.pai_id, arvore))
        no = arvore[no.pai_id]
    return resultado


def construir_bidir(linhas: list[str], min_prefixo: int = 3):
    fwd_arvore, _, fwd_str_to_eid = construir_inicial(linhas)
    fwd_arvore = aplicar_patricia(fwd_arvore, min_prefixo=min_prefixo)

    linhas_inv = [s[::-1] for s in linhas]
    rev_arvore, _, rev_str_to_eid = construir_inicial(linhas_inv)
    rev_arvore = aplicar_patricia(rev_arvore, min_prefixo=min_prefixo)

    return fwd_arvore, fwd_str_to_eid, rev_arvore, rev_str_to_eid


def decompor_strings(strings_unicas: list[str],
                     fwd_arvore, fwd_str_to_eid,
                     rev_arvore, rev_str_to_eid,
                     min_prefixo: int = 3) -> dict[str, Decomposicao]:
    resultado: dict[str, Decomposicao] = {}
    for s in strings_unicas:
        # Candidatos pref: pai, avo, bisavo, ... + opcao vazia
        eid_fwd = fwd_str_to_eid[s]
        pref_cands = [t for t in _cadeia_ancestrais_textos(eid_fwd, fwd_arvore)
                      if len(t) >= min_prefixo]
        pref_cands.append("")

        # Candidatos suf: idem na arvore reverse, des-invertendo
        s_inv = s[::-1]
        eid_rev = rev_str_to_eid[s_inv]
        suf_cands_inv = _cadeia_ancestrais_textos(eid_rev, rev_arvore)
        suf_cands = [ti[::-1] for ti in suf_cands_inv]
        suf_cands = [t for t in suf_cands if len(t) >= min_prefixo]
        suf_cands.append("")

        # Busca melhor combinacao
        melhor_p = ""
        melhor_x = ""
        melhor_cob = 0
        melhor_lp = -1
        for p in pref_cands:
            lp = len(p)
            for x in suf_cands:
                lx = len(x)
                if lp + lx > len(s):
                    continue
                if p and not s.startswith(p):
                    continue
                if x and not s.endswith(x):
                    continue
                cob = lp + lx
                # tie-break: maior lp
                if cob > melhor_cob or (cob == melhor_cob and lp > melhor_lp):
                    melhor_p = p
                    melhor_x = x
                    melhor_cob = cob
                    melhor_lp = lp

        middle = (s[len(melhor_p): len(s) - len(melhor_x)]
                  if melhor_x else s[len(melhor_p):])
        resultado[s] = Decomposicao(s=s, prefix_text=melhor_p,
                                    middle=middle, suffix_text=melhor_x)
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

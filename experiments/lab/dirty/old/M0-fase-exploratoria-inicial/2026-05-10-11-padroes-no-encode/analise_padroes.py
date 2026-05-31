"""Analise simbolica de padroes repetidos no encode composto.

Sem fatorar. Apenas conta e estima ganho potencial.

Tipos de padrao analisados:
  1. par (mid_text, suf_text): "X" + suf:noN aparece em multiplas linhas
  2. par (pref_text, mid_text): pref:noP + "X" aparece em multiplas linhas
  3. (futuro) par (suf_text, mid_text) — relevante so se ordem invertida

Para cada padrao com count >= 2, estima:
  - economia por ocorrencia (substituir "X" + suf:noN por refs:noQ)
  - custo de decl extra (noQ: ...)
  - ganho liquido = C * economia - custo_decl

Custos baseados na sintaxe atual do exp 10:
  - ' + "X" + suf:noN\n' = 3 + 1 + len(X) + 1 + 3 + 7 + len(eid_str) chars
  - ' + noQ\n' = 3 + 4 + len(eid_str_novo) chars
  - decl extra '  noQ: "X" + suf:noN\n' = 2 + 4 + 2 + 1 + len(X) + 1 + 3 + 7 + len(eid_str) chars
"""

from collections import Counter
from dataclasses import dataclass

from arvore_bidir import Decomposicao


@dataclass
class Padrao:
    tipo: str           # 'mid_suf' ou 'pref_mid'
    par: tuple          # (mid_text, suf_text) ou (pref_text, mid_text)
    count: int          # quantas strings unicas exibem o padrao
    economia_por_oc: int
    custo_decl: int
    ganho_liquido: int

    def __lt__(self, other):
        return self.ganho_liquido > other.ganho_liquido  # ordem desc


def _len_id(n: int) -> int:
    return len(str(n))


def coletar_padroes_mid_suf(decomps: dict[str, Decomposicao],
                            eids_suf: dict[str, int]) -> list[Padrao]:
    """eids_suf: mapa de suf_text -> eid (do encoder do exp 10)."""
    contagens: Counter = Counter()
    for d in decomps.values():
        if d.middle and d.suffix_text:
            contagens[(d.middle, d.suffix_text)] += 1

    padroes = []
    for (mid, suf), c in contagens.items():
        if c < 2:
            continue
        eid_suf = eids_suf[suf]
        # custo atual por ocorrencia: ' + "{mid}" + suf:no{eid}'
        custo_atual = 3 + 1 + len(mid) + 1 + 3 + 3 + 3 + _len_id(eid_suf)
        # custo apos fatorar: ' + no{new_eid}' (assumindo eid_novo de 1-2 chars)
        custo_novo = 3 + 2 + 1  # ' + noN' aprox 6 chars (N pode crescer)
        economia = custo_atual - custo_novo
        # custo da decl extra: '  noN: "{mid}" + suf:no{eid}'
        custo_decl = 2 + 2 + 1 + 2 + 1 + len(mid) + 1 + 3 + 3 + 3 + _len_id(eid_suf)
        ganho = c * economia - custo_decl
        padroes.append(Padrao(
            tipo='mid_suf',
            par=(mid, suf),
            count=c,
            economia_por_oc=economia,
            custo_decl=custo_decl,
            ganho_liquido=ganho,
        ))
    padroes.sort()
    return padroes


def coletar_padroes_pref_mid(decomps: dict[str, Decomposicao],
                             eids_pref: dict[str, int]) -> list[Padrao]:
    contagens: Counter = Counter()
    for d in decomps.values():
        if d.prefix_text and d.middle:
            contagens[(d.prefix_text, d.middle)] += 1

    padroes = []
    for (pref, mid), c in contagens.items():
        if c < 2:
            continue
        eid_pref = eids_pref[pref]
        # custo atual por ocorrencia: 'pref:no{eid} + "{mid}"'
        custo_atual = 5 + 2 + _len_id(eid_pref) + 3 + 1 + len(mid) + 1
        # custo apos fatorar: 'no{new_eid}'
        custo_novo = 2 + 1
        economia = custo_atual - custo_novo
        custo_decl = 2 + 2 + 1 + 2 + 5 + 2 + _len_id(eid_pref) + 3 + 1 + len(mid) + 1
        ganho = c * economia - custo_decl
        padroes.append(Padrao(
            tipo='pref_mid',
            par=(pref, mid),
            count=c,
            economia_por_oc=economia,
            custo_decl=custo_decl,
            ganho_liquido=ganho,
        ))
    padroes.sort()
    return padroes


def _alocar_eids(decomps: dict[str, Decomposicao]) -> tuple[dict[str, int], dict[str, int]]:
    """Simula a alocacao de eids do encoder do exp 10 para pref e suf
    textos (em ordem de aparicao das strings).
    """
    eid = 1
    eids_pref: dict[str, int] = {}
    eids_suf: dict[str, int] = {}
    eids_str: dict[str, int] = {}
    for s, d in decomps.items():
        # ordem: str primeiro, depois pref novo, depois suf novo
        # mas seguindo a logica do encoder real, str_eid eh alocado primeiro
        # quando o noN: ... eh emitido. Pref/suf vem dentro da decl externa.
        if s not in eids_str:
            eids_str[s] = eid
            eid += 1
        if d.prefix_text and d.prefix_text not in eids_pref:
            eids_pref[d.prefix_text] = eid
            eid += 1
        if d.suffix_text and d.suffix_text not in eids_suf:
            eids_suf[d.suffix_text] = eid
            eid += 1
    return eids_pref, eids_suf

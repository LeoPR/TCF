"""cardlib — engenhoca: DEDUZIR a cardinalidade (1x1 / 1xN / Nx1 / NxN) entre duas colunas a partir dos
DADOS, e mapear pra mecânica do TCF. É normalização de banco (dependência funcional) aplicada ao formato.

Teste por contagem de distintos (clássico de descoberta de FD):
  nA=|distintos A|, nB=|distintos B|, nAB=|pares distintos (A,B)|
  A→B (A determina B)  sse  nAB == nA        (cada A mapeia p/ 1 B)
  B→A                  sse  nAB == nB
  ambos → 1:1 (bijeção) · só B→A → A:B = 1:N (A repete, é pai) · só A→B → A:B = N:1 (B repete, é dict)
  nenhum → N:N (precisa de tabela-ponte)

Ideia-chave (owner): numa 1:N a coluna-pai REPETE se ficar plana (viraria RLE '*N|'); declarar 1:N no
header deixa o pai virar 'elemento' 1x + ligado à coluna N (dual RLE↔referência = a peça 1).
"""
from __future__ import annotations


def classify(a: list, b: list):
    nA, nB = len(set(a)), len(set(b))
    nAB = len(set(zip(a, b)))
    R = len(a)
    a_det_b = (nAB == nA)          # A→B
    b_det_a = (nAB == nB)          # B→A
    if a_det_b and b_det_a:
        card, lado = "1:1", "bijeção — nada a fatorar (TCF nativo)"
    elif b_det_a and not a_det_b:
        card, lado = "1:N", "A é o '1' (repete, é PAI); B é o 'N'"
    elif a_det_b and not b_det_a:
        card, lado = "N:1", "B é o '1' (repete, é DICIONÁRIO/categoria); A é o 'N'"
    else:
        card, lado = "N:N", "nenhuma FD — precisa de tabela-ponte"
    return {"nA": nA, "nB": nB, "nAB": nAB, "R": R, "A->B": a_det_b, "B->A": b_det_a,
            "card": card, "leitura": lado}


def factor_1n(a: list, b: list):
    """Fatora uma 1:N (A=pai que repete → B=filho). Devolve (pais_distintos, {pai:[filhos]})."""
    groups = {}
    for pa, pb in zip(a, b):
        groups.setdefault(pa, []).append(pb)
    return list(groups), groups


def dict_n1(a: list, b: list):
    """Nx1: B é dicionário low-card. Devolve (valores_distintos_B, indice_por_linha)."""
    vals = list(dict.fromkeys(b))
    idx = {v: i for i, v in enumerate(vals)}
    return vals, [idx[x] for x in b]


def bridge_nn(a: list, b: list):
    """NxN: dicionários de A e B + a lista de pares (a tabela-ponte)."""
    va = list(dict.fromkeys(a)); vb = list(dict.fromkeys(b))
    ia = {v: i for i, v in enumerate(va)}; ib = {v: i for i, v in enumerate(vb)}
    pairs = [(ia[x], ib[y]) for x, y in zip(a, b)]
    return va, vb, pairs


def byte_intuition(a: list, b: list, card: str):
    """Intuição de bytes: plano (repete) vs normalizado (guarda 1x). Só contagem de caracteres."""
    flat_A = sum(len(str(x)) for x in a)                 # A repetido por linha (plano)
    distinct_A = sum(len(str(x)) for x in set(a))        # A guardado 1x (normalizado)
    return {"A_plano_chars": flat_A, "A_1x_chars": distinct_A,
            "economia_A_chars": flat_A - distinct_A,
            "nota": "economia real depende do link/estrutura; aqui é só o texto de A repetido vs 1x"}

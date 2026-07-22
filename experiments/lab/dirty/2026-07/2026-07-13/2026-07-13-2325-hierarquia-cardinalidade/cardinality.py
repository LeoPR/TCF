"""Classificador de cardinalidade (recupera a peça 7 / teoria-cardinalidade.md).

Teste de contagem de distintos = descoberta de FD (o primitivo do TANE):
  dA=|A|, dB=|B|, dAB=|pares (A,B)|.  A→B sse dAB==dA ; B→A sse dAB==dB.

Mapa cardinalidade -> mecânica TCF -> realização na hierarquia:
  1:1  (ambas FDs)        -> nativo/retangular        -> `{}` objeto aninhado (ANINHA)
  1:N  (só B→A, A repete) -> hierarquia (dual do RLE) -> `[]` array           (ANINHA)
  N:1  (só A→B, B repete) -> @dict low-card           -> coluna compartilhada  (NÃO é ramo)
  N:N  (nenhuma FD)       -> tabela-ponte (junction)  -> NÃO vira árvore simples

Refinamentos da teoria:
  - CHAVE (d=n) != GRUPO-COARSE (d<<n): 1:1 de duas chaves (cpf-nome) é dict bijetivo,
    não hierarquia; distinguir antes de propor fatorar.
  - cardinalidade ⊥ compressibilidade: multiplicidade (RLE↔fk, conservada) é separada
    de largura-de-valor (dict, encolhe). O ganho de bytes do N:1 é a LARGURA (valor
    largo repetido -> código estreito), não a multiplicidade.
"""
from __future__ import annotations


def classify(a: list, b: list) -> str:
    dA, dB, dAB = len(set(a)), len(set(b)), len(set(zip(a, b)))
    if dAB == dA and dAB == dB:
        return "1:1"
    if dAB == dA:            # A→B (cada A tem 1 B) -> B repete -> N:1 (A é o "muitos")
        return "N:1"
    if dAB == dB:            # B→A (cada B tem 1 A) -> A repete -> 1:N (A é o pai)
        return "1:N"
    return "N:N"


MECANICA = {
    "1:1": ("nativo / dict bijetivo", "`{}` objeto aninhado", "ANINHA"),
    "1:N": ("hierarquia = dual do RLE `*N|pai`", "`[]` array", "ANINHA"),
    "N:1": ("@dict low-card (o TCF já emite)", "coluna compartilhada", "não é ramo"),
    "N:N": ("tabela-ponte (2 dicts + pares)", "—", "NÃO aninha (ponte)"),
}


def is_key(col: list) -> bool:
    """d==n: chave/UCC -> FD trivial SEM repetição = zero ganho de normalização."""
    return len(set(col)) == len(col)


def describe(a_name: str, a: list, b_name: str, b: list) -> dict:
    cls = classify(a, b)
    mec, hier, nest = MECANICA[cls]
    return {
        "par": f"{a_name}–{b_name}",
        "dA": len(set(a)), "dB": len(set(b)), "dAB": len(set(zip(a, b))),
        "classe": cls,
        "chaves": f"{a_name}={'chave' if is_key(a) else 'grupo'}, "
                  f"{b_name}={'chave' if is_key(b) else 'grupo'}",
        "mecanica_tcf": mec,
        "na_hierarquia": hier,
        "aninha": nest,
    }

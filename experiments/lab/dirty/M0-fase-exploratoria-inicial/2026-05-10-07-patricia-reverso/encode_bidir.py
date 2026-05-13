"""Wrapper de encode em direcao 'forward' ou 'reverse'.

Conceito (Maaß 1999/2003, affix tree): para detectar sufixos comuns,
basta construir uma segunda arvore Patricia sobre as strings invertidas.
Os dois algoritmos (construir_inicial, aplicar_patricia, rle_adjacente,
encode_aninhado) sao usados sem modificacao.

A unica responsabilidade deste wrapper:
  1. Inverter as strings antes de construir, se 'reverse'.
  2. Anotar a direcao no TCF com um marcador `<dir:NAME>` na 1a linha
     nao-vazia.

Decode (em decode_bidir.py) le o marcador e inverte de volta se necessario.

Nao ha heuristica de escolha automatica nem casamento entre direcoes —
o objetivo deste experimento e isolar o efeito do espelho.
"""

from encode_aninhado import encode_aninhado
from patricia import aplicar_patricia, construir_inicial, rle_adjacente


def encode_direcao(linhas: list[str], direcao: str, header: str) -> str:
    if direcao not in ("forward", "reverse"):
        raise ValueError(f"direcao invalida: {direcao!r}")

    if direcao == "reverse":
        linhas_proc = [s[::-1] for s in linhas]
    else:
        linhas_proc = list(linhas)

    nos, body = construir_inicial(linhas_proc)
    nos = aplicar_patricia(nos)
    body_rle = rle_adjacente(body)
    tcf_inner = encode_aninhado(nos, body_rle, header)

    return f"<dir:{direcao}>\n{tcf_inner}"

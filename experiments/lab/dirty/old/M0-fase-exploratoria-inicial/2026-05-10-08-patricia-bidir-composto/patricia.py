"""Construcao da arvore Patricia + RLE adjacente no body.

Refeito do zero (nao importa de dirty/old). 3 fases:

1. construir_inicial: cada valor unico vira folha top-level com id sequencial;
   body e a sequencia de no_id por linha.
2. aplicar_patricia: detecta prefixos comuns (>= MIN_PREFIXO chars) que
   aparecem em >= MIN_GRUPO folhas top-level e fatora em no pai. Iterativo
   ate nao haver mais candidatos.
3. rle_adjacente: comprime body de [no_id, ...] em [(no_id, repeticao)].

Cada no tem id estavel desde a fase 1. As refs no body apontam para o id
do no que reconstroi a string completa. Quando um no folha vira filho de
um pai (Patricia), seu id se mantem; muda apenas seu pai_id e seu
fragmento (vira o sufixo a partir do pai).
"""

from collections import Counter
from dataclasses import dataclass
from typing import Optional

MIN_PREFIXO = 3
MIN_GRUPO = 2


@dataclass
class No:
    id: int
    pai_id: Optional[int]
    fragmento: str  # se pai_id is None: string completa; senao: sufixo


def texto_completo(no_id: int, nos: dict[int, No]) -> str:
    n = nos[no_id]
    if n.pai_id is None:
        return n.fragmento
    return texto_completo(n.pai_id, nos) + n.fragmento


def construir_inicial(linhas: list[str]) -> tuple[dict[int, No], list[int], dict[str, int]]:
    """Retorna (nos, body, str_to_eid). str_to_eid permite localizar a
    folha pelo texto original — util para o experimento 08.
    """
    valor_para_id: dict[str, int] = {}
    nos: dict[int, No] = {}
    body: list[int] = []
    proximo_id = 1
    for v in linhas:
        if v in valor_para_id:
            body.append(valor_para_id[v])
        else:
            nos[proximo_id] = No(proximo_id, None, v)
            valor_para_id[v] = proximo_id
            body.append(proximo_id)
            proximo_id += 1
    return nos, body, valor_para_id


def aplicar_patricia(nos: dict[int, No], min_prefixo: int = MIN_PREFIXO,
                     min_grupo: int = MIN_GRUPO) -> dict[int, No]:
    """Iterativo: cada passada acha o prefixo top-level mais longo
    que aparece em >= min_grupo folhas top-level e fatora.
    """
    proximo_id = max(nos.keys()) + 1 if nos else 1

    while True:
        top_level = [n for n in nos.values() if n.pai_id is None]
        if len(top_level) < min_grupo:
            break

        contagens: Counter = Counter()
        for n in top_level:
            v = n.fragmento
            for k in range(min_prefixo, len(v)):  # < len: prefixo proprio
                contagens[v[:k]] += 1

        candidatos = [(p, c) for p, c in contagens.items() if c >= min_grupo]
        if not candidatos:
            break
        # mais longo, desempate por mais frequente, depois lex
        candidatos.sort(key=lambda x: (-len(x[0]), -x[1], x[0]))
        prefixo, _ = candidatos[0]

        pai = No(proximo_id, None, prefixo)
        nos[proximo_id] = pai
        proximo_id += 1
        for n in top_level:
            if n.fragmento.startswith(prefixo) and n.id != pai.id:
                n.pai_id = pai.id
                n.fragmento = n.fragmento[len(prefixo):]
        # se o pai tem fragmento "", e nenhum filho usa-o sozinho, ele
        # pode ser dispensado — neste experimento mantemos por clareza.

    return nos


def rle_adjacente(body: list[int]) -> list[tuple[int, int]]:
    if not body:
        return []
    res: list[tuple[int, int]] = []
    atual_id = body[0]
    rep = 1
    for x in body[1:]:
        if x == atual_id:
            rep += 1
        else:
            res.append((atual_id, rep))
            atual_id = x
            rep = 1
    res.append((atual_id, rep))
    return res


def desenhar_arvore(nos: dict[int, No]) -> str:
    """ASCII tree: raizes top-level com indentacao para filhos."""
    filhos_de: dict[Optional[int], list[int]] = {}
    for n in nos.values():
        filhos_de.setdefault(n.pai_id, []).append(n.id)
    for k in filhos_de:
        filhos_de[k].sort()

    linhas: list[str] = []

    def emite(no_id: int, prof: int):
        n = nos[no_id]
        if n.pai_id is None:
            rotulo = f'no{n.id} = "{n.fragmento}"'
        else:
            rotulo = f'no{n.id} = pai(no{n.pai_id}) + "{n.fragmento}"  -> "{texto_completo(n.id, nos)}"'
        linhas.append("  " * prof + rotulo)
        for filho_id in filhos_de.get(no_id, []):
            emite(filho_id, prof + 1)

    for raiz in filhos_de.get(None, []):
        emite(raiz, 0)
    return "\n".join(linhas)

"""notationlib — ESTUDO (não um formato): qual a forma MAIS MINIMALISTA de agrupar colunas numa árvore,
dentro de um cabeçalho linear? Compara as famílias de "portador de forma" que o owner levantou:

  (S) start/end        — delimitadores casados: nome[filhos]         (os colchetes; 1 exemplo, não o alvo)
  (A) descend/ascend   — símbolos entre elementos: nome>filhos<      (irmão dos colchetes)
  (C) contagem inicial — aridade por nó interno: nome*3 f1 f2 f3     (o "contagem que indica")
  (D) profundidade     — nível por nó (pré-ordem): nome:1 filho:2    (vetor de depth)

Todos codificam a MESMA topologia+nomes; diferem em COMO marcam o aninhamento. Cada um tem encode +
parse (RT da topologia). Mede bytes da STRING de agrupamento (a parte de header; sizes/dados são ortogonais).

Achado-guia (teoria): uma lista linear de irmãos com separador NÃO basta pra reconstruir uma árvore —
precisa de UM portador de forma: {delimitador casado} OU {contagem/aridade} OU {profundidade}. 'Símbolo
entre elementos' só resolve o nesting se o símbolo for um desses (ex.: descend/ascend = delimitador).
"""
from __future__ import annotations


# ---- doc → árvore (floresta de filhos da raiz); nó = {name, children|None} ----
def build_tree(node: dict):
    ch = []
    for k, v in node.items():
        if isinstance(v, dict):
            ch.append({"name": k, "children": build_tree(v)})
        elif isinstance(v, list):
            cols = list(v[0]) if v else []
            ch.append({"name": k, "children": [{"name": c, "children": None} for c in cols]})
        else:
            ch.append({"name": k, "children": None})
    return ch


# ---- (S) start/end (colchetes) ----
def enc_startend(forest):
    return ",".join(n["name"] if n["children"] is None
                    else f"{n['name']}[{enc_startend(n['children'])}]" for n in forest)


def parse_startend(s):
    pos = 0

    def seq(closing):
        nonlocal pos
        out = []
        while pos < len(s) and s[pos] != closing:
            if s[pos] == ",":
                pos += 1
                continue
            j = pos
            while pos < len(s) and s[pos] not in ",[]":
                pos += 1
            name = s[j:pos]
            if pos < len(s) and s[pos] == "[":
                pos += 1
                kids = seq("]")
                if pos < len(s) and s[pos] == "]":
                    pos += 1
                out.append({"name": name, "children": kids})
            else:
                out.append({"name": name, "children": None})
        return out
    return seq(None)


# ---- (A) descend/ascend (símbolos > <) ----
def enc_da(forest):
    return ",".join(n["name"] if n["children"] is None
                    else f"{n['name']}>{enc_da(n['children'])}<" for n in forest)


def parse_da(s):
    pos = 0

    def seq():
        nonlocal pos
        out = []
        while pos < len(s) and s[pos] != "<":
            if s[pos] == ",":
                pos += 1
                continue
            j = pos
            while pos < len(s) and s[pos] not in ",><":
                pos += 1
            name = s[j:pos]
            if pos < len(s) and s[pos] == ">":
                pos += 1
                kids = seq()
                if pos < len(s) and s[pos] == "<":
                    pos += 1
                out.append({"name": name, "children": kids})
            else:
                out.append({"name": name, "children": None})
        return out
    return seq()


# ---- (C) contagem inicial (aridade por nó interno) — pré-ordem, tokens separados por espaço ----
def enc_count(forest):
    toks = []

    def walk(nodes):
        for n in nodes:
            if n["children"] is None:
                toks.append(n["name"])
            else:
                toks.append(f"{n['name']}*{len(n['children'])}")
                walk(n["children"])
    walk(forest)
    return " ".join(toks)


def parse_count(s):
    toks = s.split()
    pos = 0

    def node():
        nonlocal pos
        t = toks[pos]; pos += 1
        if "*" in t:
            name, k = t.rsplit("*", 1)
            return {"name": name, "children": [node() for _ in range(int(k))]}
        return {"name": t, "children": None}
    out = []
    while pos < len(toks):
        out.append(node())
    return out


# ---- (D) profundidade (nível por nó, pré-ordem) ----
def enc_depth(forest):
    toks = []

    def walk(nodes, d):
        for n in nodes:
            toks.append(f"{n['name']}:{d}")
            if n["children"] is not None:
                walk(n["children"], d + 1)
    walk(forest, 1)
    return " ".join(toks)


def parse_depth(s):
    items = [(t.rsplit(":", 1)[0], int(t.rsplit(":", 1)[1])) for t in s.split()]
    root = {"children": []}
    stack = [(0, root)]                        # (depth, node)
    for name, d in items:
        while stack[-1][0] >= d:
            stack.pop()
        n = {"name": name, "children": []}     # começa [] pra poder receber filhos
        stack[-1][1]["children"].append(n)
        stack.append((d, n))
    return _leafify(root["children"])


def _leafify(forest):
    # normaliza: nó sem filhos coletados vira folha (children=None)
    for n in forest:
        if not n["children"]:
            n["children"] = None
        else:
            _leafify(n["children"])
    return forest


NOTATIONS = {
    "S start/end   (colchetes)": (enc_startend, parse_startend),
    "A descend/asc  (> <)": (enc_da, parse_da),
    "C contagem     (nome*N)": (enc_count, parse_count),
    "D profundidade (nome:d)": (enc_depth, parse_depth),
}

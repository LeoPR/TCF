"""schemalib — engenhoca: a LINGUAGEM SEMÂNTICA do schema TCF.8 (cardinalidade/hierarquia), primeiro
EXPLÍCITA (todos os itens), depois a DEDUÇÃO do que sai (implícito) → a forma MÍNIMA.

Metodologia (owner): a linguagem tem sempre TODOS os itens; implícito/explícito é uma camada de cima —
depois se vê o que dá pra tirar. Tese a testar: a forma mínima da linguagem completa CONVERGE pro
colchete da peça 5 (P5). Cardinalidade ≈ hierarquia (duais). NÃO toca src/tcf. Valores como string.
"""
from __future__ import annotations


# ---- doc → colunas (DFS) + árvore de nós ----
def columns(node: dict):
    cols = []
    for k, v in node.items():
        if isinstance(v, dict):
            cols += columns(v)
        elif isinstance(v, list):
            for c in (list(v[0]) if v else []):
                cols.append((c, [str(r[c]) for r in v]))
        else:
            cols.append((k, [str(v)]))
    return cols


# ===== FORMA 1 — EXPLÍCITA (todos os itens da linguagem semântica) =====
def explicit_header(doc: dict) -> str:
    """Todo item explícito: flags, no (kind/rows/parent/cardinalidade), coluna (tipo/marker/size/container)."""
    L = ["#TCF.8 M N", "@schema-explicito"]

    def walk(node, name, kind, parent, card, rows):
        L.append(f"@grp {name} kind={kind} rows={rows} parent={parent} card={card}")
        for k, v in node.items():
            if isinstance(v, dict):
                walk(v, k, "object", name, "1:1", 1)
            elif isinstance(v, list):
                cols = list(v[0]) if v else []
                walk_arr(v, k, name, cols)
            else:
                sz = len(str(v).encode())
                L.append(f"@col {k} type=str marker=! size={sz} in={name}")

    def walk_arr(arr, name, parent, cols):
        n = len(arr)
        L.append(f"@grp {name} kind=array rows={n} parent={parent} card=1:N")
        for c in cols:
            sz = sum(len(str(r[c]).encode()) for r in arr)
            L.append(f"@col {c} type=str marker=! size={sz} in={name}")

    walk(doc, "$root", "object", "-", "-", 1)
    return "\n".join(L) + "\n"


# ===== FORMA 2 — MÍNIMA (dedução aplicada) = o colchete da P5 =====
def _bracket(node, sizes, ctr, nleaves):
    parts = []
    for k, v in node.items():
        if isinstance(v, dict):
            parts.append(f"{k}[{_bracket(v, sizes, ctr, nleaves)}]")
        elif isinstance(v, list):
            inner = []
            for c in (list(v[0]) if v else []):
                i = ctr[0]; ctr[0] += 1
                inner.append(c if i == nleaves - 1 else f"{c}:{sizes[i]}")
            parts.append(f"{k}[{','.join(inner)}]")
        else:
            i = ctr[0]; ctr[0] += 1
            parts.append(k if i == nleaves - 1 else f"{k}:{sizes[i]}")
    return ",".join(parts)


def minimal_header(doc: dict, bodies_sizes: list) -> str:
    return "#TCF.8\n[" + _bracket(doc, bodies_sizes, [0], len(bodies_sizes)) + "]\n"


# ---- decode da forma mínima (colchete) → JSON (RT) ----
def _parse(meta):
    s, pos = meta, 0

    def group():
        nonlocal pos
        assert s[pos] == "["
        pos += 1
        items = []
        while pos < len(s) and s[pos] != "]":
            while pos < len(s) and s[pos] in " ,":
                pos += 1
            if s[pos] == "]":
                break
            j = pos
            while pos < len(s) and s[pos] not in ",[]:":
                pos += 1
            name = s[j:pos]
            if pos < len(s) and s[pos] == ":":
                pos += 1
                j2 = pos
                while pos < len(s) and s[pos] not in ",[]":
                    pos += 1
                items.append(("leaf", name, int(s[j2:pos])))
            elif pos < len(s) and s[pos] == "[":
                items.append(("group", name, group()))
            else:
                items.append(("leaf", name, None))
        if pos < len(s) and s[pos] == "]":
            pos += 1
        return items
    return group()


def decode_minimal(blob: str, decode_col) -> dict:
    meta, rest = blob.split("\n", 2)[1], blob.split("\n", 2)[2]
    tree = _parse(meta)
    leaves = []

    def walkL(items):
        for kind, name, payload in items:
            leaves.append((name, payload)) if kind == "leaf" else walkL(payload)
    walkL(tree)
    raw = rest.encode("utf-8")
    cols, off = {}, 0
    for name, sz in leaves:
        body = raw[off:].decode() if sz is None else raw[off:off + sz].decode()
        if sz is not None:
            off += sz
        cols[name] = decode_col(body)

    def dfr(items):
        for k, n, _ in items:
            if k == "leaf":
                return len(cols[n])
        return 1

    def rebuild(items, root):
        if not root and dfr(items) > 1:
            ln = [n for k, n, _ in items if k == "leaf"]
            return [{x: cols[x][i] for x in ln} for i in range(len(cols[ln[0]]))]
        out = {}
        for k, n, p in items:
            out[n] = cols[n][0] if k == "leaf" else rebuild(p, False)
        return out
    return rebuild(tree, True)


# ---- tabela de dedução (o que sai da forma explícita) ----
DEDUCTION = [
    ("magic #TCF.8", "NÃO", "roteamento/versão (libmagic)"),
    ("flag M (multi)", "SIM", "≥2 colunas ⇒ multi (P5/P6)"),
    ("flag N (nested)", "SIM", "presença de aninhamento (colchete)"),
    ("hierarquia (arestas pai→filho)", "NÃO*", "é o SCHEMA; *derivável se pré-acordado (O-FMT-14)"),
    ("nomes de coluna/grupo", "parcial", "drop_names se anônimo; senão o consumidor precisa"),
    ("cardinalidade (1:1/1:N/...)", "SIM", "nº de linhas dos filhos (P7): 1→obj, N→array"),
    ("kind (object/array)", "SIM", "idem cardinalidade"),
    ("rows (contagem)", "SIM", "decodar o body revela"),
    ("type (str/num/...)", "parcial", "default str; senão :tipo por coluna"),
    ("marker (!/@/%)", "NÃO", "o decode precisa (raw/dict/split)"),
    ("size por coluna", "parcial", "última-sem-size; derivável se streaming"),
]

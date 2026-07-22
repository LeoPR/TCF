"""bracketlib — engenhoca (descartável): modelo P5 "agrupamento por COLCHETES no meta".

Ideia do owner (ainda mais simples que P4): não precisa de flag `M`/`N` explícito nem de linha `#H`
separada — o **próprio meta das colunas** carrega a hierarquia via colchetes:

    [nome, telefones[tel]]
    [nome, endereco[rua, cidade, geo[lat, lon]], telefones[tel]]

- `M` e `N` são **deduzidos**: várias colunas ⇒ multi; presença de `[...]` aninhado ⇒ hierárquico.
- **array vs objeto é DEDUZIDO do nº de linhas dos filhos** ("repetir pode ser deduzido dos filhos"):
  um grupo cujas colunas-folha diretas têm **>1 linha** = array (1:N); **1 linha** = objeto (1:1).
- O **nome do grupo** reconstrói o campo (telefones, endereco). A raiz é objeto (1 instância).
- A hierarquia (os colchetes) só é necessária **SE for pra reconstruir o JSON**; sem ela, é multi-col plano.

Sizes: inline `nome:<bytes>` por folha (última folha em ordem DFS omite, estilo multi-col). Valores como
string (fixtures all-string). Ambiguidade conhecida: grupo de **1 linha** não distingue objeto de array-de-1
(deduz objeto); grupo só com subgrupos (sem folha direta) deduz objeto. → anotado, refinar depois.
"""
from __future__ import annotations

SHEBANG = "#TCF.8"


def columns(node: dict):
    """(nome, [valores-string]) em ordem DFS — casa com a ordem das folhas no meta."""
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


def _bracket(node, sizes, ctr, nleaves):
    parts = []
    for k, v in node.items():
        if isinstance(v, dict):
            parts.append(f"{k}[{_bracket(v, sizes, ctr, nleaves)}]")
        elif isinstance(v, list):
            cols = list(v[0]) if v else []
            inner = []
            for c in cols:
                i = ctr[0]; ctr[0] += 1
                inner.append(c if i == nleaves - 1 else f"{c}:{sizes[i]}")
            parts.append(f"{k}[{','.join(inner)}]")
        else:
            i = ctr[0]; ctr[0] += 1
            parts.append(k if i == nleaves - 1 else f"{k}:{sizes[i]}")
    return ",".join(parts)


def encode_p5(doc: dict, encode) -> str:
    cols = columns(doc)
    bodies = [encode(vals) for _n, vals in cols]
    sizes = [len(b.encode()) for b in bodies]
    meta = "[" + _bracket(doc, sizes, [0], len(cols)) + "]"
    return f"{SHEBANG}\n{meta}\n" + "".join(bodies)


# ---- parse do meta em colchetes ----
def _parse(meta: str):
    s = meta
    pos = 0

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
            if pos < len(s) and s[pos] == ":":            # folha com size
                pos += 1
                j2 = pos
                while pos < len(s) and s[pos] not in ",[]":
                    pos += 1
                items.append(("leaf", name, int(s[j2:pos])))
            elif pos < len(s) and s[pos] == "[":          # subgrupo nomeado
                items.append(("group", name, group()))
            else:                                          # folha sem size (última)
                items.append(("leaf", name, None))
        if pos < len(s) and s[pos] == "]":
            pos += 1
        return items

    return group()


def decode_p5(text: str, decode) -> dict:
    shebang, meta, rest = text.split("\n", 2)
    assert shebang == SHEBANG, f"shebang inesperado: {shebang!r}"
    tree = _parse(meta)
    # ordem DFS das folhas + sizes
    leaves = []

    def walk(items):
        for kind, name, payload in items:
            if kind == "leaf":
                leaves.append((name, payload))
            else:
                walk(payload)
    walk(tree)
    raw = rest.encode("utf-8")
    cols, off = {}, 0
    for name, sz in leaves:
        body = raw[off:].decode("utf-8") if sz is None else raw[off:off + sz].decode("utf-8")
        if sz is not None:
            off += sz
        cols[name] = decode(body)

    def direct_leaf_rows(items):
        for kind, name, _p in items:
            if kind == "leaf":
                return len(cols[name])
        return 1                                           # sem folha direta → trata como objeto

    def rebuild(items, is_root):
        # array se as folhas diretas têm >1 linha (dedução) e não é raiz
        if not is_root and direct_leaf_rows(items) > 1:
            leafnames = [n for k, n, _ in items if k == "leaf"]
            n = len(cols[leafnames[0]])
            return [{ln: cols[ln][i] for ln in leafnames} for i in range(n)]
        out = {}
        for kind, name, payload in items:
            out[name] = cols[name][0] if kind == "leaf" else rebuild(payload, False)
        return out

    return rebuild(tree, True)

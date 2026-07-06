"""structlib — engenhoca (descartável): documento JSON {escalares + arrays-de-objetos} →
tabelas → **blocos TCF.8 aninhados um após o outro**, com cabeçalho AUTO-DESCRITIVO da árvore.

FOCO: ESTRUTURA (não bytes). Round-trip de volta ao JSON. NÃO toca src/tcf. Draft v0 — o owner
redesenha a sintaxe do envelope; aqui a ideia é ver as peças e provar que decoda.

Formato do envelope (draft):

    #TCF.8-NEST v0
    @tree {"order":["nome","telefones"],"root":{"nome":"str"},"arrays":{"telefones":{"tel":"str"}}}
    @block root
    #TCF.8
    leonardo
    @block telefones
    #TCF.8
    (\\41) \\9999*\\9*-\\9999
    1\\4*3

- `@tree`  = esquema auto-descritivo (ordem dos campos + tipos + quais são array).
- `@block <nome>` delimita cada TCF (leaf). Bloco `root` = escalares (1 linha); demais = arrays.
- Cada leaf usa **TCF.8** (single-col via `stamp=True`; multi-col cairia em TCF.7 — TCF.8 multi só com nature).
"""
from __future__ import annotations
import json

MAGIC = "#TCF.8-NEST v0"


# ---- tipagem célula ↔ string ----
def celltype(vals):
    v = next((x for x in vals if x is not None), None)
    if isinstance(v, bool):
        return "bool"
    if isinstance(v, (int, float)):
        return "num"
    return "str"


def enc_cell(v):
    if isinstance(v, bool):
        return "true" if v else "false"
    if v is None:
        return ""
    return str(v)


def dec_cell(s, t):
    if t == "bool":
        return s == "true"
    if t == "num":
        return None if s == "" else (int(s) if ("." not in s and "e" not in s.lower()) else float(s))
    return s


# ---- documento → blocos ----
def split_doc(doc: dict):
    scalars = {k: v for k, v in doc.items() if not isinstance(v, list)}
    arrays = {k: v for k, v in doc.items() if isinstance(v, list)}
    return scalars, arrays


def to_tables(doc: dict):
    """Devolve (tree, tables) — tree = esquema; tables = {'root':{...}, '<array>':{...}} (strings)."""
    scalars, arrays = split_doc(doc)
    tree = {"order": list(doc), "root": {k: celltype([v]) for k, v in scalars.items()}, "arrays": {}}
    tables = {}
    if scalars:
        tables["root"] = {k: [enc_cell(v)] for k, v in scalars.items()}
    for name, arr in arrays.items():
        cols = list(arr[0]) if arr else []
        tree["arrays"][name] = {c: celltype([r.get(c) for r in arr]) for c in cols}
        tables[name] = {c: [enc_cell(r.get(c)) for r in arr] for c in cols}
    return tree, tables


# ---- encode/decode de 1 bloco leaf (TCF.8) ----
def encode_leaf(table: dict, encode):
    cols = list(table)
    if len(cols) == 1:                       # single-col → TCF.8 via stamp
        return encode(table[cols[0]], stamp=True)
    return encode(table)                     # multi-col (TCF.7; nota: TCF.8 multi exige nature)


def decode_leaf(text: str, cols: list, decode):
    g = decode(text)
    if isinstance(g, list):                  # single-col stamp → lista; recompõe com o nome da coluna
        return {cols[0]: g}
    return g                                  # multi-col → dict


# ---- aninhar / desaninhar ----
def nest(doc: dict, encode) -> str:
    tree, tables = to_tables(doc)
    parts = [MAGIC, "@tree " + json.dumps(tree, ensure_ascii=False)]
    block_order = (["root"] if "root" in tables else []) + list(tree["arrays"])
    for name in block_order:
        parts.append("@block " + name)
        parts.append(encode_leaf(tables[name], encode).rstrip("\n"))
    return "\n".join(parts) + "\n"


def unnest(text: str, decode) -> dict:
    lines = text.split("\n")
    assert lines[0] == MAGIC, f"magic inesperado: {lines[0]!r}"
    tree = json.loads(lines[1][len("@tree "):])
    # fatia os blocos por '@block <nome>'
    blocks, cur, name = {}, [], None
    for ln in lines[2:]:
        if ln.startswith("@block "):
            if name is not None:
                blocks[name] = "\n".join(cur)
            name, cur = ln[len("@block "):], []
        else:
            cur.append(ln)
    if name is not None:
        blocks[name] = "\n".join(cur).rstrip("\n")
    # reconstrói o doc na ordem original
    doc = {}
    root_types = tree["root"]
    root_tbl = decode_leaf(blocks["root"], list(root_types), decode) if "root" in blocks else {}
    for field in tree["order"]:
        if field in tree["arrays"]:
            atypes = tree["arrays"][field]
            tbl = decode_leaf(blocks[field], list(atypes), decode)
            n = len(next(iter(tbl.values()))) if tbl else 0
            doc[field] = [{c: dec_cell(tbl[c][i], atypes[c]) for c in atypes} for i in range(n)]
        else:
            doc[field] = dec_cell(root_tbl[field][0], root_types[field])
    return doc

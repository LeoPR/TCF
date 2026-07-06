"""linklib — engenhoca (descartável): estuda a LIGAÇÃO pai/filho entre blocos TCF empilhados.

Já temos meta que relaciona COLUNAS dentro de uma tabela; falta relacionar TABELAS (blocos) entre si.
Como a hierarquia JSON é CONTENÇÃO (não FK numérica), a ligação é **pai/filho**. Técnica implementada:
**adjacência lado-do-pai** — o cabeçalho dá a dica `#TCF.8 N` (nested) e, por bloco, lista os campos;
campo escalar = `nome:tipo`; campo que é filho = `nome>K` (aponta pro bloco K). O tipo/kind do filho
(obj vs arr) está na linha `@bK` dele. Isso carrega, junto: ordem + tipo + a aresta pai→filho.

Classe suportada (sem link posicional / repetition level — isso é peça FUTURA):
  raiz única; objetos aninham objetos (1:1) em qualquer profundidade; arrays contêm objetos SÓ-escalares
  (folha), pendurados em qualquer objeto de instância única. PROIBIDO array-dentro-de-array e
  objeto/array dentro de elemento de array (levanta NotImplementedError → precisa de link posicional).

Formato (draft):
    #TCF.8 N
    @b0 root nome:str endereco>1 telefones>3
    @b1 obj rua:str cidade:str geo>2
    @b2 obj lat:str lon:str
    @b3 arr tel:str
    @data 0
    #TCF.8
    leonardo
    @data 1
    #TCF.7 M
    ...
"""
from __future__ import annotations

MAGIC = "#TCF.8 N"


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


# ---- documento → blocos (DFS pre-order; idx do pai < idx dos filhos) ----
def build_blocks(doc: dict):
    blocks = []

    def add_object(node, kind):
        idx = len(blocks)
        blocks.append(None)                       # reserva o idx (pré-ordem)
        fields, table, types = [], {}, {}
        for k, v in node.items():
            if isinstance(v, dict):
                fields.append(("c", k, add_object(v, "obj")))
            elif isinstance(v, list):
                fields.append(("c", k, add_array(v)))
            else:
                t = celltype([v]); table[k] = [enc_cell(v)]; types[k] = t
                fields.append(("s", k, t))
        blocks[idx] = {"idx": idx, "kind": kind, "fields": fields, "table": table, "types": types}
        return idx

    def add_array(arr):
        for r in arr:
            for c, v in r.items():
                if isinstance(v, (dict, list)):
                    raise NotImplementedError(
                        "elemento de array com filho aninhado precisa de link posicional (peça futura)")
        cols = list(arr[0]) if arr else []
        types = {c: celltype([r.get(c) for r in arr]) for c in cols}
        table = {c: [enc_cell(r.get(c)) for r in arr] for c in cols}
        idx = len(blocks)
        blocks.append({"idx": idx, "kind": "arr", "fields": [("s", c, types[c]) for c in cols],
                       "table": table, "types": types})
        return idx

    root = add_object(doc, "root")
    return blocks, root


# ---- encode/decode de 1 bloco leaf ----
def _scalar_cols(meta):
    return [name for (k, name, _t) in meta["fields"] if k == "s"]


def encode_leaf(meta, encode):
    cols = _scalar_cols(meta)
    if not cols:
        return ""                                 # bloco só-estrutura (sem escalar)
    if len(cols) == 1:
        return encode(meta["table"][cols[0]], stamp=True)   # single-col → TCF.8
    return encode({c: meta["table"][c] for c in cols})       # multi-col → TCF.7


def decode_leaf(text, meta, decode):
    cols = _scalar_cols(meta)
    if not cols:
        return {}
    g = decode(text)
    return {cols[0]: g} if isinstance(g, list) else g


# ---- cabeçalho: adjacência lado-do-pai ----
def _field_token(entry):
    k, name, x = entry
    return f"{name}:{x}" if k == "s" else f"{name}>{x}"


def nest(doc, encode) -> str:
    blocks, _root = build_blocks(doc)
    lines = [MAGIC]
    for b in blocks:
        lines.append(f"@b{b['idx']} {b['kind']} " + " ".join(_field_token(e) for e in b["fields"]))
    for b in blocks:
        lines.append(f"@data {b['idx']}")
        leaf = encode_leaf(b, encode)
        if leaf:
            lines.append(leaf.rstrip("\n"))
    return "\n".join(lines) + "\n"


def _parse_field(tok):
    if ">" in tok:
        name, k = tok.rsplit(">", 1)
        return ("c", name, int(k))
    name, t = tok.rsplit(":", 1)
    return ("s", name, t)


def unnest(text, decode) -> dict:
    lines = text.split("\n")
    assert lines[0] == MAGIC, f"magic inesperado: {lines[0]!r}"
    metas, order = {}, []
    i = 1
    while i < len(lines) and lines[i].startswith("@b"):
        parts = lines[i].split(" ")
        idx = int(parts[0][2:]); kind = parts[1]
        fields = [_parse_field(t) for t in parts[2:] if t]
        metas[idx] = {"idx": idx, "kind": kind, "fields": fields}
        order.append(idx); i += 1
    # blocos de dados
    blocktext, cur, curidx = {}, [], None
    for ln in lines[i:]:
        if ln.startswith("@data "):
            if curidx is not None:
                blocktext[curidx] = "\n".join(cur).strip("\n")
            curidx = int(ln[len("@data "):]); cur = []
        else:
            cur.append(ln)
    if curidx is not None:
        blocktext[curidx] = "\n".join(cur).strip("\n")
    decoded = {idx: decode_leaf(blocktext.get(idx, ""), metas[idx], decode) for idx in metas}

    def rebuild(idx):
        meta, tbl = metas[idx], decoded[idx]
        if meta["kind"] == "arr":
            n = len(next(iter(tbl.values()))) if tbl else 0
            return [{name: dec_cell(tbl[name][r], t) for (k, name, t) in meta["fields"]} for r in range(n)]
        out = {}
        for (k, name, x) in meta["fields"]:
            out[name] = dec_cell(tbl[name][0], x) if k == "s" else rebuild(x)
        return out

    return rebuild(0)

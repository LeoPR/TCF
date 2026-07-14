"""TCF.8H recuperado — o modelo do TABELÃO (lab 1509), simples.

Insight fundador (owner, reafirmado 2026-07-13): hierarquia = **tabela combinatória
denormalizada**, IDÊNTICA à multi-coluna. Nome com 2 telefones vira:

    nome        telefone
    Ana Souza   +55 11 99999-0001
    Ana Souza   +55 11 3333-0001      <- o pai REPETE por filho

Encoda com a MESMA máquina multi-col (`tcf.encode`). O pai que repete colapsa
sozinho no RLE `*2|Ana Souza` — e **o comprimento do run = a multiplicidade** do
array. O header de colchetes (contrato consagrado, ADR-0031 / EXP-015 / lab 1830)
guarda só a árvore, pra re-aninhar no decode.

Dual do EXP-015 (que guarda o pai UMA vez, ragged, e deduz N do tamanho do filho):
aqui o pai repete e o RLE conta — "exatamente a mesma estrutura" da multi-col.

Wire (protótipo; sizes DECIMAIS bytes-incl-LF, como o contrato firmou em 1830):

    #TCF.8H <bracket-meta>\\n<bodies-por-coluna-concatenados>

  bracket-meta (recursivo, itens separados por `,`):
    name:size          folha ESCALAR (pai — repete no tabelão)
    name[              array 1:N de escalares (a coluna `name` = elementos achatados)
    name[f1:size,...]  array 1:N de objetos (colunas f1.. = campos do elemento)
  Regras consagradas: ÚLTIMA folha (DFS) omite size; omit-closes dropa o run final
  de `]`/`}`; o `\\n` + EOF auto-fecham. Bodies = `tcf.encode(coluna)` em ordem DFS,
  fatiados pelos sizes (última folha pega o resto).

RT-alvo: `decode(encode(records)) == records` (lista de dicts). Zero src/tcf
(uso read-only de tcf.encode/decode). Um array por registro; {} 1:1 e multi-array
= extensão registrada.
"""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(_ROOT / "src"))
from tcf import decode as tcf_decode, encode as tcf_encode  # noqa: E402

MAGIC = "#TCF.8H"


# ============================================================ schema da árvore
def derive_tree(records: list[dict]) -> list:
    """Ordem DFS dos campos. Cada item: ('scalar', name) | ('arr_scalars', name) |
    ('arr_objects', name, [field...]). Um array por registro (o resto = escalar pai)."""
    first = records[0]
    tree = []
    for k, v in first.items():
        if isinstance(v, list):
            if v and isinstance(v[0], dict):
                tree.append(("arr_objects", k, list(v[0].keys())))
            else:
                tree.append(("arr_scalars", k))
        else:
            tree.append(("scalar", k))
    return tree


# ============================================================ denormalizar
def denormalize(records: list[dict], tree: list) -> dict:
    """Tabelão: pai repete por filho; array achatado. Todas as colunas ficam com o
    MESMO comprimento (= soma das multiplicidades) — uma tabela multi-col de verdade."""
    parents = [t[1] for t in tree if t[0] == "scalar"]
    arr = next(t for t in tree if t[0] != "scalar")
    cols: dict[str, list[str]] = {p: [] for p in parents}
    if arr[0] == "arr_scalars":
        cols[arr[1]] = []
        elem_cols = [arr[1]]
    else:
        elem_cols = arr[2]
        for f in elem_cols:
            cols[f] = []
    for rec in records:
        children = rec[arr[1]]
        m = max(len(children), 1)  # registro sem filhos ainda ocupa 1 linha (pai visível)
        for _ in range(m):
            for p in parents:
                cols[p].append(str(rec[p]))
        if arr[0] == "arr_scalars":
            for c in children:
                cols[arr[1]].append(str(c))
            if not children:  # array vazio -> 1 linha com sentinela? mantemos simples: exige >=1
                raise ValueError("protótipo simples: array vazio não coberto (extensão)")
        else:
            for obj in children:
                for f in elem_cols:
                    cols[f].append(str(obj[f]))
    return cols


# ============================================================ header (bracket-meta)
def build_meta(tree: list, bodies: dict, *, last_omits=True, omit_closes=True) -> str:
    """bracket-meta com sizes (bytes-incl-LF do body por coluna). Forma:
      scalar          -> `name:size`
      array-escalares -> `name[]:size`   (coluna `name` = elementos)
      array-objetos   -> `name[f1:size,f2:size,...]`
    Consagrados (opt, default-on): ÚLTIMA folha DFS omite size; omit-closes dropa o
    run final de `]`."""
    leaves = _dfs_leaf_names(tree)
    last = leaves[-1]

    def sz(name):
        return "" if (last_omits and name == last) else f":{len(bodies[name].encode())}"

    parts = []
    for t in tree:
        if t[0] == "scalar":
            parts.append(f"{t[1]}{sz(t[1])}")
        elif t[0] == "arr_scalars":
            parts.append(f"{t[1]}[]{sz(t[1])}")
        else:
            parts.append(f"{t[1]}[{','.join(f'{f}{sz(f)}' for f in t[2])}]")
    meta = ",".join(parts)
    if omit_closes:
        meta = meta.rstrip("]}")
    return meta


def _dfs_leaf_names(tree: list) -> list[str]:
    out = []
    for t in tree:
        if t[0] == "scalar":
            out.append(t[1])
        elif t[0] == "arr_scalars":
            out.append(t[1])
        else:
            out.extend(t[2])
    return out


# ============================================================ encode
def encode_h(records: list[dict], *, last_omits=True, omit_closes=True) -> str:
    tree = derive_tree(records)
    cols = denormalize(records, tree)
    order = _dfs_leaf_names(tree)
    bodies = {name: tcf_encode(cols[name]) for name in order}
    meta = build_meta(tree, bodies, last_omits=last_omits, omit_closes=omit_closes)
    return f"{MAGIC} {meta}\n" + "".join(bodies[name] for name in order)


# ============================================================ decode
def decode_h(blob: str) -> list[dict]:
    head, rest = blob.split("\n", 1)
    assert head.startswith(MAGIC + " "), f"magic inesperado: {head!r}"
    tree, order_sizes = _parse_meta(head[len(MAGIC) + 1:])
    raw = rest.encode("utf-8")
    cols, off = {}, 0
    for name, size in order_sizes:
        body = raw[off:].decode() if size is None else raw[off:off + size].decode()
        if size is not None:
            off += size
        cols[name] = tcf_decode(body)
    return _renest(tree, cols)


def _parse_meta(meta: str):
    """(tree, [(leaf_name, size|None) em ordem DFS]). Aceita a forma consagrada:
    último size omitido (None) + `]` finais omit-closed (tolera `[` sem `]`)."""
    tree, order = [], []
    i, n = 0, len(meta)

    def read_name(stop):
        nonlocal i
        j = i
        while i < n and meta[i] not in stop:
            i += 1
        return meta[j:i]

    def read_size():
        """lê `:size` se houver; senão None (última folha)."""
        nonlocal i
        if i < n and meta[i] == ":":
            i += 1
            return int(read_name(",]"))
        return None

    while i < n:
        while i < n and meta[i] in " ,":
            i += 1
        if i >= n:
            break
        name = read_name(",[:")
        if i < n and meta[i] == "[":
            i += 1
            if i < n and meta[i] == "]":         # array de ESCALARES: `name[]:size`
                i += 1
                order.append((name, read_size()))
                tree.append(("arr_scalars", name))
            elif i >= n or meta[i] == ",":        # `[` sem `]` (omit-closes) = escalares, último
                order.append((name, None))
                tree.append(("arr_scalars", name))
            else:                                 # array de OBJETOS: `name[f:size,...]`
                fields = []
                while i < n and meta[i] != "]":
                    while i < n and meta[i] in " ,":
                        i += 1
                    if i >= n or meta[i] == "]":
                        break
                    fname = read_name(",]:")
                    fields.append(fname)
                    order.append((fname, read_size()))
                if i < n and meta[i] == "]":
                    i += 1
                tree.append(("arr_objects", name, fields))
        else:                                     # escalar
            order.append((name, read_size()))
            tree.append(("scalar", name))
    return tree, order


def _renest(tree: list, cols: dict) -> list[dict]:
    parents = [t[1] for t in tree if t[0] == "scalar"]
    arr = next(t for t in tree if t[0] != "scalar")
    n = len(cols[_dfs_leaf_names(tree)[0]])
    # agrupa linhas contíguas pela tupla de pais (o run do RLE = a multiplicidade)
    records, i = [], 0
    while i < n:
        key = tuple(cols[p][i] for p in parents)
        j = i
        while j < n and tuple(cols[p][j] for p in parents) == key:
            j += 1
        rec = {}
        # reconstrói na ordem da árvore
        for t in tree:
            if t[0] == "scalar":
                rec[t[1]] = cols[t[1]][i]
            elif t[0] == "arr_scalars":
                rec[t[1]] = [cols[t[1]][k] for k in range(i, j)]
            else:
                rec[t[1]] = [{f: cols[f][k] for f in t[2]} for k in range(i, j)]
        records.append(rec)
        i = j
    return records

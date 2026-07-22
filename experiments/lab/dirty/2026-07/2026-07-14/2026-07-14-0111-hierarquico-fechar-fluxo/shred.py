"""TCF.8H — codec hierárquico por SHREDDING em blocos + counts (fecha o fluxo).

Fecha a funcionalidade do hierárquico para os CLÁSSICOS de transmissão (cadastro,
telemetria, pedido) — a maioria em JSON. Generaliza:
  - envelope-de-blocos (peça 2/3): cada nó-repetido = 1 bloco TCF, ligado ao pai;
  - counts (o "sincronismo" do owner + Modelo B do lab 2356): a multiplicidade
    viaja 1× por array, EXPLÍCITA — resolve as 3 coisas que o tabelão integrado
    NÃO fecha: (a) MÚLTIPLAS listas irmãs (telefones[] E emails[], comum em
    cadastro) sem produto cartesiano; (b) arrays aninhados (pedido⊃itens); (c) a
    ambiguidade de chave (count é escrito, não deduzido do run RLE).

Modelo: a árvore vira BLOCOS (um por nível-de-array + a raiz). Objetos {} 1:1 são
INLINE (colunas do mesmo bloco). Cada array [] abre um bloco filho, ligado ao pai
por um count [n_i por instância-pai]. Cada bloco = uma tabela multi-col do motor
real (tcf.encode) — as colunas-pai NÃO repetem (ficam na sua granularidade).

Wire (protótipo, LF-only):
  #TCF.8H <meta>\\n<colunas em ordem DFS, tcf.encode cada, fatiadas por size>
  meta recursivo: name:size (escalar) · name{...} (objeto 1:1, inline) ·
    name[...] (array de objetos: bloco filho) · name[]:size (array de escalares).
  Cada array carrega um count implícito na sua coluna sentinela `name#` (nº de
  filhos por instância-pai) — em ordem DFS logo após o marcador do array.

RT-alvo: decode(encode(records)) == records. Zero src/tcf (read-only tcf.encode/decode).
Sem tipos/nulos (ortogonal). N:N real (2 arrays cruzados) não ocorre aqui — listas
irmãs são 1:N independentes, cada uma seu bloco.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "src"))
from tcf import decode as tcf_decode, encode as tcf_encode  # noqa: E402

MAGIC = "#TCF.8H"


# ============================================================ schema
# nó: ('scalar', name) | ('object', name, [filhos]) |
#     ('arr_scalars', name) | ('arr_objects', name, [filhos])
def derive_schema(records: list[dict]) -> list:
    """Schema robusto: varre TODOS os registros p/ achar o tipo de elemento de cada
    array (arrays vazios no 1º registro são comuns em transmissão — pessoa sem
    telefones). Assume conjunto de chaves uniforme (chaves heterogêneas = ragged,
    fora do escopo aqui)."""
    first = records[0]
    return [_node_for_field(k, [r[k] for r in records if k in r]) for k in first]


def _node_for_field(name, values: list):
    v0 = values[0]
    if isinstance(v0, dict):
        subs = [v for v in values if isinstance(v, dict)]
        return ("object", name, derive_schema(subs))
    if isinstance(v0, list):
        elems = [e for arr in values for e in arr]  # todos os elementos, todas as instâncias
        if elems and isinstance(elems[0], dict):
            return ("arr_objects", name, derive_schema(elems))
        return ("arr_scalars", name)
    return ("scalar", name)


# ============================================================ colunas (ordem DFS)
# cada folha: (path, kind) — kind: 'scalar' | 'arr_scalars' | 'count'
# um array-de-objetos NÃO é folha de dado; emite uma folha 'count' e recursa.
def leaves(schema: list, prefix=()) -> list[tuple]:
    out = []
    for node in schema:
        p = prefix + (node[1],)
        if node[0] == "scalar":
            out.append((p, "scalar"))
        elif node[0] == "arr_scalars":
            out.append((p, "count"))        # nº de escalares por instância-pai
            out.append((p, "arr_scalars"))  # os escalares achatados
        elif node[0] == "object":
            out += leaves(node[2], p)
        else:  # arr_objects
            out.append((p, "count"))        # nº de objetos por instância-pai
            out += leaves(node[2], p)       # colunas do elemento (bloco filho)
    return out


# ============================================================ encode (shred)
def encode_h(records: list[dict], **kw) -> str:
    schema = derive_schema(records)
    cols = {}
    for path, kind in leaves(schema):
        cols[(path, kind)] = []
    # emite a lista de raízes como um "array de objetos" implícito (bloco raiz)
    _emit_array(records, schema, (), cols)
    order = leaves(schema)
    # coluna VAZIA (bloco-filho sem elementos: todos os pais têm array vazio) -> body
    # vazio (o tcf.encode não faz 0-rows, BUG-03); os counts=[0,..] reconstroem.
    bodies = {(p, k): (tcf_encode(cols[(p, k)]) if cols[(p, k)] else "") for p, k in order}
    meta = _build_meta(schema, bodies, **kw)
    return f"{MAGIC} {meta}\n" + "".join(bodies[(p, k)] for p, k in order)


def _emit_array(instances: list, children: list, prefix: tuple, cols: dict):
    """Emite N instâncias irmãs (um bloco): cada uma contribui 1 linha às colunas
    escalares/1:1 do nível + recursa arrays com seus counts."""
    for obj in instances:
        _emit_object_row(obj, children, prefix, cols)


def _emit_object_row(obj: dict, children: list, prefix: tuple, cols: dict):
    for node in children:
        p = prefix + (node[1],)
        if node[0] == "scalar":
            cols[(p, "scalar")].append(str(obj[node[1]]))
        elif node[0] == "object":
            _emit_object_row(obj[node[1]], node[2], p, cols)      # inline (1:1)
        elif node[0] == "arr_scalars":
            arr = obj[node[1]]
            cols[(p, "count")].append(str(len(arr)))
            for e in arr:
                cols[(p, "arr_scalars")].append(str(e))
        else:  # arr_objects
            arr = obj[node[1]]
            cols[(p, "count")].append(str(len(arr)))
            _emit_array(arr, node[2], p, cols)                    # bloco filho


# ============================================================ header
def _build_meta(schema: list, bodies: dict, *, last_omits=True, omit_closes=True) -> str:
    order = leaves(schema)
    last = order[-1]

    def sz(path, kind):
        return "" if (last_omits and (path, kind) == last) else f":{len(bodies[(path, kind)].encode())}"

    def emit(children, prefix):
        parts = []
        for node in children:
            p = prefix + (node[1],)
            if node[0] == "scalar":
                parts.append(f"{node[1]}{sz(p, 'scalar')}")
            elif node[0] == "arr_scalars":
                parts.append(f"{node[1]}#{sz(p, 'count')}[]{sz(p, 'arr_scalars')}")
            elif node[0] == "object":
                parts.append(f"{node[1]}{{{emit(node[2], p)}}}")
            else:
                parts.append(f"{node[1]}#{sz(p, 'count')}[{emit(node[2], p)}]")
        return ",".join(parts)

    meta = emit(schema, ())
    if omit_closes:
        meta = meta.rstrip("]}")
    return meta


def _parse_meta(meta: str):
    """(schema, [(path, kind, size|None) DFS])."""
    order = []
    i, n = 0, len(meta)

    def nm(stop):
        nonlocal i
        j = i
        while i < n and meta[i] not in stop:
            i += 1
        return meta[j:i]

    def size():
        nonlocal i
        if i < n and meta[i] == ":":
            i += 1
            return int(nm(",]}#["))   # `[` para o count `name#:N[`
        return None

    def seq(closer, prefix):
        nonlocal i
        nodes = []
        while i < n and (closer is None or meta[i] != closer):
            while i < n and meta[i] in " ,":
                i += 1
            if i >= n or (closer and meta[i] == closer):
                break
            name = nm(",[]{}:#")
            p = prefix + (name,)
            if i < n and meta[i] == "#":            # array (tem count)
                i += 1
                csize = size()
                order.append((p, "count", csize))
                if i < n and meta[i] == "[":
                    i += 1
                    if i < n and meta[i] == "]":     # array de escalares
                        i += 1
                        order.append((p, "arr_scalars", size()))
                        nodes.append(("arr_scalars", name))
                    elif i >= n or meta[i] == ",":   # `[` omit-closed (escalares, último)
                        order.append((p, "arr_scalars", None))
                        nodes.append(("arr_scalars", name))
                    else:                             # array de objetos
                        kids = seq("]", p)
                        if i < n and meta[i] == "]":
                            i += 1
                        nodes.append(("arr_objects", name, kids))
            elif i < n and meta[i] == "{":          # objeto 1:1
                i += 1
                kids = seq("}", p)
                if i < n and meta[i] == "}":
                    i += 1
                nodes.append(("object", name, kids))
            else:                                    # escalar
                order.append((p, "scalar", size()))
                nodes.append(("scalar", name))
        return nodes

    return seq(None, ()), order


# ============================================================ decode
def decode_h(blob: str) -> list[dict]:
    head, rest = blob.split("\n", 1)
    assert head.startswith(MAGIC + " ")
    schema, order = _parse_meta(head[len(MAGIC) + 1:])
    raw = rest.encode("utf-8")
    cols, off = {}, 0
    for path, kind, size in order:
        body = raw[off:].decode() if size is None else raw[off:off + size].decode()
        if size is not None:
            off += size
        cols[(path, kind)] = tcf_decode(body) if body else []  # body vazio -> coluna vazia
    # cursores por coluna (consumo sequencial guiado pelos counts)
    cur = {key: 0 for key in cols}
    # nº de raízes = tamanho da 1ª coluna do bloco raiz (DFS-first leaf)
    fp, fk = leaves(schema)[0][0], leaves(schema)[0][1]
    total = len(cols[(fp, fk)])
    out = []
    for _ in range(total):
        out.append(_read_object(schema, (), cols, cur))
    return out


def _read_object(children: list, prefix: tuple, cols: dict, cur: dict) -> dict:
    obj = {}
    for node in children:
        p = prefix + (node[1],)
        if node[0] == "scalar":
            obj[node[1]] = _take(cols, cur, (p, "scalar"))
        elif node[0] == "object":
            obj[node[1]] = _read_object(node[2], p, cols, cur)
        elif node[0] == "arr_scalars":
            k = int(_take(cols, cur, (p, "count")))
            obj[node[1]] = [_take(cols, cur, (p, "arr_scalars")) for _ in range(k)]
        else:  # arr_objects
            k = int(_take(cols, cur, (p, "count")))
            obj[node[1]] = [_read_object(node[2], p, cols, cur) for _ in range(k)]
    return obj


def _take(cols: dict, cur: dict, key):
    v = cols[key][cur[key]]
    cur[key] += 1
    return v

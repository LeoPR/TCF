"""TCF.8H — codec hierárquico (weld T-CODE-TCF8H-WELD, ADR-0031).

Camada L2 (RELACIONAMENTO entre colunas) + L3 (OTIMIZAÇÃO) sobre L1 (o compressor
de colunas do core, REUSADO sem mudança). Arquitetura em 3 camadas do owner
(2026-07-14, `experiments/lab/dirty/notas/tcf-camadas-arquitetura.md`):

  L1  compressor de colunas  -> `encode(list)`/`decode(body)` do core (INTOCADO).
  L2  relacionamento          -> a topologia da árvore vive no HEADER; só o header
                                 reconstrói o dataset, independente da compressão.
  L3  otimização              -> counts (multiplicidade 1×), última-folha-sem-size,
                                 omit-closes — deduções que economizam bytes.

Modelo: SHREDDING em blocos. A árvore vira colunas agrupadas por bloco (raiz + um
bloco por array). Objetos `{}` (1:1) são inline (colunas do mesmo bloco). Cada array
`[]` (1:N) abre um bloco filho, ligado ao pai por um `#count` explícito (nº de filhos
por instância-pai). Isso fecha os clássicos de transmissão: múltiplas listas irmãs,
arrays aninhados, arrays vazios, e a ambiguidade de chave (count ESCRITO, não deduzido).

Wire (ADR-0031, sem-espaço, LF-only):
  #TCF.8H<meta>\\n<colunas em ordem DFS, encode() cada, fatiadas por size>
    name:size            escalar
    name{...}            objeto 1:1 (inline, mesmo bloco)
    name#:csize[...]     array de objetos (bloco filho; #csize = coluna de counts)
    name#:csize[]:asize  array de escalares (coluna name = elementos; #csize = counts)
    última folha DFS omite size; omit-closes dropa o `]`/`}` final.

Escopo (classe coberta): uma raiz (lista de registros), chaves UNIFORMES por nível,
`{}`/`[]` recursivos. Fora (fail-loud / futuro): objetos ragged (máscara def-level),
N raízes, N:N/snowflake (FK). Tipos = camada ortogonal (tudo string aqui).

Aditivo: `#TCF.8M`/single/órfão intactos. Este módulo é CLIENTE de `encode`/`decode`.
"""
from __future__ import annotations

from tcf.decoder import decode as _decode_col   # L1: decode de 1 coluna (body órfão)
from tcf.encoder import encode as _encode_col    # L1: encode de 1 coluna (lista -> body)

MAGIC = "#TCF.8H"


class HierarchicalError(ValueError):
    """Entrada/blob hierárquico malformado ou fora da classe coberta (fail-loud)."""


# ============================================================ L2: schema (topologia)
# nó: ('scalar', name) | ('object', name, [filhos]) |
#     ('arr_scalars', name) | ('arr_objects', name, [filhos])
def _derive_schema(records: list) -> list:
    """Schema robusto: varre TODOS os registros p/ o tipo de elemento de cada array
    (arrays vazios no 1º registro são comuns). Chaves uniformes por nível."""
    if not records or not isinstance(records[0], dict):
        raise HierarchicalError("hierárquico espera uma lista de objetos (registros)")
    first = records[0]
    return [_field_node(k, [r[k] for r in records if k in r]) for k in first]


def _field_node(name, values: list):
    v0 = values[0]
    if isinstance(v0, dict):
        return ("object", name, _derive_schema([v for v in values if isinstance(v, dict)]))
    if isinstance(v0, list):
        elems = [e for arr in values for e in arr]
        if elems and isinstance(elems[0], dict):
            return ("arr_objects", name, _derive_schema(elems))
        return ("arr_scalars", name)
    return ("scalar", name)


def _leaves(schema: list, prefix=()):
    """[(path, kind)] em ordem DFS. kind: 'scalar' | 'arr_scalars' | 'count'."""
    out = []
    for node in schema:
        p = prefix + (node[1],)
        if node[0] == "scalar":
            out.append((p, "scalar"))
        elif node[0] == "arr_scalars":
            out.append((p, "count"))
            out.append((p, "arr_scalars"))
        elif node[0] == "object":
            out += _leaves(node[2], p)
        else:  # arr_objects
            out.append((p, "count"))
            out += _leaves(node[2], p)
    return out


# ============================================================ encode (L2 shred + L1)
def encode_hierarchical(records: list) -> str:
    schema = _derive_schema(records)
    cols = {key: [] for key in _leaves(schema)}
    _emit_array(records, schema, (), cols)
    order = _leaves(schema)
    # L1: encode por coluna (o compressor do core). Coluna vazia -> body vazio.
    bodies = {key: (_encode_col(cols[key]) if cols[key] else "") for key in order}
    meta = _build_meta(schema, bodies)
    return f"{MAGIC}{meta}\n" + "".join(bodies[key] for key in order)


def _emit_array(instances: list, children: list, prefix: tuple, cols: dict):
    for obj in instances:
        _emit_row(obj, children, prefix, cols)


def _emit_row(obj: dict, children: list, prefix: tuple, cols: dict):
    if not isinstance(obj, dict):
        raise HierarchicalError(f"esperava objeto em {'/'.join(prefix) or 'raiz'}")
    for node in children:
        p = prefix + (node[1],)
        name = node[1]
        if name not in obj:
            raise HierarchicalError(
                f"campo ausente {p} — objetos ragged (chaves faltando) fora da classe "
                "coberta (precisa de máscara def-level; peça 11)"
            )
        if node[0] == "scalar":
            cols[(p, "scalar")].append(str(obj[name]))
        elif node[0] == "object":
            _emit_row(obj[name], node[2], p, cols)                 # inline (1:1)
        elif node[0] == "arr_scalars":
            arr = obj[name]
            cols[(p, "count")].append(str(len(arr)))
            for e in arr:
                cols[(p, "arr_scalars")].append(str(e))
        else:  # arr_objects
            arr = obj[name]
            cols[(p, "count")].append(str(len(arr)))
            _emit_array(arr, node[2], p, cols)                     # bloco filho


# ============================================================ L3: header (meta)
def _build_meta(schema: list, bodies: dict) -> str:
    order = _leaves(schema)
    last = order[-1]

    def sz(path, kind):  # última folha DFS omite size (L3)
        return "" if (path, kind) == last else f":{len(bodies[(path, kind)].encode())}"

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

    return emit(schema, ()).rstrip("]}")   # omit-closes (L3)


def _parse_meta(meta: str):
    order, i, n = [], 0, len(meta)

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
            tok = nm(",]}#[")
            try:
                return int(tok)
            except ValueError:
                raise HierarchicalError(f"size/count invalido no header: {tok!r}")
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
            if i < n and meta[i] == "#":                 # array (com count)
                i += 1
                order.append((p, "count", size()))
                if i < n and meta[i] == "[":
                    i += 1
                    if i < n and meta[i] == "]":          # array de escalares
                        i += 1
                        order.append((p, "arr_scalars", size()))
                        nodes.append(("arr_scalars", name))
                    elif i >= n or meta[i] == ",":        # `[` omit-closed
                        order.append((p, "arr_scalars", None))
                        nodes.append(("arr_scalars", name))
                    else:                                  # array de objetos
                        kids = seq("]", p)
                        if i < n and meta[i] == "]":
                            i += 1
                        nodes.append(("arr_objects", name, kids))
                else:
                    raise HierarchicalError(f"esperava '[' após '#' em {p}")
            elif i < n and meta[i] == "{":               # objeto 1:1
                i += 1
                kids = seq("}", p)
                if i < n and meta[i] == "}":
                    i += 1
                nodes.append(("object", name, kids))
            else:                                         # escalar
                order.append((p, "scalar", size()))
                nodes.append(("scalar", name))
        return nodes

    return seq(None, ()), order


# ============================================================ decode (L1 + L2 rebuild)
def decode_hierarchical(tcf_text: str) -> list:
    if not tcf_text.startswith(MAGIC):
        raise HierarchicalError(f"magic inesperado (esperava {MAGIC})")
    line1 = tcf_text.split("\n", 1)[0]
    schema, order = _parse_meta(line1[len(MAGIC):])
    raw = tcf_text[len(line1) + 1:].encode("utf-8")
    cols, off = {}, 0
    for path, kind, size in order:
        body = raw[off:].decode() if size is None else raw[off:off + size].decode()
        if size is not None:
            off += size
        cols[(path, kind)] = _decode_col(body) if body else []   # L1: decode de coluna
    cur = {key: 0 for key in cols}
    fp, fk = order[0][0], order[0][1]
    total = len(cols[(fp, fk)])
    return [_read_object(schema, (), cols, cur) for _ in range(total)]


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

"""TCF.8H fortificado — hierarquia recursiva por cardinalidade (sem tipos/nulos).

Base: o tabelão do lab 2026-07-13-2301 (hierarquia = tabela denormalizada, pai
repete, RLE `*N|pai` = multiplicidade, motor multi-col real). Aqui FORTIFICA:

  - `{}` objeto 1:1 (recursivo)  — campos viram colunas-pai (repetem no tabelão)
  - `[]` array 1:N (recursivo)   — expande linhas; pai repete por filho
  - aninhamento arbitrário {} dentro de [] dentro de {} ...
  - chaveamento por CAMINHO (corrige o bug de nome-repetido do lab 1830)

Cardinalidades (estudo de dimensionalidade, mapa da peça 7):
  1:1  -> `{}` objeto aninhado (nativo/retangular)
  1:N  -> `[]` array (hierarquia; dual do RLE)          <- os dois que ANINHAM
  N:1  -> coluna low-card compartilhada (@dict do motor) <- aparece como coluna, não ramo
  N:N  -> tabela-ponte; NÃO vira árvore simples          <- fail-loud (>1 array por nível)

Gramática do header (contrato consagrado 1830/EXP-015/ADR-0031):
  #TCF.8H <meta>\\n<bodies-por-coluna-DFS-concatenados>
  meta (recursivo, itens `,`):
    name:size          folha escalar (bytes-incl-LF decimais)
    name{ ...itens... } objeto 1:1
    name[ ...itens... ] array de OBJETOS 1:N
    name[]:size         array de ESCALARES 1:N (coluna = name)
  Consagrados (opt, default-on): ÚLTIMA folha DFS omite size; omit-closes dropa o
  run final de `]`/`}`.

RT-alvo: decode(encode(records)) == records. Zero src/tcf (read-only encode/decode).
"""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(_ROOT / "src"))
from tcf import decode as tcf_decode, encode as tcf_encode  # noqa: E402

MAGIC = "#TCF.8H"


class NNError(ValueError):
    """>1 array por nível = N:N; não vira árvore simples (precisa ponte)."""


class AmbiguityError(ValueError):
    """Instâncias irmãs de mesma CHAVE que abrigam array aninhado → a re-nestação por
    chave contígua as fundiria (limite FD/chave da peça 7; precisa de fronteira/rep-level).
    encode se recusa a produzir um blob que NÃO reverte — nunca corromper calado."""


# ============================================================ schema
# nó: ('scalar', name) | ('object', name, [filhos]) | ('arr_scalars', name)
#     | ('arr_objects', name, [filhos])
def derive_schema(record: dict) -> list:
    return [_node(k, v) for k, v in record.items()]


def _node(name, v):
    if isinstance(v, dict):
        return ("object", name, [_node(k, x) for k, x in v.items()])
    if isinstance(v, list):
        if v and isinstance(v[0], dict):
            return ("arr_objects", name, [_node(k, x) for k, x in v[0].items()])
        return ("arr_scalars", name)
    return ("scalar", name)


def _check_one_array(children: list, where: str):
    arrs = [c for c in children if c[0] in ("arr_scalars", "arr_objects")]
    if len(arrs) > 1:
        raise NNError(
            f"{where}: {len(arrs)} arrays no mesmo nível ({[a[1] for a in arrs]}) = N:N "
            f"(produto cartesiano semanticamente errado); use tabela-ponte / dois 1:N."
        )


# ============================================================ folhas (DFS, por caminho)
def leaves(schema: list, prefix=()) -> list[tuple]:
    """[(path, kind)] em ordem DFS. kind: 'scalar' | 'arr_scalars' | 'obj_field'."""
    out = []
    for node in schema:
        p = prefix + (node[1],)
        if node[0] == "scalar":
            out.append((p, "scalar"))
        elif node[0] == "arr_scalars":
            out.append((p, "arr_scalars"))
        elif node[0] == "object":
            out += leaves(node[2], p)
        else:  # arr_objects
            out += leaves(node[2], p)
    return out


# ============================================================ denormalizar (tabelão)
def denormalize(records: list[dict], schema: list) -> dict:
    cols = {path: [] for path, _ in leaves(schema)}
    for rec in records:
        for row in _expand_object(rec, schema, ()):
            for path in cols:
                cols[path].append(row[path])
    return cols


def _expand_object(obj: dict, children: list, prefix: tuple) -> list[dict]:
    """Linhas (dict path->str) de um OBJETO: escalares/1:1 fixos × o (único) array."""
    _check_one_array(children, "/".join(prefix) or "raiz")
    base, array = {}, None
    for node in children:
        p = prefix + (node[1],)
        if node[0] == "scalar":
            base[p] = str(obj[node[1]])
        elif node[0] == "object":
            sub = _expand_object(obj[node[1]], node[2], p)
            assert len(sub) == 1, f"objeto 1:1 {p} contém array (não é 1:1)"
            base.update(sub[0])
        else:
            array = node
    if array is None:
        return [base]
    p = prefix + (array[1],)
    rows = []
    for elem in obj[array[1]]:
        if array[0] == "arr_scalars":
            r = dict(base); r[p] = str(elem); rows.append(r)
        else:
            for sub in _expand_object(elem, array[2], p):
                r = dict(base); r.update(sub); rows.append(r)
    if not rows:
        raise ValueError(f"array vazio em {p} — protótipo exige >=1 elemento (extensão)")
    return rows


# ============================================================ header
def build_meta(schema: list, bodies: dict, *, last_omits=True, omit_closes=True) -> str:
    order = [p for p, _ in leaves(schema)]
    last = order[-1]

    def sz(path):
        return "" if (last_omits and path == last) else f":{len(bodies[path].encode())}"

    def emit(children, prefix):
        parts = []
        for node in children:
            p = prefix + (node[1],)
            if node[0] == "scalar":
                parts.append(f"{node[1]}{sz(p)}")
            elif node[0] == "arr_scalars":
                parts.append(f"{node[1]}[]{sz(p)}")
            elif node[0] == "object":
                parts.append(f"{node[1]}{{{emit(node[2], p)}}}")
            else:
                parts.append(f"{node[1]}[{emit(node[2], p)}]")
        return ",".join(parts)

    meta = emit(schema, ())
    if omit_closes:
        meta = meta.rstrip("]}")
    return meta


def _parse_meta(meta: str):
    """(schema, [(path, size|None) DFS]). Tolera último-sem-size + omit-closes."""
    order = []
    i, n = 0, len(meta)

    def name(stop):
        nonlocal i
        j = i
        while i < n and meta[i] not in stop:
            i += 1
        return meta[j:i]

    def size():
        nonlocal i
        if i < n and meta[i] == ":":
            i += 1
            return int(name(",]}"))
        return None

    def seq(closer, prefix):
        nonlocal i
        nodes = []
        while i < n and (closer is None or meta[i] != closer):
            while i < n and meta[i] in " ,":
                i += 1
            if i >= n or (closer and meta[i] == closer):
                break
            nm = name(",[]{}:")
            p = prefix + (nm,)
            if i < n and meta[i] == "{":                # objeto 1:1
                i += 1
                kids = seq("}", p)
                if i < n and meta[i] == "}":
                    i += 1
                nodes.append(("object", nm, kids))
            elif i < n and meta[i] == "[":              # array
                i += 1
                if i < n and meta[i] == "]":            # array de escalares
                    i += 1
                    order.append((p, size()))
                    nodes.append(("arr_scalars", nm))
                elif i >= n or meta[i] == ",":          # `[` omit-closed = escalares, último
                    order.append((p, None))
                    nodes.append(("arr_scalars", nm))
                else:                                    # array de objetos
                    kids = seq("]", p)
                    if i < n and meta[i] == "]":
                        i += 1
                    nodes.append(("arr_objects", nm, kids))
            else:                                        # escalar
                order.append((p, size()))
                nodes.append(("scalar", nm))
        return nodes

    schema = seq(None, ())
    return schema, order


# ============================================================ encode / decode
def encode_h(records: list[dict], *, _verify=True, **kw) -> str:
    schema = derive_schema(records[0])
    cols = denormalize(records, schema)
    order = [p for p, _ in leaves(schema)]
    bodies = {p: tcf_encode(cols[p]) for p in order}
    meta = build_meta(schema, bodies, **kw)
    blob = f"{MAGIC} {meta}\n" + "".join(bodies[p] for p in order)
    if _verify and decode_h(blob) != records:
        raise AmbiguityError(
            "este documento não reverte com a re-nestação por chave contígua: há "
            "instâncias irmãs de mesma chave abrigando array aninhado (fusão). "
            "Precisa de fronteira/repetition-level (peça 9) — encode recusa em vez de corromper."
        )
    return blob


def decode_h(blob: str) -> list[dict]:
    head, rest = blob.split("\n", 1)
    assert head.startswith(MAGIC + " ")
    schema, order = _parse_meta(head[len(MAGIC) + 1:])
    raw = rest.encode("utf-8")
    cols, off = {}, 0
    for path, size in order:
        body = raw[off:].decode() if size is None else raw[off:off + size].decode()
        if size is not None:
            off += size
        cols[path] = tcf_decode(body)
    n = len(next(iter(cols.values())))
    return _renest_array(schema, cols, 0, n, ())


# ============================================================ re-aninhar (recursivo)
def _own_key_paths(children: list, prefix: tuple) -> list[tuple]:
    """Colunas-chave DESTE nível (escalares + 1:1), excluindo arrays mais fundos —
    servem pra agrupar as linhas contíguas de uma mesma instância."""
    out = []
    for node in children:
        p = prefix + (node[1],)
        if node[0] == "scalar":
            out.append(p)
        elif node[0] == "object":
            out += _own_key_paths(node[2], p)
    return out


def _has_array(children: list) -> bool:
    for node in children:
        if node[0] in ("arr_scalars", "arr_objects"):
            return True
        if node[0] == "object" and _has_array(node[2]):
            return True
    return False


def _renest_array(children: list, cols: dict, lo: int, hi: int, prefix: tuple) -> list:
    """[lo,hi) = as linhas de UM array (lista de instâncias irmãs)."""
    if not _has_array(children):
        # elemento FOLHA (sem array aninhado): 1 linha = 1 elemento (preserva duplicatas)
        return [_renest_object(children, cols, i, i + 1, prefix) for i in range(lo, hi)]
    # elemento com array aninhado: agrupa por chave própria de nível (assume chave
    # distinta por instância — a ambiguidade FD/chave que a peça 7 registrou).
    keys = _own_key_paths(children, prefix)
    out, i = [], lo
    while i < hi:
        kv = tuple(cols[k][i] for k in keys)
        j = i
        while j < hi and tuple(cols[k][j] for k in keys) == kv:
            j += 1
        out.append(_renest_object(children, cols, i, j, prefix))
        i = j
    return out


def _renest_object(children: list, cols: dict, lo: int, hi: int, prefix: tuple) -> dict:
    obj = {}
    for node in children:
        p = prefix + (node[1],)
        if node[0] == "scalar":
            obj[node[1]] = cols[p][lo]
        elif node[0] == "object":
            obj[node[1]] = _renest_object(node[2], cols, lo, hi, p)
        elif node[0] == "arr_scalars":
            obj[node[1]] = [cols[p][k] for k in range(lo, hi)]
        else:  # arr_objects: sub-agrupa [lo,hi) pela chave do elemento
            obj[node[1]] = _renest_array(node[2], cols, lo, hi, p)
    return obj

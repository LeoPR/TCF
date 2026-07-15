r"""PROTÓTIPO P1 — presença/ragged (def-level) integrada à gramática do #TCF.8H weldado.

NÃO toca src/tcf. Extrai a IDEIA do lab 2246 (máscara por célula + corpo denso) e a integra
ao modelo de SHREDDING do weld (ADR-0033): a máscara vira uma COLUNA DE CONTROLE — como o
`#count` — comprimida pelo L1 (RLE colapsa runs de `.`).

GRAMÁTICA proposta (extensão mínima; campos uniformes NÃO mudam — byte-idêntico ao weld):
    name:size                escalar obrigatório           (weld atual, inalterado)
    name?:msize:size         escalar OPCIONAL              (msize = coluna-máscara)
    name?:msize{...}         objeto OPCIONAL
    name?:msize#:csize[...]  array OPCIONAL (mask distingue AUSENTE de vazio; count só p/ presentes)
O `?` cola no nome (antes do `:msize`); vira char estrutural → entra no escape (`\?`).

MÁSCARA (alfabeto 3-estados, wire reservado pra não soldar duas vezes):
    '.' = presente   ·   '-' = ausente   ·   '0' = RESERVADO null (P3; decode fail-loud por ora)
Uma entrada por INSTÂNCIA do nível (não por registro-raiz): opcional dentro de array tem
uma entrada por ELEMENTO. Colunas de dado/children só carregam as instâncias PRESENTES (denso).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))
from tcf.decoder import decode as _decode_col  # L1 (reusado read-only)
from tcf.encoder import encode as _encode_col

MAGIC = "#TCF.8H"


class P1Error(ValueError):
    pass


# escaping: MESMA convenção do weld (40a7e10) + '?' agora estrutural
_SEP = ",[]{}:#?\\"
_ESC_OK = _SEP + " "


def _esc(name: str) -> str:
    if not name:
        raise P1Error("nome vazio")
    if "\n" in name:
        raise P1Error("nome com \\n")
    s = "".join(("\\" + c if c in _SEP else c) for c in name)
    return "\\" + s if s[0] == " " else s


def _unesc(s: str) -> str:
    out, i, n = [], 0, len(s)
    while i < n:
        if s[i] == "\\":
            if i + 1 >= n or s[i + 1] not in _ESC_OK:
                raise P1Error(f"escape invalido no nome {s!r}")
            out.append(s[i + 1]); i += 2
        else:
            out.append(s[i]); i += 1
    return "".join(out)


# ---------------------------------------------------------------- schema (L2)
# nó: (kind, name, optional, children)  ·  kind: scalar|object|arr_objects|arr_scalars
def derive_schema(records: list) -> list:
    if not records or not isinstance(records[0], dict):
        raise P1Error("esperava lista de objetos")
    keys = []                                   # união de chaves, ordem de 1ª aparição
    for r in records:
        for k in r:
            if k not in keys:
                keys.append(k)
    out = []
    for k in keys:
        present = [r[k] for r in records if k in r]
        optional = len(present) < len(records)
        v0 = present[0]
        if isinstance(v0, dict):
            out.append(("object", k, optional, derive_schema([v for v in present if isinstance(v, dict)])))
        elif isinstance(v0, list):
            elems = [e for arr in present for e in arr]
            if elems and isinstance(elems[0], dict):
                out.append(("arr_objects", k, optional, derive_schema(elems)))
            else:
                out.append(("arr_scalars", k, optional, None))
        else:
            out.append(("scalar", k, optional, None))
    return out


def _leaves(schema, prefix=()):
    """[(path, kind)] em ordem DFS. Máscara vem ANTES das colunas do campo (como count)."""
    cols = []
    for kind, name, opt, kids in schema:
        p = prefix + (name,)
        if opt:
            cols.append((p, "mask"))
        if kind == "scalar":
            cols.append((p, "scalar"))
        elif kind == "arr_scalars":
            cols.append((p, "count"))
            cols.append((p, "arr_scalars"))
        elif kind == "object":
            cols += _leaves(kids, p)
        else:
            cols.append((p, "count"))
            cols += _leaves(kids, p)
    return cols


# ---------------------------------------------------------------- encode
def encode_h(records: list) -> str:
    schema = derive_schema(records)
    cols = {key: [] for key in _leaves(schema)}
    for rec in records:
        _emit_row(rec, schema, (), cols)
    order = _leaves(schema)
    bodies = {k: (_encode_col(cols[k]) if cols[k] else "") for k in order}
    return f"{MAGIC}{_meta(schema, bodies, order)}\n" + "".join(bodies[k] for k in order)


def _emit_row(obj, schema, prefix, cols):
    if not isinstance(obj, dict):
        raise P1Error(f"esperava objeto em {'/'.join(prefix) or 'raiz'}")
    known = {name for _, name, _, _ in schema}
    extra = set(obj) - known
    if extra:
        raise P1Error(f"chave fora do schema em {'/'.join(prefix) or 'raiz'}: {sorted(extra)}")
    for kind, name, opt, kids in schema:
        p = prefix + (name,)
        if name not in obj:
            if not opt:
                raise P1Error(f"campo obrigatorio ausente: {p}")
            cols[(p, "mask")].append("-")
            continue                                   # ausente: NADA nas colunas de dado
        if obj[name] is None:
            raise P1Error(f"null em {p} — P3 (null) nao implementado; P1 e' presenca")
        if opt:
            cols[(p, "mask")].append(".")
        v = obj[name]
        if kind == "scalar":
            cols[(p, "scalar")].append(str(v))
        elif kind == "object":
            _emit_row(v, kids, p, cols)
        elif kind == "arr_scalars":
            cols[(p, "count")].append(str(len(v)))
            for e in v:
                cols[(p, "arr_scalars")].append(str(e))
        else:
            cols[(p, "count")].append(str(len(v)))
            for e in v:
                _emit_row(e, kids, p, cols)


# ---------------------------------------------------------------- meta
def _meta(schema, bodies, order):
    last = order[-1]

    def sz(p, kind):
        return "" if (p, kind) == last else f":{len(bodies[(p, kind)].encode())}"

    def emit(children, prefix):
        parts = []
        for kind, name, opt, kids in children:
            p = prefix + (name,)
            head = _esc(name) + (f"?{sz(p, 'mask')}" if opt else "")
            if kind == "scalar":
                parts.append(f"{head}{sz(p, 'scalar')}")
            elif kind == "arr_scalars":
                parts.append(f"{head}#{sz(p, 'count')}[]{sz(p, 'arr_scalars')}")
            elif kind == "object":
                parts.append(f"{head}{{{emit(kids, p)}}}")
            else:
                parts.append(f"{head}#{sz(p, 'count')}[{emit(kids, p)}]")
        return ",".join(parts)

    return _rstrip_closes(emit(schema, ()))


def _rstrip_closes(s):
    end = len(s)
    while end > 0 and s[end - 1] in "]}":
        k, nb = end - 1, 0
        while k > 0 and s[k - 1] == "\\":
            nb += 1; k -= 1
        if nb % 2 == 1:
            break
        end -= 1
    return s[:end]


def _parse_meta(meta):
    order, i, n = [], 0, len(meta)

    def nm(stop):
        nonlocal i
        j = i
        while i < n:
            if meta[i] == "\\" and i + 1 < n:
                i += 2; continue
            if meta[i] in stop:
                break
            i += 1
        return meta[j:i]

    def size():
        nonlocal i
        if i < n and meta[i] == ":":
            i += 1
            tok = nm(",]}#[?:{")   # ':' e '{' param o token (msize pode preceder :size ou {...})
            try:
                return int(tok)
            except ValueError:
                raise P1Error(f"size invalido: {tok!r}")
        return None

    def seq(closer, prefix):
        nonlocal i
        nodes = []
        while i < n and (closer is None or meta[i] != closer):
            while i < n and meta[i] in " ,":
                i += 1
            if i >= n or (closer and meta[i] == closer):
                break
            name = _unesc(nm(",[]{}:#?"))
            p = prefix + (name,)
            opt = False
            if i < n and meta[i] == "?":                       # campo OPCIONAL
                opt = True
                i += 1
                order.append((p, "mask", size()))
            if i < n and meta[i] == "#":
                i += 1
                order.append((p, "count", size()))
                if i < n and meta[i] == "[":
                    i += 1
                    if i < n and meta[i] == "]":
                        i += 1
                        order.append((p, "arr_scalars", size()))
                        nodes.append(("arr_scalars", name, opt, None))
                    elif i >= n or meta[i] == ",":
                        order.append((p, "arr_scalars", None))
                        nodes.append(("arr_scalars", name, opt, None))
                    else:
                        kids = seq("]", p)
                        if i < n and meta[i] == "]":
                            i += 1
                        nodes.append(("arr_objects", name, opt, kids))
                else:
                    raise P1Error(f"esperava '[' apos '#' em {p}")
            elif i < n and meta[i] == "{":
                i += 1
                kids = seq("}", p)
                if i < n and meta[i] == "}":
                    i += 1
                nodes.append(("object", name, opt, kids))
            else:
                order.append((p, "scalar", size()))
                nodes.append(("scalar", name, opt, None))
        return nodes

    return seq(None, ()), order


# ---------------------------------------------------------------- decode
def decode_h(text: str) -> list:
    if not text.startswith(MAGIC):
        raise P1Error("magic inesperado")
    line1 = text.split("\n", 1)[0]
    schema, order = _parse_meta(line1[len(MAGIC):])
    raw = text[len(line1) + 1:].encode("utf-8")
    cols, off = {}, 0
    for p, kind, size in order:
        body = raw[off:].decode() if size is None else raw[off:off + size].decode()
        if size is not None:
            off += size
        cols[(p, kind)] = _decode_col(body) if body else []
    cur = {k: 0 for k in cols}
    p0, k0 = order[0][0], order[0][1]
    total = len(cols[(p0, k0)])
    return [_read(schema, (), cols, cur) for _ in range(total)]


def _read(schema, prefix, cols, cur):
    obj = {}
    for kind, name, opt, kids in schema:
        p = prefix + (name,)
        if opt:
            m = _take(cols, cur, (p, "mask"))
            if m == "-":
                continue                                   # chave OMITIDA (ausente)
            if m == "0":
                raise P1Error(f"mask '0' (null) em {p} — reservado P3, nao implementado")
            if m != ".":
                raise P1Error(f"mask invalida {m!r} em {p}")
        if kind == "scalar":
            obj[name] = _take(cols, cur, (p, "scalar"))
        elif kind == "object":
            obj[name] = _read(kids, p, cols, cur)
        elif kind == "arr_scalars":
            k = int(_take(cols, cur, (p, "count")))
            obj[name] = [_take(cols, cur, (p, "arr_scalars")) for _ in range(k)]
        else:
            k = int(_take(cols, cur, (p, "count")))
            obj[name] = [_read(kids, p, cols, cur) for _ in range(k)]
    return obj


def _take(cols, cur, key):
    v = cols[key][cur[key]]
    cur[key] += 1
    return v

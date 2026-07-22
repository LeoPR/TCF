"""PROTÓTIPO P4a — array-em-array via COUNT RECURSIVO. Extrai a IDEIA; não copia o core.

Tese (levantamento + parecer do owner): o repetition-level do Dremel colapsa, no TCF, em
COUNTS POR NÍVEL — um array cujo ELEMENTO é um array reusa o mesmo mecanismo count→elementos,
recursivamente. Cada nível de aninhamento = uma coluna de counts própria (+ emask se houver null
naquele nível). Mantém a separabilidade O(1)/stream (Ciclo 4): a ESTRUTURA (contagens por nível)
é legível sem materializar as folhas.

Modelo de ELEMENTO (spec recursiva):
    ('scalar', stype)            elemento escalar (string/number/bool — P2)
    ('object', kids)             elemento objeto (kids = schema de campos)
    ('array', elem, elem_null)   elemento ARRAY (P4a!) — elem = spec do nível interno,
                                 elem_null = há null ENTRE os elementos desse nível interno

Colunas de um campo-array (path p), em ordem DFS por nível:
    (p,'count',0) [, (p,'emask',0)] , (p,'count',1) [, (p,'emask',1)] , ... , folhas
    counts do nível k+1 têm UMA entrada por elemento NÃO-null do nível k (denso).

Gramática demonstrada (meta_str): campo#[#[]] — cada '#' abre um nível de array; '?' após o '#'
do nível = element-mask daquele nível (null entre elementos). No weld os sizes entram como hoje.
Serialização simples (colunas em listas) p/ provar RT + invariantes; NÃO é o wire final."""
from __future__ import annotations

import json
import math


class P4Error(ValueError):
    pass


# ---------------- deducao da spec de ELEMENTO (recursiva) ----------------
def _stype_of(vals):
    ts = set()
    for v in vals:
        if isinstance(v, bool):
            ts.add("b")
        elif isinstance(v, (int, float)):
            if isinstance(v, float) and not math.isfinite(v):
                raise P4Error("NaN/Inf fora do JSON")
            ts.add("n")
        elif isinstance(v, str):
            ts.add("s")
        else:
            raise P4Error(f"escalar não suportado: {type(v).__name__}")
    if len(ts) > 1:
        raise P4Error(f"tipos escalares mistos {ts} (P5)")
    return ts.pop() if ts else "s"


def elem_spec(elems):
    """spec do ELEMENTO a partir dos elementos NÃO-null de um nível."""
    kinds = set()
    for e in elems:
        if isinstance(e, list):
            kinds.add("array")
        elif isinstance(e, dict):
            kinds.add("object")
        else:
            kinds.add("scalar")
    if len(kinds) > 1:
        raise P4Error(f"elementos de tipos mistos {kinds} (P5)")
    if not kinds or kinds == {"scalar"}:
        return ("scalar", _stype_of(elems))
    if kinds == {"object"}:
        return ("object", derive_fields(elems))
    # array: descer um nível — junta os sub-elementos de todos
    subs = [x for e in elems for x in e]
    elem_null = any(x is None for x in subs)
    subs_nn = [x for x in subs if x is not None]
    return ("array", elem_spec(subs_nn), elem_null)


def derive_fields(records):
    keys = []
    for r in records:
        for k in r:
            if k not in keys:
                keys.append(k)
    out = []
    for k in keys:
        present = [r[k] for r in records if k in r]
        pnn = [v for v in present if v is not None]
        masked = (len(present) < len(records)) or (len(pnn) < len(present))
        if pnn and isinstance(pnn[0], list):
            elems = [x for arr in pnn for x in arr]
            e_null = any(x is None for x in elems)
            spec = ("array", elem_spec([x for x in elems if x is not None]), e_null)
        elif pnn and isinstance(pnn[0], dict):
            spec = ("object", derive_fields(pnn))
        else:
            spec = ("scalar", _stype_of(pnn))
        out.append((k, masked, spec))
    return out


# ---------------- encode (shred recursivo) ----------------
def _enc_scalar(v, st):
    if st == "n":
        return json.dumps(v)
    if st == "b":
        return "true" if v else "false"
    return str(v)


def emit_array(arr, spec, elem_null, cols, p, level):
    """arr = lista de elementos deste nível; emite count, emask (se houver) e desce."""
    cols.setdefault((p, "count", level), []).append(len(arr))
    for e in arr:
        if e is None:
            if not elem_null:
                raise P4Error("null inesperado")
            cols.setdefault((p, "emask", level), []).append("0")
            continue
        if elem_null:
            cols.setdefault((p, "emask", level), []).append(".")
        emit_elem(e, spec, cols, p, level)


def emit_elem(e, spec, cols, p, level):
    kind = spec[0]
    if kind == "scalar":
        cols.setdefault((p, "leaf"), []).append(_enc_scalar(e, spec[1]))
    elif kind == "object":
        emit_obj(e, spec[1], cols, p)
    else:  # array: nível interno
        emit_array(e, spec[1], spec[2], cols, p, level + 1)


def emit_obj(obj, fields, cols, prefix):
    for name, masked, spec in fields:
        p = prefix + (name,)
        if name not in obj:
            cols.setdefault((p, "mask"), []).append("-")
            continue
        v = obj[name]
        if v is None:
            cols.setdefault((p, "mask"), []).append("0")
            continue
        if masked:
            cols.setdefault((p, "mask"), []).append(".")
        if spec[0] == "array":
            emit_array(v, spec[1], spec[2], cols, p, 0)
        elif spec[0] == "object":
            emit_obj(v, spec[1], cols, p)
        else:
            cols.setdefault((p, "leaf"), []).append(_enc_scalar(v, spec[1]))


def encode(records):
    fields = derive_fields(records)
    cols = {}
    for r in records:
        emit_obj(r, fields, cols, ())
    return fields, cols, len(records)


# ---------------- decode (rebuild recursivo) ----------------
def _dec_scalar(s, st):
    if st == "n":
        return json.loads(s)
    if st == "b":
        return {"true": True, "false": False}[s]
    return s


def read_array(spec, elem_null, cols, cur, p, level):
    k = _take(cols, cur, (p, "count", level))
    out = []
    for _ in range(k):
        if elem_null:
            m = _take(cols, cur, (p, "emask", level))
            if m == "0":
                out.append(None)
                continue
        out.append(read_elem(spec, cols, cur, p, level))
    return out


def read_elem(spec, cols, cur, p, level):
    kind = spec[0]
    if kind == "scalar":
        return _dec_scalar(_take(cols, cur, (p, "leaf")), spec[1])
    if kind == "object":
        return read_obj(spec[1], cols, cur, p)
    return read_array(spec[1], spec[2], cols, cur, p, level + 1)


def read_obj(fields, cols, cur, prefix):
    obj = {}
    for name, masked, spec in fields:
        p = prefix + (name,)
        if masked:
            m = _take(cols, cur, (p, "mask"))
            if m == "-":
                continue
            if m == "0":
                obj[name] = None
                continue
        if spec[0] == "array":
            obj[name] = read_array(spec[1], spec[2], cols, cur, p, 0)
        elif spec[0] == "object":
            obj[name] = read_obj(spec[1], cols, cur, p)
        else:
            obj[name] = _dec_scalar(_take(cols, cur, (p, "leaf")), spec[1])
    return obj


def _take(cols, cur, key):
    lst = cols.get(key, [])
    idx = cur.get(key, 0)
    if idx >= len(lst):
        raise P4Error(f"coluna {key} exaurida — frame inconsistente")
    cur[key] = idx + 1
    return lst[idx]


def decode(fields, cols, n):
    cur = {}
    out = [read_obj(fields, cols, cur, ()) for _ in range(n)]
    for key, lst in cols.items():                    # exaustão (o invariante do weld)
        if cur.get(key, 0) != len(lst):
            raise P4Error(f"coluna {key} não exaurida")
    return out


# ---------------- meta inspecionável (a gramática por nível) ----------------
def meta_str(fields):
    def spec_str(spec, masked_mark=""):
        kind = spec[0]
        if kind == "scalar":
            return "" if spec[1] == "s" else spec[1]
        if kind == "object":
            return "{" + fields_str(spec[1]) + "}"
        inner = spec_str(spec[1])
        q = "?" if spec[2] else ""
        if spec[1][0] == "array":
            return f"#{q}[{inner}]"
        if spec[1][0] == "object":
            return f"#{q}[{fields_str(spec[1][1])}]"
        return f"#{q}[]{inner}"

    def fields_str(fs):
        parts = []
        for name, masked, spec in fs:
            head = name + ("?" if masked else "")
            if spec[0] == "array":
                q = "?" if spec[2] else ""
                inner = spec[1]
                if inner[0] == "array":
                    parts.append(f"{head}#{q}[{spec_str(inner)}]")
                elif inner[0] == "object":
                    parts.append(f"{head}#{q}[{fields_str(inner[1])}]")
                else:
                    t = "" if inner[1] == "s" else inner[1]
                    parts.append(f"{head}#{q}[]{t}")
            elif spec[0] == "object":
                parts.append(f"{head}{{{fields_str(spec[1])}}}")
            else:
                t = "" if spec[1] == "s" else spec[1]
                parts.append(f"{head}{t}")
        return ",".join(parts)

    return fields_str(fields)

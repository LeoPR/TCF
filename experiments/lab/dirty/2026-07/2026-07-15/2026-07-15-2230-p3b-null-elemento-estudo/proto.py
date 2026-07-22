"""PROTÓTIPO P3b — null em ELEMENTO de array (element-mask). Extrai a IDEIA, não copia o core.

Valida o design ANTES de tocar src/tcf: máscara alinhada aos ELEMENTOS (não às instâncias do
campo, como P1/P3a). Alfabeto 2-estados: '.'=valor · '0'=null (SEM '-' — a posição existe via count).
Ordem das colunas de um array element-nullable: count → EMASK → elementos densos (só '.').

Gramática demonstrada no meta: `nome#?[...]` (o `?` após `#count` = elementos mascarados).
Codec recursivo mínimo (colunas = listas; serialização simples p/ provar RT + inspeção). NÃO é o
wire final (sem L1/escaping/omit-closes) — é prova de CONCEITO do alinhamento count×emask×dense."""
from __future__ import annotations

import json

NULLE = object()   # sentinela p/ elemento null (interno; nunca é string real)


# ---- schema: (kind, name, kids, elem_null) ; kind: scalar|arr_scalars|arr_objects
def derive(records):
    keys = []
    for r in records:
        for k in r:
            if k not in keys:
                keys.append(k)
    out = []
    for k in keys:
        vals = [r[k] for r in records if k in r]
        v0 = vals[0]
        if isinstance(v0, list):
            elems = [e for arr in vals for e in arr]
            elem_null = any(e is None for e in elems)
            nn = [e for e in elems if e is not None]
            if nn and isinstance(nn[0], dict):
                out.append(("arr_objects", k, derive(nn), elem_null))
            else:
                out.append(("arr_scalars", k, None, elem_null))
        else:
            out.append(("scalar", k, None, False))
    return out


def _emit(records, schema, cols, prefix=()):
    for kind, name, kids, elem_null in schema:
        p = prefix + (name,)
        if kind == "scalar":
            cols.setdefault((p, "val"), [])
            for r in records:
                cols[(p, "val")].append(str(r[name]))
        else:  # array
            cols.setdefault((p, "count"), [])
            if elem_null:
                cols.setdefault((p, "emask"), [])
            for r in records:
                arr = r[name]
                cols[(p, "count")].append(len(arr))
                for e in arr:
                    if elem_null:
                        cols[(p, "emask")].append("0" if e is None else ".")
                    # elementos densos só p/ '.' (não-null)
                if kind == "arr_scalars":
                    cols.setdefault((p, "val"), [])
                    for e in arr:
                        if e is not None:
                            cols[(p, "val")].append(str(e))
                else:  # arr_objects: recursa nos elementos NÃO-null
                    _emit([e for e in arr if e is not None], kids, cols, p)


def encode(records):
    schema = derive(records)
    cols = {}
    _emit(records, schema, cols)
    return schema, cols, len(records)


def _read(schema, cols, cur, n, prefix=()):
    out = [{} for _ in range(n)]
    for kind, name, kids, elem_null in schema:
        p = prefix + (name,)
        if kind == "scalar":
            for i in range(n):
                out[i][name] = cols[(p, "val")][cur[(p, "val")]]; cur[(p, "val")] += 1
        else:
            # 1º descobre, por instância, o nº de elementos e quais são null (via count+emask)
            for i in range(n):
                k = cols[(p, "count")][cur[(p, "count")]]; cur[(p, "count")] += 1
                flags = []
                for _ in range(k):
                    if elem_null:
                        m = cols[(p, "emask")][cur[(p, "emask")]]; cur[(p, "emask")] += 1
                        flags.append(m)
                    else:
                        flags.append(".")
                out[i][name] = flags   # placeholder: preenche abaixo
            if kind == "arr_scalars":
                for i in range(n):
                    arr = []
                    for m in out[i][name]:
                        if m == "0":
                            arr.append(None)
                        else:
                            arr.append(cols[(p, "val")][cur[(p, "val")]]); cur[(p, "val")] += 1
                    out[i][name] = arr
            else:  # arr_objects
                total_nn = sum(1 for i in range(n) for m in out[i][name] if m != "0")
                kids_objs = _read(kids, cols, cur, total_nn, p)
                it = iter(kids_objs)
                for i in range(n):
                    arr = []
                    for m in out[i][name]:
                        arr.append(None if m == "0" else next(it))
                    out[i][name] = arr
    return out


def decode(schema, cols, n):
    cur = {key: 0 for key in cols}
    return _read(schema, cols, cur, n)


# ---- meta inspecionável (demonstra a gramática element-mask) ----
def meta_str(schema):
    parts = []
    for kind, name, kids, elem_null in schema:
        if kind == "scalar":
            parts.append(name)
        elif kind == "arr_scalars":
            parts.append(f"{name}#{'?' if elem_null else ''}[]")
        else:
            parts.append(f"{name}#{'?' if elem_null else ''}[{meta_str(kids)}]")
    return ",".join(parts)

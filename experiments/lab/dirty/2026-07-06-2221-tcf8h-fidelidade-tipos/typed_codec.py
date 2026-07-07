"""typed_codec — dirty fork do TCF.8H com FIDELIDADE DE TIPOS (Ciclo 1a).

Problema (provado): o codec EXP-015 faz str(v) → JSON tipado NÃO faz RT
(30→"30", true→"True", null→"None"). Só é lossless pra JSON all-string.

Ideia naive (string = default, tag só na divergência — mesma filosofia do hex):
 - toda folha string: como antes (sem tag).
 - folha int/float/bool/null: UMA letra de tipo colada no size (i/f/b/n).
 - última-folha-sem-size continua valendo SÓ pra string; folha-última tipada
   mantém o size + letra (mede-se o custo).
 - body em forma JSON-canônica (true/false, não True/False; null = body vazio).

Coluna homogênea (a letra é por-coluna, tirada do 1º valor). Engenhoca
descartável — prova a ideia; não toca EXP-015 clean nem src/tcf.
"""
from __future__ import annotations
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[4]        # .../TCF (experiments/lab/dirty/<lab>/typed_codec.py)
sys.path.insert(0, str(_ROOT / "src"))
from tcf import encode, decode                       # noqa: E402

MAGIC = "#TCF.8H"


# ---- tipo <-> letra + body JSON-canônico (bool ANTES de int: bool é subclasse) ----
def _tletter(v) -> str:
    if isinstance(v, bool):
        return "b"
    if isinstance(v, int):
        return "i"
    if isinstance(v, float):
        return "f"
    if v is None:
        return "n"
    return ""                                        # str = default (sem tag)


def _tbody(v) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if v is None:
        return ""                                    # null: sem dado, só a tag 'n'
    return str(v)


def _tcast(letter: str, body: str):
    if letter == "i":
        return int(body)
    if letter == "f":
        return float(body)
    if letter == "b":
        return body == "true"
    if letter == "n":
        return None
    return body                                      # str


# ---- árvore -> colunas (DFS), agora carregando a letra de tipo por coluna ----
def _dfs_cols(node: dict):
    cols = []                                        # (nome, [bodies_str], letra)
    for k, v in node.items():
        if isinstance(v, dict):
            cols += _dfs_cols(v)
        elif isinstance(v, list):
            for c in (list(v[0]) if v else []):
                letter = _tletter(v[0][c]) if v else ""
                cols.append((c, [_tbody(r[c]) for r in v], letter))
        else:
            cols.append((k, [_tbody(v)], _tletter(v)))
    return cols


def _leaf_tok(name, size, letter, is_last, all_sizes) -> str:
    # string última em DFS omite size (e não tem letra); qualquer outra escreve size(+letra)
    if is_last and not all_sizes and letter == "":
        return name
    return f"{name}:{size}{letter}"


def _bracket(node, sizes, letters, ctr, nleaves, all_sizes=False) -> str:
    parts = []
    for k, v in node.items():
        if isinstance(v, dict):
            parts.append(f"{k}{{{_bracket(v, sizes, letters, ctr, nleaves, all_sizes)}}}")
        elif isinstance(v, list):
            inner = []
            for c in (list(v[0]) if v else []):
                i = ctr[0]; ctr[0] += 1
                inner.append(_leaf_tok(c, sizes[i], letters[i], i == nleaves - 1, all_sizes))
            parts.append(f"{k}[{','.join(inner)}]")
        else:
            i = ctr[0]; ctr[0] += 1
            parts.append(_leaf_tok(k, sizes[i], letters[i], i == nleaves - 1, all_sizes))
    return ",".join(parts)


def obj_to_tcf(obj: dict, omit_closes: bool = True, all_sizes: bool = False) -> str:
    cols = _dfs_cols(obj)
    bodies = [encode(b) for _n, b, _l in cols]
    sizes = [len(b.encode()) for b in bodies]
    letters = [l for _n, _b, l in cols]
    meta = _bracket(obj, sizes, letters, [0], len(cols), all_sizes)
    if omit_closes:
        meta = meta.rstrip("}]")
    return f"{MAGIC} {meta}\n" + "".join(bodies)


# ---- parse do meta: nome, opcional ':'size, opcional letra de tipo colada ----
def _parse(meta: str):
    s, pos = meta, 0

    def read_size_and_type():
        nonlocal pos
        pos += 1                                     # consome ':'
        j = pos
        while pos < len(s) and s[pos].isdigit():
            pos += 1
        size = int(s[j:pos])
        letter = ""
        if pos < len(s) and s[pos] not in ",[]{}":   # letra de tipo colada
            letter = s[pos]; pos += 1
        return size, letter

    def seq(close):
        nonlocal pos
        items = []
        while pos < len(s) and (close is None or s[pos] != close):
            while pos < len(s) and s[pos] in " ,":
                pos += 1
            if pos >= len(s) or (close and s[pos] == close):
                break
            j = pos
            while pos < len(s) and s[pos] not in ",[]{}:":
                pos += 1
            name = s[j:pos]
            if pos < len(s) and s[pos] == ":":
                size, letter = read_size_and_type()
                items.append(("leaf", name, size, letter))
            elif pos < len(s) and s[pos] == "{":
                pos += 1
                items.append(("obj", name, seq("}"), ""))
                if pos < len(s) and s[pos] == "}":
                    pos += 1
            elif pos < len(s) and s[pos] == "[":
                pos += 1
                cols = []
                while pos < len(s) and s[pos] != "]":
                    while pos < len(s) and s[pos] in " ,":
                        pos += 1
                    j2 = pos
                    while pos < len(s) and s[pos] not in ",]:":
                        pos += 1
                    nm = s[j2:pos]
                    sz, lt = None, ""
                    if pos < len(s) and s[pos] == ":":
                        sz, lt = read_size_and_type()
                    if nm:
                        cols.append((nm, sz, lt))
                if pos < len(s) and s[pos] == "]":
                    pos += 1
                items.append(("arr", name, cols, ""))
            else:
                items.append(("leaf", name, None, ""))
        return items
    return seq(None)


def tcf_to_obj(blob: str) -> dict:
    head, rest = blob.split("\n", 1)
    assert head.startswith(MAGIC + " "), f"magic inesperado: {head!r}"
    tree = _parse(head[len(MAGIC) + 1:])
    order = []                                       # (name, size, letter)

    def walk(items):
        for kind, name, payload, letter in items:
            if kind == "leaf":
                order.append((name, payload, letter))
            elif kind == "obj":
                walk(payload)
            else:                                    # arr
                for nm, sz, lt in payload:
                    order.append((nm, sz, lt))
    walk(tree)
    raw = rest.encode("utf-8")
    cols, off = {}, 0
    for name, sz, letter in order:
        body = raw[off:].decode() if sz is None else raw[off:off + sz].decode()
        if sz is not None:
            off += sz
        cols[name] = (decode(body), letter)

    def rebuild(items):
        out = {}
        for kind, name, payload, letter in items:
            if kind == "leaf":
                vals, lt = cols[name]
                out[name] = _tcast(lt, vals[0])
            elif kind == "obj":
                out[name] = rebuild(payload)
            else:                                    # arr
                cn = [nm for nm, _, _ in payload]
                n = len(cols[cn[0]][0]) if cn else 0
                rows = []
                for i in range(n):
                    row = {}
                    for c in cn:
                        vals, lt = cols[c]
                        row[c] = _tcast(lt, vals[i])
                    rows.append(row)
                out[name] = rows
        return out
    return rebuild(tree)


# ---- baseline lossy (str(v), como o EXP-015): pra medir o CUSTO da fidelidade ----
def obj_to_tcf_allstr(obj: dict) -> str:
    def dfs(node):
        cols = []
        for k, v in node.items():
            if isinstance(v, dict):
                cols += dfs(v)
            elif isinstance(v, list):
                for c in (list(v[0]) if v else []):
                    cols.append((c, [str(r[c]) for r in v]))
            else:
                cols.append((k, [str(v)]))
        return cols
    cols = dfs(obj)
    bodies = [encode(b) for _n, b in cols]
    sizes = [len(b.encode()) for b in bodies]

    def brk(node, ctr, nleaves):
        parts = []
        for k, v in node.items():
            if isinstance(v, dict):
                parts.append(f"{k}{{{brk(v, ctr, nleaves)}}}")
            elif isinstance(v, list):
                inner = []
                for c in (list(v[0]) if v else []):
                    i = ctr[0]; ctr[0] += 1
                    inner.append(c if i == nleaves - 1 else f"{c}:{sizes[i]}")
                parts.append(f"{k}[{','.join(inner)}]")
            else:
                i = ctr[0]; ctr[0] += 1
                parts.append(k if i == nleaves - 1 else f"{k}:{sizes[i]}")
        return ",".join(parts)
    meta = brk(obj, [0], len(cols)).rstrip("}]")
    return f"{MAGIC} {meta}\n" + "".join(bodies)

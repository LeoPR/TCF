"""codec — protótipo v0 (CLEAN) do TCF hierárquico. Lê CSV e JSON, reverte pros dois.

Consolida as IDEIAS do estudo dirty (peças 1-9), reconstruído do zero (não copia a engenhoca):
 - meta em COLCHETE descrevendo a árvore (P5), `M`/`N`/cardinalidade deduzidos;
 - dedução de cardinalidade por dependência funcional (FD, P7);
 - explícito (JSON preserva a árvore) vs implícito (CSV deduz; RT-alvo é a tabela plana).

Formato protótipo **TCF.8H** (opt-in, fora de src/tcf):
    #TCF.8H <bracket-meta>\\n<bodies>
`bracket-meta` = árvore com nomes + sizes inline (última folha sem size); `bodies` = corpos TCF por
coluna em ordem DFS (via `tcf.encode`). Valores como string (tipos = extensão futura). RT lossless.
"""
from __future__ import annotations
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[4]        # .../TCF (experiments/lab/clean/EXP-.../codec.py)
sys.path.insert(0, str(_ROOT / "src"))
from tcf import encode, decode                       # noqa: E402

MAGIC = "#TCF.8H"


# ======================================================================
# árvore ↔ colunas (DFS). árvore = objeto{campo→sub} | array-de-objetos | escalar
# ======================================================================
def _dfs_cols(node: dict):
    cols = []
    for k, v in node.items():
        if isinstance(v, dict):
            cols += _dfs_cols(v)
        elif isinstance(v, list):
            for c in (list(v[0]) if v else []):
                cols.append((c, [str(r[c]) for r in v]))
        else:
            cols.append((k, [str(v)]))
    return cols


def _bracket(node: dict, sizes, ctr, nleaves) -> str:
    parts = []
    for k, v in node.items():
        if isinstance(v, dict):
            parts.append(f"{k}{{{_bracket(v, sizes, ctr, nleaves)}}}")     # {} = objeto (1:1)
        elif isinstance(v, list):
            inner = []
            for c in (list(v[0]) if v else []):
                i = ctr[0]; ctr[0] += 1
                inner.append(c if i == nleaves - 1 else f"{c}:{sizes[i]}")
            parts.append(f"{k}[{','.join(inner)}]")                        # [] = array (1:N)
        else:
            i = ctr[0]; ctr[0] += 1
            parts.append(k if i == nleaves - 1 else f"{k}:{sizes[i]}")
    return ",".join(parts)


def _parse(meta: str):
    s, pos = meta, 0

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
                pos += 1
                j2 = pos
                while pos < len(s) and s[pos] not in ",[]{}":
                    pos += 1
                items.append(("leaf", name, int(s[j2:pos])))
            elif pos < len(s) and s[pos] == "{":
                pos += 1
                items.append(("obj", name, seq("}")))
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
                    sz = None
                    if pos < len(s) and s[pos] == ":":
                        pos += 1
                        j3 = pos
                        while pos < len(s) and s[pos] not in ",]":
                            pos += 1
                        sz = int(s[j3:pos])
                    if nm:
                        cols.append((nm, sz))
                if pos < len(s) and s[pos] == "]":
                    pos += 1
                items.append(("arr", name, cols))
            else:
                items.append(("leaf", name, None))
        return items
    return seq(None)


# ======================================================================
# árvore (obj JSON) ↔ blob TCF.8H
# ======================================================================
def obj_to_tcf(obj: dict) -> str:
    cols = _dfs_cols(obj)
    bodies = [encode(v) for _n, v in cols]
    sizes = [len(b.encode()) for b in bodies]
    meta = _bracket(obj, sizes, [0], len(cols))
    return f"{MAGIC} {meta}\n" + "".join(bodies)


def tcf_to_obj(blob: str) -> dict:
    head, rest = blob.split("\n", 1)
    assert head.startswith(MAGIC + " "), f"magic inesperado: {head!r}"
    tree = _parse(head[len(MAGIC) + 1:])
    # ordem DFS das folhas + sizes
    order = []

    def walk(items):
        for kind, name, payload in items:
            if kind == "leaf":
                order.append((name, payload))
            elif kind == "obj":
                walk(payload)
            else:                                   # arr
                for nm, sz in payload:
                    order.append((nm, sz))
    walk(tree)
    raw = rest.encode("utf-8")
    cols, off = {}, 0
    for name, sz in order:
        body = raw[off:].decode() if sz is None else raw[off:off + sz].decode()
        if sz is not None:
            off += sz
        cols[name] = decode(body)

    def rebuild(items):
        out = {}
        for kind, name, payload in items:
            if kind == "leaf":
                out[name] = cols[name][0]
            elif kind == "obj":
                out[name] = rebuild(payload)
            else:                                   # arr
                cn = [nm for nm, _ in payload]
                n = len(cols[cn[0]]) if cn else 0
                out[name] = [{c: cols[c][i] for c in cn} for i in range(n)]
        return out
    return rebuild(tree)


# ======================================================================
# CSV plano ↔ blob (multi-col do TCF; sem hierarquia) — RT-alvo = a tabela plana
# ======================================================================
def csv_to_cols(text: str):
    import csv
    import io
    rows = list(csv.reader(io.StringIO(text)))
    header, data = rows[0], rows[1:]
    return {h: [r[i] for r in data] for i, h in enumerate(header)}, header


def cols_to_tcf_flat(cols: dict) -> str:
    return encode({k: [str(x) for x in v] for k, v in cols.items()})


def tcf_flat_to_cols(blob: str) -> dict:
    return decode(blob)


def cols_to_csv(cols: dict, header: list) -> str:
    n = len(next(iter(cols.values()))) if cols else 0
    lines = [",".join(header)]
    for i in range(n):
        lines.append(",".join(str(cols[h][i]) for h in header))
    return "\n".join(lines) + "\n"


# ======================================================================
# DEDUÇÃO (CSV): detecta 1:N (pai que repete) e hierarquiza → obj aninhado.
# RT-alvo continua a tabela PLANA (o codec re-achata no decode).
# ======================================================================
def classify(a, b):
    nA, nB, nAB = len(set(a)), len(set(b)), len(set(zip(a, b)))
    if nAB == nA and nAB == nB:
        return "1:1"
    if nAB == nB:
        return "1:N"          # A é o pai (repete)
    if nAB == nA:
        return "N:1"
    return "N:N"


def deduce_to_obj(cols: dict, parent: str, child: str) -> dict:
    """1:N (parent→child): agrupa child por parent → array de {parent, filhos[child]}."""
    groups, order = {}, []
    for pv, cv in zip(cols[parent], cols[child]):
        if pv not in groups:
            groups[pv] = []; order.append(pv)
        groups[pv].append(cv)
    return {"_grupos": [{parent: p, child + "s": [{child: c} for c in groups[p]]} for p in order]}


def obj_to_flat_cols(obj: dict, parent: str, child: str) -> dict:
    """re-achata o obj deduzido de volta pras colunas planas (parent, child)."""
    pa, ch = [], []
    for g in obj["_grupos"]:
        for row in g[child + "s"]:
            pa.append(g[parent]); ch.append(row[child])
    return {parent: pa, child: ch}

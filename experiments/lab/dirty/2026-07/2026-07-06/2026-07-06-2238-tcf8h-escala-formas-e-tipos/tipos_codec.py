"""tipos_codec — Ciclo 1b: mede as ESTRATÉGIAS de tipo (decisão com número) + escala de formas.

Reusa o typed_codec do Ciclo 1a (build-on-prior). Três estratégias no eixo TIPO:
 - A (explícita, 1a): string=default; tag i/f/b/n em TODA folha não-string. Lossless. Custo = #não-string.
 - B (dedução pura): SEM tags; o decode DEDUZ o tipo do body. Custo 0, mas LOSSY em ambiguidade
   (string "30" → int; "true" → bool; null "" → string vazia).
 - C (híbrido): tag SÓ quando a dedução erraria (string que parece número/bool → força 's'; null → 'n';
   número/bool que a dedução acerta → SEM tag). Lossless. Custo = #ambíguas.

A decisão sai do número: A é seguro+caro; B é barato+lossy; C é lossless e o mais barato quando números
dominam e strings-ambíguas são raras. Engenhoca descartável — não toca src/tcf nem EXP-015 clean.
"""
from __future__ import annotations
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "2026-07-06-2221-tcf8h-fidelidade-tipos"))
import typed_codec as TC                              # noqa: E402
from tcf import encode, decode                        # noqa: E402

MAGIC = TC.MAGIC
_INT = re.compile(r"-?\d+$")
_FLOAT = re.compile(r"-?\d+\.\d+$")


def deduce(body: str):
    """string do body → valor Python por inferência (a heurística da estratégia B/C)."""
    if body == "true":
        return True
    if body == "false":
        return False
    if _INT.match(body):
        return int(body)
    if _FLOAT.match(body):
        return float(body)
    return body                                       # str (inclui "" = string vazia)


def _ded_letter(body: str) -> str:
    return TC._tletter(deduce(body))                  # que tipo a dedução chamaria


# ---- ENCODE (as 3 estratégias diferem só na LETRA por coluna) ----
def _encode(obj, letter_of):
    cols = TC._dfs_cols(obj)                           # (nome, [bodies_str], actual_letter)
    bodies = [encode(b) for _n, b, _l in cols]
    sizes = [len(b.encode()) for b in bodies]
    letters = [letter_of(actual, raw) for _n, raw, actual in cols]
    meta = TC._bracket(obj, sizes, letters, [0], len(cols), False).rstrip("}]")
    return f"{MAGIC} {meta}\n" + "".join(bodies), letters


def encode_A(obj):
    return _encode(obj, lambda actual, raw: actual)                       # tag = tipo real
def encode_B(obj):
    return _encode(obj, lambda actual, raw: "")                          # nunca taggeia
def _c_letter(actual, raw_bodies):
    for body in raw_bodies:
        if _ded_letter(body) != actual:                                  # dedução erraria
            return actual or "s"                                         # string ambígua → força 's'
    return ""                                                            # dedução acerta → sem tag
def encode_C(obj):
    return _encode(obj, _c_letter)


# ---- DECODE (genérico; val_fn resolve o valor por folha) ----
def _decode(blob, val_fn):
    head, rest = blob.split("\n", 1)
    tree = TC._parse(head[len(MAGIC) + 1:])
    order = []

    def walk(items):
        for kind, name, payload, letter in items:
            if kind == "leaf":
                order.append((name, payload, letter))
            elif kind == "obj":
                walk(payload)
            else:
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
                out[name] = val_fn(lt, vals[0])
            elif kind == "obj":
                out[name] = rebuild(payload)
            else:
                cn = [nm for nm, _, _ in payload]
                n = len(cols[cn[0]][0]) if cn else 0
                out[name] = [{c: val_fn(cols[c][1], cols[c][0][i]) for c in cn} for i in range(n)]
        return out
    return rebuild(tree)


def _c_cast(lt, v):
    if lt == "":
        return deduce(v)                              # sem tag → deduz
    if lt == "s":
        return v                                      # forçado string
    return TC._tcast(lt, v)


def decode_A(blob):
    return _decode(blob, lambda lt, v: TC._tcast(lt, v))
def decode_B(blob):
    return _decode(blob, lambda lt, v: deduce(v))
def decode_C(blob):
    return _decode(blob, _c_cast)


STRAT = {
    "A-explicita": (encode_A, decode_A),
    "B-deducao": (encode_B, decode_B),
    "C-hibrida": (encode_C, decode_C),
}

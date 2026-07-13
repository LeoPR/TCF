"""Stage-1 TCF.H codec: DatasetH <-> #TCF.8H text (topology + leaf identity).

STAGE 1 = "hierarchy logic first" (owner 2026-07-13). Goal: `decode_h(encode_h(ds)) == ds`
exact for the DatasetH domain the POC accepts (finite, standard-JSON scalars), covering
**topology** (objects/arrays/nesting/order), **presence** (empty object vs empty array vs
null vs ""), ragged objects, array-of-array, and **`\n` inside a string** — the case the flat
`#TCF.8M` format rejects. It is PER-INSTANCE (each node carries its own shape), because general
trees are irregular (ragged, mixed arrays) and a static header-schema (EXP-015 / ADR-0031) only
fits *regular* nesting.

DELIBERATELY DEFERRED to stage 2 (types & variations):
- special scalars (`NaN`/`+Inf`/`-Inf` — the POC rejects them; `-0.0` identity);
- number lexical forms (`1e3` -> value 1000.0; semantic, not lexical, preservation);
- compression / factoring (OBAT/HCC per-leaf, repeated-subtree dedup, RLE);
- the minimal bracket-header / def-levels representation (ADR-0031 schema form) and base/hex.

Wire form (provisional, POC — NOT the welded grammar; that is a P5 decision):

    #TCF.8H\n
    <node stream, preorder>

  node := O<count>\n (K<blen>\n<key-bytes> node){count}    # object, ordered fields
        | A<count>\n (node){count}                          # array, ordered items
        | Z\n                                               # null
        | T\n | F\n                                         # boolean true / false
        | I<digits>\n                                       # integer (str(int), may be -)
        | N<repr>\n                                         # number (repr(float), RT-exact)
        | S<blen>\n<utf8-bytes>                             # string (blen = BYTE length)

  Counts and byte-lengths are DECIMAL here for inspectability; hex/base is a stage-2
  representation choice (cross T-FMT-HEADER-BASE-HEX). Strings/keys are length-prefixed so
  arbitrary content (incl. `\n`, `{`, `:`) round-trips with zero escaping.

Fail-loud: any malformed stream raises `TCFHDecodeError` (never silent corruption).
"""

from __future__ import annotations

import math

from dataset_h import DatasetH, DuplicateFieldError, HArray, HObject, HScalar

MAGIC = "#TCF.8H"


class TCFHDecodeError(ValueError):
    """Malformed #TCF.8H stream (fail-loud, never silent)."""


# ---------------------------------------------------------------- encode

def encode_h(ds: DatasetH) -> str:
    out = bytearray()
    out += MAGIC.encode("ascii")
    out += b"\n"
    _emit(ds.root, out)
    return out.decode("utf-8")


def _emit(node, out: bytearray) -> None:
    if isinstance(node, HObject):
        out += b"O%d\n" % len(node.fields)
        for name, child in node.fields:
            kb = name.encode("utf-8")
            out += b"K%d\n" % len(kb)
            out += kb
            _emit(child, out)
    elif isinstance(node, HArray):
        out += b"A%d\n" % len(node.items)
        for child in node.items:
            _emit(child, out)
    elif isinstance(node, HScalar):
        kind = node.type_name
        if kind == "null":
            out += b"Z\n"
        elif kind == "boolean":
            out += b"T\n" if node.value else b"F\n"
        elif kind == "integer":
            out += b"I%d\n" % node.value
        elif kind == "number":
            out += b"N"
            out += repr(node.value).encode("ascii")
            out += b"\n"
        elif kind == "string":
            sb = node.value.encode("utf-8")
            out += b"S%d\n" % len(sb)
            out += sb
        else:
            raise ValueError(
                f"stage-1 codec does not handle scalar kind {kind!r} "
                f"(special scalars are stage 2)"
            )
    else:  # pragma: no cover - DatasetH is a closed union
        raise TypeError(f"unknown DatasetH node: {type(node).__name__}")


# ---------------------------------------------------------------- decode

def decode_h(text: str) -> DatasetH:
    data = text.encode("utf-8")
    nl = data.find(b"\n")
    if nl == -1:
        raise TCFHDecodeError("missing magic line")
    magic = data[:nl].decode("utf-8", "replace")
    if magic != MAGIC:
        raise TCFHDecodeError(f"bad magic {magic!r} (expected {MAGIC!r})")
    node, pos = _read(data, nl + 1)
    if pos != len(data):
        raise TCFHDecodeError(f"trailing bytes after root node ({len(data) - pos} left)")
    return DatasetH(node)


def _canonical_int(tok: bytes, *, allow_negative: bool) -> bool:
    """Only the canonical str(int) form: no '+', '_', whitespace, leading zeros or '-0'.

    (Verification finding: bare int() accepts 'O-1'/'I+5'/'0_5'/' 3' — silent laxity
    against the declared decimal grammar; decoder must be fail-loud and injective.)
    """
    if allow_negative and tok.startswith(b"-"):
        tok = tok[1:]
        if not tok.isdigit() or tok == b"0":  # '-' alone, '-0', '-x' rejected
            return False
        return not tok.startswith(b"0")
    if not tok.isdigit():
        return False
    return tok == b"0" or not tok.startswith(b"0")


def _read_int_line(data: bytes, pos: int, *, allow_negative: bool = False) -> tuple[int, int]:
    nl = data.find(b"\n", pos)
    if nl == -1:
        raise TCFHDecodeError(f"unterminated count/length at byte {pos}")
    tok = data[pos:nl]
    if not _canonical_int(tok, allow_negative=allow_negative):
        raise TCFHDecodeError(f"invalid integer token {tok!r} at byte {pos}")
    return int(tok), nl + 1


def _read(data: bytes, pos: int):
    if pos >= len(data):
        raise TCFHDecodeError("unexpected end of stream (expected a node)")
    tag = data[pos : pos + 1]
    pos += 1
    if tag == b"O":
        count, pos = _read_int_line(data, pos)
        fields = []
        for _ in range(count):
            if data[pos : pos + 1] != b"K":
                raise TCFHDecodeError(f"expected field key 'K' at byte {pos}")
            klen, pos = _read_int_line(data, pos + 1)
            key = _decode_utf8(data[pos : pos + klen], "field key", pos)
            pos += klen
            child, pos = _read(data, pos)
            fields.append((key, child))
        try:
            return HObject(tuple(fields)), pos
        except DuplicateFieldError as exc:
            # wire com chave duplicada = malformado; fail-loud com o TIPO prometido
            raise TCFHDecodeError(str(exc)) from exc
    if tag == b"A":
        count, pos = _read_int_line(data, pos)
        items = []
        for _ in range(count):
            child, pos = _read(data, pos)
            items.append(child)
        return HArray(tuple(items)), pos
    if tag == b"Z":
        return _scalar_nl(data, pos, HScalar("null", None))
    if tag == b"T":
        return _scalar_nl(data, pos, HScalar("boolean", True))
    if tag == b"F":
        return _scalar_nl(data, pos, HScalar("boolean", False))
    if tag == b"I":
        val, pos = _read_int_line(data, pos, allow_negative=True)
        return HScalar("integer", val), pos
    if tag == b"N":
        nl = data.find(b"\n", pos)
        if nl == -1:
            raise TCFHDecodeError(f"unterminated number at byte {pos}")
        try:
            val = float(data[pos:nl])
        except ValueError:
            raise TCFHDecodeError(f"invalid number token {data[pos:nl]!r}")
        if not math.isfinite(val):
            # float() aceita 'nan'/'inf'/'Infinity' — mas o canal N e' so' de finitos
            # (nenhuma origem/encode produz nao-finito aqui; achado da verificacao).
            raise TCFHDecodeError(
                f"non-finite on N channel {data[pos:nl]!r} (stage-2 carries specials as kinds)"
            )
        return HScalar("number", val), nl + 1
    if tag == b"S":
        slen, pos = _read_int_line(data, pos)
        sb = data[pos : pos + slen]
        if len(sb) != slen:
            raise TCFHDecodeError(f"string truncated (wanted {slen} bytes)")
        return HScalar("string", _decode_utf8(sb, "string body", pos)), pos + slen
    raise TCFHDecodeError(f"unknown node tag {tag!r} at byte {pos - 1}")


def _scalar_nl(data: bytes, pos: int, scalar: HScalar):
    if data[pos : pos + 1] != b"\n":
        raise TCFHDecodeError(f"expected newline after scalar tag at byte {pos}")
    return scalar, pos + 1


def _decode_utf8(raw: bytes, what: str, pos: int) -> str:
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise TCFHDecodeError(f"invalid UTF-8 in {what} at byte {pos}: {exc}") from exc

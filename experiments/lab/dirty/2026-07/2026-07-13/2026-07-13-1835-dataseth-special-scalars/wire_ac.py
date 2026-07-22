"""Stage-2 wire study: representation A (typed leaf) vs C (escaped string lexeme).

Same per-instance preorder stream as stage 1 (idea extracted, not imported: O/A/K containers,
Z/T/F/I/N/S leaves, decimal counts, length-prefixed strings). The two variants differ ONLY in
how the special scalars (nan / pos_inf / neg_inf) ride the wire:

  A (typed leaf)     : new tag  Vnan\n | Vinf\n | V-inf\n
                       -> kind explicit on the wire; the string channel is untouched.
  C (escaped string) : specials ride the STRING channel as reserved lexemes
                       NaN | Infinity | -Infinity
                       -> any literal string equal to a lexeme OR starting with '\\' must be
                          escaped ('\\' prefixed); decode peels one '\\' or recognizes a lexeme.

Fail-loud on malformed input in both.
"""

from __future__ import annotations

import math

from model_ext import DatasetH, HArray, HObject, HScalar
from dataset_h import DuplicateFieldError  # via sys.path do model_ext

MAGIC = "#TCF.8H"
_C_LEXEMES = {"nan": "NaN", "pos_inf": "Infinity", "neg_inf": "-Infinity"}
_C_REVERSE = {v: k for k, v in _C_LEXEMES.items()}
_A_TOKENS = {"nan": "nan", "pos_inf": "inf", "neg_inf": "-inf"}
_A_REVERSE = {v: k for k, v in _A_TOKENS.items()}


class WireError(ValueError):
    pass


def encode(ds: DatasetH, variant: str) -> str:
    assert variant in ("A", "C")
    out = bytearray()
    out += MAGIC.encode() + b"\n"
    _emit(ds.root, out, variant)
    return out.decode("utf-8")


def _emit_string(body: str, out: bytearray, variant: str) -> None:
    if variant == "C" and (body in _C_REVERSE or body.startswith("\\")):
        body = "\\" + body  # escape lexeme-lookalikes and backslash-leaders
    sb = body.encode("utf-8")
    out += b"S%d\n" % len(sb)
    out += sb


def _emit(node, out: bytearray, variant: str) -> None:
    if isinstance(node, HObject):
        out += b"O%d\n" % len(node.fields)
        for name, child in node.fields:
            kb = name.encode("utf-8")
            out += b"K%d\n" % len(kb)
            out += kb
            _emit(child, out, variant)
    elif isinstance(node, HArray):
        out += b"A%d\n" % len(node.items)
        for child in node.items:
            _emit(child, out, variant)
    elif isinstance(node, HScalar):
        k = node.type_name
        if k == "null":
            out += b"Z\n"
        elif k == "boolean":
            out += b"T\n" if node.value else b"F\n"
        elif k == "integer":
            out += b"I%d\n" % node.value
        elif k == "number":
            out += b"N" + repr(node.value).encode() + b"\n"
        elif k == "string":
            _emit_string(node.value, out, variant)
        elif k in _A_TOKENS:
            if variant == "A":
                out += b"V" + _A_TOKENS[k].encode() + b"\n"
            else:
                sb = _C_LEXEMES[k].encode()
                out += b"S%d\n" % len(sb)
                out += sb
        else:
            raise WireError(f"unknown scalar kind {k!r}")
    else:
        raise TypeError(type(node).__name__)


def decode(text: str, variant: str) -> DatasetH:
    assert variant in ("A", "C")
    data = text.encode("utf-8")
    nl = data.find(b"\n")
    if nl == -1 or data[:nl].decode("utf-8", "replace") != MAGIC:
        raise WireError("bad magic")
    node, pos = _read(data, nl + 1, variant)
    if pos != len(data):
        raise WireError("trailing bytes")
    return DatasetH(node)


def _canonical_int(tok: bytes, *, allow_negative: bool) -> bool:
    """Só a forma canônica str(int) — sem '+', '_', whitespace, zeros à esquerda ou '-0'."""
    if allow_negative and tok.startswith(b"-"):
        tok = tok[1:]
        if not tok.isdigit() or tok == b"0":
            return False
        return not tok.startswith(b"0")
    if not tok.isdigit():
        return False
    return tok == b"0" or not tok.startswith(b"0")


def _int_line(data: bytes, pos: int, *, allow_negative: bool = False):
    nl = data.find(b"\n", pos)
    if nl == -1:
        raise WireError("unterminated int")
    tok = data[pos:nl]
    if not _canonical_int(tok, allow_negative=allow_negative):
        raise WireError(f"bad int {tok!r}")
    return int(tok), nl + 1


def _read(data: bytes, pos: int, variant: str):
    if pos >= len(data):
        raise WireError("eof")
    tag = data[pos : pos + 1]
    pos += 1
    if tag == b"O":
        n, pos = _int_line(data, pos)
        fields = []
        for _ in range(n):
            if data[pos : pos + 1] != b"K":
                raise WireError("expected K")
            klen, pos = _int_line(data, pos + 1)
            key = _utf8(data[pos : pos + klen], pos)
            pos += klen
            child, pos = _read(data, pos, variant)
            fields.append((key, child))
        try:
            return HObject(tuple(fields)), pos
        except DuplicateFieldError as exc:
            raise WireError(str(exc)) from exc
    if tag == b"A":
        n, pos = _int_line(data, pos)
        items = []
        for _ in range(n):
            child, pos = _read(data, pos, variant)
            items.append(child)
        return HArray(tuple(items)), pos
    if tag == b"Z":
        return HScalar("null", None), _nl(data, pos)
    if tag == b"T":
        return HScalar("boolean", True), _nl(data, pos)
    if tag == b"F":
        return HScalar("boolean", False), _nl(data, pos)
    if tag == b"I":
        v, pos = _int_line(data, pos, allow_negative=True)
        return HScalar("integer", v), pos
    if tag == b"N":
        nl2 = data.find(b"\n", pos)
        if nl2 == -1:
            raise WireError("unterminated number")
        try:
            v = float(data[pos:nl2])
        except ValueError:
            raise WireError(f"bad number token {data[pos:nl2]!r}")
        if not math.isfinite(v):
            # float() aceita 'nan'/'inf'/'Infinity' — fabricaria um number nao-finito
            # que NENHUMA origem/encode produz (achado da verificacao adversarial):
            # especiais viajam como kind (V em A; lexema em C), nunca no canal N.
            raise WireError(f"non-finite on N channel {data[pos:nl2]!r}")
        return HScalar("number", v), nl2 + 1
    if tag == b"S":
        slen, pos = _int_line(data, pos)
        body = data[pos : pos + slen]
        if len(body) != slen:
            raise WireError("string truncated")
        s = _utf8(body, pos)
        pos += slen
        if variant == "C":
            if s in _C_REVERSE:
                return HScalar(_C_REVERSE[s], None), pos
            if s.startswith("\\"):
                s = s[1:]
        return HScalar("string", s), pos
    if tag == b"V":
        if variant != "A":
            raise WireError("V tag is variant-A only")
        nl2 = data.find(b"\n", pos)
        if nl2 == -1:
            raise WireError("unterminated V token")
        token = _utf8(data[pos:nl2], pos)
        if token not in _A_REVERSE:
            raise WireError(f"bad special token {token!r}")
        return HScalar(_A_REVERSE[token], None), nl2 + 1
    raise WireError(f"unknown tag {tag!r}")


def _nl(data: bytes, pos: int) -> int:
    if data[pos : pos + 1] != b"\n":
        raise WireError("expected newline")
    return pos + 1


def _utf8(raw: bytes, pos: int) -> str:
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise WireError(f"invalid UTF-8 at byte {pos}: {exc}") from exc

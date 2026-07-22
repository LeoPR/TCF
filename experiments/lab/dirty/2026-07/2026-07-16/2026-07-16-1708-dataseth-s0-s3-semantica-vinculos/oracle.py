"""Explicit preorder wire used only as the S1 semantic oracle."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
import re

from model import (
    DatasetH,
    DuplicateFieldError,
    HArray,
    HNode,
    HObject,
    HScalar,
    MAX_DEPTH,
    decimal_token,
)

MAGIC = b"#PROTO.DATASETH.S1\n"
_INT = re.compile(rb"-?(?:0|[1-9][0-9]*)\Z")
_NUMBER = re.compile(rb"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)(?:[eE][+-]?[0-9]+)?\Z")


class OracleWireError(ValueError):
    pass


def encode(dataset: DatasetH) -> bytes:
    out = bytearray(MAGIC)
    _emit(dataset.root, out, depth=0)
    return bytes(out)


def _emit(node: HNode, out: bytearray, *, depth: int) -> None:
    if depth > MAX_DEPTH:
        raise OracleWireError(f"wire depth exceeds {MAX_DEPTH}")
    if isinstance(node, HObject):
        out += f"O{len(node.fields)}\n".encode("ascii")
        for name, child in node.fields:
            key = name.encode("utf-8")
            out += f"K{len(key)}\n".encode("ascii") + key
            _emit(child, out, depth=depth + 1)
        return
    if isinstance(node, HArray):
        out += f"A{len(node.items)}\n".encode("ascii")
        for child in node.items:
            _emit(child, out, depth=depth + 1)
        return
    if node.kind == "null":
        out += b"Z\n"
    elif node.kind == "boolean":
        out += b"T\n" if node.value else b"F\n"
    elif node.kind == "integer":
        out += f"I{node.value}\n".encode("ascii")
    elif node.kind == "number":
        assert isinstance(node.value, Decimal)
        out += b"N" + decimal_token(node.value).encode("ascii") + b"\n"
    elif node.kind == "string":
        body = str(node.value).encode("utf-8")
        out += f"S{len(body)}\n".encode("ascii") + body
    else:
        raise OracleWireError(f"unknown scalar kind {node.kind!r}")


def decode(data: bytes) -> DatasetH:
    if not data.startswith(MAGIC):
        raise OracleWireError("bad or missing S1 magic")
    root, pos = _read(data, len(MAGIC), depth=0)
    if pos != len(data):
        raise OracleWireError(f"trailing bytes after root ({len(data) - pos})")
    return DatasetH(root)


def _line(data: bytes, pos: int) -> tuple[bytes, int]:
    end = data.find(b"\n", pos)
    if end < 0:
        raise OracleWireError(f"unterminated token at byte {pos}")
    return data[pos:end], end + 1


def _natural(token: bytes, *, what: str) -> int:
    if not re.fullmatch(rb"0|[1-9][0-9]*", token):
        raise OracleWireError(f"invalid {what}: {token!r}")
    return int(token)


def _read(data: bytes, pos: int, *, depth: int) -> tuple[HNode, int]:
    if depth > MAX_DEPTH:
        raise OracleWireError(f"wire depth exceeds {MAX_DEPTH}")
    if pos >= len(data):
        raise OracleWireError("unexpected end of wire")
    tag = data[pos : pos + 1]
    token, next_pos = _line(data, pos + 1)
    if tag == b"O":
        count = _natural(token, what="object field count")
        fields = []
        pos = next_pos
        for _ in range(count):
            if data[pos : pos + 1] != b"K":
                raise OracleWireError(f"expected key at byte {pos}")
            key_len_token, pos = _line(data, pos + 1)
            key_len = _natural(key_len_token, what="key byte length")
            raw = data[pos : pos + key_len]
            if len(raw) != key_len:
                raise OracleWireError("truncated key")
            try:
                key = raw.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise OracleWireError("invalid UTF-8 key") from exc
            child, pos = _read(data, pos + key_len, depth=depth + 1)
            fields.append((key, child))
        try:
            return HObject(tuple(fields)), pos
        except DuplicateFieldError as exc:
            raise OracleWireError(str(exc)) from exc
    if tag == b"A":
        count = _natural(token, what="array item count")
        items = []
        pos = next_pos
        for _ in range(count):
            child, pos = _read(data, pos, depth=depth + 1)
            items.append(child)
        return HArray(tuple(items)), pos
    if tag in (b"Z", b"T", b"F"):
        if token:
            raise OracleWireError(f"scalar tag {tag!r} carries unexpected payload")
        values = {b"Z": HScalar("null", None), b"T": HScalar("boolean", True), b"F": HScalar("boolean", False)}
        return values[tag], next_pos
    if tag == b"I":
        if not _INT.fullmatch(token):
            raise OracleWireError(f"invalid integer token {token!r}")
        return HScalar("integer", int(token)), next_pos
    if tag == b"N":
        if not _NUMBER.fullmatch(token):
            raise OracleWireError(f"invalid number token {token!r}")
        try:
            value = Decimal(token.decode("ascii"))
        except InvalidOperation as exc:
            raise OracleWireError(f"invalid number token {token!r}") from exc
        if not value.is_finite():
            raise OracleWireError("non-finite number")
        return HScalar("number", value), next_pos
    if tag == b"S":
        size = _natural(token, what="string byte length")
        raw = data[next_pos : next_pos + size]
        if len(raw) != size:
            raise OracleWireError("truncated string")
        try:
            value = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise OracleWireError("invalid UTF-8 string") from exc
        return HScalar("string", value), next_pos + size
    raise OracleWireError(f"unknown node tag {tag!r} at byte {pos}")

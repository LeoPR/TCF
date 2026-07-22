"""DatasetH semantic oracle for S0-S3 (research code, not canonical core)."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
import json
import math
from typing import Any, Mapping, TypeAlias

MAX_DEPTH = 128


class DatasetHError(ValueError):
    pass


class DuplicateFieldError(DatasetHError):
    pass


class DepthLimitError(DatasetHError):
    pass


class CycleError(DatasetHError):
    pass


@dataclass(frozen=True)
class _JsonObject:
    fields: tuple[tuple[str, Any], ...]


@dataclass(frozen=True)
class HScalar:
    kind: str
    value: str | int | Decimal | bool | None


@dataclass(frozen=True)
class HArray:
    items: tuple[HNode, ...]


@dataclass(frozen=True)
class HObject:
    fields: tuple[tuple[str, HNode], ...]

    def __post_init__(self) -> None:
        names = [name for name, _ in self.fields]
        if any(not isinstance(name, str) for name in names):
            raise TypeError("DatasetH object field names must be strings")
        if len(names) != len(set(names)):
            duplicate = next(name for name in names if names.count(name) > 1)
            raise DuplicateFieldError(f"duplicate DatasetH field: {duplicate!r}")


HNode: TypeAlias = HScalar | HArray | HObject


@dataclass(frozen=True)
class DatasetH:
    root: HNode

    @classmethod
    def from_json(cls, text: str) -> DatasetH:
        value = json.loads(
            text,
            object_pairs_hook=_capture_object,
            parse_float=Decimal,
            parse_int=int,
            parse_constant=_reject_constant,
        )
        return cls(_node_from_python(value, depth=0, active=set()))

    @classmethod
    def from_python(cls, value: Any) -> DatasetH:
        return cls(_node_from_python(value, depth=0, active=set()))

    def canonical_json(self) -> str:
        return _emit_json(self.root)


def _capture_object(pairs: list[tuple[str, Any]]) -> _JsonObject:
    names = [name for name, _ in pairs]
    if len(names) != len(set(names)):
        duplicate = next(name for name in names if names.count(name) > 1)
        raise DuplicateFieldError(f"duplicate JSON field: {duplicate!r}")
    return _JsonObject(tuple(pairs))


def _reject_constant(value: str) -> None:
    raise DatasetHError(f"non-standard JSON constant: {value}")


def _node_from_python(value: Any, *, depth: int, active: set[int]) -> HNode:
    if depth > MAX_DEPTH:
        raise DepthLimitError(f"DatasetH depth exceeds {MAX_DEPTH}")
    if isinstance(value, _JsonObject):
        return HObject(
            tuple(
                (name, _node_from_python(child, depth=depth + 1, active=active))
                for name, child in value.fields
            )
        )
    if isinstance(value, Mapping) or isinstance(value, (list, tuple)):
        identity = id(value)
        if identity in active:
            raise CycleError("DatasetH source contains a cycle")
        active.add(identity)
        try:
            if isinstance(value, Mapping):
                return HObject(
                    tuple(
                        (name, _node_from_python(child, depth=depth + 1, active=active))
                        for name, child in value.items()
                    )
                )
            return HArray(
                tuple(_node_from_python(child, depth=depth + 1, active=active) for child in value)
            )
        finally:
            active.remove(identity)
    if value is None:
        return HScalar("null", None)
    if isinstance(value, bool):
        return HScalar("boolean", value)
    if isinstance(value, int):
        return HScalar("integer", value)
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise DatasetHError("DatasetH accepts only finite JSON numbers")
        return HScalar("number", value)
    if isinstance(value, float):
        if not math.isfinite(value):
            raise DatasetHError("DatasetH accepts only finite JSON numbers")
        return HScalar("number", Decimal(str(value)))
    if isinstance(value, str):
        return HScalar("string", value)
    raise TypeError(f"unsupported DatasetH value: {type(value).__name__}")


def decimal_token(value: Decimal) -> str:
    if value == value.to_integral_value():
        return f"{format(value.quantize(Decimal(1)), 'f')}.0"
    return format(value.normalize(), "f")


def _emit_json(node: HNode) -> str:
    if isinstance(node, HObject):
        fields = (
            f"{json.dumps(name, ensure_ascii=False)}:{_emit_json(child)}"
            for name, child in node.fields
        )
        return "{" + ",".join(fields) + "}"
    if isinstance(node, HArray):
        return "[" + ",".join(_emit_json(child) for child in node.items) + "]"
    if node.kind == "null":
        return "null"
    if node.kind == "boolean":
        return "true" if node.value else "false"
    if node.kind == "integer":
        return str(node.value)
    if node.kind == "number":
        assert isinstance(node.value, Decimal)
        return decimal_token(node.value)
    return json.dumps(node.value, ensure_ascii=False)

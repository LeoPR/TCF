"""Minimal source-independent DatasetH model for the research bridge."""

from __future__ import annotations

from dataclasses import dataclass
import json
import math
from typing import Any, Mapping, TypeAlias


class DuplicateFieldError(ValueError):
    """The provisional DatasetH contract rejects duplicate object fields."""


class NonStandardJsonConstantError(ValueError):
    """A JSON parser extension such as NaN or Infinity was encountered."""


@dataclass(frozen=True)
class _JsonObject:
    fields: tuple[tuple[str, Any], ...]


@dataclass(frozen=True)
class HScalar:
    type_name: str
    value: str | int | float | bool | None


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
    """A provisional tree model independent of the source format."""

    root: HNode

    @classmethod
    def from_json(cls, text: str) -> DatasetH:
        value = json.loads(
            text,
            object_pairs_hook=_capture_object,
            parse_constant=_reject_nonstandard_constant,
        )
        return cls.from_python(value)

    @classmethod
    def from_python(cls, value: Any) -> DatasetH:
        return cls(_node_from_python(value))

    def to_python(self) -> Any:
        return _python_from_node(self.root)

    def to_json(self, *, pretty: bool = False) -> str:
        options: dict[str, Any] = {
            "ensure_ascii": False,
            "allow_nan": False,
        }
        if pretty:
            options["indent"] = 2
        else:
            options["separators"] = (",", ":")
        return json.dumps(self.to_python(), **options)


def _capture_object(pairs: list[tuple[str, Any]]) -> _JsonObject:
    names = [name for name, _ in pairs]
    if len(names) != len(set(names)):
        duplicate = next(name for name in names if names.count(name) > 1)
        raise DuplicateFieldError(f"duplicate JSON field: {duplicate!r}")
    return _JsonObject(tuple(pairs))


def _reject_nonstandard_constant(value: str) -> None:
    raise NonStandardJsonConstantError(f"non-standard JSON constant: {value}")


def _node_from_python(value: Any) -> HNode:
    if isinstance(value, _JsonObject):
        return HObject(tuple((name, _node_from_python(item)) for name, item in value.fields))
    if isinstance(value, Mapping):
        return HObject(tuple((name, _node_from_python(item)) for name, item in value.items()))
    if isinstance(value, list):
        return HArray(tuple(_node_from_python(item) for item in value))
    return _scalar_from_python(value)


def _scalar_from_python(value: Any) -> HScalar:
    if value is None:
        return HScalar("null", None)
    if isinstance(value, bool):
        return HScalar("boolean", value)
    if isinstance(value, int):
        return HScalar("integer", value)
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("DatasetH does not accept non-finite numbers")
        return HScalar("number", value)
    if isinstance(value, str):
        return HScalar("string", value)
    raise TypeError(f"unsupported DatasetH value: {type(value).__name__}")


def _python_from_node(node: HNode) -> Any:
    if isinstance(node, HScalar):
        return node.value
    if isinstance(node, HArray):
        return [_python_from_node(item) for item in node.items]
    return {name: _python_from_node(item) for name, item in node.fields}

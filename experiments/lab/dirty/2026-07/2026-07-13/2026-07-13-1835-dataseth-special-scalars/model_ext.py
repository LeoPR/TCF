"""Stage-2 extension: special scalars (NaN/+Inf/-Inf) + semantic identity oracle.

Extends the bridge-lab DatasetH (imported, not copied) with:
- typed special kinds  : HScalar("nan"|"pos_inf"|"neg_inf", None)  — alternative A's model;
- `from_python_ext`    : Python-tree origin that ACCEPTS non-finite floats (the bridge POC
  rejects them as a standard-JSON baseline; this lab studies them per H-HIER-SCALAR-01);
- `from_jsonlike`      : a SECOND textual origin with a DECLARED grammar "JSON + NaN/Infinity
  constants" (it does not claim to be standard JSON) — P3 requires two origins;
- `semantic_key`       : the identity ORACLE. Naive equality is NOT enough:
    * float('nan') != float('nan')  -> a NaN leaf as float would never equal itself;
      as a typed kind (value None) reflexivity is restored;
    * -0.0 == 0.0 in Python          -> naive dataclass eq COLLAPSES them; the oracle
      distinguishes via repr ('-0.0' vs '0.0') when the source declares sign relevant.

No src/tcf import. No change to the bridge lab files.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any, Mapping

_BRIDGE = Path(__file__).resolve().parents[1] / "2026-07-13-dataseth-json-bridge"
sys.path.insert(0, str(_BRIDGE))

from dataset_h import (  # noqa: E402
    DatasetH,
    DuplicateFieldError,
    HArray,
    HObject,
    HScalar,
)

SPECIAL_KINDS = ("nan", "pos_inf", "neg_inf")


# ------------------------------------------------------------ origins (P3)

def from_python_ext(value: Any) -> DatasetH:
    """Python-tree origin accepting non-finite floats -> typed special kinds."""
    return DatasetH(_node(value))


def _node(value: Any):
    if isinstance(value, Mapping):
        # chaves passam INTACTAS: HObject.__post_init__ fail-louda em nao-str.
        # (achado da verificacao: str(k) coagia {1:'x'} e {'1':'x'} pro MESMO
        # DatasetH — colisao semantica bypassando o invariante do modelo.)
        return HObject(tuple((k, _node(v)) for k, v in value.items()))
    if isinstance(value, list):
        return HArray(tuple(_node(v) for v in value))
    if value is None:
        return HScalar("null", None)
    if isinstance(value, bool):
        return HScalar("boolean", value)
    if isinstance(value, int):
        return HScalar("integer", value)
    if isinstance(value, float):
        if math.isnan(value):
            return HScalar("nan", None)
        if value == math.inf:
            return HScalar("pos_inf", None)
        if value == -math.inf:
            return HScalar("neg_inf", None)
        return HScalar("number", value)
    if isinstance(value, str):
        return HScalar("string", value)
    raise TypeError(f"unsupported value: {type(value).__name__}")


def from_jsonlike(text: str) -> DatasetH:
    """Second origin: 'JSON-like' text with a DECLARED grammar = JSON + NaN/Infinity/-Infinity.

    Not standard JSON (which has no such constants); the grammar is declared, per the plan
    ('o adaptador JSON-like, se houver, deve declarar sua gramática'). Duplicate keys are
    REJECTED like the bridge origin (finding: bare json.loads collapses them last-key-wins
    silently — the hidden policy the bridge exists to forbid).
    """
    value = json.loads(text, object_pairs_hook=_reject_dup_pairs)
    return from_python_ext(value)


def _reject_dup_pairs(pairs: list[tuple[str, Any]]) -> dict:
    names = [n for n, _ in pairs]
    if len(names) != len(set(names)):
        dup = next(n for n in names if names.count(n) > 1)
        raise DuplicateFieldError(f"duplicate JSON-like field: {dup!r}")
    return dict(pairs)  # dict preserva ordem de insercao


# ------------------------------------------------------------ oracle

def semantic_key(node) -> tuple:
    """Canonical identity: reflexive for NaN, sign-aware for -0.0, type-aware for 1 vs '1'."""
    if isinstance(node, HScalar):
        if node.type_name == "number":
            return ("number", repr(node.value))  # '-0.0' != '0.0'; '1.0' canonical
        return (node.type_name, node.value)  # specials carry value None -> reflexive
    if isinstance(node, HArray):
        return ("array", tuple(semantic_key(i) for i in node.items))
    if isinstance(node, HObject):
        return ("object", tuple((n, semantic_key(c)) for n, c in node.fields))
    raise TypeError(type(node).__name__)


def semantically_equal(a: DatasetH, b: DatasetH) -> bool:
    return semantic_key(a.root) == semantic_key(b.root)

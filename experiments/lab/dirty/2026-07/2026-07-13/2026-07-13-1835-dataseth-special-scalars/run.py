"""Stage-2 checks: special scalars A vs C — RT under the semantic oracle, matrix, bytes.

Reproducible; writes artifacts/ (matrix, RT counter-proof, bytes comparison, wire samples).
Run: python run.py   (from this directory or repo root)
"""

from __future__ import annotations

import math
from pathlib import Path

from model_ext import (
    DatasetH,
    from_jsonlike,
    from_python_ext,
    semantic_key,
    semantically_equal,
)
from wire_ac import WireError, decode, encode

ART = Path(__file__).resolve().parent / "artifacts"
ART.mkdir(exist_ok=True)

NAN, INF = float("nan"), float("inf")

# ---- falsification matrix (the plan's table, executable) ----
MATRIX = [
    # presence
    ("absent-field", {"a": 1}),
    ("null-field", {"a": 1, "b": None}),
    ("empty-string", {"a": ""}),
    ("string-null-word", {"a": "null"}),
    # non-finites: value vs the string that spells it
    ("nan-value", {"a": NAN}),
    ("string-NaN", {"a": "NaN"}),
    ("pos-inf-value", {"a": INF}),
    ("string-Infinity", {"a": "Infinity"}),
    ("neg-inf-value", {"a": -INF}),
    ("string-neg-Infinity", {"a": "-Infinity"}),
    ("string-escape-stress", {"a": "\\NaN", "b": "\\\\Infinity", "c": "\\x"}),
    # numbers
    ("int-1", {"a": 1}),
    ("number-1.0", {"a": 1.0}),
    ("string-1", {"a": "1"}),
    ("string-1.0", {"a": "1.0"}),
    ("neg-zero", {"a": -0.0}),
    ("pos-zero", {"a": 0.0}),
    # containers
    ("empty-object", {"a": {}}),
    ("empty-array", {"a": []}),
    ("mixed-array-with-specials", [1, "NaN", NAN, None, INF, True]),
    ("array-in-array-specials", {"m": [[NAN], [], [INF, -INF]]}),
]

MUST_DIFFER = [
    ("absent-field", "null-field"),
    ("null-field", "empty-string"),
    ("empty-string", "string-null-word"),
    ("nan-value", "string-NaN"),
    ("pos-inf-value", "string-Infinity"),
    ("neg-inf-value", "string-neg-Infinity"),
    ("int-1", "number-1.0"),
    ("number-1.0", "string-1.0"),
    ("neg-zero", "pos-zero"),
    ("empty-object", "empty-array"),
]


def main() -> None:
    lines = []

    # (0) why the ORACLE is mandatory — registered traps of naive equality
    dz_neg = from_python_ext({"a": -0.0})
    dz_pos = from_python_ext({"a": 0.0})
    naive_collapses = dz_neg == dz_pos  # dataclass eq: -0.0 == 0.0 -> True
    oracle_distinct = not semantically_equal(dz_neg, dz_pos)
    assert naive_collapses and oracle_distinct
    nan_reflexive = semantically_equal(from_python_ext({"a": NAN}), from_python_ext({"a": NAN}))
    assert nan_reflexive  # as a typed kind; as a raw float it would be False
    lines.append("oracle traps: naive == collapses -0.0/0.0 = True ; oracle distinguishes = True")
    lines.append("oracle traps: NaN reflexive under oracle (typed kind) = True")
    lines.append("")

    # (1) two origins (P3): python tree vs declared JSON-like text -> SAME DatasetH
    py_origin = from_python_ext({"x": [NAN, INF, -INF, None, "NaN"]})
    jl_origin = from_jsonlike('{"x": [NaN, Infinity, -Infinity, null, "NaN"]}')
    assert semantically_equal(py_origin, jl_origin)
    lines.append("two origins (python tree vs JSON-like declared grammar): same DatasetH = True")
    lines.append("")

    # (2) RT under the oracle, for A and C, across the whole matrix; collect wires
    wires = {"A": {}, "C": {}}
    for label, value in MATRIX:
        ds = from_python_ext(value)
        for variant in ("A", "C"):
            wire = encode(ds, variant)
            back = decode(wire, variant)
            ok = semantically_equal(back, ds)
            assert ok, f"RT({variant}) FAILED on {label}"
            wires[variant][label] = wire
        lines.append(f"matrix {label:28s} RT(A) = True   RT(C) = True")
    lines.append("")

    # (3) distinctness in DatasetH and on BOTH wires
    lines.append("distinctness (dataset + wire A + wire C):")
    values = dict(MATRIX)
    for a, b in MUST_DIFFER:
        ka = semantic_key(from_python_ext(values[a]).root)
        kb = semantic_key(from_python_ext(values[b]).root)
        wa = wires["A"][a] != wires["A"][b]
        wc = wires["C"][a] != wires["C"][b]
        assert ka != kb and wa and wc, f"COLLISION {a} vs {b}"
        lines.append(f"  {a:24s} != {b:24s} : oracle=True wireA=True wireC=True")
    lines.append("")

    # (4) declared SEMANTIC equivalence (not a collision): lexical number forms
    same = semantically_equal(from_jsonlike('{"a": 1e3}'), from_jsonlike('{"a": 1000.0}'))
    assert same
    lines.append("declared equivalence: 1e3 == 1000.0 (value preserved, lexeme not) = True")
    lines.append("")

    # (5) fail-loud (casos originais + guards da verificacao adversarial 2026-07-13:
    # canal N so' finito; int canonico; V nao-terminado; chave duplicada no wire)
    bad_cases = [
        ("#TCF.8H\nVnan\n", "C", "V tag under variant C"),
        ("#TCF.8H\nNnan\n", "A", "Nnan (non-finite on N channel, A)"),
        ("#TCF.8H\nNnan\n", "C", "Nnan (non-finite on N channel, C)"),
        ("#TCF.8H\nNInfinity\n", "A", "NInfinity"),
        ("#TCF.8H\nO-1\n", "A", "negative count"),
        ("#TCF.8H\nI+5\n", "A", "I+5 non-canonical int"),
        ("#TCF.8H\nS03\nabc", "A", "S03 leading-zero length"),
        ("#TCF.8H\nVnan", "A", "unterminated V token"),
        ("#TCF.8H\nO2\nK1\naZ\nK1\naT\n", "A", "duplicate key on wire"),
    ]
    for bad, variant, what in bad_cases:
        try:
            decode(bad, variant)
        except WireError:
            lines.append(f"fail-loud: {what} = True")
        else:
            raise AssertionError(f"must fail-loud: {what}")

    # (5b) model guards (verificacao adversarial): chave nao-str NAO coage;
    # from_jsonlike REJEITA chave duplicada (sem last-key-wins calado)
    from model_ext import DuplicateFieldError
    try:
        from_python_ext({1: "x"})
    except TypeError:
        lines.append("model guard: non-str key fail-loud (no str() coercion) = True")
    else:
        raise AssertionError("non-str key must fail-loud")
    try:
        from_jsonlike('{"a": 1, "a": 2}')
    except DuplicateFieldError:
        lines.append("model guard: from_jsonlike rejects duplicate keys = True")
    else:
        raise AssertionError("duplicate JSON-like keys must fail-loud")

    (ART / "02-rt-counterproof.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")

    # (6) bytes: specials-heavy, lookalike-strings-heavy, neutral
    def wire_len(value, variant):
        return len(encode(from_python_ext(value), variant).encode())

    profiles = {
        "specials-heavy (100 NaN leaves)": [NAN] * 100,
        "lookalike-strings (100 'NaN' strings)": ["NaN"] * 100,
        "backslash-strings (100 '\\\\x' strings)": ["\\x"] * 100,
        "neutral (100 plain strings)": ["abc"] * 100,
    }
    cmp_lines = ["profile | bytes A | bytes C | delta C-A"]
    for name, value in profiles.items():
        a, c = wire_len(value, "A"), wire_len(value, "C")
        cmp_lines.append(f"{name} | {a} | {c} | {c - a:+d}")
    (ART / "04-bytes-comparison.txt").write_text("\n".join(cmp_lines) + "\n", encoding="utf-8")

    # (7) inspectable wire samples
    sample = from_python_ext({"v": [NAN, "NaN", INF, "\\x", -0.0]})
    (ART / "01-wire-sample-A.txt").write_text(encode(sample, "A"), encoding="utf-8")
    (ART / "03-wire-sample-C.txt").write_text(encode(sample, "C"), encoding="utf-8")

    print("stage-2: all checks PASS")
    print(f"  {len(MATRIX)} matrix cases x 2 variants, {len(MUST_DIFFER)} distinctness pairs")
    print("--- bytes ---")
    print("\n".join(cmp_lines))
    print("--- wire A ---")
    print(encode(sample, "A"))
    print("--- wire C ---")
    print(encode(sample, "C"))


if __name__ == "__main__":
    main()

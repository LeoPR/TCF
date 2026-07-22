"""Stage-1 codec checks: DatasetH -> TCF.H -> DatasetH round-trip + topology matrix.

Reproducible. Writes artifacts/ (wire sample, RT counter-proof, falsification matrix)
per the visibility/traceability commitment. Does NOT touch src/tcf, dataset_h.py or run.py.

Run: python run_codec.py
"""

from __future__ import annotations

import json
from pathlib import Path

from codec_h import decode_h, encode_h, TCFHDecodeError
from dataset_h import DatasetH
from run import PYTHON_SOURCE, SOURCE_JSON  # reuse the owner's R0/R1 fixtures

ART = Path(__file__).resolve().parent / "artifacts"
ART.mkdir(exist_ok=True)


def rt(ds: DatasetH) -> DatasetH:
    """decode_h(encode_h(ds)) — the core stage-1 gate."""
    return decode_h(encode_h(ds))


# ---- topology / presence / basic-scalar falsification matrix (stage 1) ----
# Each entry: (label, python_value). RT must preserve it; DISTINCT entries must
# NOT collapse to the same DatasetH (no information loss).
MATRIX = [
    ("absent-field", {"a": 1}),
    ("null-field", {"a": 1, "b": None}),
    ("empty-string", {"a": ""}),
    ("string-null-word", {"a": "null"}),
    ("int-1", {"a": 1}),
    ("number-1.0", {"a": 1.0}),
    ("string-1", {"a": "1"}),
    ("string-1.0", {"a": "1.0"}),
    ("bool-true", {"a": True}),
    ("bool-false", {"a": False}),
    ("empty-object", {"a": {}}),
    ("empty-array", {"a": []}),
    ("array-in-array", {"a": [[1, 2], [], [3]]}),
    ("ragged-objects", [{"k": "email", "v": "x", "verified": True}, {"k": "phone", "v": "y"}]),
    ("mixed-array-with-null", [1, "1", None, True]),
    ("newline-in-string", {"note": "line 1\nline 2"}),
    ("string-spells-structure", {"a": "O3", "b": "{x:1}", "c": "S5\nZ"}),
    ("scalar-root-string", "just a string"),
    ("scalar-root-int", 42),
    ("scalar-root-null", None),
    ("unicode-key-and-value", {"naïve": "José 日本語  "}),
    ("deep-nesting", {"a": {"b": {"c": {"d": [{"e": [1, [2, [3]]]}]}}}}),
]


def main() -> None:
    lines = []  # RT counter-proof log

    # (1) round-trip on the owner's R0/R1 fixtures
    ds_json = DatasetH.from_json(SOURCE_JSON)
    ds_py = DatasetH.from_python(PYTHON_SOURCE)
    assert ds_json == ds_py, "R0/R1 baseline drift: json != python source"

    rt_json = rt(ds_json)
    assert rt_json == ds_json, "RT FAILED on SOURCE_JSON fixture"
    # full bridge: json -> DatasetH -> TCF.H -> DatasetH -> json (semantic)
    round_json = rt_json.to_json()
    assert json.loads(round_json) == json.loads(SOURCE_JSON), "JSON bridge semantic RT failed"
    lines.append("fixture SOURCE_JSON: DatasetH->TCF.H->DatasetH RT = True")
    lines.append("bridge json->DatasetH->TCF.H->DatasetH->json (semantic) = True")

    # wire sample artifact (inspectable)
    wire = encode_h(ds_json)
    (ART / "01-wire-sample.txt").write_text(wire, encoding="utf-8")

    # (2) falsification matrix — RT + distinctness
    encoded = {}
    for label, value in MATRIX:
        ds = DatasetH.from_python(value)
        back = rt(ds)
        ok = back == ds
        assert ok, f"RT FAILED on matrix case {label!r}"
        encoded[label] = encode_h(ds)
        lines.append(f"matrix {label:26s} RT = {ok}")

    # distinctness: the pairs the plan says must never collide
    must_differ = [
        ("absent-field", "null-field"),
        ("null-field", "empty-string"),
        ("empty-string", "string-null-word"),
        ("int-1", "number-1.0"),
        ("int-1", "string-1"),
        ("number-1.0", "string-1.0"),
        ("empty-object", "empty-array"),
        ("bool-true", "string-1"),
    ]
    lines.append("")
    lines.append("distinctness (must NOT collide after codec):")
    for a, b in must_differ:
        distinct = DatasetH.from_python(dict(MATRIX)[a]) != DatasetH.from_python(dict(MATRIX)[b])
        wire_distinct = encoded[a] != encoded[b]
        assert distinct and wire_distinct, f"COLLISION between {a} and {b}"
        lines.append(f"  {a:20s} != {b:20s} : dataset={distinct} wire={wire_distinct}")

    # (3) fail-loud on malformed input
    # (Nnan/Ninf, O-1, I+5, S03, dup-key: guards adicionados pela verificacao
    # adversarial 2026-07-13 — float()/int() lenientes aceitavam formas que
    # nenhum encode produz; canal N e' so' de finitos.)
    malformed = [
        "", "#TCF.8M\nx", "#TCF.8H\nQ\n", "#TCF.8H\nS5\nhi", "#TCF.8H\nO1\nK1\naZ\nextra",
        "#TCF.8H\nNnan\n", "#TCF.8H\nNinf\n", "#TCF.8H\nN-Infinity\n",
        "#TCF.8H\nO-1\n", "#TCF.8H\nI+5\n", "#TCF.8H\nI0_5\n", "#TCF.8H\nS03\nabc",
        "#TCF.8H\nO2\nK1\naZ\nK1\naT\n",  # chave duplicada no wire
    ]
    lines.append("")
    lines.append("fail-loud on malformed (must raise):")
    for m in malformed:
        try:
            decode_h(m)
        except TCFHDecodeError:
            lines.append(f"  raised TCFHDecodeError on {m!r:40s} OK")
        else:
            raise AssertionError(f"malformed input did not fail-loud: {m!r}")

    (ART / "02-rt-counterproof.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")

    # (4) matrix artifact: value -> wire (inspectable)
    mx = []
    for label, value in MATRIX:
        mx.append(f"### {label}")
        mx.append(f"python: {value!r}")
        mx.append("tcf.h:")
        mx.append(encoded[label])
        mx.append("")
    (ART / "03-falsification-matrix.txt").write_text("\n".join(mx), encoding="utf-8")

    print("stage-1 codec: all round-trips PASS")
    print(f"  fixtures + {len(MATRIX)} matrix cases + distinctness + fail-loud")
    print(f"  artifacts in {ART}")
    print("--- wire sample (SOURCE_JSON) ---")
    print(wire)


if __name__ == "__main__":
    main()

"""Regenerate all S0-S3 evidence. Zero imports from src/tcf."""

from __future__ import annotations

import json
from pathlib import Path
import re

from ir import build_ir, lossy_boundary_counterexample, relationship_forms
from model import (
    CycleError,
    DatasetH,
    DatasetHError,
    DepthLimitError,
    DuplicateFieldError,
    HArray,
    HObject,
    HScalar,
)
from oracle import OracleWireError, decode, encode

HERE = Path(__file__).resolve().parent
INPUTS = HERE / "inputs"
INTERMEDIATES = HERE / "intermediates"
OUTPUTS = HERE / "outputs"
INTERMEDIATES.mkdir(exist_ok=True)
OUTPUTS.mkdir(exist_ok=True)


def field(obj: HObject, name: str):
    return next(child for field_name, child in obj.fields if field_name == name)


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def expect_error(label: str, expected: type[Exception], operation, lines: list[str]) -> None:
    try:
        operation()
    except expected as exc:
        lines.append(f"OK {label}: {type(exc).__name__}: {exc}")
    else:
        raise AssertionError(f"{label}: expected {expected.__name__}")


def main() -> None:
    source = DatasetH.from_json((INPUTS / "01-corpus-json-completo.json").read_text(encoding="utf-8"))
    if not isinstance(source.root, HObject):
        raise AssertionError("corpus root must be an object")
    cases_node = field(source.root, "cases")
    if not isinstance(cases_node, HArray):
        raise AssertionError("cases must be an array")

    canonical = source.canonical_json() + "\n"
    (INTERMEDIATES / "01-corpus-canonico.json").write_text(canonical, encoding="utf-8", newline="\n")

    rebuilt_cases = []
    all_ir = []
    all_forms = []
    byte_rows = []
    for index, case in enumerate(cases_node.items, start=1):
        if not isinstance(case, HObject):
            raise AssertionError("each case must be an object")
        name_node = field(case, "name")
        if not isinstance(name_node, HScalar) or name_node.kind != "string":
            raise AssertionError("case name must be a string")
        name = str(name_node.value)
        value = field(case, "value")
        dataset = DatasetH(value)
        wire = encode(dataset)
        wire_path = OUTPUTS / f"{index:02d}-{slug(name)}.tcf"
        wire_path.write_bytes(wire)
        decoded = decode(wire)
        if decoded != dataset:
            raise AssertionError(f"semantic RT failed for {name}")

        logical_ir = build_ir(dataset)
        forms = relationship_forms(logical_ir)
        all_ir.append({"name": name, **logical_ir})
        all_forms.append({"name": name, **forms})
        rebuilt_fields = tuple(
            (field_name, decoded.root if field_name == "value" else child)
            for field_name, child in case.fields
        )
        rebuilt_cases.append(HObject(rebuilt_fields))
        byte_rows.append({"case": name, "wire_bytes": len(wire), "nodes": len(logical_ir["nodes"]), "edges": len(logical_ir["edges"])})

    rebuilt = DatasetH(HObject((("cases", HArray(tuple(rebuilt_cases))),)))
    roundtrip = rebuilt.canonical_json() + "\n"
    if roundtrip.encode("utf-8") != canonical.encode("utf-8"):
        raise AssertionError("corpus round-trip is not byte-identical to canonical intermediate")
    (OUTPUTS / "21-corpus.roundtrip.json").write_text(roundtrip, encoding="utf-8", newline="\n")

    (INTERMEDIATES / "02-ir-logico.json").write_text(
        json.dumps(all_ir, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    (INTERMEDIATES / "03-formas-de-vinculo.json").write_text(
        json.dumps(all_forms, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    (OUTPUTS / "22-bytes.csv").write_text(
        "case,wire_bytes,nodes,edges\n"
        + "".join(f"{row['case']},{row['wire_bytes']},{row['nodes']},{row['edges']}\n" for row in byte_rows),
        encoding="utf-8",
        newline="\n",
    )

    failures: list[str] = []
    duplicate_text = (INPUTS / "02-duplicate-key-invalid.json").read_text(encoding="utf-8")
    expect_error("duplicate-key", DuplicateFieldError, lambda: DatasetH.from_json(duplicate_text), failures)
    expect_error("NaN", DatasetHError, lambda: DatasetH.from_json("NaN"), failures)
    expect_error("Infinity", DatasetHError, lambda: DatasetH.from_json("Infinity"), failures)

    cycle: list = []
    cycle.append(cycle)
    expect_error("cycle", CycleError, lambda: DatasetH.from_python(cycle), failures)

    deep = None
    for _ in range(130):
        deep = [deep]
    expect_error("total-depth", DepthLimitError, lambda: DatasetH.from_python(deep), failures)

    valid = encode(DatasetH.from_json('{"a":1}'))
    expect_error("wire-trailing", OracleWireError, lambda: decode(valid + b"x"), failures)
    expect_error("wire-unknown-tag", OracleWireError, lambda: decode(valid.replace(b"I1", b"X1")), failures)
    expect_error("wire-truncated", OracleWireError, lambda: decode(valid[:-1]), failures)

    counterexample = lossy_boundary_counterexample()
    if counterexample["parent_index"] == counterexample["competing_parent_index"]:
        raise AssertionError("counterexample must contain distinct linkages")
    (OUTPUTS / "23-contraprovas.txt").write_text(
        "S0/S1 FAIL-LOUD\n" + "\n".join(failures) + "\n\n"
        "S3 FRONTEIRA LOSSY\n" + json.dumps(counterexample, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    total_bytes = sum(row["wire_bytes"] for row in byte_rows)
    (OUTPUTS / "24-resultado.txt").write_text(
        "S0-S3 RESULTADO PROBATORIO\n"
        f"cases_rt={len(byte_rows)}/{len(byte_rows)}\n"
        f"link_algebra={len(all_forms)}/{len(all_forms)}\n"
        f"fail_loud={len(failures)}/{len(failures)}\n"
        f"wire_files={len(byte_rows)}\n"
        f"wire_bytes_total={total_bytes}\n"
        "canonical_roundtrip=BYTE_IDENTICAL\n"
        "src_tcf_imported=NO\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"OK: {len(byte_rows)} RT; {len(all_forms)} link algebras; {len(failures)} fail-loud")


if __name__ == "__main__":
    main()

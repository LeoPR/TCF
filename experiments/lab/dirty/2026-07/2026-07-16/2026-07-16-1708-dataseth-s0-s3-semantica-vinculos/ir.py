"""Source-neutral logical IR and equivalent S3 relationship carriers."""

from __future__ import annotations

from decimal import Decimal
from itertools import accumulate

from model import DatasetH, HArray, HNode, HObject, HScalar, decimal_token


def build_ir(dataset: DatasetH) -> dict:
    nodes: list[dict] = []
    edges: list[dict] = []
    lanes: dict[str, list[dict]] = {}

    def visit(node: HNode) -> int:
        node_id = len(nodes)
        record = {"id": node_id, "kind": _kind(node)}
        nodes.append(record)
        if isinstance(node, HScalar):
            value = _json_value(node)
            lanes.setdefault(node.kind, []).append({"node": node_id, "value": value})
            return node_id
        children = node.fields if isinstance(node, HObject) else tuple((None, item) for item in node.items)
        for ordinal, (label, child) in enumerate(children):
            child_id = visit(child)
            edges.append(
                {"parent": node_id, "child": child_id, "ordinal": ordinal, "label": label}
            )
        return node_id

    root = visit(dataset.root)
    edges.sort(key=lambda edge: (edge["parent"], edge["ordinal"]))
    return {"root": root, "nodes": nodes, "edges": edges, "value_lanes": lanes}


def _kind(node: HNode) -> str:
    if isinstance(node, HObject):
        return "object"
    if isinstance(node, HArray):
        return "array"
    return node.kind


def _json_value(node: HScalar):
    if isinstance(node.value, Decimal):
        return decimal_token(node.value)
    return node.value


def relationship_forms(ir: dict) -> dict:
    parent_ids = [node["id"] for node in ir["nodes"] if node["kind"] in ("object", "array")]
    parent_position = {node_id: index for index, node_id in enumerate(parent_ids)}
    edges = ir["edges"]
    expected = [parent_position[edge["parent"]] for edge in edges]

    counts = [0] * len(parent_ids)
    for parent_index in expected:
        counts[parent_index] += 1
    offsets = [0, *accumulate(counts)]

    steps: list[int] = []
    previous_nonempty = -1
    previous_child_parent = None
    for parent_index in expected:
        if parent_index == previous_child_parent:
            steps.append(0)
        else:
            steps.append(parent_index - previous_nonempty)
            previous_nonempty = parent_index
            previous_child_parent = parent_index

    payload = [
        {"child": edge["child"], "ordinal": edge["ordinal"], "label": edge["label"]}
        for edge in edges
    ]
    forms = {
        "parent_domain": parent_ids,
        "edge_payload": payload,
        "counts": counts,
        "offsets": offsets,
        "parent_index": expected,
        "steps": steps,
    }
    validate_relationship_forms(forms)
    return forms


def validate_relationship_forms(forms: dict) -> None:
    expected = forms["parent_index"]
    if _from_counts(forms["counts"]) != expected:
        raise AssertionError("counts do not reconstruct parent linkage")
    if _from_offsets(forms["offsets"]) != expected:
        raise AssertionError("offsets do not reconstruct parent linkage")
    if _from_steps(forms["steps"]) != expected:
        raise AssertionError("steps do not reconstruct parent linkage")
    if len(forms["edge_payload"]) != len(expected):
        raise AssertionError("edge payload is not aligned with linkage")


def _from_counts(counts: list[int]) -> list[int]:
    return [parent for parent, count in enumerate(counts) for _ in range(count)]


def _from_offsets(offsets: list[int]) -> list[int]:
    return [parent for parent in range(len(offsets) - 1) for _ in range(offsets[parent + 1] - offsets[parent])]


def _from_steps(steps: list[int]) -> list[int]:
    out = []
    current = -1
    for step in steps:
        if step:
            current += step
        if current < 0:
            raise AssertionError("invalid relationship step")
        out.append(current)
    return out


def lossy_boundary_counterexample() -> dict:
    parent_index = [0, 2, 2]
    first_bits = [True, True, False]
    competing_parent_index = [0, 1, 1]
    return {
        "parent_count": 3,
        "parent_index": parent_index,
        "competing_parent_index": competing_parent_index,
        "first_child_bits_both": first_bits,
        "conclusion": "first-child bits alone lose the skipped empty parent; steps retain it",
    }

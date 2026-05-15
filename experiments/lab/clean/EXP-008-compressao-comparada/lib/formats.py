"""Input formats for the comparative compression experiment.

Cada formato expoe `serialize(linhas) -> str` e `parse(texto) -> list[str]`.
RT obrigatorio: `parse(serialize(linhas)) == linhas`.

Formatos:
- csv:   `val\\n<l1>\\n<l2>\\n...\\n` (com header)
- jsonl: `{"val":"<l1>"}\\n{"val":"<l2>"}\\n...`
- json:  `["<l1>","<l2>",...]` (array)
- tcf:   `encode(linhas)` (TCF v0.6 — OBAT + HCC)
"""

from __future__ import annotations

import json
from typing import Callable


def csv_serialize(linhas: list[str]) -> str:
    return "val\n" + "\n".join(linhas) + "\n"


def csv_parse(text: str) -> list[str]:
    rows = text.split("\n")
    if rows and rows[-1] == "":
        rows = rows[:-1]
    return rows[1:]  # drop header "val"


def jsonl_serialize(linhas: list[str]) -> str:
    return (
        "\n".join(
            json.dumps({"val": l}, ensure_ascii=False) for l in linhas
        )
        + "\n"
    )


def jsonl_parse(text: str) -> list[str]:
    parts = text.split("\n")
    if parts and parts[-1] == "":
        parts = parts[:-1]
    return [json.loads(p)["val"] for p in parts]


def json_serialize(linhas: list[str]) -> str:
    return json.dumps(linhas, ensure_ascii=False)


def json_parse(text: str) -> list[str]:
    return list(json.loads(text))


def build_formats(
    encode_fn: Callable[[list[str]], str],
    decode_fn: Callable[[str], list[str]],
) -> dict[str, dict]:
    """Retorna dict de formats com metadados (incluindo tcf)."""
    return {
        "csv": {
            "serialize": csv_serialize,
            "parse":     csv_parse,
            "ext":       "csv",
            "descricao": "CSV com header `val`",
        },
        "jsonl": {
            "serialize": jsonl_serialize,
            "parse":     jsonl_parse,
            "ext":       "jsonl",
            "descricao": "JSON Lines (1 objeto por linha)",
        },
        "json": {
            "serialize": json_serialize,
            "parse":     json_parse,
            "ext":       "json",
            "descricao": "JSON array",
        },
        "tcf": {
            "serialize": encode_fn,
            "parse":     decode_fn,
            "ext":       "tcf",
            "descricao": "TCF v0.6 (OBAT + HCC)",
        },
    }

import json
from typing import Any, Dict, List, Tuple


def flatten_record(rec: Dict[str, Any], parent: str = "") -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for k, v in rec.items():
        key = f"{parent}.{k}" if parent else k
        if isinstance(v, dict):
            out.update(flatten_record(v, key))
        else:
            out[key] = v
    return out


def load_consolidated(path: str) -> Dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def choose_table(data: Dict[str, List[Dict[str, Any]]], preferred: str | None = None) -> str:
    if preferred and preferred in data:
        return preferred
    # Prefer table with nested objects
    for tname, rows in data.items():
        if any(isinstance(v, dict) for r in rows for v in r.values()):
            return tname
    # else first
    return next(iter(data))


def make_rows(consolidated: Dict[str, Any], table: str) -> List[Dict[str, Any]]:
    rows = consolidated["data"].get(table, [])
    return [flatten_record(r) for r in rows]


def chunk_rows(rows: List[Dict[str, Any]], rows_per_chunk: int = 200) -> List[List[Dict[str, Any]]]:
    chunks: List[List[Dict[str, Any]]] = []
    for i in range(0, len(rows), rows_per_chunk):
        chunks.append(rows[i:i+rows_per_chunk])
    return chunks


def format_chunk(ch: List[Dict[str, Any]], strategy: str = "jsonl") -> str:
    if strategy == "jsonl":
        return "\n".join(json.dumps(r, ensure_ascii=False) for r in ch)
    if strategy == "json":
        return json.dumps(ch, ensure_ascii=False)
    if strategy == "mdtable":
        # Markdown table for quick visual runs (lossy types)
        if not ch:
            return ""
        cols = list(ch[0].keys())
        lines = ["|" + "|".join(cols) + "|",
                 "|" + "|".join(["---"]*len(cols)) + "|"]
        for r in ch:
            lines.append("|" + "|".join(str(r.get(c, "")) for c in cols) + "|")
        return "\n".join(lines)
    raise ValueError(f"Unknown strategy: {strategy}")

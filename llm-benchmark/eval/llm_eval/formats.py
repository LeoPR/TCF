import csv
import io
import json
from typing import Any, Dict, Iterable, List, Sequence, Tuple

Row = Dict[str, Any]


def _render_header(label: str, hints: Sequence[str]) -> str:
    lines = [f"# formato: {label}"]
    for hint in hints:
        if hint:
            lines.append(f"# {hint}")
    lines.append("# Use apenas os dados abaixo, nada mais.")
    return "\n".join(lines)


def _detect_columns(rows: Sequence[Row], preferred: Sequence[str] | None = None) -> List[str]:
    if preferred:
        return list(preferred)
    if not rows:
        return []
    # Preserve insertion order from first row for readability
    return list(rows[0].keys())


def _normalize_cell(value: Any) -> Any:
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False)
    return value if value is not None else ""


def _format_toon_scalar(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    text = str(value)
    if not text:
        return ""
    sanitized = text.replace("\n", " ")
    needs_quotes = sanitized.strip() != sanitized or any(ch in sanitized for ch in [",", "{", "}", "[", "]", ":"])
    if needs_quotes:
        return json.dumps(sanitized, ensure_ascii=False)
    return sanitized


def _render_delimited(rows: Sequence[Row], delimiter: str, label: str, hints: Sequence[str], columns: Sequence[str] | None = None) -> str:
    header = _render_header(label, hints)
    cols = _detect_columns(rows, columns)
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=delimiter, lineterminator="\n")
    writer.writerow(cols)
    for row in rows:
        writer.writerow([_normalize_cell(row.get(col, "")) for col in cols])
    return header + "\n" + buffer.getvalue().strip()


def format_csv(rows: Sequence[Row], columns: Sequence[str] | None = None) -> str:
    return _render_delimited(
        rows,
        delimiter=",",
        label="CSV",
        hints=(
            "A primeira linha contém os nomes das colunas.",
            "Cada linha subsequente representa um registro separado.",
        ),
        columns=columns,
    )


def format_tsv(rows: Sequence[Row], columns: Sequence[str] | None = None) -> str:
    return _render_delimited(
        rows,
        delimiter="\t",
        label="TSV",
        hints=(
            "Colunas separadas por TAB (\t).",
            "A primeira linha contém os nomes das colunas.",
        ),
        columns=columns,
    )


def format_jsonl(rows: Sequence[Row]) -> str:
    header = _render_header(
        "JSONL",
        (
            "Cada linha a seguir é um objeto JSON independente.",
            "Leia linha por linha sem misturar campos de registros diferentes.",
        ),
    )
    body = "\n".join(json.dumps(row, ensure_ascii=False) for row in rows)
    return header + "\n" + body


def format_ndjson(rows: Sequence[Row]) -> str:
    # Alias para JSONL (mesma estrutura)
    return format_jsonl(rows)


def format_token_object(rows: Sequence[Row], columns: Sequence[str] | None = None) -> str:
    """TOON textual encoding (https://github.com/toon-format/toon)."""
    header = _render_header(
        "TOON",
        (
            "Token-Oriented Object Notation (TOON): formato compacto para LLMs.",
            "Arrays uniformes usam a sintaxe [N]{col1,col2}.",
            "Cada linha abaixo representa uma linha tabular separada por vírgulas.",
        ),
    )
    cols = _detect_columns(rows, columns)
    block_header = f"dados[{len(rows)}]{{{','.join(cols)}}}:" if cols else f"dados[{len(rows)}]:"
    lines = [header, block_header]
    for row in rows:
        row_values = [_format_toon_scalar(row.get(col)) for col in cols]
        lines.append("  " + ",".join(row_values))
    return "\n".join(lines)


def format_mdtable(rows: Sequence[Row]) -> str:
    header = _render_header(
        "MARKDOWN_TABLE",
        (
            "Representação em tabela Markdown (uso principalmente visual).",
            "Pode haver perda de tipos para campos complexos.",
        ),
    )
    if not rows:
        return header + "\n# Tabela vazia"
    cols = _detect_columns(rows)
    lines = ["|" + "|".join(cols) + "|", "|" + "|".join(["---"] * len(cols)) + "|"]
    for row in rows:
        lines.append("|" + "|".join(str(_normalize_cell(row.get(col, ""))) for col in cols) + "|")
    return header + "\n" + "\n".join(lines)


def format_tcf(tcf_text: str) -> str:
    """Wrap a pre-generated TCF string with a minimal instruction header."""
    header = _render_header(
        "TCF",
        (
            "Textual Columnar Format.",
            "Cada bloco começa com nome da coluna seguido de ':'.",
            "N*val = val repetido N vezes consecutivamente.",
            "Dados podem estar ordenados para agrupar repetições.",
        ),
    )
    return header + "\n" + tcf_text.strip()


FORMATTERS: Dict[str, Any] = {
    "csv": format_csv,
    "tsv": format_tsv,
    "jsonl": format_jsonl,
    "ndjson": format_ndjson,
    "token_object": format_token_object,
    "mdtable": format_mdtable,
    "tcf": format_tcf,  # TCF receives pre-generated string, not rows
}


def render_format(rows: Sequence[Row], format_name: str, columns: Sequence[str] | None = None) -> str:
    if format_name not in FORMATTERS:
        raise ValueError(f"Formato desconhecido: {format_name}")
    if format_name == "tcf":
        raise ValueError("TCF não usa rows — passe o texto TCF diretamente via format_tcf()")
    formatter = FORMATTERS[format_name]
    if format_name in {"csv", "tsv", "token_object"}:
        return formatter(rows, columns=columns)
    return formatter(rows)


def list_formats() -> List[str]:
    return list(FORMATTERS.keys())

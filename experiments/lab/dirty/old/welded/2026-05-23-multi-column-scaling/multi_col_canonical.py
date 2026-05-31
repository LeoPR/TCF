"""Multi-column canonical — port de EXP-011 pra src/tcf M10.

Mudancas vs EXP-011:
- Usa `from tcf import encode, decode` (canonical M10 pipeline completo)
  ao inves de `from delta_aware import encode_column, decode_column`
  (EXP-010 prototype)
- `tcf.encode()` NAO emite shebang single-col; multi-col adiciona
  `#TCF.6 M` + meta line conforme convencao ADR-0004 / EXP-011
- Sem `col_options` (M10 e' auto-tuned via ColumnFeatures)

API:
  encode_table(table: dict[str, list[str]]) -> tuple[str, dict]
  decode_table(tcf_text: str) -> dict[str, list[str]]

Header format (ADR-0004 / O-FMT-11b):

  #TCF.6 M
  # <size1>=<name1>,<size2>=<name2>,...
  <body1><body2>... (concatenado, byte-precise por size)

Restricoes:
- Nomes de coluna nao podem conter `,` ou `=`
- Todas colunas mesmo n_rows
"""

from __future__ import annotations

import sys
from pathlib import Path

# Garantir que src/tcf esta no path
THIS = Path(__file__).parent
ROOT = THIS.parents[3]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tcf import encode, decode  # noqa: E402


MAGIC_MULTI = b"#TCF.6 M"
META_PREFIX = b"# "


def encode_table(table: dict[str, list[str]]) -> tuple[str, dict]:
    """Encode tabela multi-coluna pra TCF v0.6 canonical M10.

    Args:
        table: {col_name: [val1, val2, ...]}. Todas colunas mesma length.

    Returns:
        (tcf_text, info) — info tem total_bytes, header_bytes, body_bytes,
        per_col_bytes, etc.
    """
    if not table:
        raise ValueError("table vazia")

    lengths = {col: len(vals) for col, vals in table.items()}
    if len(set(lengths.values())) > 1:
        raise ValueError(f"colunas com lengths diferentes: {lengths}")

    for col_name in table.keys():
        if ',' in col_name or '=' in col_name:
            raise ValueError(f"col name contem char reservado: {col_name!r}")

    col_bodies_bytes = []
    per_col = {}
    for col_name, values in table.items():
        # Garantir strings (real-world SQL pode retornar int/float/None)
        str_values = [_to_str(v) for v in values]
        body = encode(str_values, header=col_name)
        body_bytes = body.encode("utf-8")
        col_bodies_bytes.append((col_name, body_bytes))
        per_col[col_name] = {
            "n_values": len(values),
            "body_bytes": len(body_bytes),
        }

    meta_pairs = ",".join(f"{len(b)}={name}" for name, b in col_bodies_bytes)
    header = MAGIC_MULTI + b"\n" + META_PREFIX + meta_pairs.encode("utf-8") + b"\n"
    body_concat = b"".join(b for _, b in col_bodies_bytes)
    full = header + body_concat
    text = full.decode("utf-8")

    info = {
        "n_rows": next(iter(lengths.values())),
        "n_cols": len(table),
        "total_bytes": len(full),
        "header_bytes": len(header),
        "body_bytes": len(body_concat),
        "per_col": per_col,
    }
    return text, info


def decode_table(tcf_text: str) -> dict[str, list[str]]:
    """Decode TCF v0.6 multi-column em dict[col_name, rows]."""
    raw = tcf_text.encode("utf-8")
    cursor = 0

    nl1 = raw.find(b"\n")
    if nl1 == -1:
        raise ValueError("formato invalido: sem linha 1 (shebang)")
    line1 = raw[:nl1]
    if not line1.startswith(MAGIC_MULTI):
        raise ValueError(
            f"magic invalido: esperado {MAGIC_MULTI!r}, got {line1[:20]!r}"
        )
    cursor = nl1 + 1

    nl2 = raw.find(b"\n", cursor)
    if nl2 == -1:
        raise ValueError("formato invalido: sem linha de meta")
    line2 = raw[cursor:nl2]
    if not line2.startswith(META_PREFIX):
        raise ValueError(
            f"meta invalido: esperado {META_PREFIX!r} prefix, got {line2[:5]!r}"
        )
    meta_str = line2[len(META_PREFIX):].decode("utf-8")
    pairs = []
    for p in meta_str.split(","):
        size_str, name = p.split("=", 1)
        pairs.append((int(size_str), name))

    cursor = nl2 + 1
    result = {}
    for size, name in pairs:
        body_bytes = raw[cursor:cursor + size]
        body_text = body_bytes.decode("utf-8")
        result[name] = decode(body_text)
        cursor += size

    return result


def _to_str(v) -> str:
    """Stringify uniform pra TCF (que opera em strings).

    NULL/None -> '' (empty string).
    """
    if v is None:
        return ""
    return str(v)

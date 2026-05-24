"""TCF multi-column — implementacao interna + aliases deprecated.

Pos-ADR-0014 (API unificada): a funcao publica e' `encode(dict)` /
`decode(text)` em `tcf.encoder` / `tcf.decoder`. Este modulo provê:

1. Implementacao interna: `_encode_multi` + `_decode_multi`, chamados
   por `encode()` / `decode()` quando dispatch identifica tipo dict
   ou shebang `#TCF.6 M`.

2. Aliases deprecated: `encode_table` + `decode_table` re-exportados
   pra back-compat (emite DeprecationWarning).

Header format (ADR-0004 + ADR-0013):

    #TCF.6 M
    # <size1>=<name1>,<size2>=<name2>,...
    <body1><body2>... (concatenado, byte-precise por size)

Restricoes:
- Nomes de coluna nao podem conter `,` ou `=`
- Todas colunas devem ter mesmo numero de valores
- NULL/None convertido pra '' (empty string)
"""

from __future__ import annotations

import warnings

from tcf.encoder import _encode_column
from tcf.side_outputs import SideOutputs


MAGIC_MULTI = b"#TCF.6 M"
META_PREFIX = b"# "


def _encode_multi(
    table: dict[str, list[str]],
    side_outputs: SideOutputs | None = None,
) -> str:
    """Interno: encode dict pra TCF multi-col. Chamado por `encode()`."""
    if not table:
        raise ValueError("table vazia")

    lengths = {col: len(vals) for col, vals in table.items()}
    if len(set(lengths.values())) > 1:
        raise ValueError(f"colunas com lengths diferentes: {lengths}")

    for col_name in table.keys():
        if ',' in col_name or '=' in col_name:
            raise ValueError(f"col name contem char reservado: {col_name!r}")

    if side_outputs is not None:
        side_outputs.per_col = {}

    col_bodies_bytes: list[tuple[str, bytes]] = []
    for col_name, values in table.items():
        str_values = [_to_str(v) for v in values]
        per_col_side = SideOutputs() if side_outputs is not None else None
        body = _encode_column(str_values, header=col_name, side=per_col_side)
        body_bytes = body.encode("utf-8")
        col_bodies_bytes.append((col_name, body_bytes))
        if side_outputs is not None:
            side_outputs.per_col[col_name] = per_col_side

    meta_pairs = ",".join(f"{len(b)}={name}" for name, b in col_bodies_bytes)
    header = MAGIC_MULTI + b"\n" + META_PREFIX + meta_pairs.encode("utf-8") + b"\n"
    body_concat = b"".join(b for _, b in col_bodies_bytes)
    full = header + body_concat
    text = full.decode("utf-8")

    if side_outputs is not None:
        side_outputs.multi_info = {
            "n_rows": next(iter(lengths.values())),
            "n_cols": len(table),
            "total_bytes": len(full),
            "header_bytes": len(header),
            "body_bytes": len(body_concat),
        }

    return text


def _decode_multi(tcf_text: str) -> dict[str, list[str]]:
    """Interno: decode TCF multi-col. Chamado por `decode()`."""
    from tcf.decoder import _decode_column

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
    result: dict[str, list[str]] = {}
    for size, name in pairs:
        body_bytes = raw[cursor:cursor + size]
        body_text = body_bytes.decode("utf-8")
        result[name] = _decode_column(body_text)
        cursor += size

    return result


def _to_str(v) -> str:
    """Stringify uniforme. NULL/None -> '' (ADR-0013)."""
    if v is None:
        return ""
    return str(v)


# === Deprecated aliases (mantidos pra migracao em passos) ===
# Pos-ADR-0014: use `encode(dict)` / `decode(text)` em vez disso.

def encode_table(table: dict[str, list[str]]) -> tuple[str, dict]:
    """DEPRECATED (ADR-0014): use `encode(dict)` em vez disso.

    Mantido pra migracao em passos. Retorna `(text, legacy_info)` onde
    legacy_info eh o dict que `encode_table` retornava pre-ADR-0014.
    """
    warnings.warn(
        "encode_table esta deprecated. Use `encode(dict)` em vez disso. "
        "Pra obter info detalhada, passe `side_outputs=SideOutputs()`.",
        DeprecationWarning,
        stacklevel=2,
    )
    side = SideOutputs()
    text = _encode_multi(table, side_outputs=side)
    legacy_info = dict(side.multi_info or {})
    legacy_info["per_col"] = {
        name: {
            "n_values": len(table[name]),
            "body_bytes": s.body_bytes or 0,
        }
        for name, s in (side.per_col or {}).items()
    }
    return text, legacy_info


def decode_table(tcf_text: str) -> dict[str, list[str]]:
    """DEPRECATED (ADR-0014): use `decode(text)` em vez disso.

    Mantido pra migracao em passos. Comportamento identico ao decoder
    unificado quando aplicado a multi-col.
    """
    warnings.warn(
        "decode_table esta deprecated. Use `decode(text)` em vez disso "
        "(roteia automaticamente pelo shebang).",
        DeprecationWarning,
        stacklevel=2,
    )
    return _decode_multi(tcf_text)

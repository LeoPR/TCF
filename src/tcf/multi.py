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

import os
import warnings
from concurrent.futures import ProcessPoolExecutor

from tcf.encoder import _encode_column
from tcf.side_outputs import SideOutputs


MAGIC_MULTI = b"#TCF.6 M"
META_PREFIX = b"# "


def _encode_multi(
    table: dict[str, list[str]],
    side_outputs: SideOutputs | None = None,
    parallel: bool | int = False,
) -> str:
    """Interno: encode dict pra TCF multi-col. Chamado por `encode()`.

    Args:
        table: dict[col_name, list[str]].
        side_outputs: opcional, recipiente pra capturar info per-coluna.
        parallel: False (default serial), True (cpu_count workers),
            int N >= 1 (N workers explicitos). Workers paralelizam
            `_encode_column` por coluna via ProcessPoolExecutor.
    """
    if not table:
        raise ValueError("table vazia")

    lengths = {col: len(vals) for col, vals in table.items()}
    if len(set(lengths.values())) > 1:
        raise ValueError(f"colunas com lengths diferentes: {lengths}")

    for col_name in table.keys():
        if ',' in col_name or '=' in col_name:
            raise ValueError(f"col name contem char reservado: {col_name!r}")

    # Stringify upfront (per-col paralelo recebe valores ja' string)
    table_str: dict[str, list[str]] = {
        name: [_to_str(v) for v in values]
        for name, values in table.items()
    }

    # Dispatch paralelo se solicitado E vale a pena (>= 2 cols)
    use_parallel = bool(parallel) and len(table_str) >= 2
    n_workers = 0
    if use_parallel:
        if parallel is True:
            n_workers = os.cpu_count() or 1
        else:  # int >= 1 (bool(0)/False filtrados acima)
            n_workers = int(parallel)
        n_workers = max(1, min(n_workers, len(table_str)))
        col_bodies_bytes, per_col_sides = _encode_columns_parallel(
            table_str, want_side=(side_outputs is not None), n_workers=n_workers
        )
    else:
        col_bodies_bytes, per_col_sides = _encode_columns_serial(
            table_str, want_side=(side_outputs is not None)
        )

    if side_outputs is not None:
        side_outputs.per_col = dict(per_col_sides)

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
            "parallel_workers": n_workers if use_parallel else 0,
        }

    return text


def _encode_columns_serial(
    table_str: dict[str, list[str]],
    want_side: bool,
) -> tuple[list[tuple[str, bytes]], dict[str, SideOutputs]]:
    """Encoda colunas serialmente (comportamento original)."""
    col_bodies: list[tuple[str, bytes]] = []
    per_col_sides: dict[str, SideOutputs] = {}
    for col_name, str_values in table_str.items():
        side = SideOutputs() if want_side else None
        body = _encode_column(str_values, header=col_name, side=side)
        col_bodies.append((col_name, body.encode("utf-8")))
        if want_side:
            per_col_sides[col_name] = side
    return col_bodies, per_col_sides


def _encode_columns_parallel(
    table_str: dict[str, list[str]],
    want_side: bool,
    n_workers: int,
) -> tuple[list[tuple[str, bytes]], dict[str, SideOutputs]]:
    """Encoda colunas em paralelo via ProcessPoolExecutor.

    Output byte-identico ao serial — ordem preservada via
    `ProcessPoolExecutor.map` (mantem ordem de submissao).
    """
    col_names = list(table_str.keys())
    args_iter = [(name, table_str[name], want_side) for name in col_names]
    with ProcessPoolExecutor(max_workers=n_workers) as ex:
        results = list(ex.map(_worker_encode_column, args_iter))

    col_bodies: list[tuple[str, bytes]] = []
    per_col_sides: dict[str, SideOutputs] = {}
    for col_name, body_str, side in results:
        col_bodies.append((col_name, body_str.encode("utf-8")))
        if want_side:
            per_col_sides[col_name] = side
    return col_bodies, per_col_sides


def _worker_encode_column(args: tuple[str, list[str], bool]) -> tuple[str, str, SideOutputs | None]:
    """Worker module-level (picklavel) pra ProcessPoolExecutor.

    Recebe (col_name, str_values, want_side); retorna (col_name, body_str, side).
    """
    col_name, str_values, want_side = args
    side = SideOutputs() if want_side else None
    body = _encode_column(str_values, header=col_name, side=side)
    return col_name, body, side


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

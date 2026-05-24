"""TCF multi-column — encode_table / decode_table (ADR-0013).

API publica multi-column. Aplica pipeline canonical M10 (`encode` /
`decode`) por coluna independentemente, agregando bodies com header
compacto byte-precise.

Header format (ADR-0004 + ADR-0013):

    #TCF.6 M
    # <size1>=<name1>,<size2>=<name2>,...
    <body1><body2>... (concatenado, byte-precise por size)

Onde:
- `#TCF.6 M` = magic + flag multi-column (8 bytes + LF)
- `# s=n,s=n,...` = pares size=name (size em bytes UTF-8 do body)
- Bodies concatenados sem delimitador (sizes garantem separacao)

Restricoes:
- Nomes de coluna nao podem conter `,` ou `=`
- Todas colunas devem ter mesmo numero de valores
- NULL/None convertido pra '' (empty string); cf. ADR-0013 NULL handling

Uso minimo:

    from tcf import encode_table, decode_table

    table = {"id": ["1", "2", "3"], "name": ["a", "b", "c"]}
    tcf_text, info = encode_table(table)
    decoded = decode_table(tcf_text)
    assert decoded == table

Validacao em real-world: 9 tabelas (Adult Census + TPC-H tier 1+2,
136k linhas, 15.8MB raw) -> -33.02% weighted vs raw, -31.46% vs
single-col concat, RT 9/9. Ver T-EXP-MULTI-COL-SCALING ticket.
"""

from __future__ import annotations

from tcf.decoder import decode
from tcf.encoder import encode


MAGIC_MULTI = b"#TCF.6 M"
META_PREFIX = b"# "


def encode_table(table: dict[str, list[str]]) -> tuple[str, dict]:
    """Encode tabela multi-coluna pra TCF v0.6 canonical M10.

    Parametros:
        table: {col_name: [val1, val2, ...]}. Todas colunas mesma length.
            NULL/None convertido automaticamente pra '' (empty string).

    Retorna:
        (tcf_text, info) onde info tem total_bytes, header_bytes,
        body_bytes, per_col (com body_bytes e n_values por coluna).

    Levanta:
        ValueError se table vazia, colunas com lengths diferentes,
        ou nomes contendo `,` ou `=` (caracteres reservados do header).
    """
    if not table:
        raise ValueError("table vazia")

    lengths = {col: len(vals) for col, vals in table.items()}
    if len(set(lengths.values())) > 1:
        raise ValueError(f"colunas com lengths diferentes: {lengths}")

    for col_name in table.keys():
        if ',' in col_name or '=' in col_name:
            raise ValueError(f"col name contem char reservado: {col_name!r}")

    col_bodies_bytes: list[tuple[str, bytes]] = []
    per_col: dict[str, dict] = {}
    for col_name, values in table.items():
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
    """Decode TCF v0.6 multi-column em dict[col_name, list[str]].

    Parametros:
        tcf_text: conteudo TCF multi-column (com shebang `#TCF.6 M`
            + meta line `# size=name,...` + bodies concatenados).

    Retorna:
        dict[col_name, list[str]] na ordem do header.

    Levanta:
        ValueError se formato invalido (sem shebang, magic errado,
        sem meta line).
    """
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
        result[name] = decode(body_text)
        cursor += size

    return result


def _to_str(v) -> str:
    """Stringify uniforme pra TCF (que opera em strings).

    NULL/None -> '' (empty string). Cf. ADR-0013 NULL handling.
    """
    if v is None:
        return ""
    return str(v)

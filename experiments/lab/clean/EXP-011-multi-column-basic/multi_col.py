"""Multi-column basico — header compacto seguindo convencao shebang TCF.

API:
  encode_table(table: dict[str, list[str]]) -> str
  decode_table(tcf_text: str) -> dict[str, list[str]]

Header (corrigido 2026-05-17 com convencao versao TCF):

  #TCF.6 M
  # <size1>=<name1>,<size2>=<name2>,...
  <body1><body2>... (concatenado, byte-precise por size)

Onde:
- `#TCF.6` = magic + versao 0.6 (regra: major 0 omite "0", escreve `.<minor>`)
  - 0.5 → `#TCF.5`, 0.6 → `#TCF.6`, 1.0 → `#TCF1`, 1.3 → `#TCF1.3`
- `M` = flag multi-column (single-col tambem tem shebang `#TCF.6` mas sem flag)
- `# s=n,s=n,...` = pares size=name (size em bytes UTF-8 do body)
- Bodies concatenados sem delimitador

Restricoes assumidas:
- Nomes de coluna nao contem `,` ou `=`
- Header sempre emitido por default; exception: `include_shebang=False`
  quando caller garante formato/versao out-of-band
- Mobile per-channel header pra transmissao paralela: ver O-FMT-13
  em `../../dirty/notas/futuras-otimizacoes-formato.md`
"""

from __future__ import annotations

import sys
from pathlib import Path

THIS = Path(__file__).parent
EXP_010 = THIS.parent / "EXP-010-tcf-delta-aware-prototype"
sys.path.insert(0, str(EXP_010))

from delta_aware import encode_column, decode_column  # noqa: E402


MAGIC_MULTI = b"#TCF.6 M"
META_PREFIX = b"# "


def encode_table(table: dict[str, list[str]],
                  col_options: dict[str, dict] | None = None,
                  include_shebang: bool = True) -> tuple[str, dict]:
    """Encode tabela multi-coluna pra TCF v0.6 com header compacto.

    Args:
        table: {col_name: [val1, val2, ...]}. Todas mesma length.
        col_options: opcional, {col_name: {arg: val}}.
        include_shebang: default True (sempre emite header). False
                         quando caller garante formato/versao
                         out-of-band (caso excepcional).

    Returns:
        (tcf_text, info)
    """
    if not table:
        raise ValueError("table vazia")
    lengths = {col: len(vals) for col, vals in table.items()}
    if len(set(lengths.values())) > 1:
        raise ValueError(f"colunas com lengths diferentes: {lengths}")

    for col_name in table.keys():
        if ',' in col_name or '=' in col_name:
            raise ValueError(f"col name contem char reservado: {col_name!r}")

    col_options = col_options or {}
    col_info_per_col = {}
    col_bodies_bytes = []
    for col_name, values in table.items():
        opts = col_options.get(col_name, {})
        # Sub-encoders sem shebang (encoder de tabela ja' cuida)
        opts_no_shebang = {**opts, "include_shebang": False}
        body, info = encode_column(values, header=col_name, **opts_no_shebang)
        body_bytes = body.encode("utf-8")
        col_bodies_bytes.append((col_name, body_bytes))
        col_info_per_col[col_name] = info

    # Header (default emit)
    if include_shebang:
        meta_pairs = ",".join(f"{len(b)}={name}" for name, b in col_bodies_bytes)
        header = MAGIC_MULTI + b"\n" + META_PREFIX + meta_pairs.encode("utf-8") + b"\n"
    else:
        # Excepcional — caller garante formato. Mas precisa de SIZES
        # de alguma forma (decoder nao consegue sem). Por enquanto,
        # forcamos inclusao de meta line mesmo sem shebang.
        meta_pairs = ",".join(f"{len(b)}={name}" for name, b in col_bodies_bytes)
        header = META_PREFIX + meta_pairs.encode("utf-8") + b"\n"

    body_concat = b"".join(b for _, b in col_bodies_bytes)
    full = header + body_concat
    text = full.decode("utf-8")

    info = {
        "n_rows": next(iter(lengths.values())),
        "n_cols": len(table),
        "col_info": col_info_per_col,
        "total_bytes": len(full),
        "header_bytes": len(header),
        "body_bytes": len(body_concat),
    }
    return text, info


def decode_table(tcf_text: str,
                  expect_shebang: bool = True) -> dict[str, list[str]]:
    """Decode TCF v0.6 multi-column em dict[col_name, rows].

    Args:
        tcf_text: conteudo TCF.
        expect_shebang: default True. False quando caller garante
                        out-of-band que header foi omitido.
    """
    raw = tcf_text.encode("utf-8")
    cursor = 0

    if expect_shebang:
        nl1 = raw.find(b"\n")
        if nl1 == -1:
            raise ValueError("formato invalido: sem linha 1")
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
        if not body_text.endswith("\n"):
            body_text += "\n"
        result[name] = decode_column(body_text, expect_shebang=False)
        cursor += size

    return result

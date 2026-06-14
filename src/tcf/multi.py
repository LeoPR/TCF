"""TCF multi-column — implementacao interna + aliases deprecated.

Pos-ADR-0014 (API unificada): a funcao publica e' `encode(dict)` /
`decode(text)` em `tcf.encoder` / `tcf.decoder`. Este modulo provê:

1. Implementacao interna: `_encode_multi` + `_decode_multi`, chamados
   por `encode()` / `decode()` quando dispatch identifica tipo dict
   ou shebang `#TCF.6 M`.

2. Aliases deprecated: `encode_table` + `decode_table` re-exportados
   pra back-compat (emite DeprecationWarning).

Header format. **0.7 / #TCF.7 e' o DEFAULT** (ADR-0024); o #TCF.6 legado segue
produzivel internamente (`_encode_multi(fallback=False, min_header=False)`) e
LIDO pelo decoder.

#TCF.7 (default) — meta SEM prefixo (o flag `M` no shebang ja' declara que a
proxima linha e' o meta de colunas, ADR-0023):

    #TCF.7 M
    <s1>=<n1>,!<s2>=<n2>,...,<nN>
    <body1><raw_body2>...<bodyN>

    - `!` antes do size = coluna em modo RAW (body = "\\n".join(valores),
      escolhido quando menor que o TCF — V2-A, ADR-0022). `!` nunca colide com
      nome (size e' digito).
    - ULTIMA coluna sem size (corpo ate' EOF, igual single-col — ADR-0023): par
      sem `=`.
    - bodies concatenados byte-precise (sem delimitador; sizes no meta).

#TCF.6 (legado) — meta com prefixo `# ` e todos os sizes:

    #TCF.6 M
    # <s1>=<n1>,<s2>=<n2>,...,<sN>=<nN>
    <body1><body2>...

Decoder self-describing: #TCF.6 exige `# `; #TCF.7 dispensa o prefixo (tolerante
a `# `/`#`/nenhum). Le ambos os magics sem flag.

Restricoes:
- Nomes de coluna nao podem conter `,` ou `=`
- Todas colunas devem ter mesmo numero de valores
- NULL/None convertido pra '' (empty string)
"""

from __future__ import annotations

import os
import warnings
from concurrent.futures import ProcessPoolExecutor, as_completed

from tcf.encoder import _encode_column
from tcf.pipeline import DEFAULT_PIPELINE, PipelineConfig
from tcf.side_outputs import SideOutputs


MAGIC_MULTI = b"#TCF.6 M"
MAGIC_MULTI_V2 = b"#TCF.7 M"  # V2-A fallback identity (ADR-0022, abre v2.0)
META_PREFIX = b"# "  # v1 (#TCF.6, congelado). #TCF.7 dispensa o prefixo do meta
                     # (o flag `M` no shebang ja' declara multi-col) — ADR-0023.


def _encode_multi(
    table: dict[str, list[str]],
    side_outputs: SideOutputs | None = None,
    parallel: bool | int = False,
    cfg: PipelineConfig = DEFAULT_PIPELINE,
    fallback: bool = True,
    min_header: bool = True,
) -> str:
    """Interno: encode dict pra TCF multi-col. Chamado por `encode()`.

    Args:
        table: dict[col_name, list[str]].
        side_outputs: opcional, recipiente pra capturar info per-coluna.
        parallel: False (default serial), True (cpu_count workers),
            int N >= 1 (N workers explicitos). Workers paralelizam
            `_encode_column` por coluna via ProcessPoolExecutor.
        cfg: PipelineConfig pra controle de camadas (T-CODE-LAYERED-PIPELINE
            Fase 1). Default = M10 canonical.
        fallback: V2-A fallback identity (ADR-0022). **Default True** (0.7 e' o
            default, ADR-0024). Por coluna escolhe min(TCF, raw). False ->
            mantem TCF em toda coluna (usado p/ produzir o legado #TCF.6 em
            comparacao/regressao; o `encode()` publico nao expoe este toggle).
        min_header: header v2 minimo (ADR-0023, O-FMT-15+16). **Default True**.
            Meta sem prefixo (o flag M ja' declara colunas) + ultima coluna sem
            size (corpo ate' EOF). False -> header legado `# size=name,...`.
            (fallback=False E min_header=False juntos -> #TCF.6 byte-identico ao
            legado, p/ comparacao.)
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
            table_str, want_side=(side_outputs is not None),
            n_workers=n_workers, cfg=cfg,
        )
    else:
        col_bodies_bytes, per_col_sides = _encode_columns_serial(
            table_str, want_side=(side_outputs is not None), cfg=cfg,
        )

    if side_outputs is not None:
        side_outputs.per_col = dict(per_col_sides)

    # V2-A fallback identity (ADR-0022). Opt-in (fallback=True). Por coluna,
    # escolhe min(TCF, raw). Raw = "\n".join(valores), usado so' quando e'
    # ESTRITAMENTE menor E seguro (sem '\n' embutido — que quebraria o split
    # do decode). Marca raw com '!' ANTES do size no par meta (`!<size>=<name>`)
    # — '!' so' aparece em #TCF.7 e nunca colide com nomes (size e' digito).
    # Emite #TCF.7 M sse ALGUMA coluna cai pra raw; senao #TCF.6 M byte-
    # identico ao v1 (default fallback=False sempre cai aqui).
    fallback_cols: list[str] = []
    final_bodies: list[tuple[str, bytes, str]] = []  # (name, body, mode)
    for name, tcf_bytes in col_bodies_bytes:
        if fallback and _fallback_safe(table_str[name]):
            raw_bytes = "\n".join(table_str[name]).encode("utf-8")
            if len(raw_bytes) < len(tcf_bytes):
                final_bodies.append((name, raw_bytes, "raw"))
                fallback_cols.append(name)
                continue
        final_bodies.append((name, tcf_bytes, "tcf"))

    used_fallback = bool(fallback_cols)
    used_v2 = used_fallback or min_header
    magic = MAGIC_MULTI_V2 if used_v2 else MAGIC_MULTI

    # Meta line. #TCF.7 (qualquer feature v2) DISPENSA o prefixo do meta: o flag
    # `M` no shebang ja' declara que a proxima linha e' o meta das colunas, entao
    # o `# ` e' redundante (revisao do header v0.6, ADR-0023). #TCF.6 mantem o
    # `# ` (congelado, ADR-0017).
    # min_header tambem OMITE o size da ULTIMA coluna (corpo ate' EOF — igual ao
    # single-col, O-FMT-15). '!' (V2-A raw) compoe normalmente.
    last_i = len(final_bodies) - 1
    parts = []
    for i, (name, b, mode) in enumerate(final_bodies):
        pre = "!" if mode == "raw" else ""
        if min_header and i == last_i:
            parts.append(f"{pre}{name}")            # ultima sem size
        else:
            parts.append(f"{pre}{len(b)}={name}")
    meta_pairs = ",".join(parts)
    meta_prefix = b"" if used_v2 else META_PREFIX
    header = magic + b"\n" + meta_prefix + meta_pairs.encode("utf-8") + b"\n"
    body_concat = b"".join(b for _, b, _ in final_bodies)
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
            "format": "v2" if used_v2 else "v1",
            "fallback_cols": list(fallback_cols),
            "min_header": min_header,
        }

    return text


def _encode_columns_serial(
    table_str: dict[str, list[str]],
    want_side: bool,
    cfg: PipelineConfig = DEFAULT_PIPELINE,
) -> tuple[list[tuple[str, bytes]], dict[str, SideOutputs]]:
    """Encoda colunas serialmente (comportamento original)."""
    col_bodies: list[tuple[str, bytes]] = []
    per_col_sides: dict[str, SideOutputs] = {}
    for col_name, str_values in table_str.items():
        side = SideOutputs() if want_side else None
        body = _encode_column(str_values, header=col_name, side=side, cfg=cfg)
        col_bodies.append((col_name, body.encode("utf-8")))
        if want_side:
            per_col_sides[col_name] = side
    return col_bodies, per_col_sides


def _encode_columns_parallel(
    table_str: dict[str, list[str]],
    want_side: bool,
    n_workers: int,
    cfg: PipelineConfig = DEFAULT_PIPELINE,
) -> tuple[list[tuple[str, bytes]], dict[str, SideOutputs]]:
    """Encoda colunas em paralelo via ProcessPoolExecutor (Fase 1b: work-stealing).

    Estrategia (sub-fase otimizacao 2026-05-24):
    1. **Ordena colunas por workload descendente** (sum de bytes por coluna)
       — heavyweights submetidos primeiro, workers ocupam mais cedo
    2. **Submit + as_completed** ao inves de map — work-stealing dinamico
       (workers pegam proxima coluna assim que terminam, sem esperar
       fila sequencial)
    3. **Reordena resultado** por ordem original do dict (output
       byte-identico independente da ordem de conclusao)

    Output byte-identico ao serial — paralelismo apenas reordena
    computacao, nao bytes.
    """
    original_order = list(table_str.keys())

    # Heuristica de workload: sum de bytes de cada coluna (proxy razoavel
    # pra custo HCC que e' dominado pelo tamanho dos valores). Sorted desc.
    cols_with_work = sorted(
        (
            (sum(len(v) for v in table_str[name]), name)
            for name in original_order
        ),
        key=lambda x: -x[0],
    )

    results_by_name: dict[str, tuple[str, SideOutputs | None]] = {}
    with ProcessPoolExecutor(max_workers=n_workers) as ex:
        future_to_name = {
            ex.submit(_worker_encode_column, (name, table_str[name], want_side, cfg)): name
            for _, name in cols_with_work
        }
        for future in as_completed(future_to_name):
            col_name, body_str, side = future.result()
            results_by_name[col_name] = (body_str, side)

    # Reordena pela ordem original do dict (output deterministico)
    col_bodies: list[tuple[str, bytes]] = []
    per_col_sides: dict[str, SideOutputs] = {}
    for name in original_order:
        body_str, side = results_by_name[name]
        col_bodies.append((name, body_str.encode("utf-8")))
        if want_side:
            per_col_sides[name] = side
    return col_bodies, per_col_sides


def _worker_encode_column(args: tuple[str, list[str], bool, PipelineConfig]) -> tuple[str, str, SideOutputs | None]:
    """Worker module-level (picklavel) pra ProcessPoolExecutor.

    Recebe (col_name, str_values, want_side, cfg); retorna (col_name, body_str, side).
    """
    col_name, str_values, want_side, cfg = args
    side = SideOutputs() if want_side else None
    body = _encode_column(str_values, header=col_name, side=side, cfg=cfg)
    return col_name, body, side


def _decode_multi(tcf_text: str) -> dict[str, list[str]]:
    """Interno: decode TCF multi-col. Chamado por `decode()`.

    Aceita #TCF.6 M (v1, meta com prefixo `# `) e #TCF.7 M (v2, meta SEM prefixo
    — o flag M ja' declara colunas, ADR-0023). Em #TCF.7: par com `!` = coluna
    raw / fallback (V2-A, ADR-0022); par sem `=` = ultima coluna com size
    omitido (min_header, corpo ate' EOF). Self-describing: magic + forma dos
    pares dizem tudo, sem flag no decode.
    """
    from tcf.decoder import _decode_column

    raw = tcf_text.encode("utf-8")
    cursor = 0

    nl1 = raw.find(b"\n")
    if nl1 == -1:
        raise ValueError("formato invalido: sem linha 1 (shebang)")
    line1 = raw[:nl1]
    is_v7 = line1.startswith(MAGIC_MULTI_V2)
    if not (line1.startswith(MAGIC_MULTI) or is_v7):
        raise ValueError(
            f"magic invalido: esperado {MAGIC_MULTI!r} ou {MAGIC_MULTI_V2!r}, "
            f"got {line1[:20]!r}"
        )
    cursor = nl1 + 1

    nl2 = raw.find(b"\n", cursor)
    if nl2 == -1:
        raise ValueError("formato invalido: sem linha de meta")
    line2 = raw[cursor:nl2]
    # Meta line. #TCF.6 (congelado) exige o prefixo '# '. #TCF.7 dispensa-o (o
    # flag `M` no shebang ja' declara o meta de colunas, ADR-0023) — aceita
    # tolerante: '# ', '#' avulso, ou sem prefixo (forma canonical v7).
    if line2.startswith(META_PREFIX):          # b"# "
        meta_str = line2[len(META_PREFIX):].decode("utf-8")
    elif is_v7:
        meta_str = (line2[1:] if line2.startswith(b"#") else line2).decode("utf-8")
    else:
        raise ValueError(
            f"meta invalido (#TCF.6 exige '# '): got {line2[:5]!r}"
        )
    pairs = []  # (size|None, name, mode)
    for p in meta_str.split(","):
        if p.startswith("!"):
            mode = "raw"
            p = p[1:]
        else:
            mode = "tcf"
        if "=" in p:
            size_str, name = p.split("=", 1)
            pairs.append((int(size_str), name, mode))
        else:
            # size omitido (header v2 minimo): ultima coluna, corpo ate' EOF
            pairs.append((None, p, mode))

    cursor = nl2 + 1
    result: dict[str, list[str]] = {}
    for size, name, mode in pairs:
        if size is None:
            body_bytes = raw[cursor:]              # ate' EOF (ultima coluna)
        else:
            body_bytes = raw[cursor:cursor + size]
        body_text = body_bytes.decode("utf-8")
        if mode == "raw":
            # V2-A: body raw = "\n".join(valores); split exato (sem '\n'
            # embutido, garantido por _fallback_safe no encode).
            result[name] = body_text.split("\n")
        else:
            result[name] = _decode_column(body_text)
        cursor += len(body_bytes)

    return result


def _to_str(v) -> str:
    """Stringify uniforme. NULL/None -> '' (ADR-0013)."""
    if v is None:
        return ""
    return str(v)


def _fallback_safe(values: list[str]) -> bool:
    """Raw mode (V2-A) e' seguro sse nenhum valor tem '\\n' embutido.

    Body raw = "\\n".join(values); decode faz body.split("\\n"). Um '\\n'
    dentro de um valor quebraria a contagem de valores. (O caminho TCF tambem
    assume valores sem '\\n' — premissa de 'dados felizes' — entao isto nao
    restringe alem do que ja' e' assumido; apenas evita escolher raw onde
    seria lossy.)
    """
    return not any("\n" in v for v in values)


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

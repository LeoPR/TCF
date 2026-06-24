"""TCF multi-column — implementacao interna.

Pos-ADR-0014 (API unificada): a funcao publica e' `encode(dict)` /
`decode(text)` em `tcf.encoder` / `tcf.decoder`. Este modulo provê a
implementacao interna `_encode_multi` + `_decode_multi`, chamados por
`encode()` / `decode()` quando dispatch identifica tipo dict ou shebang
`#TCF.6 M`/`#TCF.7 M`.

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
import re
from concurrent.futures import ProcessPoolExecutor, as_completed

from tcf.encoder import _encode_column
from tcf.pipeline import DEFAULT_PIPELINE, PipelineConfig
from tcf.side_outputs import SideOutputs


MAGIC_MULTI = b"#TCF.6 M"
MAGIC_MULTI_V2 = b"#TCF.7 M"  # V2-A fallback identity (ADR-0022, abre v2.0)
META_PREFIX = b"# "  # v1 (#TCF.6, congelado). #TCF.7 dispensa o prefixo do meta
                     # (o flag `M` no shebang ja' declara multi-col) — ADR-0023.

# --- V2-B dicionario/categorico (ADR-0025) ---
# Coluna low-card -> [tabela de unicos: encode(unicas)] + [stream de indices].
# Alfabeto printable 0x21..0x7E (94 chars, exclui '\n'): K<=94 -> 1 char/linha.
# Marcador '@<size>=<name>' no header #TCF.7 (ao lado de '!' raw e tcf normal).
# Slot = b"<ntable>\n" + table_bytes + stream  (ntable = bytes da tabela ->
# fronteira inequivoca; width derivado de K apos decodar a tabela).
_V2B_ALPHA = "".join(chr(c) for c in range(0x21, 0x7F))
_V2B_BASE = len(_V2B_ALPHA)
_V2B_MAX_CARD = 1024  # gating: acima disso V2-B nao compensa (evita custo)


def _v2b_width(k: int) -> int:
    """chars por indice no alfabeto base-94 (minimo w com base^w >= k)."""
    w, cap = 1, _V2B_BASE
    while k > cap:
        w += 1
        cap *= _V2B_BASE
    return w


def _v2b_idx_chars(idx: int, width: int) -> str:
    """indice inteiro -> `width` chars base-94 (big-endian)."""
    if width == 1:
        return _V2B_ALPHA[idx]
    out = []
    for _ in range(width):
        out.append(_V2B_ALPHA[idx % _V2B_BASE])
        idx //= _V2B_BASE
    return "".join(reversed(out))


def _v2b_encode(values: list[str], *, cfg: PipelineConfig,
                min_len: int | None) -> bytes | None:
    """Candidato V2-B. Retorna body bytes, ou None se nao aplicavel (high-card
    ou sem repeticao). Caller escolhe min(tcf, raw, v2b) no fallback."""
    seen: dict[str, int] = {}
    unicas: list[str] = []
    for v in values:
        if v not in seen:
            seen[v] = len(unicas)
            unicas.append(v)
            if len(unicas) > _V2B_MAX_CARD:
                return None  # high-card -> V2-B improvavel, evita o sub-encode
    K = len(unicas)
    N = len(values)
    if K < 2 or K >= N:
        return None  # sem repeticao -> nada a ganhar
    width = _v2b_width(K)
    table_bytes = _encode_column(unicas, header="val", cfg=cfg,
                                 min_len=min_len).encode("utf-8")
    stream = "".join(_v2b_idx_chars(seen[v], width) for v in values)
    return f"{len(table_bytes)}\n".encode("utf-8") + table_bytes + stream.encode("utf-8")


def _decode_v2b(body_bytes: bytes) -> list[str]:
    """Decoda slot V2-B: <ntable>\\n + table + stream -> lista de valores."""
    from tcf.decoder import _decode_column

    nl = body_bytes.find(b"\n")
    ntable = int(body_bytes[:nl])
    start = nl + 1
    unicas = _decode_column(body_bytes[start:start + ntable].decode("utf-8"))
    width = _v2b_width(len(unicas))
    stream = body_bytes[start + ntable:]  # ASCII, len == N*width
    out: list[str] = []
    for j in range(0, len(stream), width):
        idx = 0
        for ch in stream[j:j + width]:  # ch e' int (byte)
            idx = idx * _V2B_BASE + (ch - 0x21)
        out.append(unicas[idx])
    return out


# --- Split estrutural (ADR-0026, H-STRUCT-01) ---
# Valor estruturado (decimal, data, datetime, CPF/CNPJ) = grupos de DIGITOS
# separados por NAO-digitos. Se TODOS os valores tem o MESMO template (mesmos
# separadores, mesma contagem de campos), os grupos de digito viram colunas-campo
# e o template e' guardado 1x. Cada campo tende a low-card -> esmagado pelo V2-B
# (sinergia, o motor do ganho). Marcador `%<size>=<name>` no header #TCF.7.
# Slot = <ntmpl>\n + template_blob + field_subtable(#TCF.7 M).
#   template_blob = (<bytelen>:<bytes>) por parte nao-digito (nf+1 partes).
_DIGITS = re.compile(r"(\d+)")


def _struct_split_encode(values: list[str], *, cfg: PipelineConfig,
                         min_len: int | None) -> bytes | None:
    """Candidato split estrutural. Retorna body bytes, ou None se nao aplicavel
    (template nao-uniforme, <2 campos, ou campos todos constantes)."""
    if len(values) < 2:
        return None
    toks0 = _DIGITS.split(values[0])
    nf = len(toks0) // 2
    if nf < 2:
        return None  # <2 campos de digito -> nada a ganhar com split
    sig = tuple(toks0[::2])  # nf+1 partes nao-digito (o template)
    all_toks = [toks0]
    for v in values[1:]:
        t = _DIGITS.split(v)
        if len(t) // 2 != nf or tuple(t[::2]) != sig:
            return None  # template NAO-uniforme -> nao splita (gate 100%)
        all_toks.append(t)
    fields = [[t[1 + 2 * fi] for t in all_toks] for fi in range(nf)]
    if all(len(set(f)) <= 1 for f in fields):
        return None  # sem variacao real -> dedup/OBAT ja' cobre
    # sub-table de campos -> reusa o pipeline multi-col (-> V2-B nos campos low-card).
    # Campos sao digitos puros -> _struct_split_encode neles retorna None (sem recursao).
    sub_bytes = _encode_multi(
        {f"c{i}": f for i, f in enumerate(fields)}, cfg=cfg, min_len=min_len
    ).encode("utf-8")
    tmpl_blob = b"".join(
        str(len(pb)).encode() + b":" + pb
        for p in sig for pb in (p.encode("utf-8"),)
    )
    return str(len(tmpl_blob)).encode() + b"\n" + tmpl_blob + sub_bytes


def _decode_struct_split(body_bytes: bytes) -> list[str]:
    """Decoda slot split estrutural: template + sub-table de campos -> valores."""
    nl = body_bytes.find(b"\n")
    ntmpl = int(body_bytes[:nl])
    start = nl + 1
    tmpl_blob = body_bytes[start:start + ntmpl]
    sub = body_bytes[start + ntmpl:]
    parts: list[str] = []
    i = 0
    while i < len(tmpl_blob):
        c = tmpl_blob.find(b":", i)
        L = int(tmpl_blob[i:c])
        i = c + 1
        parts.append(tmpl_blob[i:i + L].decode("utf-8"))
        i += L
    nf = len(parts) - 1
    ftable = _decode_multi(sub.decode("utf-8"))
    fields = [ftable[f"c{k}"] for k in range(nf)]
    nrows = len(fields[0]) if fields else 0
    out = []
    for r in range(nrows):
        out.append("".join(parts[k] + fields[k][r] for k in range(nf)) + parts[nf])
    return out


def _encode_multi(
    table: dict[str, list[str]],
    side_outputs: SideOutputs | None = None,
    parallel: bool | int = False,
    cfg: PipelineConfig = DEFAULT_PIPELINE,
    fallback: bool = True,
    min_header: bool = True,
    min_len: int | None = None,
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
        min_len: override do min_len do OBAT (mesmo p/ todas as colunas). None
            (default) -> auto por coluna (inalterado). Threaded a _encode_column.
    """
    if not table:
        raise ValueError("table vazia")

    lengths = {col: len(vals) for col, vals in table.items()}
    if len(set(lengths.values())) > 1:
        raise ValueError(f"colunas com lengths diferentes: {lengths}")

    for col_name in table.keys():
        if ',' in col_name or '=' in col_name:
            raise ValueError(f"col name contem char reservado: {col_name!r}")
        if col_name[:1] in '!@%':
            # marcadores de modo no #TCF.7 (! raw, @ dict, % split): um nome
            # comecando com eles colidiria com o parse da ultima-coluna-bare.
            raise ValueError(
                f"col name nao pode comecar com !@% (marcador de modo): {col_name!r}"
            )

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
            n_workers=n_workers, cfg=cfg, min_len=min_len,
        )
    else:
        col_bodies_bytes, per_col_sides = _encode_columns_serial(
            table_str, want_side=(side_outputs is not None), cfg=cfg,
            min_len=min_len,
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
    # Candidatos por coluna: tcf (sempre), raw (V2-A, ADR-0022), dict (V2-B,
    # ADR-0025). Escolhe o MENOR -> zero-regressao por construcao. Tudo gated por
    # `fallback`: com fallback=False so' tcf -> #TCF.6 legado byte-identico.
    fallback_cols: list[str] = []
    dict_cols: list[str] = []
    split_cols: list[str] = []
    final_bodies: list[tuple[str, bytes, str]] = []  # (name, body, mode)
    for name, tcf_bytes in col_bodies_bytes:
        best_body, best_mode = tcf_bytes, "tcf"
        if fallback:
            vals = table_str[name]
            if _fallback_safe(vals):
                raw_bytes = "\n".join(vals).encode("utf-8")
                if len(raw_bytes) < len(best_body):
                    best_body, best_mode = raw_bytes, "raw"
            v2b_bytes = _v2b_encode(vals, cfg=cfg, min_len=min_len)
            if v2b_bytes is not None and len(v2b_bytes) < len(best_body):
                best_body, best_mode = v2b_bytes, "dict"
            split_bytes = _struct_split_encode(vals, cfg=cfg, min_len=min_len)
            if split_bytes is not None and len(split_bytes) < len(best_body):
                best_body, best_mode = split_bytes, "split"
        final_bodies.append((name, best_body, best_mode))
        if best_mode == "raw":
            fallback_cols.append(name)
        elif best_mode == "dict":
            dict_cols.append(name)
        elif best_mode == "split":
            split_cols.append(name)

    used_fallback = bool(fallback_cols)
    used_v2 = used_fallback or bool(dict_cols) or bool(split_cols) or min_header
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
        pre = {"raw": "!", "dict": "@", "split": "%"}.get(mode, "")
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
            "dict_cols": list(dict_cols),
            "split_cols": list(split_cols),
            "min_header": min_header,
        }

    return text


def _encode_columns_serial(
    table_str: dict[str, list[str]],
    want_side: bool,
    cfg: PipelineConfig = DEFAULT_PIPELINE,
    min_len: int | None = None,
) -> tuple[list[tuple[str, bytes]], dict[str, SideOutputs]]:
    """Encoda colunas serialmente (comportamento original)."""
    col_bodies: list[tuple[str, bytes]] = []
    per_col_sides: dict[str, SideOutputs] = {}
    for col_name, str_values in table_str.items():
        side = SideOutputs() if want_side else None
        body = _encode_column(str_values, header=col_name, side=side, cfg=cfg,
                              min_len=min_len)
        col_bodies.append((col_name, body.encode("utf-8")))
        if want_side:
            per_col_sides[col_name] = side
    return col_bodies, per_col_sides


def _encode_columns_parallel(
    table_str: dict[str, list[str]],
    want_side: bool,
    n_workers: int,
    cfg: PipelineConfig = DEFAULT_PIPELINE,
    min_len: int | None = None,
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
            ex.submit(_worker_encode_column,
                      (name, table_str[name], want_side, cfg, min_len)): name
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


def _worker_encode_column(args) -> tuple[str, str, SideOutputs | None]:
    """Worker module-level (picklavel) pra ProcessPoolExecutor.

    Recebe (col_name, str_values, want_side, cfg, min_len); retorna
    (col_name, body_str, side).
    """
    col_name, str_values, want_side, cfg, min_len = args
    side = SideOutputs() if want_side else None
    body = _encode_column(str_values, header=col_name, side=side, cfg=cfg,
                          min_len=min_len)
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
    # #TCF.7 (MAGIC_MULTI_V2) = vivo. MAGIC_MULTI (#TCF.6) = LEGADO de leitura,
    # remover no 1.0 (T-CODE-LEGACY-PRUNE-PRE-07; ADR-0024 git-as-compat).
    is_v7 = line1.startswith(MAGIC_MULTI_V2)
    if not (line1.startswith(MAGIC_MULTI) or is_v7):
        raise ValueError(
            f"magic invalido: esperado {MAGIC_MULTI_V2!r} (ou legado {MAGIC_MULTI!r}), "
            f"got {line1[:20]!r}"
        )
    cursor = nl1 + 1

    nl2 = raw.find(b"\n", cursor)
    if nl2 == -1:
        raise ValueError("formato invalido: sem linha de meta")
    line2 = raw[cursor:nl2]
    # Meta line. #TCF.7 (vivo) dispensa prefixo (o flag `M` ja' declara o meta,
    # ADR-0023) — tolera '# ', '#' avulso, ou sem prefixo (forma canonical v7).
    # LEGADO #TCF.6 (remover no 1.0, T-CODE-LEGACY-PRUNE-PRE-07): EXIGE o '# '.
    if line2.startswith(META_PREFIX):          # b"# " — #TCF.6 legado OU #TCF.7 tolerante
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
        elif p.startswith("@"):
            mode = "dict"          # V2-B dicionario (ADR-0025)
            p = p[1:]
        elif p.startswith("%"):
            mode = "split"         # split estrutural (ADR-0026)
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
        if mode == "raw":
            # V2-A: body raw = "\n".join(valores); split exato (sem '\n'
            # embutido, garantido por _fallback_safe no encode).
            result[name] = body_bytes.decode("utf-8").split("\n")
        elif mode == "dict":
            result[name] = _decode_v2b(body_bytes)  # V2-B (ADR-0025)
        elif mode == "split":
            result[name] = _decode_struct_split(body_bytes)  # ADR-0026
        else:
            result[name] = _decode_column(body_bytes.decode("utf-8"))
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


# Aliases v0.6 `encode_table`/`decode_table` APOSENTADOS (T-CODE-LEGACY-PRUNE-PRE-07,
# 2026-06-24). Estavam deprecated desde ADR-0014. Use `encode(dict)` / `decode(text)`.
# Pré-1.0 (ADR-0024, git-as-compat): codigo que dependia deles reproduz via git checkout.

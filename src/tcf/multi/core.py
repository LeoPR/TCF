"""TCF multi-column — core enc/dec (orquestra os candidatos por coluna).

Pos-ADR-0014 (API unificada): a funcao publica e' `encode(dict)` /
`decode(text)` em `tcf.encoder` / `tcf.decoder`. Este modulo provê a
implementacao interna `_encode_multi` + `_decode_multi`, chamados por
`encode()` / `decode()` quando dispatch identifica tipo dict ou shebang
`#TCF.6 M`/`#TCF.7 M`.

Candidatos por coluna (fallback V2-A): tcf (sempre) / raw (`!`) / dict (`@`,
[`dict_v2b`](dict_v2b.py)) / split (`%`, [`split`](split.py)). Paralelismo em
[`parallel`](parallel.py) (host). Re-export publico em [`__init__`](__init__.py).

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

from tcf.multi.dict_v2b import _decode_v2b, _v2b_encode
from tcf.multi.parallel import (
    _encode_columns_parallel,
    _encode_columns_serial,
)
from tcf.multi.split import _decode_struct_split, _struct_split_encode
from tcf.pipeline import DEFAULT_PIPELINE, PipelineConfig
from tcf.side_outputs import SideOutputs

MAGIC_MULTI = b"#TCF.6 M"
MAGIC_MULTI_V2 = b"#TCF.7 M"  # V2-A fallback identity (ADR-0022, abre o formato #TCF.7)
MAGIC_MULTI_V3 = b"#TCF.8M"   # self-describing natures (ADR-0027/0029). Discriminador
                              # de 1 char: 'M' logo apos #TCF.8 (SEM espaco) = multi;
                              # meta INLINE na linha do shebang ('#TCF.8M<meta>\n').
                              # Emitido SSE bool(nature_ids) — opt-in estrito.
MAGIC_SINGLE_V3 = b"#TCF.8"   # single-col self-describing (SEM flag M -> single,
                              # decode retorna list). Header numa linha: '#TCF.8 [nome]:spec'
                              # (espaco = single+spec) ou '#TCF.8' (newline = version-stamp).
                              # Opt-in. ADR-0027/0029.
META_PREFIX = b"# "  # v1 (#TCF.6, congelado). #TCF.7 dispensa o prefixo do meta
                     # (o flag `M` no shebang ja' declara multi-col) — ADR-0023.


def _encode_multi(
    table: dict[str, list[str]],
    side_outputs: SideOutputs | None = None,
    parallel: bool | int = False,
    cfg: PipelineConfig = DEFAULT_PIPELINE,
    fallback: bool = True,
    min_header: bool = True,
    min_len: int | None = None,
    nature_ids: dict[str, str] | None = None,
    drop_names: bool = False,
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
        nature_ids: dict[col_name -> nature-id STRING] (ADR-0027, self-describing).
            So' a STRING do spec.name (cpf/cnpj/ip), nunca o objeto. Se nao-vazio:
            magic sobe pra #TCF.8 e cada col marcada ganha sufixo ':id' no nome do
            meta-line. **byte-neutro**: condicionado EXCLUSIVAMENTE a bool(nature_ids)
            — None/{} -> codepath identico ao de hoje (zero delta).
    """
    if not table:
        raise ValueError("table vazia")

    lengths = {col: len(vals) for col, vals in table.items()}
    if len(set(lengths.values())) > 1:
        raise ValueError(f"colunas com lengths diferentes: {lengths}")

    for col_name in table.keys():
        if ',' in col_name or '=' in col_name:
            raise ValueError(f"col name contem char reservado: {col_name!r}")
        if nature_ids and ':' in col_name:
            # ':' separa name/nature-id no meta-line do #TCF.8 (ADR-0027). So'
            # proibido quando ha nature (V3); sem nature o nome com ':' segue
            # valido (#TCF.6/7 nao parseiam ':') — preserva superficie de input.
            raise ValueError(
                f"col name nao pode conter ':' quando ha nature (#TCF.8): {col_name!r}"
            )
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
    # #TCF.8 SSE ha feature v8: nature OU colunas anonimas (drop_names). Colunas
    # anonimas sao feature v8 (mantem #TCF.7 nomeado intacto). byte-neutralidade:
    # condicionado SO' a force_v8, nunca a used_v2/min_header -> default (nomeado,
    # sem nature) = magic de hoje, zero delta (D1-D9/D17a intactos).
    force_v8 = bool(nature_ids) or drop_names
    if force_v8:
        magic = MAGIC_MULTI_V3
    elif used_v2:
        magic = MAGIC_MULTI_V2
    else:
        magic = MAGIC_MULTI

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
        # Sufixo ':id' (ADR-0027) SSE a coluna tem nature. Condicional ao spec
        # da coluna -> coluna sem nature gera string byte-identica a de hoje.
        suf = f":{nature_ids[name]}" if nature_ids and name in nature_ids else ""
        if drop_names:
            # Coluna ANONIMA (ADR-0029): nome omitido -> posicional no decode.
            # Nao-ultima = '<size>[:spec]' (sem '=nome'); ultima = '[:spec]'/vazio.
            parts.append(f"{pre}{suf}" if (min_header and i == last_i)
                         else f"{pre}{len(b)}{suf}")
        elif min_header and i == last_i:
            parts.append(f"{pre}{name}{suf}")        # ultima sem size
        else:
            parts.append(f"{pre}{len(b)}={name}{suf}")
    meta_pairs = ",".join(parts)
    if magic == MAGIC_MULTI_V3:
        # #TCF.8M: meta INLINE na linha do shebang (discriminador 1-char, ADR-0029)
        # -> '#TCF.8M<meta>\n<bodies>'. Sem espaco, sem linha de meta separada.
        header = magic + meta_pairs.encode("utf-8") + b"\n"
    else:
        # #TCF.6 carrega o prefixo '# '; #TCF.7 dispensa (flag M na linha 1, ADR-0023).
        meta_prefix = META_PREFIX if magic == MAGIC_MULTI else b""
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
            "nature_cols": dict(nature_ids) if nature_ids else {},
        }

    return text


def _decode_multi_impl(
    tcf_text: str,
) -> tuple[dict[str, list[str]], dict[str, str]]:
    """Parse + decode multi-col, SEM aplicar natures.

    Retorna (result, nature_ids), onde nature_ids = {col_name -> nature-id
    STRING} extraido do sufixo ':id' do meta-line (#TCF.8, ADR-0027); vazio pra
    #TCF.6/7. A APLICACAO da nature (resolve + decode_value) fica no `decode()`
    publico, que resolve a precedencia header-vs-usuario. Mantem multi/core
    agnostico de nature (so' PARSEIA a tag, nao depende de tcf.natures).

    Aceita #TCF.6 M (v1, meta com `# `), #TCF.7 M e #TCF.8 M (v2/v3, meta SEM
    prefixo). Em #TCF.7+: `!` = raw (V2-A), `@` = dict (V2-B), `%` = split; par
    sem `=` = ultima coluna (corpo ate' EOF). Self-describing: magic + forma dos
    pares dizem tudo.
    """
    from tcf.decoder import _decode_column

    raw = tcf_text.encode("utf-8")

    nl1 = raw.find(b"\n")
    if nl1 == -1:
        raise ValueError("formato invalido: sem linha 1 (shebang)")
    line1 = raw[:nl1]
    # #TCF.7/#TCF.8 = vivos. MAGIC_MULTI (#TCF.6) = LEGADO de leitura, remover no
    # 1.0 (T-CODE-LEGACY-PRUNE-PRE-07; ADR-0024 git-as-compat).
    is_v7 = line1.startswith(MAGIC_MULTI_V2)
    is_v8 = line1.startswith(MAGIC_MULTI_V3)
    if not (line1.startswith(MAGIC_MULTI) or is_v7 or is_v8):
        raise ValueError(
            f"magic invalido: esperado {MAGIC_MULTI_V2!r}/{MAGIC_MULTI_V3!r} "
            f"(ou legado {MAGIC_MULTI!r}), got {line1[:20]!r}"
        )
    if is_v8:
        # #TCF.8M: meta INLINE na linha do shebang (discriminador 1-char, ADR-0029).
        # Body comeca logo apos a 1a '\n'.
        meta_str = line1[len(MAGIC_MULTI_V3):].decode("utf-8")
        cursor = nl1 + 1
    else:
        # #TCF.7/#TCF.6: meta na linha 2. #TCF.7 dispensa prefixo (flag `M` ja'
        # declara colunas, ADR-0023) — tolera '# '/'#'/nenhum. #TCF.6 EXIGE '# '.
        nl2 = raw.find(b"\n", nl1 + 1)
        if nl2 == -1:
            raise ValueError("formato invalido: sem linha de meta")
        line2 = raw[nl1 + 1:nl2]
        if line2.startswith(META_PREFIX):      # b"# " — #TCF.6 legado OU tolerante
            meta_str = line2[len(META_PREFIX):].decode("utf-8")
        elif is_v7:
            meta_str = (line2[1:] if line2.startswith(b"#") else line2).decode("utf-8")
        else:
            raise ValueError(
                f"meta invalido (#TCF.6 exige '# '): got {line2[:5]!r}"
            )
        cursor = nl2 + 1
    # Parse POSITION-AWARE (ADR-0029): so' a ULTIMA coluna nao tem size
    # (min_header). Logo nao-ultima sem '=nome' = coluna ANONIMA (size sozinho);
    # ultima vazia = anonima. Isso desambigua nome-opcional sem quebrar o nomeado.
    tokens = meta_str.split(",")
    n_cols = len(tokens)
    pairs = []  # (size|None, name|None, mode, nature_id|None)
    for i, p in enumerate(tokens):
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
        # Sufixo ':id' (#TCF.8, ADR-0027) separado primeiro. So' em V8 -> nomes
        # com ':' em #TCF.6/7 ficam intocados (nome nunca tem ':' em V8: validador
        # proibe; spec e' um unico token cpf/cnpj/ip).
        nat_id = None
        if is_v8 and ":" in p:
            p, nat_id = p.rsplit(":", 1)
        if "=" in p:
            # '<size>=<nome>' — nomeada. Vale em qualquer posicao (em #TCF.6 com
            # min_header=False ATE' a ultima coluna tem size=nome).
            size_str, name = p.split("=", 1)
            size = int(size_str)
        elif i == n_cols - 1:
            # ultima coluna SEM '=': min_header (corpo ate' EOF). p = nome (vazio
            # = anonima posicional).
            size = None
            name = p if p else None
        else:
            # nao-ultima SEM '=' -> coluna ANONIMA: p = '<size>' (so' V8/drop_names)
            size = int(p)
            name = None
        pairs.append((size, name, mode, nat_id))

    # cursor ja' aponta o inicio do body (apos line1 no V8, apos line2 no V7/6)
    result: dict[str, list[str]] = {}
    nature_ids: dict[str, str] = {}
    for i, (size, name, mode, nat_id) in enumerate(pairs):
        if size is None:
            body_bytes = raw[cursor:]              # ate' EOF (ultima coluna)
        else:
            body_bytes = raw[cursor:cursor + size]
        # Coluna anonima (name is None) -> nome POSICIONAL = ordem (ADR-0029).
        col = name if name is not None else str(i)
        if mode == "raw":
            # V2-A: body raw = "\n".join(valores); split exato (sem '\n'
            # embutido, garantido por _fallback_safe no encode).
            result[col] = body_bytes.decode("utf-8").split("\n")
        elif mode == "dict":
            result[col] = _decode_v2b(body_bytes)  # V2-B (ADR-0025)
        elif mode == "split":
            result[col] = _decode_struct_split(body_bytes)  # ADR-0026
        else:
            result[col] = _decode_column(body_bytes.decode("utf-8"))
        if nat_id is not None:
            nature_ids[col] = nat_id
        cursor += len(body_bytes)

    return result, nature_ids


def _decode_multi(tcf_text: str) -> dict[str, list[str]]:
    """Wrapper compat: decode multi-col retornando so' o dict (natures NAO
    aplicadas). Usado por `split.py` na recursao de sub-tabela (que nunca tem
    nature) e re-exportado. `decode()` usa `_decode_multi_impl` pra aplicar as
    natures do header com a precedencia correta."""
    result, _ = _decode_multi_impl(tcf_text)
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

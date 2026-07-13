"""TCF multi-column — core enc/dec (orquestra os candidatos por coluna).

Pos-ADR-0014 (API unificada): a funcao publica e' `encode(dict)` /
`decode(text)` em `tcf.encoder` / `tcf.decoder`. Este modulo provê a
implementacao interna `_encode_multi` + `_decode_multi`, chamados por
`encode()` / `decode()` quando dispatch identifica tipo dict ou shebang `#TCF.8M`.

Candidatos por coluna (fallback V2-A): tcf (sempre) / raw (`!`) / dict (`@`,
[`dict_v2b`](dict_v2b.py)) / split (`%`, [`split`](split.py)). Paralelismo em
[`parallel`](parallel.py) (host). Re-export publico em [`__init__`](__init__.py).

Header format. **#TCF.8M e' o DEFAULT** (ADR-0032, 2026-07-09). Legado #TCF.6/#TCF.7
CORTADO de src/tcf (git-as-compat pra comparacao historica; decode fail-loud).

#TCF.8M — meta INLINE na linha do shebang (discriminador 1-char `M`, ADR-0029);
byte-sizes em HEX (T-FMT-HEADER-BASE-HEX):

    #TCF.8M<s1>=<n1>,!<s2>=<n2>,...,<nN>
    <body1><raw_body2>...<bodyN>

    - `!`/`@`/`%` antes do size = coluna raw (V2-A) / dict (V2-B) / split (V2-C).
      Nunca colide com nome (size e' hex-digito).
    - Sufixo `:id` no nome = nature (ADR-0027). Coluna anonima (drop_names): sem `=nome`.
    - ULTIMA coluna sem size (corpo ate' EOF, O-FMT-15/ADR-0023): par sem `=`.
    - bodies concatenados byte-precise (sem delimitador; sizes hex no meta).

Contratos de fronteira (T-FMT-NAME-ESCAPING M2 + T-QA-8 F0):
- Nomes de coluna com `,`/`=`/`:`/`\\` e prefixo `!@%` sao ESCAPADOS com
  backslash no meta (aceitos); so' `\\n` e' proibido (separador de linha).
- Nome '' = coluna ANONIMA (decode da' nome posicional; warning).
- Todas colunas devem ter mesmo numero de valores (>= 1; 0 linhas = erro).
- NULL/None convertido pra '' (empty string); coluna deve ser LISTA (str/bytes
  = erro que ensina).
"""

from __future__ import annotations

import os
import warnings

from tcf.multi.dict_v2b import _decode_v2b, _v2b_encode
from tcf.multi.parallel import (
    _encode_columns_parallel,
    _encode_columns_serial,
)
from tcf.multi.split import _decode_struct_split, _struct_split_encode
from tcf.pipeline import DEFAULT_PIPELINE, PipelineConfig
from tcf.side_outputs import SideOutputs

MAGIC_MULTI_V3 = b"#TCF.8M"  # multi-col DEFAULT (ADR-0032). Discriminador de 1 char:
# 'M' logo apos #TCF.8 (SEM espaco); meta INLINE na linha
# do shebang ('#TCF.8M<meta>\n'). Legado #TCF.6/.7 cortado.
MAGIC_SINGLE_V3 = b"#TCF.8"  # single-col self-describing (SEM flag M -> single,
# decode retorna list). Header numa linha: '#TCF.8 [nome]:spec'
# (espaco = single+spec) ou '#TCF.8' (newline = version-stamp).
# Opt-in. ADR-0027/0029.


# --- Escape de NOMES no meta (T-FMT-NAME-ESCAPING, M2 2026-07-09) ---
# Interim: SO' backslash (estilo CSV-quoting simplificado; estudo de quoting/outros
# casos adiado — ver ticket). Escapa os separadores do meta (,/=/:) + o proprio '\'
# + prefixo de modo (!@%) INICIAL (colidiria com a ultima-coluna-bare). O tokenizer
# splita em separador NAO-escapado. So' '\n' fica proibido (separador de linha,
# irrepresentavel no meta de 1 linha).
_NAME_SEP = ",=:\\"


def _esc_name(name: str) -> str:
    """Escapa (backslash) os chars estruturais de um nome de coluna no meta.

    Contrato: NUNCA recebe '' — nome vazio vira coluna ANONIMA na fronteira
    (`_encode_multi`, BUG-01 T-QA-8 F0). O guard `s[:1] and` fecha o buraco
    do idiom (`'' in "!@%"` e' True — substring vazia)."""
    out = []
    for ch in name:
        if ch in _NAME_SEP:
            out.append("\\")
        out.append(ch)
    s = "".join(out)
    if s[:1] and s[:1] in "!@%":  # prefixo de modo no inicio colidiria (last-col bare)
        s = "\\" + s
    return s


def _unesc_name(s: str) -> str:
    """Reverte `_esc_name`: remove um '\\' antes de cada char escapado."""
    out, i, n = [], 0, len(s)
    while i < n:
        if s[i] == "\\" and i + 1 < n:
            out.append(s[i + 1])
            i += 2
        else:
            out.append(s[i])
            i += 1
    return "".join(out)


def _split_unesc(s: str, sep: str, maxsplit: int = -1) -> list[str]:
    """`s.split(sep)` ignorando separadores escapados por '\\'."""
    parts, buf, i, n, cnt = [], [], 0, len(s), 0
    while i < n:
        c = s[i]
        if c == "\\" and i + 1 < n:
            buf.append(s[i : i + 2])
            i += 2
            continue
        if c == sep and (maxsplit < 0 or cnt < maxsplit):
            parts.append("".join(buf))
            buf = []
            cnt += 1
            i += 1
            continue
        buf.append(c)
        i += 1
    parts.append("".join(buf))
    return parts


def _rsplit1_unesc(s: str, sep: str):
    """Split no ULTIMO `sep` NAO-escapado -> (left, right), ou None se nao ha."""
    last, i, n = -1, 0, len(s)
    while i < n:
        if s[i] == "\\" and i + 1 < n:
            i += 2
            continue
        if s[i] == sep:
            last = i
        i += 1
    return None if last < 0 else (s[:last], s[last + 1 :])


_ESC_OK = ",=:\\!@%"  # whitelist canonica: o encoder SO' escapa estes chars
# (_NAME_SEP em qualquer posicao + prefixo de modo !@%)


def _unesc_name_strict(s: str) -> str:
    """Unescape ESTRITO do nome (decode): so' aceita o que o encoder emite.

    Fail-loud (marcadores de corrupcao — T-TOOL-TCF-FIX-CORRUPTION):
    - backslash SOLTO no fim (escape de nada): '\\' legitimo sai '\\\\' (BUG-01);
    - escape de char FORA da whitelist `_ESC_OK` ('\\b', '\\x'...): nao-emitivel;
      aceitar mudaria o nome CALADO (BUG-11b, lote 3 — whitelist por deducao do
      canone: escapes validos sao exatamente os que `_esc_name` produz)."""
    out, i, n = [], 0, len(s)
    while i < n:
        c = s[i]
        if c == "\\":
            if i + 1 >= n:
                raise ValueError(
                    f"meta corrompido: escape dangling (backslash solto) no nome "
                    f"{s!r} — o encoder nunca emite isso (nome '' vira coluna anonima)"
                )
            nxt = s[i + 1]
            if nxt not in _ESC_OK:
                raise ValueError(
                    f"meta corrompido: escape de char nao-estrutural '\\{nxt}' no "
                    f"nome {s!r} — o encoder so' escapa {_ESC_OK!r} (T-QA-8 BUG-11)"
                )
            out.append(nxt)
            i += 2
        else:
            out.append(c)
            i += 1
    return "".join(out)


def _hex_size(s: str) -> int:
    """Size hex do meta -> int, com erro CLARO em corrupcao (fail-loud)."""
    try:
        return int(s, 16)
    except ValueError:
        raise ValueError(
            f"meta corrompido: size hex invalido {s!r} no meta do #TCF.8M"
        ) from None


def _parse_meta(meta_str: str) -> list[tuple[int | None, str | None, str, str | None]]:
    """Parse do meta INLINE do #TCF.8M -> [(size, name, mode, nature_id)] por coluna.

    FONTE UNICA do parse do meta — `_decode_multi_impl` E `tcf.view` consomem
    daqui: paridade decode/view por CONSTRUCAO, nao por verificacao (BUG-02,
    T-QA-8 F0 2026-07-10). `size=None` = ultima coluna (corpo ate' EOF);
    `name=None` = coluna ANONIMA (nome POSICIONAL str(i) fica no caller).

    Fail-loud (marcadores de corrupcao; futuro reparador: T-TOOL-TCF-FIX-CORRUPTION):
    - nome DECLARADO vazio ('<size>='): o encoder nunca emite ('' vira anonima);
    - backslash solto no fim de nome (escape de nada);
    - size hex invalido.
    """
    tokens = _split_unesc(meta_str, ",")  # ',' escapado no nome fica intacto
    n_cols = len(tokens)
    pairs: list[tuple[int | None, str | None, str, str | None]] = []
    for i, p in enumerate(tokens):
        if p.startswith("!"):
            mode = "raw"
            p = p[1:]
        elif p.startswith("@"):
            mode = "dict"  # V2-B dicionario (ADR-0025)
            p = p[1:]
        elif p.startswith("%"):
            mode = "split"  # split estrutural (ADR-0026)
            p = p[1:]
        else:
            mode = "tcf"
        # Sufixo ':id' (nature, ADR-0027) = ULTIMO ':' NAO-escapado (um ':' no NOME
        # vem escapado '\\:' via _esc_name). Split escape-aware (T-FMT-NAME-ESCAPING).
        nat_id = None
        r = _rsplit1_unesc(p, ":")
        if r is not None:
            p, nat_id = r
        eq = _split_unesc(p, "=", 1)  # primeiro '=' NAO-escapado
        if len(eq) == 2:
            # '<size>=<nome>' — nomeada. Nome des-escapado (nomes com ,/=/:/! etc).
            size_str, name = eq
            size = _hex_size(size_str)
            name = _unesc_name_strict(name)
            if name == "":
                raise ValueError(
                    "meta corrompido: nome de coluna DECLARADO vazio ('<size>=') — "
                    "o encoder nunca emite (nome '' vira coluna anonima, sem '=')"
                )
        elif i == n_cols - 1:
            # ultima coluna SEM '=': min_header (corpo ate' EOF). p = nome (vazio
            # = anonima posicional).
            size = None
            name = _unesc_name_strict(p) if p else None
        else:
            # nao-ultima SEM '=' -> coluna ANONIMA: p = '<size>' (so' drop_names/'')
            size = _hex_size(p)
            name = None
        pairs.append((size, name, mode, nat_id))
    return pairs


def _encode_multi(
    table: dict[str, list[str]],
    side_outputs: SideOutputs | None = None,
    parallel: bool | int = False,
    cfg: PipelineConfig = DEFAULT_PIPELINE,
    fallback: bool = True,
    min_header: bool = True,
    min_len: int | None = None,
    nature_specs: dict | None = None,
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
        fallback: candidatos V2 por coluna (ADR-0022/0025/0026). **Default
            True**: escolhe min(tcf, raw, dict, split). False -> so' candidato
            tcf em toda coluna (comparacao/regressao; o magic segue #TCF.8M —
            legado #TCF.6 CORTADO, ADR-0032, git-as-compat).
        min_header: ultima coluna sem size (corpo ate' EOF; ADR-0023,
            O-FMT-15). **Default True**. False -> todas as colunas com size
            (inspecao); meta segue INLINE (#TCF.8M). Ultima coluna ANONIMA e'
            SEMPRE sem size (gramatica: size bare no ultimo token colidiria
            com nome — achado adversarial F0).
        min_len: override do min_len do OBAT (mesmo p/ todas as colunas). None
            (default) -> auto por coluna (inalterado). Threaded a _encode_column.
        nature_specs: dict[col_name -> spec] (ADR-0027 + FLOOR, T-SPEC-DEEPDIVE-08
            §5.1, owner 2026-07-12). A nature COMPETE no min() por coluna: encoda-se
            a coluna ORIGINAL e a NATURE-transformada, fica a MENOR pelo blob
            serializado completo (incluindo meta, sizes e o custo do ':id'). Se a
            nature vence -> ':id' no meta + corpo
            base-94; se perde/empata -> original, SEM ':id'. Safe-by-construction:
            NUNCA pior que o baseline (resolve a regressao F4). None/{} -> codepath
            identico ao de hoje (zero delta byte-canonical).
    """
    if not table:
        raise ValueError("table vazia")

    for col_name, vals in table.items():
        # BUG-09 (T-QA-8 lote 3): str e' iteravel — {'a': 'xyz'} viraria 3
        # linhas de 1 char CALADO. Nao auto-embrulhar (duas leituras possiveis
        # -> declarar > deduzir); fail-loud que ensina.
        if isinstance(vals, (str, bytes)):
            raise TypeError(
                f"coluna {col_name!r}: valor deve ser LISTA de valores, nao "
                f"{type(vals).__name__} — envolva em [...] se e' 1 valor "
                f"(uma str iteraria char a char; T-QA-8 BUG-09)"
            )

    lengths = {col: len(vals) for col, vals in table.items()}
    if len(set(lengths.values())) > 1:
        raise ValueError(f"colunas com lengths diferentes: {lengths}")
    if next(iter(lengths.values())) == 0:
        # BUG-03 (T-QA-8 F0 lote 2): 0 linhas colide com 1-linha-vazia (body de
        # 0 bytes nos dois casos; nada de onde deduzir) -> fail-loud. Registro-'0'
        # declarando schema fica pro trilho append/parquet/tcfx (registrado).
        raise ValueError(
            "tabela com 0 linhas: nao representavel (colide com 1 linha vazia — "
            "o formato nao grava row-count); ver T-QA-8 BUG-03"
        )

    for col_name in table.keys():
        # #TCF.8M default (ADR-0032): separadores do meta (,/=/:) + '\' + prefixo de
        # modo (!@%) inicial sao ESCAPADOS no nome (_esc_name, T-FMT-NAME-ESCAPING, M2).
        # So' '\n' fica proibido: e' o separador de linha do meta (irrepresentavel).
        if "\n" in col_name:
            raise ValueError(
                f"col name nao pode conter '\\n' (separador de linha do meta): {col_name!r}"
            )

    # Nome VAZIO '' = coluna SEM nome (BUG-01, T-QA-8 F0 — decisao do owner 2026-07-10):
    # a ENTRADA e' transformada na fronteira — a coluna vira ANONIMA no meta (sem
    # '=nome', mesmo mecanismo do drop_names; decode da' o nome POSICIONAL). O meta
    # NUNCA emite escape-vazio (evita o '\' solto que fundia tokens). Internamente
    # nao faz diferenca: o tcf lida com nomes OU com a numeracao em ordem.
    if "" in table:
        pos = list(table.keys()).index("")
        # Colisao SO' quando as demais colunas MANTEM nome (sem drop_names): com
        # drop_names=True TODAS decodam posicionais — nao ha colisao possivel
        # (falso-positivo achado na verificacao adversarial F0, 2026-07-10).
        if str(pos) in table and not drop_names:
            raise ValueError(
                f"coluna com nome vazio '' vira anonima e decoda com o nome "
                f"posicional {str(pos)!r}, que colidiria com a coluna existente "
                f"{str(pos)!r} — renomeie uma das duas"
            )
        warnings.warn(
            f"coluna com nome vazio '' tratada como ANONIMA — o decode retorna o "
            f"nome posicional {str(pos)!r} (entrada sem nome, provavel engano)",
            UserWarning,
            stacklevel=3,
        )

    # Stringify upfront (per-col paralelo recebe valores ja' string) + check
    # de \n/\r na MESMA passada — FONTE ÚNICA `_stringify_checked` (BUG-06
    # lote 2; dedup C0 D2: o ramo list do encoder consome a mesma função).
    table_str: dict[str, list[str]] = {
        name: _stringify_checked(values, name) for name, values in table.items()
    }

    # Dispatch paralelo se solicitado E vale a pena (>= 2 cols).
    # parallel=1 -> SERIAL por DEDUCAO (BUG-10c, lote 3): 1 worker produz os
    # MESMOS bytes por construcao — economiza o spawn do pool inteiro.
    # CUIDADO: True == 1 em Python — o isinstance(bool) preserva parallel=True.
    use_parallel = len(table_str) >= 2 and (
        parallel is True
        or (
            not isinstance(parallel, bool)
            and isinstance(parallel, int)
            and parallel >= 2
        )
    )
    n_workers = 0
    if use_parallel:
        if parallel is True:
            n_workers = os.cpu_count() or 1
        else:  # int >= 1 (bool(0)/False filtrados acima)
            n_workers = int(parallel)
        n_workers = max(1, min(n_workers, len(table_str)))
        col_bodies_bytes, per_col_sides = _encode_columns_parallel(
            table_str,
            want_side=(side_outputs is not None),
            n_workers=n_workers,
            cfg=cfg,
            min_len=min_len,
        )
    else:
        col_bodies_bytes, per_col_sides = _encode_columns_serial(
            table_str,
            want_side=(side_outputs is not None),
            cfg=cfg,
            min_len=min_len,
        )

    if side_outputs is not None:
        side_outputs.per_col = dict(per_col_sides)

    # V2-A fallback identity (ADR-0022). Opt-in (fallback=True). Por coluna,
    # escolhe min(TCF, raw). Raw = "\n".join(valores), usado so' quando e'
    # ESTRITAMENTE menor E seguro (sem '\n' embutido — que quebraria o split
    # do decode). Marca raw com '!' ANTES do size no par meta (`!<size>=<name>`)
    # — '!' nunca colide com nomes (size e' hex-digito). Sempre #TCF.8M (ADR-0032);
    # `fallback`/`min_header` controlam so' os candidatos/last-col-sizeless.
    # Candidatos por coluna: tcf (sempre), raw (V2-A, ADR-0022), dict (V2-B,
    # ADR-0025). Escolhe o MENOR -> zero-regressao por construcao. Tudo gated por
    # `fallback`: com fallback=False so' tcf -> #TCF.6 legado byte-identico.
    # FLOOR (T-SPEC-DEEPDIVE §5.1): a nature vira candidato do min() por coluna.
    # nature_ids EMITIDO = so' as colunas onde a nature venceu (nao mais input).
    nature_ids: dict[str, str] = {}
    nature_apply: dict = {}
    fallback_cols: list[str] = []
    dict_cols: list[str] = []
    split_cols: list[str] = []
    col_modes: dict[str, str] = {}
    final_bodies: list[tuple[str, bytes, str]] = []  # (name, body, mode)
    nature_candidates: dict[str, tuple[bytes, str, str]] = {}

    def _serialize(
        bodies: list[tuple[str, bytes, str]],
        ids: dict[str, str],
    ) -> bytes:
        """Monta um blob multi-col para comparar candidatos do FLOOR."""
        last_i = len(bodies) - 1
        parts = []
        _sz = lambda n: format(n, "x")  # noqa: E731
        for i, (name, body, mode) in enumerate(bodies):
            pre = {"raw": "!", "dict": "@", "split": "%"}.get(mode, "")
            suf = f":{ids[name]}" if name in ids else ""
            if drop_names or name == "":
                parts.append(
                    f"{pre}{suf}" if i == last_i else f"{pre}{_sz(len(body))}{suf}"
                )
            elif min_header and i == last_i:
                parts.append(f"{pre}{_esc_name(name)}{suf}")
            else:
                parts.append(f"{pre}{_sz(len(body))}={_esc_name(name)}{suf}")
        header = MAGIC_MULTI_V3 + ",".join(parts).encode("utf-8") + b"\n"
        return header + b"".join(body for _, body, _ in bodies)

    def _best_of(vals: list[str], tcf_body: bytes):
        """min(tcf, raw, dict, split) de uma coluna -> (body, mode)."""
        bb, bm = tcf_body, "tcf"
        if fallback:
            if _fallback_safe(vals):
                rb = "\n".join(vals).encode("utf-8")
                if len(rb) < len(bb):
                    bb, bm = rb, "raw"
            vb = _v2b_encode(vals, cfg=cfg, min_len=min_len)
            if vb is not None and len(vb) < len(bb):
                bb, bm = vb, "dict"
            sb = _struct_split_encode(vals, cfg=cfg, min_len=min_len)
            if sb is not None and len(sb) < len(bb):
                bb, bm = sb, "split"
        return bb, bm

    for name, tcf_bytes in col_bodies_bytes:
        best_body, best_mode = _best_of(table_str[name], tcf_bytes)

        spec = nature_specs.get(name) if nature_specs else None
        if spec is not None:
            # CANDIDATO nature: encoda os valores NATURE-transformados e compete.
            # A nature so' vence se reduz o blob serializado completo (never-worse).
            # apply-rate reportado SEMPRE (telemetria da transformacao).
            from tcf.encoder import _encode_column
            from tcf.natures.templated_checked import encode_value

            pairs = [encode_value(spec, v) for v in table_str[name]]
            transformed = [p for p, _ in pairs]
            if side_outputs is not None:
                from tcf.encoder import _nature_apply_stats

                nature_apply[name] = _nature_apply_stats(spec, [s for _, s in pairs])
            nat_tcf = _encode_column(
                transformed, header=name, cfg=cfg, min_len=min_len
            ).encode("utf-8")
            nat_body, nat_mode = _best_of(transformed, nat_tcf)
            nature_candidates[name] = (nat_body, nat_mode, spec.name)

        final_bodies.append((name, best_body, best_mode))

    # Todas as colunas ja' estao presentes: com min_header=True, isso e' necessario
    # para que o custo de size/meta seja calculado na posicao final correta.
    for i, (name, _best_body, _best_mode) in enumerate(final_bodies):
        candidate = nature_candidates.get(name)
        if candidate is None:
            continue
        nat_body, nat_mode, nature_id = candidate
        candidate_bodies = list(final_bodies)
        candidate_bodies[i] = (name, nat_body, nat_mode)
        candidate_ids = dict(nature_ids)
        candidate_ids[name] = nature_id
        if len(_serialize(candidate_bodies, candidate_ids)) < len(
            _serialize(final_bodies, nature_ids)
        ):
            final_bodies = candidate_bodies
            nature_ids[name] = nature_id
            if side_outputs is not None:
                nature_apply[name]["used"] = True
        elif side_outputs is not None:
            nature_apply[name]["used"] = False

    for name, best_body, best_mode in final_bodies:
        if best_mode == "raw":
            fallback_cols.append(name)
        elif best_mode == "dict":
            dict_cols.append(name)
        elif best_mode == "split":
            split_cols.append(name)
        if side_outputs is not None:
            col_modes[name] = best_mode
            pc = side_outputs.per_col.get(name) if side_outputs.per_col else None
            if pc is not None:
                pc.emitted_bytes = len(best_body)
                pc.emitted_mode = best_mode

    used_fallback = bool(fallback_cols)
    used_v2 = used_fallback or bool(dict_cols) or bool(split_cols) or min_header
    # #TCF.8M e' o formato DEFAULT do multi-col (ADR-0032, 2026-07-09). O legado
    # #TCF.6/#TCF.7 foi CORTADO de src/tcf (git-as-compat pra comparacao historica).
    # Single-col NAO muda (orfao default, 0029/0030). used_v2 mantido so' p/ o campo
    # de side_outputs (nao decide mais o magic).
    body_concat = b"".join(b for _, b, _ in final_bodies)
    full = _serialize(final_bodies, nature_ids)
    header_bytes = len(full) - len(body_concat)
    text = full.decode("utf-8")

    if side_outputs is not None:
        side_outputs.multi_info = {
            "n_rows": next(iter(lengths.values())),
            "n_cols": len(table),
            "total_bytes": len(full),
            "header_bytes": header_bytes,
            "body_bytes": len(body_concat),
            "parallel_workers": n_workers if use_parallel else 0,
            "format": "v3",  # #TCF.8M (ADR-0032 default); used_v2 abaixo detalha as features
            "used_v2_features": used_v2,
            "fallback_cols": list(fallback_cols),
            "dict_cols": list(dict_cols),
            "split_cols": list(split_cols),
            # Modo vencedor POR coluna (incl. 'tcf', que as listas acima nao dizem)
            # — BUG-07: capturado no min(), chave = nome de ENTRADA da coluna.
            "col_modes": dict(col_modes),
            "min_header": min_header,
            # nature_cols = so' as que VENCERAM o min() (FLOOR); nature_lost = as
            # que foram propostas mas perderam (telemetria da competicao).
            "nature_cols": dict(nature_ids),
            "nature_lost": [c for c in (nature_specs or {}) if c not in nature_ids],
        }
        if nature_apply:
            side_outputs.nature_apply = nature_apply

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

    Aceita SO' #TCF.8M (ADR-0032; legado #TCF.6/.7 cortado -> fail-loud no decode()
    publico). Meta INLINE: `!` = raw (V2-A), `@` = dict (V2-B), `%` = split; sufixo
    `:id` = nature; par sem `=` = ultima coluna (corpo ate' EOF). Sizes em HEX.
    Self-describing: magic + forma dos pares dizem tudo.
    """
    from tcf.decoder import _decode_column

    raw = tcf_text.encode("utf-8")

    nl1 = raw.find(b"\n")
    if nl1 == -1:
        raise ValueError("formato invalido: sem linha 1 (shebang)")
    line1 = raw[:nl1]
    # #TCF.8M e' o UNICO multi-col vivo (ADR-0032, 2026-07-09). Legado #TCF.6/#TCF.7
    # CORTADO de src/tcf — fail-loud com dica de git (o decode() publico ja' rejeita
    # antes com msg de legado; aqui e' defesa em profundidade).
    if not line1.startswith(MAGIC_MULTI_V3):
        raise ValueError(
            f"multi-col: esperado {MAGIC_MULTI_V3!r} (#TCF.8M). Legado #TCF.6/#TCF.7 "
            f"cortado (ADR-0032) — git checkout <pre-0.8> pra ler; got {line1[:20]!r}"
        )
    # meta INLINE na linha do shebang (#TCF.8M<meta>\n<bodies>).
    meta_str = line1[len(MAGIC_MULTI_V3) :].decode("utf-8")
    cursor = nl1 + 1
    # BUG-08 (lote 3, fold): meta vazio + body vazio e' NAO-EMITIVEL (0-rows e'
    # rejeitado no encode; 1-linha-vazia sempre gera >=1 byte de body ou
    # marcador '!') — antes fabricava {'0': ['']} calado. Meta vazio COM body
    # e' LEGITIMO (1 coluna anonima em modo tcf via drop_names). Semantica
    # definitiva do vazio: T-API-BOUNDARY-CONTRACTS (pre-1.0).
    if not meta_str and cursor >= len(raw):
        raise ValueError(
            "blob corrompido: meta vazio sem body ('#TCF.8M\\n' nao-emitivel — "
            "0 linhas nao e' representavel; T-QA-8 BUG-08)"
        )
    # Parse POSITION-AWARE (ADR-0029) delegado a `_parse_meta` — FONTE UNICA
    # core+view (paridade por construcao, BUG-02 T-QA-8 F0). Sizes em HEX.
    pairs = _parse_meta(meta_str)  # [(size|None, name|None, mode, nature_id|None)]

    # cursor ja' aponta o inicio do body (apos a linha do shebang).
    # BUG-05 (T-QA-8 F0 lote 2): 3 cheques de integridade DEDUZIDOS do que o
    # formato ja' declara — zero byte novo, custo ~zero: (1) size do header vs
    # bytes disponiveis; (2) fecho do blob (sem excedente); (3) n_rows igual em
    # todas as colunas (invariante nunca gravado, deduzivel de graca no decode).
    # Limite conhecido (registrado): ultima coluna SEM size + excedente
    # row-consistente e' indetectavel (raw absorve). Profundo (streaming/
    # completude na chegada) registrado no ticket.
    result: dict[str, list[str]] = {}
    nature_ids: dict[str, str] = {}
    for i, (size, name, mode, nat_id) in enumerate(pairs):
        # Coluna anonima (name is None) -> nome POSICIONAL = ordem (ADR-0029).
        col = name if name is not None else str(i)
        if size is None:
            body_bytes = raw[cursor:]  # ate' EOF (ultima coluna)
        else:
            body_bytes = raw[cursor : cursor + size]
            if len(body_bytes) != size:
                raise ValueError(
                    f"body truncado: coluna {col!r} declara {size}B no header, "
                    f"restam {len(body_bytes)}B no blob (T-QA-8 BUG-05)"
                )
        if mode == "raw":
            # V2-A: fonte única `_decode_raw_body` (dedup C0 D3 — a view
            # consome a mesma função; paridade por construção).
            result[col] = _decode_raw_body(body_bytes)
        elif mode == "dict":
            result[col] = _decode_v2b(body_bytes)  # V2-B (ADR-0025)
        elif mode == "split":
            result[col] = _decode_struct_split(body_bytes)  # ADR-0026
        else:
            result[col] = _decode_column(body_bytes.decode("utf-8"))
        if nat_id is not None:
            nature_ids[col] = nat_id
        cursor += len(body_bytes)

    if cursor != len(raw):
        # So' alcancavel com ultima coluna COM size (min_header=False): sobra
        # de bytes que o header nao declara -> corrompido/concatenado.
        raise ValueError(
            f"bytes excedentes: {len(raw) - cursor}B apos a ultima coluna "
            f"(header declara menos que o blob contem; T-QA-8 BUG-05)"
        )
    counts = {c: len(v) for c, v in result.items()}
    if len(set(counts.values())) > 1:
        raise ValueError(
            f"colunas com n_rows divergentes {counts} — blob corrompido/"
            f"truncado (T-QA-8 BUG-05)"
        )

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


def _stringify_checked(values, col_name: str | None = None) -> list[str]:
    """Stringify (_to_str) + validação de \\n/\\r na MESMA passada — FONTE
    ÚNICA dos ramos list (encoder) e dict (_encode_multi).

    Dedup C0 (T-CODE-CORE-CONSOLIDATE D2): os dois ramos carregavam loops
    gêmeos (BUG-06 lote 2 + BUG-10a lote 3) — regra e mensagem agora vivem
    aqui, uma vez. Valida o que VAI SER USADO (pós-transformação): objeto com
    __str__ contendo quebra não fura. Contrato lossless: LF delimita 1 valor
    por linha; \\n embutido corromperia o RT em silêncio -> fail-loud."""
    out: list[str] = []
    loc = f"coluna {col_name!r}, " if col_name is not None else ""
    for i, v in enumerate(values):
        s = _to_str(v)
        if "\n" in s or "\r" in s:
            bad = "\\n" if "\n" in s else "\\r"
            raise ValueError(
                f"valor com quebra de linha ({bad}) nao e' representavel no "
                f"TCF (LF delimita linhas): {loc}indice {i}: {s!r}"
            )
        out.append(s)
    return out


def _decode_raw_body(body_bytes: bytes) -> list[str]:
    """Body raw (V2-A `!`) -> valores — FONTE ÚNICA decode+view (dedup C0,
    T-CODE-CORE-CONSOLIDATE D3; paridade por CONSTRUÇÃO, mesmo padrão do
    _parse_meta). Split exato por LF: _fallback_safe garantiu no encode que
    nenhum valor tem '\\n' embutido (sem LF terminal — body é join puro)."""
    return body_bytes.decode("utf-8").split("\n")


def _fallback_safe(values: list[str]) -> bool:
    """Raw mode (V2-A) e' seguro sse nenhum valor tem '\\n' embutido.

    Body raw = "\\n".join(values); decode faz body.split("\\n"). Um '\\n'
    dentro de um valor quebraria a contagem de valores. (O caminho TCF tambem
    assume valores sem '\\n' — premissa de 'dados felizes' — entao isto nao
    restringe alem do que ja' e' assumido; apenas evita escolher raw onde
    seria lossy.)
    """
    return not any("\n" in v for v in values)

"""TCF multi-column — core enc/dec (orquestra os candidatos por coluna).

Pos-ADR-0014 (API unificada): a funcao publica e' `encode(dict)` /
`decode(text)` em `tcf.encoder` / `tcf.decoder`. Este modulo provê a
implementacao interna `_encode_multi` + `_decode_multi`, chamados por
`encode()` / `decode()` quando dispatch identifica tipo dict ou shebang `#TCF.8M`.

Candidatos por coluna (fallback V2-A): tcf (sempre) / raw (`!`) / dict (`@`,
[`dict_v2b`](dict_v2b.py)) / split (`%`, [`split`](split.py)). Paralelismo em
[`parallel`](parallel.py) (host). Re-export publico em [`__init__`](__init__.py).

Header format. **#TCF.8M e' o DEFAULT** (ADR-0032). Legado #TCF.6/#TCF.7
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
- Nome '' = nome VAZIO, emitido como `\\z` no meta (ADR-0046, espelho do `.8H`) e
  preservado no decode. Coluna ANONIMA (posicional) so' via `drop_names`.
- Todas colunas devem ter mesmo numero de valores (0 inclusive: a tabela de 0 linhas
  sai com corpo `@` de tabelinha vazia, que diz zero sem ambiguidade).
- NULL/None convertido pra '' (empty string); coluna deve ser LISTA (str/bytes
  = erro que ensina).
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

from tcf.wire import MAGIC_BASE_B, MAGIC_MULTI_B
MAGIC_MULTI_V3 = MAGIC_MULTI_B  # multi-col DEFAULT (ADR-0032). Discriminador de 1 char:
# 'M' logo apos #TCF.8 (SEM espaco); meta INLINE na linha
# do shebang ('#TCF.8M<meta>\n'). Legado #TCF.6/.7 cortado.
MAGIC_SINGLE_V3 = MAGIC_BASE_B  # single-col self-describing (SEM flag M -> single,
# decode retorna list). Header numa linha: '#TCF.8 [nome]:spec'
# (espaco = single+spec) ou '#TCF.8' (newline = version-stamp).
# Opt-in. ADR-0027/0029.


# --- Escape de NOMES no meta ---
# Interim: SO' backslash (estilo CSV-quoting simplificado; estudo de quoting/outros
# casos adiado — ver ticket). Escapa os separadores do meta (,/=/:) + o proprio '\'
# + prefixo de modo (!@%) INICIAL (colidiria com a ultima-coluna-bare). O tokenizer
# splita em separador NAO-escapado. So' '\n' fica proibido (separador de linha,
# irrepresentavel no meta de 1 linha).
_NAME_SEP = ",=:\\"


def _esc_name(name: str) -> str:
    """Escapa (backslash) os chars estruturais de um nome de coluna no meta.

    Nome VAZIO '' -> `\\z` (ADR-0046; espelho de `hierarchical._esc_name`, ADR-0033).
    Por que um marcador e nao "emitir nada": "nome vazio no header" e' o SENTINELA
    DE CORRUPCAO do parse, e emitir nada tornava `{"": v}` indistinguivel de coluna
    ANONIMA (`drop_names`) — o decode devolvia o nome POSICIONAL, o UNICO caso em
    que o TCF alterava o dado (BUG-CHAVE-VAZIA-POSICIONAL). `\\z` e' inemitivel por
    dado: o `\\` de dado e' sempre dobrado, entao o nome literal `\\z` sai `\\\\z`.
    A decisao anterior ('' = anonima, BUG-01 T-QA-8 F0) vinha de
    um `\\` SOLTO que fundia tokens — `\\z` nao e' solto, e' escape completo.
    O guard `s[:1] and` fecha o buraco do idiom (`'' in "!@%"` e' True)."""
    if name == "":
        return "\\z"
    out = []
    for ch in name:
        if ch in _NAME_SEP:
            out.append("\\")
        out.append(ch)
    s = "".join(out)
    if s[:1] and s[:1] in "!@%":  # prefixo de modo no inicio colidiria (last-col bare)
        s = "\\" + s
    if s[-1:] in _TAGS:
        # Nome que TERMINA em tag de tipo colidiria na ultima coluna bare: sem o
        # escape, o token `!N` seria ao mesmo tempo "coluna chamada N" e "coluna
        # anonima de tipo N". Mesma razao do prefixo de modo acima, no outro extremo
        # do token. Custa 1 byte, e so' em nome que termina assim.
        s = s[:-1] + "\\" + s[-1]
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


_ESC_OK = ",=:\\!@%NB"  # whitelist canonica: o encoder SO' escapa estes chars
# (_NAME_SEP em qualquer posicao + prefixo de modo !@%)


def _unesc_name_strict(s: str) -> str:
    """Unescape ESTRITO do nome (decode): so' aceita o que o encoder emite.

    Fail-loud (marcadores de corrupcao — T-TOOL-TCF-FIX-CORRUPTION):
    - backslash SOLTO no fim (escape de nada): '\\' legitimo sai '\\\\' (BUG-01);
    - escape de char FORA da whitelist `_ESC_OK` ('\\b', '\\x'...): nao-emitivel;
      aceitar mudaria o nome CALADO (BUG-11b, lote 3 — whitelist por deducao do
      canone: escapes validos sao exatamente os que `_esc_name` produz)."""
    if s == "\\z":                      # nome VAZIO (ADR-0046) — so' como token INTEIRO;
        return ""                       # `\z` embutido cai na whitelist abaixo (z nao esta')
    out, i, n = [], 0, len(s)
    while i < n:
        c = s[i]
        if c == "\\":
            if i + 1 >= n:
                raise ValueError(
                    f"meta corrompido: escape dangling (backslash solto) no nome "
                    f"{s!r} — o encoder nunca emite isso (nome '' sai como '\\z')"
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


_HEX = "0123456789abcdef"

# TAG DE TIPO por coluna, logo DEPOIS do size (`!aN=valor`). Duas tags bastam:
# string e' o default (sem tag) e int-vs-float se deduz do valor, como o `.8H`
# ja' faz. MAIUSCULA porque o size e' hex minusculo canonico: fora do alfabeto
# hex, a tag e' inequivoca e nenhum wire ja' emitido pode ser mal-lido.
_TAG_DO_TIPO = {int: "N", float: "N", bool: "B"}
_TIPO_DA_TAG = {"N": "n", "B": "b"}      # -> a grafia interna, a mesma do `.8H`
_TAGS = frozenset(_TIPO_DA_TAG)


def _hex_size(s: str) -> int:
    """Size hex CANONICO do meta -> int, com erro CLARO em corrupcao (fail-loud).

    Canonico = o que `format(n, 'x')` emite: minusculo, sem zero a esquerda, sem
    sinal, sem '0x', sem separador, sem espaco. E' a MESMA regra que a familia .8
    ja' aplica no bN de dominio (`dominio_bn.py`) e no `#TCF.8bB` (`decoder.py`),
    pela mesma razao: duas grafias para o mesmo valor quebram a canonicidade do
    wire, e um blob que so' UM lado aceita nao e' um formato.

    O `int(s, 16)` cru aceitava `0x5`, `+5`, `-5` (size NEGATIVO), `5_0`, espaco
    em volta e digito nao-ASCII. Varredura dos 3632 `.tcf` do repo: 662 slots de
    size reais, ZERO fora do canonico, entao apertar nao recusa nada que o TCF
    tenha emitido. De quebra, deixa `A`-`F` livres como alfabeto de TAG DE TIPO.
    """
    if not s or any(c not in _HEX for c in s):
        raise ValueError(
            f"meta corrompido: size hex invalido {s!r} no meta do #TCF.8M "
            f"(canonico: minusculo, sem sinal, sem '0x', sem zero a esquerda)"
        )
    n = int(s, 16)
    if f"{n:x}" != s:                       # grafia MINIMA: '05' nao e' '5'
        raise ValueError(
            f"meta corrompido: size nao-canonico {s!r} no meta do #TCF.8M "
            f"(canonico: {n:x})"
        )
    return n


def _parse_meta(meta_str: str) -> list[tuple[int | None, str | None, str, str | None]]:
    """Parse do meta INLINE do #TCF.8M -> [(size, name, mode, nature_id)] por coluna.

    FONTE UNICA do parse do meta — `_decode_multi_impl` E `tcf.view` consomem
    daqui: paridade decode/view por CONSTRUCAO, nao por verificacao (BUG-02,
    T-QA-8 F0 2026-07-10). `size=None` = ultima coluna (corpo ate' EOF);
    `name=None` = coluna ANONIMA (nome POSICIONAL str(i) fica no caller).

    Fail-loud (marcadores de corrupcao; futuro reparador: T-TOOL-TCF-FIX-CORRUPTION):
    - nome DECLARADO vazio no TOKEN CRU ('<size>='): o encoder nunca emite ('' sai
      como `\\z`, que des-escapa pra '' e e' LEGITIMO — ADR-0046);
    - backslash solto no fim de nome (escape de nada);
    - size hex invalido.
    """
    tokens = _split_unesc(meta_str, ",")  # ',' escapado no nome fica intacto
    n_cols = len(tokens)
    # `drop_names` (coluna anonima, ADR-0029) e' DEDUZIVEL do meta: nenhum token tem
    # '=' e a ULTIMA e' so' o prefixo de modo (nao ha' nome a omitir). Sem isso, a
    # ultima coluna anonima TIPADA seria lida como coluna de NOME '3N', e o tipo se
    # perderia calado. `\z` (nome vazio, ADR-0046) nao confunde: e' token nao-vazio.
    # Com `drop_names` NENHUM token tem '=', porque nao ha' nome a declarar. Numa
    # tabela nomeada o `min_header` omite o '=' SO' da ultima coluna, entao a partir
    # de 2 colunas os dois casos se separam sozinhos. Com 1 coluna a distincao e' o
    # token vazio: `!` e' anonima, `!nome` e' nomeada.
    sem_nome = all(len(_split_unesc(tk, "=", 1)) == 1 for tk in tokens)
    # Com 1 coluna anonima o token e' so' o prefixo (`!`) ou o prefixo mais a tag
    # (`!N`): nao ha' size, porque o corpo vai ate' EOF. Um nome de UMA letra
    # maiuscula que por acaso seja `N` ou `B` fica indistinguivel, e a saida e' a
    # mesma de sempre: o encoder nao emite essa forma (nome sai com size, `!3N=N`),
    # entao so' wire escrito a mao cai aqui.
    _bare = tokens[0].lstrip("!@%") if tokens else ""
    drop_names_hint = sem_nome and (
        n_cols >= 2 or (n_cols == 1 and (_bare == "" or _bare in _TAGS))
    )
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
        tipo = None
        if len(eq) == 2 and eq[0][-1:] in _TAGS:
            # `<size><TAG>=<nome>`: a tag e' MAIUSCULA e o size e' hex minusculo,
            # entao ela nunca se confunde com o size nem com o nome (que vem
            # depois do '='). Sem tag = coluna de texto, o default.
            tipo = _TIPO_DA_TAG[eq[0][-1]]
            eq[0] = eq[0][:-1]
        if len(eq) == 2:
            # '<size>=<nome>' — nomeada. Nome des-escapado (nomes com ,/=/:/! etc).
            size_str, name = eq
            size = _hex_size(size_str)
            # O sentinela de corrupcao e' o TOKEN CRU vazio ('<size>='), checado
            # ANTES do unescape — `\z` des-escapa pra '' e e' LEGITIMO (ADR-0046,
            # mesmo desenho do `.8H`: "o parse passou a checar o TOKEN CRU").
            if name == "":
                raise ValueError(
                    "meta corrompido: nome de coluna DECLARADO vazio ('<size>=') — "
                    "o encoder nunca emite (nome '' sai como '<size>=\\z')"
                )
            name = _unesc_name_strict(name)
        elif i == n_cols - 1:
            # ultima coluna SEM '=': min_header (corpo ate' EOF). p = nome; token
            # cru '' = anonima posicional (drop_names); `\z` = nome VAZIO (ADR-0046).
            #
            # Com `drop_names` NAO ha' nome, entao o token e' `<size><TAG>` e a tag
            # precisa sair ANTES do `_hex_size`. Sem este ramo, `!3N` virava a coluna
            # de NOME '3N' e o tipo se perdia calado: o decode devolvia string.
            if drop_names_hint and p and p[-1:] in _TAGS:
                tipo = _TIPO_DA_TAG[p[-1]]
                p = p[:-1]        # sobra o size, ou '' na anonima de 1 coluna
            if drop_names_hint:
                size = _hex_size(p) if p else None
                name = None
            else:
                size = None
                name = _unesc_name_strict(p) if p else None
        else:
            # nao-ultima SEM '=' -> coluna ANONIMA: p = '<size>' (so' drop_names)
            if p[-1:] in _TAGS:
                tipo = _TIPO_DA_TAG[p[-1]]
                p = p[:-1]
            size = _hex_size(p)
            name = None
        pairs.append((size, name, mode, nat_id, tipo))
    return pairs


def _nomes_resolvidos(pairs) -> list[str]:
    """Nomes de coluna JA' resolvidos: anonima -> nome POSICIONAL `str(i)` (ADR-0029).

    FONTE UNICA core+view, pela MESMA razao do `_parse_meta` (BUG-02, T-QA-8 F0): os dois
    consumidores resolviam o posicional por conta propria e indexavam um dict por nome —
    logo a resolucao podia colidir nos dois, e o cheque teria de existir em duplicata.
    Resolvendo aqui, a paridade e' por CONSTRUCAO e o guard e' herdado.

    Fail-loud em colisao: um nome EXPLICITO
    que casa com o posicional de uma anonima (ex.: `#TCF.8M!5,!5=0,!fim`) fazia o
    `decode` devolver MENOS colunas do que o header declara — a 2a sobrescrevia a 1a no
    dict — e a `view` servir os MESMOS bytes em duas chaves, reportando as 3 colunas
    (pior: a contagem nao denunciava). Nos dois casos CALADO, e os cheques do BUG-05 nao
    pegam: bytes e n_rows fecham.

    O ENCODE nunca emite esta forma — chave de dict e' unica, `''` e' um nome como
    outro (sai `\\z`, ADR-0046) e `drop_names` torna TODAS posicionais e distintas. Logo o
    guard so' alcanca wire ESTRANGEIRO/corrompido, e e' deduzido de graca como os outros.
    """
    nomes = [n if n is not None else str(i) for i, (_s, n, _m, _x, _t) in enumerate(pairs)]
    if len(set(nomes)) != len(nomes):
        vistos: set[str] = set()
        repetidos: list[str] = []
        for n in nomes:
            if n in vistos and n not in repetidos:
                repetidos.append(n)
            vistos.add(n)
        raise ValueError(
            f"meta corrompido: nome de coluna repetido {repetidos} — colisao entre nome "
            f"EXPLICITO e nome POSICIONAL de coluna anonima; o header declara "
            f"{len(nomes)} colunas mas so' {len(set(nomes))} chaves distintas, e o "
            f"excedente seria perdido calado (T-META-COLISAO-NOME-POSICIONAL)"
        )
    return nomes


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
            §5.1, owner). A nature COMPETE no min() por coluna: encoda-se
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
    n_linhas = next(iter(lengths.values()))
    if n_linhas == 0 and nature_specs:
        # Uma spec declarada numa coluna de ZERO linhas nao tem valor pra transformar, e
        # nao pode vencer o FLOOR por construcao (original e transformado tem o mesmo
        # tamanho, e o `:id` so' soma bytes). Deixar passar seria descartar em silencio o
        # que o chamador declarou, que e' a classe de defeito do T-NATURE-IGNORADA-CALADA.
        # Antes de 2026-08-26 esta entrada nem chegava aqui: ela caia no `.8H`, que ja'
        # levantava. Fail-loud CONTINUA, so' muda o ponto e a mensagem.
        alvo = sorted(set(nature_specs) & set(table))
        if alvo:
            raise ValueError(
                f"schema/nature declarado em coluna(s) de 0 linhas {alvo}: nao ha' valor "
                f"pra transformar, e aplicar calado esconderia a declaracao"
            )

    for col_name in table.keys():
        # #TCF.8M default (ADR-0032): separadores do meta (,/=/:) + '\' + prefixo de
        # modo (!@%) inicial sao ESCAPADOS no nome (_esc_name, T-FMT-NAME-ESCAPING, M2).
        # So' '\n' fica proibido: e' o separador de linha do meta (irrepresentavel).
        if "\n" in col_name:
            raise ValueError(
                f"col name nao pode conter '\\n' (separador de linha do meta): {col_name!r}"
            )

    # Nome VAZIO '' e' um NOME como outro — sai no meta como `\z` (ADR-0046) e volta ''.
    # Com `drop_names=True` e' dropado como qualquer outro nome: o posicional e' o pedido.

    # Stringify upfront (per-col paralelo recebe valores ja' string) + check
    # de \n/\r na MESMA passada — FONTE ÚNICA `_stringify_checked` (BUG-06
    # lote 2; dedup C0 D2: o ramo list do encoder consome a mesma função).
    table_str: dict[str, list[str]] = {
        name: _stringify_checked(values, name) for name, values in table.items()
    }
    # TIPO por coluna: o primitivo do dado ja' e' uma declaracao, e o header e' o
    # unico lugar onde ela cabe. Nao se deduz do corpo: `["1","2"]` e `[1,2]` geram
    # bytes IGUAIS, e sem a tag o decode nao teria como distinguir. String e' o
    # default (tag ausente), entao a tabela de texto continua com o mesmo header.
    col_types: dict[str, str] = {}
    for name, values in table.items():
        primeiro = next((v for v in values if v is not None), None)
        tag = _TAG_DO_TIPO.get(type(primeiro))
        if tag:
            col_types[name] = tag

    # Dispatch paralelo se solicitado E vale a pena (>= 2 cols).
    # parallel=1 -> SERIAL por DEDUCAO (BUG-10c, lote 3): 1 worker produz os
    # MESMOS bytes por construcao — economiza o spawn do pool inteiro.
    # CUIDADO: True == 1 em Python — o isinstance(bool) preserva parallel=True.
    use_parallel = len(table_str) >= 2 and n_linhas > 0 and (
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
            tag = col_types.get(name, "")     # '' = texto, o default
            ultima_bare = (min_header or drop_names) and i == last_i
            if tag and ultima_bare and not (drop_names and last_i == 0):
                # sem size nao ha' onde ancorar a tag: a coluna tipada PAGA o size.
                # Mesmo trade que o `.8H` ja' faz ("coluna tipada sempre emite
                # :size+tag"). Custa 3 a 6 B, uma vez por tabela.
                #
                # EXCECAO: tabela ANONIMA de UMA coluna. Ali `!3N` seria ambiguo com
                # uma coluna CHAMADA '3N' (com 1 token nao ha' vizinho que denuncie a
                # forma anonima), entao ela segue bare e a tag vai pro fim: `!N`. O
                # size nao faz falta, o corpo vai ate' EOF.
                ultima_bare = False
            if drop_names:
                parts.append(
                    f"{pre}{tag}{suf}" if ultima_bare
                    else f"{pre}{_sz(len(body))}{tag}{suf}"
                )
            elif ultima_bare:
                parts.append(f"{pre}{_esc_name(name)}{suf}")
            else:
                parts.append(f"{pre}{_sz(len(body))}{tag}={_esc_name(name)}{suf}")
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
        if n_linhas == 0:
            # ZERO linhas tem UMA grafia so', e ela nao sai do `min()`: o candidato raw
            # de 0 linhas e' um corpo de ZERO byte, que decodifica como UMA linha vazia,
            # e ele ganharia o min() por ser o menor. O corpo `@` de tabelinha vazia
            # (`0\n`) e' o unico que diz zero sem ambiguidade, entao ele e' imposto, e
            # `fallback=False` nao o desliga: desligar produziria wire que perde o dado
            # em silencio, e nenhum knob de bytes pode comprar isso.
            best_body, best_mode = b"0\n", "dict"
        else:
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
            # o `:id` do meta e' o wire_id (plano do DADO, ADR-0041), nao o name
            nature_candidates[name] = (nat_body, nat_mode, spec.wire_id)

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
    # #TCF.8M e' o formato DEFAULT do multi-col (ADR-0032). O legado
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
) -> tuple[dict[str, list[str]], dict[str, str], dict[str, str]]:
    """Parse + decode multi-col, SEM aplicar natures.

    Retorna (result, nature_ids, casts_adiados).

    `nature_ids` = {col_name -> nature-id STRING} extraido do sufixo ':id' do meta-line
    (#TCF.8, ADR-0027); vazio pra #TCF.6/7. A APLICACAO da nature (resolve +
    decode_value) fica no `decode()` publico, que resolve a precedencia
    header-vs-usuario. Mantem multi/core agnostico de nature (so' PARSEIA a tag, nao
    depende de tcf.natures).

    `casts_adiados` = {col_name -> tag de tipo} das colunas que tem NATURE **e** TIPO.
    Nelas o corpo guarda a grafia transformada pela nature, entao castar antes de
    desfaze-la le' `01` como numero e levanta. O chamador aplica `_dec_scalar` DEPOIS do
    `decode_value`. Coluna sem nature segue castada aqui mesmo, como sempre.

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
    # #TCF.8M e' o UNICO multi-col vivo (ADR-0032). Legado #TCF.6/#TCF.7
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
    casts_adiados: dict[str, str] = {}
    # Anonima -> nome POSICIONAL (ADR-0029) + guard de colisao, em FONTE UNICA com a
    # view (`_nomes_resolvidos`) — 4o cheque deduzido de graca do BUG-05.
    nomes = _nomes_resolvidos(pairs)
    for i, (size, name, mode, nat_id, tipo) in enumerate(pairs):
        col = nomes[i]
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
        if tipo is not None:
            if nat_id is not None:
                # NATURE ANTES DO CAST (2026-08-27, onda 1). A ordem estava invertida e
                # produzia WIRE MORTO: numa coluna numerica com spec de padding, o corpo
                # guarda a grafia TRANSFORMADA (`01`), e o cast rodava sobre ela, dando
                # `corpo number invalido '01'`. O `encode` aceitava, e so' o leitor
                # descobria, possivelmente noutra maquina.
                #
                # A aplicacao da nature mora no `decode()` publico, que e' quem resolve a
                # precedencia header-vs-usuario, e este modulo continua agnostico de
                # nature. Entao o cast desta coluna e' ADIADO e devolvido ao chamador,
                # que o aplica depois do `decode_value`.
                casts_adiados[col] = tipo
            else:
                # o header declarou o tipo: devolve o VALOR, nao a grafia. `_dec_scalar`
                # e' o mesmo do `.8H`, entao as duas rotas concordam por construcao
                # (int vs float sai do proprio valor; nulo continua nulo).
                from tcf.hierarchical import _dec_scalar
                result[col] = [None if v is None or v == "" else _dec_scalar(v, tipo)
                               for v in result[col]]
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
            f"truncado, ou wires concatenados (a ultima coluna absorve o "
            f"excedente; T-QA-8 BUG-05)"
        )

    return result, nature_ids, casts_adiados


def _decode_multi(tcf_text: str) -> dict[str, list[str]]:
    """Wrapper compat: decode multi-col retornando so' o dict (natures NAO
    aplicadas). Usado por `split.py` na recursao de sub-tabela (que nunca tem
    nature) e re-exportado. `decode()` usa `_decode_multi_impl` pra aplicar as
    natures do header com a precedencia correta."""
    result, _ids, casts_adiados = _decode_multi_impl(tcf_text)
    if casts_adiados:
        # Este wrapper NAO aplica nature, entao um cast adiado ficaria pendente pra
        # sempre e a coluna voltaria como grafia da nature. A sub-tabela do `split` nunca
        # tem nature (por isso o wrapper existe), mas quem chamar isto por fora com um
        # wire que tenha `:id` + tag de tipo receberia dado errado em silencio.
        raise ValueError(
            f"wire com nature E tipo nas colunas {sorted(casts_adiados)}: use `decode()`, "
            f"que resolve a nature antes do cast (este wrapper nao aplica nature)"
        )
    return result


def _to_str(v) -> str:
    """Stringify uniforme. NULL/None -> '' (ADR-0013).

    `bool` sai `true`/`false`, nao `True`/`False`: e' a grafia que o `.8H` ja'
    emite e que o `_dec_scalar` le'. Uma segunda grafia pro mesmo valor quebraria
    a canonicidade do wire, e as duas rotas divergiriam no round-trip.
    """
    if v is None:
        return ""
    if v is True:
        return "true"
    if v is False:
        return "false"
    return str(v)


def _stringify_checked(values, col_name: str | None = None) -> list[str]:
    """Stringify (_to_str) + validação de \\n/\\r na MESMA passada — FONTE
    ÚNICA dos ramos list (encoder) e dict (_encode_multi).

    Dedup C0 (T-CODE-CORE-CONSOLIDATE D2): os dois ramos carregavam loops
    gêmeos (BUG-06 lote 2 + BUG-10a lote 3) — regra e mensagem agora vivem
    aqui, uma vez. Valida o que VAI SER USADO (pós-transformação): objeto com
    __str__ contendo quebra não fura. Contrato lossless: LF delimita 1 valor
    por linha; \\n embutido corromperia o RT em silêncio -> fail-loud."""
    out: list[str | None] = []
    loc = f"coluna {col_name!r}, " if col_name is not None else ""
    for i, v in enumerate(values):
        if v is None:
            # `None` ATRAVESSA: null tem slot PRE-ALOCADO na tabela de
            # referencias (syntax._SLOTS_RESERVADOS), nao e' string a stringificar. O
            # `_to_str` antigo o achatava em `''` — perda SILENCIOSA da distincao
            # `null` != `""` (as duas viravam a mesma linha vazia). Quem nao aceita null
            # barra ANTES, no dispatch (`_lista_flat`/`_tabela_flat`).
            out.append(None)
            continue
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
    # `None` (nulo) nao e' string e nao tem quebra a checar. Alem disso o modo raw
    # achataria o nulo numa linha vazia, perdendo a distincao entre `None` e `""`:
    # coluna com nulo nao concorre em raw, e quem atende e' o candidato tcf, que
    # tem slot proprio pro nulo.
    if any(v is None for v in values):
        return False
    return not any("\n" in v for v in values)

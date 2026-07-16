"""TCF.8H — codec hierárquico (weld T-CODE-TCF8H-WELD, ADR-0031).

Camada L2 (RELACIONAMENTO entre colunas) + L3 (OTIMIZAÇÃO) sobre L1 (o compressor
de colunas do core, REUSADO sem mudança). Arquitetura em 3 camadas do owner
(2026-07-14, `experiments/lab/dirty/notas/tcf-camadas-arquitetura.md`):

  L1  compressor de colunas  -> `encode(list)`/`decode(body)` do core (INTOCADO).
  L2  relacionamento          -> a topologia da árvore vive no HEADER; só o header
                                 reconstrói o dataset, independente da compressão.
  L3  otimização              -> counts (multiplicidade 1×), última-folha-sem-size,
                                 omit-closes — deduções que economizam bytes.

Modelo: SHREDDING em blocos. A árvore vira colunas agrupadas por bloco (raiz + um
bloco por array). Objetos `{}` (1:1) são inline (colunas do mesmo bloco). Cada array
`[]` (1:N) abre um bloco filho, ligado ao pai por um `#count` explícito (nº de filhos
por instância-pai). Isso fecha os clássicos de transmissão: múltiplas listas irmãs,
arrays aninhados, arrays vazios, e a ambiguidade de chave (count ESCRITO, não deduzido).

Wire (ADR-0031, sem-espaço, LF-only):
  #TCF.8H<meta>\\n<colunas em ordem DFS, encode() cada, fatiadas por size>
    name:size            escalar
    name{...}            objeto 1:1 (inline, mesmo bloco)
    name#:csize[...]     array de objetos (bloco filho; #csize = coluna de counts)
    name#:csize[]:asize  array de escalares (coluna name = elementos; #csize = counts)
    name?:msize...       campo MASCARADO (P1 presença + P3a null): #msize = coluna-MÁSCARA,
                         vem ANTES das colunas do campo. Alfabeto '.'=presente(valor não-nulo)
                         '-'=ausente (P1) '0'=null (P3a). Corpo denso: só instâncias '.'.
    name#:csize?:emsize[...]  array com ELEMENTOS mascarados (P3b): #emsize = element-mask
                         (2-estados '.'=valor '0'=null, SEM '-' — a posição existe via count),
                         entre count e '['. Ordem: count → emask → elementos densos.
    name:size<tag>       coluna escalar TIPADA (P2): tag='n' number (json) · 'b' bool (true/false).
                         String = default (sem tag). Coluna TIPADA sempre emite :size+tag (só
                         string-default pode omitir size na última folha).
    última folha DFS omite size; omit-closes dropa o `]`/`}` final.

Escopo (classe coberta): uma raiz (lista de registros), `{}`/`[]` recursivos, chaves
OPCIONAIS (P1), `null` em CAMPO (P3a) e em ELEMENTO de array (P3b), e TIPOS escalares
(P2 — string/number/bool por coluna; int/float via json, distingue por-valor). Distingue
ausente≠null≠"null"≠""≠30(int)≠True(bool). Fora (fail-loud, NUNCA str()-engolido): tipos
escalares MISTOS numa coluna (P5 union), NaN/±Inf (não-JSON), array de objetos sem chaves,
N raízes, N:N/snowflake (FK).

Aditivo: `#TCF.8M`/single/órfão intactos. Este módulo é CLIENTE de `encode`/`decode`.
"""
from __future__ import annotations

import json
import math

from tcf.decoder import decode as _decode_col   # L1: decode de 1 coluna (body órfão)
from tcf.encoder import encode as _encode_col    # L1: encode de 1 coluna (lista -> body)

MAGIC = "#TCF.8H"


class HierarchicalError(ValueError):
    """Entrada/blob hierárquico malformado ou fora da classe coberta (fail-loud)."""


# ---------------- escaping de NOME no meta (portado do .8M, T-FMT-NAME-ESCAPING) ----------------
# Auditoria 2026-07-15: nomes CRUS com chars da gramática (`,[]{}:#`) corrompiam calado ou
# travavam o parse. Mesma convenção do multi/core.py: backslash-escape + unescape ESTRITO
# (whitelist; escape fora dela = marcador de corrupção, fail-loud).
_H_NAME_SEP = ",[]{}:#?\\"     # chars estruturais do meta-árvore (inclui '?' = opcional, P1) — escapados
_H_ESC_OK = _H_NAME_SEP + " "  # whitelist do unescape (espaço: escapado só se INICIAL)


def _esc_name(name: str) -> str:
    if not name:
        raise HierarchicalError(
            "nome de campo vazio nao e' representavel no meta do #TCF.8H"
        )
    if "\n" in name:
        raise HierarchicalError(
            "nome de campo com \\n nao e' representavel (meta de 1 linha)"
        )
    out = []
    for ch in name:
        if ch in _H_NAME_SEP:
            out.append("\\")
        out.append(ch)
    s = "".join(out)
    if s[0] == " ":  # espaço INICIAL: o parser come separadores " ," antes do nome
        s = "\\" + s
    return s


def _unesc_name(s: str) -> str:
    """Unescape ESTRITO (só aceita o que `_esc_name` emite; resto = corrupção)."""
    out, i, n = [], 0, len(s)
    while i < n:
        c = s[i]
        if c == "\\":
            if i + 1 >= n:
                raise HierarchicalError(
                    f"meta corrompido: escape dangling (backslash solto) no nome {s!r}"
                )
            nxt = s[i + 1]
            if nxt not in _H_ESC_OK:
                raise HierarchicalError(
                    f"meta corrompido: escape de char nao-estrutural '\\{nxt}' no nome "
                    f"{s!r} — o encoder so' escapa {_H_ESC_OK!r}"
                )
            out.append(nxt)
            i += 2
        else:
            out.append(c)
            i += 1
    return "".join(out)


# ============================================================ L2: schema (topologia)
# nó UNIFORME: (kind, name, masked, kids)
#   kind: 'scalar' | 'object' | 'arr_scalars' | 'arr_objects'   ·   kids=None p/ escalar/arr_scalars
#   masked=True -> campo tem MÁSCARA def-level 3-estados: '.'=presente · '-'=ausente (P1) ·
#                  '0'=null (P3a). masked = (pode faltar) OU (pode ser null).
# NOTA (H-PROFILE-01): null usa a MÁSCARA (slot '0' reservado no P1). O índice-de-substituição
# (lab 2026-07-15-2101) é a alternativa a MEDIR sob perfil de uso — trocável aqui depois, sem
# mudar a API. O null-repr fica localizado em _emit_row/_read_object (a "costura" pra o swap).
def _kind_of(v):
    if v is None:
        return "null"
    if isinstance(v, dict):
        return "object"
    if isinstance(v, list):
        return "array"
    return "scalar"          # str/int/float/bool — sub-tipo em _scalar_type (P2)


# ---- P2: sub-tipo escalar por-COLUNA (tag no meta) ----
# stype: 's'=string(default) · 'n'=number(int/float, json) · 'b'=bool(true/false)
def _scalar_type(values: list) -> str:
    """Deduz o tipo da coluna dos valores Python NÃO-nulos. Misto (str+num etc.) = fail-loud (P5)."""
    ts = set()
    for v in values:
        if isinstance(v, bool):            # bool ANTES de int (bool ⊂ int em Python)
            ts.add("b")
        elif isinstance(v, (int, float)):
            if isinstance(v, float) and not math.isfinite(v):
                raise HierarchicalError("NaN/Infinity fora do JSON (RFC 8259) — não é P2")
            ts.add("n")
        elif isinstance(v, str):
            ts.add("s")
        else:
            raise HierarchicalError(f"valor escalar de tipo não suportado: {type(v).__name__}")
    if len(ts) > 1:
        raise HierarchicalError(f"tipos escalares MISTOS {ts} numa coluna — fora da classe (P5 union)")
    return ts.pop() if ts else "s"         # coluna vazia/all-null → string default


def _enc_scalar(v, stype: str) -> str:
    if stype == "n":
        return json.dumps(v)               # int/float canônico ('30', '9.5', '1000.0')
    if stype == "b":
        return "true" if v else "false"
    return str(v)                          # string (identidade p/ str)


def _dec_scalar(s: str, stype: str):
    if stype == "n":
        return json.loads(s)               # int OU float (o '.'/'e' no texto distingue)
    if stype == "b":
        return s == "true"
    return s


def _derive_schema(records: list) -> list:
    """Schema robusto: união de chaves (ordem de 1ª aparição), presença por campo, e
    validação de TIPO HONESTA — campo com tipos ESTRUTURAIS mistos (scalar/object/array)
    ou `null` é fail-loud (fora da classe; P2 tipos / P3 null), NUNCA str()-engolido.
    (auditoria 2026-07-15: tipos mistos e null-em-elemento corrompiam calado.)"""
    if not isinstance(records, list) or not records:
        raise HierarchicalError("hierárquico espera uma lista NÃO-VAZIA de objetos (registros)")
    if not all(isinstance(r, dict) for r in records):
        raise HierarchicalError("hierárquico espera objetos (dict) em cada registro")
    keys = []                                    # união preservando ordem de aparição
    for r in records:
        for k in r:
            if k not in keys:
                keys.append(k)
    nodes = []
    for k in keys:
        present = [r[k] for r in records if k in r]
        optional = len(present) < len(records)   # deduzido do dado (como todo o header)
        nodes.append(_field_node(k, present, optional))
    return nodes


def _field_node(name, present: list, optional: bool):
    """P3a: null em CAMPO (máscara '0'). P3b: null em ELEMENTO de array (element-mask 2-estados,
    flag `elem_null`). kind vem dos NÃO-nulos; all-null → escalar vazio. Tipos mistos = fail-loud.
    nó: (kind, name, masked, kids, elem_null)."""
    kinds = {_kind_of(v) for v in present}
    has_null = "null" in kinds
    non_null = kinds - {"null"}
    masked = optional or has_null                    # def-mask cobre AUSENTE ('-') e NULL ('0')
    present_nn = [v for v in present if v is not None]
    if not non_null:                                 # só-null-quando-presente → escalar vazio
        return ("scalar", name, masked, None, False, "s")
    if len(non_null) > 1:
        raise HierarchicalError(
            f"campo {name!r} com tipos ESTRUTURAIS mistos {non_null} — fora da classe (P2 tipos)"
        )
    kind = non_null.pop()
    if kind == "object":
        return ("object", name, masked, _derive_schema(present_nn), False, "s")
    if kind == "array":
        elems = [e for arr in present_nn for e in arr]
        elem_null = any(e is None for e in elems)    # P3b: algum elemento null → element-mask
        elems_nn = [e for e in elems if e is not None]
        ekinds = {_kind_of(e) for e in elems_nn}
        if len(ekinds) > 1:
            raise HierarchicalError(
                f"array {name!r} com elementos de tipos mistos {ekinds} — fora da classe"
            )
        if elems_nn and next(iter(ekinds)) == "object":
            kids = _derive_schema(elems_nn)
            if not _leaves(kids):
                raise HierarchicalError(
                    f"array de objetos SEM chaves em {name!r} — fora da classe "
                    "(colidiria com array de escalares no wire)"
                )
            return ("arr_objects", name, masked, kids, elem_null, "s")
        return ("arr_scalars", name, masked, None, elem_null, _scalar_type(elems_nn))  # P2: tipo do elemento
    return ("scalar", name, masked, None, False, _scalar_type(present_nn))              # P2: tipo do campo


def _leaves(schema: list, prefix=()):
    """[(path, kind)] em ordem DFS. kind: 'mask' | 'scalar' | 'count' | 'arr_scalars'.
    A coluna de MÁSCARA (presença) vem ANTES das colunas do campo (como o count)."""
    out = []
    for kind, name, masked, kids, elem_null, stype in schema:
        p = prefix + (name,)
        if masked:
            out.append((p, "mask"))
        if kind == "scalar":
            out.append((p, "scalar"))
        elif kind == "arr_scalars":
            out.append((p, "count"))
            if elem_null:                            # P3b: element-mask entre count e elementos
                out.append((p, "emask"))
            out.append((p, "arr_scalars"))
        elif kind == "object":
            out += _leaves(kids, p)
        else:  # arr_objects
            out.append((p, "count"))
            if elem_null:
                out.append((p, "emask"))
            out += _leaves(kids, p)
    return out


# ============================================================ encode (L2 shred + L1)
def encode_hierarchical(records: list) -> str:
    schema = _derive_schema(records)
    order = _leaves(schema)
    if not order:                                # nenhuma coluna -> nº de registros irrepresentável
        raise HierarchicalError(
            "nenhuma coluna derivável (registros sem campos) — nº de registros irrepresentável"
        )
    cols = {key: [] for key in order}
    _emit_array(records, schema, (), cols)
    # L1: encode por coluna (o compressor do core). Coluna vazia -> body vazio.
    bodies = {key: (_encode_col(cols[key]) if cols[key] else "") for key in order}
    meta = _build_meta(schema, bodies, order)
    return f"{MAGIC}{meta}\n" + "".join(bodies[key] for key in order)


def _emit_array(instances: list, children: list, prefix: tuple, cols: dict):
    for obj in instances:
        _emit_row(obj, children, prefix, cols)


def _emit_row(obj: dict, children: list, prefix: tuple, cols: dict):
    if not isinstance(obj, dict):
        raise HierarchicalError(f"esperava objeto em {'/'.join(prefix) or 'raiz'}")
    for kind, name, masked, kids, elem_null, stype in children:
        p = prefix + (name,)
        if name not in obj:
            if not masked:
                raise HierarchicalError(f"campo obrigatório ausente {p}")
            cols[(p, "mask")].append("-")                          # AUSENTE: nada nas colunas de dado
            continue
        v = obj[name]
        if v is None:                                              # NULL (P3a): máscara '0', sem corpo
            if not masked:                                         # derive marca masked se há null — guarda
                raise HierarchicalError(f"null inesperado em {p}")
            cols[(p, "mask")].append("0")
            continue
        if masked:
            cols[(p, "mask")].append(".")                          # PRESENTE (valor não-nulo)
        if kind == "scalar":
            if isinstance(v, (dict, list)):
                raise HierarchicalError(f"tipo divergente em {p}: esperava escalar, veio {type(v).__name__}")
            cols[(p, "scalar")].append(_enc_scalar(v, stype))      # P2: str/number(json)/bool
        elif kind == "object":
            _emit_row(v, kids, p, cols)                            # inline (1:1); valida dict dentro
        elif kind == "arr_scalars":
            if not isinstance(v, list):
                raise HierarchicalError(f"tipo divergente em {p}: esperava array")
            cols[(p, "count")].append(str(len(v)))
            for e in v:                                            # P3b: null em elemento → emask '0'
                if e is None:
                    if not elem_null:
                        raise HierarchicalError(f"null inesperado em elemento de {p}")
                    cols[(p, "emask")].append("0")
                    continue
                if isinstance(e, (dict, list)):
                    raise HierarchicalError(f"elemento não-escalar em {p}")
                if elem_null:
                    cols[(p, "emask")].append(".")
                cols[(p, "arr_scalars")].append(_enc_scalar(e, stype))   # P2: tipo do elemento
        else:  # arr_objects
            if not isinstance(v, list):
                raise HierarchicalError(f"tipo divergente em {p}: esperava array")
            cols[(p, "count")].append(str(len(v)))
            nn = []
            for e in v:                                            # P3b: elemento-objeto null → emask '0'
                if e is None:
                    if not elem_null:
                        raise HierarchicalError(f"null inesperado em elemento de {p}")
                    cols[(p, "emask")].append("0")
                    continue
                if not isinstance(e, dict):
                    raise HierarchicalError(f"elemento não-objeto em array {p}: {type(e).__name__}")
                if elem_null:
                    cols[(p, "emask")].append(".")
                nn.append(e)
            _emit_array(nn, kids, p, cols)                         # bloco filho: só elementos não-null


# ============================================================ L3: header (meta)
def _build_meta(schema: list, bodies: dict, order: list) -> str:
    last = order[-1]

    def sz(path, kind):  # última folha DFS omite size (L3) — SÓ colunas de DADO
        return "" if (path, kind) == last else f":{len(bodies[(path, kind)].encode())}"

    def csz(path, kind):  # colunas de CONTROLE (mask/emask/count) NUNCA omitem (auditoria F1:
        return f":{len(bodies[(path, kind)].encode())}"  # obj vazio mascarado punha mask como última folha

    def dsz(path, kind, stype):  # coluna de DADO: string pode omitir (última); TIPADA sempre :size+tag
        return sz(path, kind) if stype == "s" else f"{csz(path, kind)}{stype}"

    def emit(children, prefix):
        parts = []
        for kind, name, masked, kids, elem_null, stype in children:
            p = prefix + (name,)
            head = _esc_name(name)                                 # nome ESCAPADO (inclui '?' agora)
            if masked:
                head += "?" + csz(p, "mask")                       # '?:msize' (controle: nunca omite)
            em = ("?" + csz(p, "emask")) if elem_null else ""      # P3b: '?:emsize' entre count e '['
            if kind == "scalar":
                parts.append(f"{head}{dsz(p, 'scalar', stype)}")   # P2: tag n/b após size (ou string)
            elif kind == "arr_scalars":
                parts.append(f"{head}#{csz(p, 'count')}{em}[]{dsz(p, 'arr_scalars', stype)}")
            elif kind == "object":
                parts.append(f"{head}{{{emit(kids, p)}}}")
            else:
                parts.append(f"{head}#{csz(p, 'count')}{em}[{emit(kids, p)}]")
        return ",".join(parts)

    return _rstrip_closes(emit(schema, ()))   # omit-closes (L3)


def _rstrip_closes(s: str) -> str:
    """Omit-closes: dropa do fim APENAS closers ESTRUTURAIS (não-escapados).

    Um `\\]`/`\\}` no fim é conteúdo de NOME escapado — dropá-lo deixaria escape
    dangling (interação omit-closes × escaping, auditoria 2026-07-15)."""
    end = len(s)
    while end > 0 and s[end - 1] in "]}":
        k, nb = end - 1, 0
        while k > 0 and s[k - 1] == "\\":
            nb += 1
            k -= 1
        if nb % 2 == 1:   # ímpar = o closer está escapado (pertence ao nome)
            break
        end -= 1
    return s[:end]


def _parse_meta(meta: str):
    order, i, n = [], 0, len(meta)

    def nm(stop):
        # escape-aware: um char precedido de '\' NUNCA termina o token (nome escapado);
        # devolve o trecho CRU (quem é nome des-escapa com _unesc_name; size é dígito puro)
        nonlocal i
        j = i
        while i < n:
            if meta[i] == "\\" and i + 1 < n:
                i += 2
                continue
            if meta[i] in stop:
                break
            i += 1
        return meta[j:i]

    def _to_size(tok):
        try:
            v = int(tok)
        except ValueError:
            raise HierarchicalError(f"size/count invalido no header: {tok!r}")
        if v < 0:                                         # size negativo = corrupção (auditoria)
            raise HierarchicalError(f"size negativo no header: {v}")
        return v

    def _digits():                                        # lê '-'? dígitos (para em delim OU tag n/b)
        nonlocal i
        j = i
        if i < n and meta[i] == "-":
            i += 1
        while i < n and meta[i].isdigit():
            i += 1
        return meta[j:i]

    def size():                                            # size REGULAR (só dígitos → tag pode seguir)
        nonlocal i
        if i < n and meta[i] == ":":
            i += 1
            return _to_size(_digits())
        return None

    def msize():                                          # size da MÁSCARA (controle; sempre presente)
        nonlocal i
        if not (i < n and meta[i] == ":"):
            raise HierarchicalError("'?' sem tamanho de máscara (:msize)")
        i += 1
        return _to_size(_digits())

    def stag():                                           # P2: tag de tipo (n/b) após size de DADO
        nonlocal i
        if i < n and meta[i] in ("n", "b"):
            t = meta[i]
            i += 1
            return t
        return "s"

    def seq(closer, prefix):
        nonlocal i
        nodes = []
        while i < n and (closer is None or meta[i] != closer):
            while i < n and meta[i] in " ,":
                i += 1
            if i >= n or (closer and meta[i] == closer):
                break
            name = _unesc_name(nm(",[]{}:#?"))
            if name == "":                                # nome vazio = corrupção (auditoria)
                raise HierarchicalError("nome de campo vazio no header")
            p = prefix + (name,)
            masked = False
            if i < n and meta[i] == "?":                  # campo MASCARADO (ausente '-' e/ou null '0')
                masked = True
                i += 1
                order.append((p, "mask", msize()))
            if i < n and meta[i] == "#":                  # array (com count)
                i += 1
                order.append((p, "count", size()))
                elem_null = False
                if i < n and meta[i] == "?":              # P3b: element-mask (entre count e '[')
                    elem_null = True
                    i += 1
                    order.append((p, "emask", msize()))
                if i < n and meta[i] == "[":
                    i += 1
                    if i < n and meta[i] == "]":          # array de escalares
                        i += 1
                        order.append((p, "arr_scalars", size()))
                        nodes.append(("arr_scalars", name, masked, None, elem_null, stag()))
                    elif i >= n or meta[i] == ",":        # `[` omit-closed = string (tipado sempre emite ])
                        order.append((p, "arr_scalars", None))
                        nodes.append(("arr_scalars", name, masked, None, elem_null, "s"))
                    else:                                  # array de objetos
                        kids = seq("]", p)
                        if i < n and meta[i] == "]":
                            i += 1
                        nodes.append(("arr_objects", name, masked, kids, elem_null, "s"))
                else:
                    raise HierarchicalError(f"esperava '[' após '#' em {p}")
            elif i < n and meta[i] == "{":               # objeto 1:1
                i += 1
                kids = seq("}", p)
                if i < n and meta[i] == "}":
                    i += 1
                nodes.append(("object", name, masked, kids, False, "s"))
            else:                                         # escalar
                order.append((p, "scalar", size()))
                nodes.append(("scalar", name, masked, None, False, stag()))
        return nodes

    return seq(None, ()), order


# ============================================================ decode (L1 + L2 rebuild)
def decode_hierarchical(tcf_text: str) -> list:
    if not tcf_text.startswith(MAGIC):
        raise HierarchicalError(f"magic inesperado (esperava {MAGIC})")
    line1 = tcf_text.split("\n", 1)[0]
    schema, order = _parse_meta(line1[len(MAGIC):])
    if not order:
        raise HierarchicalError("header hierárquico sem colunas")
    # size OMITIDO só é válido na ÚLTIMA coluna (auditoria: size-None-no-meio lia bytes repetidos)
    for idx, (_p, _k, size) in enumerate(order):
        if size is None and idx != len(order) - 1:
            raise HierarchicalError("size ausente fora da última coluna do header")
    raw = tcf_text[len(line1) + 1:].encode("utf-8")
    cols, off = {}, 0
    for path, kind, size in order:
        if size is not None:
            if off + size > len(raw):
                raise HierarchicalError(f"size {size} excede o corpo em {path} (blob truncado?)")
            body = raw[off:off + size].decode()
            off += size
        else:
            body = raw[off:].decode()
        try:
            cols[(path, kind)] = _decode_col(body) if body else []   # L1: decode de coluna
        except Exception as e:                              # coluna de CONTROLE corrompida = fail-loud tipado
            if kind in ("mask", "count", "emask"):          # F2: emask também é controle (auditoria)
                raise HierarchicalError(f"coluna de controle {kind} corrompida em {path}: {e}")
            raise
    cur = {key: 0 for key in cols}
    total = len(cols[(order[0][0], order[0][1])])           # 1ª coluna = 1 entrada por registro-raiz
    result = [_read_object(schema, (), cols, cur) for _ in range(total)]
    for key, vals in cols.items():                          # toda coluna deve exaurir (frame consistente)
        if cur[key] != len(vals):
            raise HierarchicalError(
                f"coluna {key} não exaurida ({cur[key]}/{len(vals)}) — frame inconsistente"
            )
    return result


def _read_object(children: list, prefix: tuple, cols: dict, cur: dict) -> dict:
    obj = {}
    for kind, name, masked, kids, elem_null, stype in children:
        p = prefix + (name,)
        if masked:
            m = _take(cols, cur, (p, "mask"))
            if m == "-":
                continue                                    # chave OMITIDA (ausente)
            if m == "0":                                    # NULL (P3a) — não lê corpo/filhos
                obj[name] = None
                continue
            if m != ".":
                raise HierarchicalError(f"máscara inválida {m!r} em {p}")
        if kind == "scalar":
            obj[name] = _dec_scalar(_take(cols, cur, (p, "scalar")), stype)   # P2: str/number/bool
        elif kind == "object":
            obj[name] = _read_object(kids, p, cols, cur)
        elif kind == "arr_scalars":
            k = _count(_take(cols, cur, (p, "count")), p)
            obj[name] = [(None if _emask_null(cols, cur, p, elem_null)
                          else _dec_scalar(_take(cols, cur, (p, "arr_scalars")), stype)) for _ in range(k)]
        else:  # arr_objects
            k = _count(_take(cols, cur, (p, "count")), p)
            obj[name] = [(None if _emask_null(cols, cur, p, elem_null)
                          else _read_object(kids, p, cols, cur)) for _ in range(k)]
    return obj


def _emask_null(cols, cur, p, elem_null) -> bool:
    """P3b: consome 1 símbolo da element-mask (se houver). '0'→null, '.'→valor. Fail-loud tipado."""
    if not elem_null:
        return False
    m = _take(cols, cur, (p, "emask"))
    if m == "0":
        return True
    if m != ".":
        raise HierarchicalError(f"element-mask inválida {m!r} em {p}")
    return False


def _count(s, p):
    try:
        k = int(s)
    except (ValueError, TypeError):
        raise HierarchicalError(f"count inválido em {p}: {s!r}")
    if k < 0:
        raise HierarchicalError(f"count negativo em {p}: {k}")
    return k


def _take(cols: dict, cur: dict, key):
    lst = cols[key]
    idx = cur[key]
    if idx >= len(lst):                                     # exaustão = frame truncado/corrompido (tipado)
        raise HierarchicalError(f"coluna {key} exaurida — frame inconsistente (blob truncado?)")
    cur[key] += 1
    return lst[idx]

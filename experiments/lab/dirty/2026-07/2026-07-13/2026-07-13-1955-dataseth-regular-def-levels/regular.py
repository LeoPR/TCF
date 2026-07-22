"""P4: especiais x topologia REGULAR — kind stream por folha vs definition levels.

Pergunta (plano P4): na forma REGULAR (schema no header, multiplicidade implícita — a
forma que o dirtylab extenso do #TCF.8H validou), como presença/ausência, `null` e os
especiais viajam por COLUNA-DE-FOLHA? Duas representações:

  R1 — leaf-kinds-only: por folha, um stream de kinds por linha
       {absent, null, nan, pos_inf, neg_inf, false, true, str, int, num};
       payloads (str/int/num) vão pro canal de payload da coluna.
       SUSPEITA: 'absent' por folha NÃO distingue ancestral-ausente de
       ancestral-presente-vazio (ex.: {} vs {"b": {}}) — colisão estrutural.

  R2 — def-level+kind: o stream por folha funde PROFUNDIDADE-DE-PRESENÇA com o kind
       terminal: {cut@0, cut@1, ..., cut@(d-1), null, nan, pos_inf, neg_inf, false,
       true, str, int, num}. cut@i = a cadeia quebrou no ancestral de profundidade i
       (i=0: o primeiro ancestral está ausente). É o espírito dos definition levels do
       Dremel (Melnik 2010), estendido com null≠ausente (Protobuf não tem null) e com
       os kinds especiais do DatasetH. Arrays (de escalares) ganham um canal de
       contagem com sentinela p/ ausente (ausente ≠ []).

Escopo desta peça: objetos aninhados opcionais + arrays RASOS de escalares (ragged).
Objeto-dentro-de-array / array-de-array na forma regular = peça seguinte (registrado).
Wire de estudo #PROTO.R1 / #PROTO.R2 (streams legíveis, ints decimais canônicos) —
NÃO é a gramática #TCF.8H; bytes packed b4 são reportados como ESTIMATIVA derivada
(len(stream) * 4 bits), sem implementar o packing (território bN/V2-L).

Zero src/tcf. Modelo/oráculo importados dos labs-irmãos (sys.path).
"""

from __future__ import annotations

import sys
from pathlib import Path

_D = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_D / "2026-07-13-dataseth-json-bridge"))
sys.path.insert(0, str(_D / "2026-07-13-1835-dataseth-special-scalars"))

from dataset_h import DatasetH, HArray, HObject, HScalar  # noqa: E402
from model_ext import from_python_ext, semantic_key  # noqa: E402

ABSENT = object()  # marcador interno de campo ausente (nunca é valor)

TERMINAL_KINDS = ("null", "nan", "pos_inf", "neg_inf", "false", "true", "str", "int", "num")


class RegularError(ValueError):
    pass


# ---------------------------------------------------------------- schema

def derive_schema(rows: list) -> dict:
    """União dos caminhos das linhas. Folha escalar -> 'leaf'; array raso -> 'array'."""
    schema: dict = {}
    for row in rows:
        _merge(schema, row)
    return schema


def _merge(schema: dict, node) -> None:
    if not isinstance(node, HObject):
        raise RegularError("forma regular desta peça exige raiz-objeto por linha")
    for name, child in node.fields:
        if isinstance(child, HObject):
            sub = schema.setdefault(name, {"kind": "object", "fields": {}})
            if sub["kind"] != "object":
                raise RegularError(f"conflito de schema em {name!r}")
            _merge_obj(sub["fields"], child)
        elif isinstance(child, HArray):
            sub = schema.setdefault(name, {"kind": "array"})
            if sub["kind"] != "array":
                raise RegularError(f"conflito de schema em {name!r}")
            for item in child.items:
                if not isinstance(item, HScalar):
                    raise RegularError("array não-raso: fora do escopo desta peça (registrado)")
        else:
            sub = schema.setdefault(name, {"kind": "leaf"})
            if sub["kind"] != "leaf":
                raise RegularError(f"conflito de schema em {name!r}")


def _merge_obj(fields: dict, obj: HObject) -> None:
    for name, child in obj.fields:
        if isinstance(child, HObject):
            sub = fields.setdefault(name, {"kind": "object", "fields": {}})
            _merge_obj(sub["fields"], child)
        elif isinstance(child, HArray):
            fields.setdefault(name, {"kind": "array"})
        else:
            fields.setdefault(name, {"kind": "leaf"})


def leaf_paths(schema: dict, prefix=()) -> list[tuple]:
    """Caminhos de folha/array em ordem determinística de schema."""
    out = []
    for name, sub in schema.items():
        p = prefix + (name,)
        if sub["kind"] == "object":
            out += leaf_paths(sub["fields"], p)
        else:
            out.append((p, sub["kind"]))
    return out


def _walk(row: HObject, path: tuple):
    """Retorna (cut_depth|None, node|ABSENT): onde a cadeia quebra, ou o nó final."""
    node = row
    for depth, name in enumerate(path):
        if not isinstance(node, HObject):
            raise RegularError(f"esperava objeto em {path[:depth]!r}")
        hit = None
        for fname, child in node.fields:
            if fname == name:
                hit = child
                break
        if hit is None:
            return depth, ABSENT
        node = hit
    return None, node


def _scalar_kind(s: HScalar) -> tuple[str, object]:
    """(kind terminal, payload|None)."""
    t = s.type_name
    if t == "null":
        return "null", None
    if t in ("nan", "pos_inf", "neg_inf"):
        return t, None
    if t == "boolean":
        return ("true" if s.value else "false"), None
    if t == "string":
        return "str", s.value
    if t == "integer":
        return "int", str(s.value)
    if t == "number":
        return "num", repr(s.value)
    raise RegularError(f"kind {t!r}")


# ---------------------------------------------------------------- R1 (leaf-kinds only)

def encode_r1(rows: list[HObject], schema: dict) -> dict:
    """Streams por caminho; presença SÓ como kind 'absent' por folha (sem def-level)."""
    cols: dict = {}
    for path, kind in leaf_paths(schema):
        kinds, payloads, counts = [], [], []
        for row in rows:
            cut, node = _walk(row, path)
            if node is ABSENT:
                kinds.append("absent")  # <- toda a informação de ONDE quebrou se perde
                if kind == "array":
                    counts.append("-")
                continue
            if kind == "array":
                if not isinstance(node, HArray):
                    raise RegularError("schema diz array")
                kinds.append("present")
                counts.append(str(len(node.items)))
                for item in node.items:
                    k, pay = _scalar_kind(item)
                    payloads.append((k, pay))
            else:
                k, pay = _scalar_kind(node)
                kinds.append(k)
                if pay is not None:
                    payloads.append(pay)
        cols[path] = {"kinds": kinds, "payloads": payloads, "counts": counts}
    return cols


def decode_r1(cols: dict, schema: dict, n_rows: int) -> list:
    """Reconstrói as linhas a partir de R1 — a AMBIGUIDADE aparece aqui: 'absent' na
    folha não diz se o ancestral estava ausente ou presente-vazio; a reconstrução
    adota a política 'ancestral presente só se alguma folha o exigir'."""
    rows = []
    for i in range(n_rows):
        rows.append(_rebuild_r1(cols, schema, i))
    return rows


def _rebuild_r1(cols: dict, schema: dict, i: int) -> HObject:
    # posição de payload por coluna calculada por varredura (estudo, não eficiência)
    fields = []
    for name, sub in schema.items():
        built = _rebuild_r1_node(cols, sub, (name,), i)
        if built is not ABSENT:
            fields.append((name, built))
    return HObject(tuple(fields))


def _rebuild_r1_node(cols: dict, sub: dict, path: tuple, i: int):
    if sub["kind"] == "object":
        fields = []
        any_present = False
        for name, s2 in sub["fields"].items():
            built = _rebuild_r1_node(cols, s2, path + (name,), i)
            if built is not ABSENT:
                any_present = True
                fields.append((name, built))
        # POLÍTICA FORÇADA (a perda!): sem def-level, objeto sem folha presente
        # é indistinguível de ausente -> reconstruímos como AUSENTE.
        return HObject(tuple(fields)) if any_present else ABSENT
    col = cols[path]
    kind = col["kinds"][i]
    if kind == "absent":
        return ABSENT
    if sub["kind"] == "array":
        n = int(col["counts"][i])
        start = 0
        for j in range(i):
            if col["kinds"][j] != "absent":
                start += int(col["counts"][j])
        items = [_payload_to_scalar(*col["payloads"][start + k]) for k in range(n)]
        return HArray(tuple(items))
    pay = None
    if kind in ("str", "int", "num"):
        idx = sum(1 for j in range(i) if col["kinds"][j] in ("str", "int", "num"))
        pay = col["payloads"][idx]
    return _kind_to_scalar(kind, pay)


# ---------------------------------------------------------------- R2 (def-level + kind)

def encode_r2(rows: list[HObject], schema: dict) -> dict:
    """Stream por folha funde profundidade-de-presença + kind terminal."""
    cols: dict = {}
    for path, kind in leaf_paths(schema):
        marks, payloads, counts = [], [], []
        for row in rows:
            cut, node = _walk(row, path)
            if node is ABSENT:
                marks.append(f"cut@{cut}")  # <- ONDE quebrou é preservado
                continue
            if kind == "array":
                if not isinstance(node, HArray):
                    raise RegularError("schema diz array")
                marks.append("present")
                counts.append(str(len(node.items)))
                for item in node.items:
                    k, pay = _scalar_kind(item)
                    payloads.append((k, pay))
            else:
                k, pay = _scalar_kind(node)
                marks.append(k)
                if pay is not None:
                    payloads.append(pay)
        cols[path] = {"marks": marks, "payloads": payloads, "counts": counts}
    return cols


def decode_r2(cols: dict, schema: dict, n_rows: int) -> list:
    rows = []
    for i in range(n_rows):
        node = _rebuild_r2_obj(cols, schema, (), i, depth=0)
        if node is ABSENT:
            raise RegularError("raiz não pode ser ausente")
        rows.append(node)
    return rows


def _rebuild_r2_obj(cols: dict, fields_schema: dict, path: tuple, i: int, depth: int):
    """Reconstrói um objeto em `path` (profundidade `depth`); ABSENT se cut@d < depth
    em todas as folhas; presente (mesmo vazio) se cut@depth ou mais fundo."""
    my_paths = []
    fields = []
    present = False
    for name, sub in fields_schema.items():
        p = path + (name,)
        if sub["kind"] == "object":
            built = _rebuild_r2_obj(cols, sub["fields"], p, i, depth + 1)
            if built is not ABSENT:
                present = True
                fields.append((name, built))
            my_paths += [lp for lp, _ in leaf_paths(sub["fields"], p)]
        else:
            my_paths.append(p)
            col = cols[p]
            mark = col["marks"][i]
            if mark.startswith("cut@"):
                cut = int(mark[4:])
                # cut@i = elementos 0..i-1 presentes, elemento i ausente; o objeto
                # formado pelos primeiros `depth` elementos esta' presente sse cut >= depth
                if cut >= depth:
                    present = True
                continue
            present = True
            if sub["kind"] == "array":
                # counts so' existem p/ linhas presentes: indexar pela ordem de presenca
                n_idx = sum(1 for j in range(i) if col["marks"][j] == "present")
                n = int(col["counts"][n_idx])
                start = sum(int(col["counts"][k]) for k in range(n_idx))
                items = [_payload_to_scalar(*col["payloads"][start + k]) for k in range(n)]
                fields.append((name, HArray(tuple(items))))
            else:
                pay = None
                if mark in ("str", "int", "num"):
                    idx = sum(1 for j in range(i) if col["marks"][j] in ("str", "int", "num"))
                    pay = col["payloads"][idx]
                fields.append((name, _kind_to_scalar(mark, pay)))
    if depth == 0:
        return HObject(tuple(fields))
    # presença deste objeto = ALGUMA folha descendente entrou nele (terminal ou
    # cut >= depth). Consistência: as folhas sob este objeto compartilham o prefixo
    # path[:depth]; se UMA quebra acima (cut < depth), TODAS quebram no mesmo ponto.
    below = []
    at_or_deeper = present  # folhas diretas terminais ja' setaram present
    for p in my_paths:
        mark = cols[p]["marks"][i]
        if mark.startswith("cut@"):
            cut = int(mark[4:])
            if cut >= depth:
                at_or_deeper = True
            else:
                below.append(cut)
        else:
            at_or_deeper = True
    if below and at_or_deeper:
        raise RegularError(f"streams inconsistentes em {path!r} linha {i}")
    if below and len(set(below)) > 1:
        raise RegularError(f"cuts divergentes acima de {path!r} linha {i}")
    return HObject(tuple(fields)) if at_or_deeper else ABSENT


# ---------------------------------------------------------------- helpers

def _kind_to_scalar(kind: str, pay) -> HScalar:
    if kind == "null":
        return HScalar("null", None)
    if kind in ("nan", "pos_inf", "neg_inf"):
        return HScalar(kind, None)
    if kind == "true":
        return HScalar("boolean", True)
    if kind == "false":
        return HScalar("boolean", False)
    if kind == "str":
        return HScalar("string", pay)
    if kind == "int":
        return HScalar("integer", int(pay))
    if kind == "num":
        return HScalar("number", float(pay))
    raise RegularError(f"kind {kind!r}")


def _payload_to_scalar(kind: str, pay) -> HScalar:
    return _kind_to_scalar(kind, pay)


def packed_bits_estimate(cols: dict, mark_key: str) -> int:
    """Estimativa b4 (4 bits/símbolo) dos streams de marca — packing real = bN/V2-L."""
    total_syms = sum(len(c[mark_key]) for c in cols.values())
    return total_syms * 4

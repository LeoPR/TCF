"""hierlib — engenhoca (descartável) do estudo JSON-hierárquico → TCF.

Duas representações de um documento {equipment:{...}, day:[{...}]}:
  A) TABELÃO (cross): 1 tabela desnormalizada, colunas de equipment repetidas por linha → 1 TCF.
  B) DUAS TABELAS: T0-equipment (1 linha) + T1-day (+ fk) + manifest → 2 TCFs ligados por cabeçalho.
Ambas com **round-trip de volta ao JSON exato** (integridade). NÃO toca src/tcf. Hardcoded p/ a
forma do estudo (equipment ⊃ day). Filosofia dirty: extrair a IDEIA, jogar a engenhoca fora depois.
"""
from __future__ import annotations


# ---- tipagem célula ↔ string (TCF opera em strings; o tipo viaja no schema) ----
def celltype(vals):
    v = next((x for x in vals if x is not None), None)
    if isinstance(v, bool):
        return "bool"
    if isinstance(v, (int, float)):
        return "num"
    return "str"


def enc_cell(v):
    if isinstance(v, bool):
        return "true" if v else "false"
    if v is None:
        return ""          # null → vazio (o tipo 'num' no schema desambigua "" = null)
    return str(v)


def dec_cell(s, t):
    if t == "bool":
        return s == "true"
    if t == "num":
        if s == "":
            return None
        return int(s) if ("." not in s and "e" not in s.lower()) else float(s)
    return s               # str


# ---- A: tabelão (cross) ----
def to_tabelao(equipment: dict, day: list[dict]):
    eqcols = list(equipment)
    daycols = list(day[0])
    types = {c: celltype([equipment[c]]) for c in eqcols}
    types.update({c: celltype([r.get(c) for r in day]) for c in daycols})
    table = {c: [] for c in eqcols + daycols}
    for r in day:
        for c in eqcols:
            table[c].append(enc_cell(equipment[c]))
        for c in daycols:
            table[c].append(enc_cell(r.get(c)))
    schema = {"levels": {"equipment": eqcols, "day": daycols}, "nest": "equipment>day", "types": types}
    return table, schema


def from_tabelao(table: dict, schema: dict):
    """Reconstrói lista de {equipment, day} a partir do tabelão + schema (agrupa por tupla-equipment)."""
    eqcols = schema["levels"]["equipment"]
    daycols = schema["levels"]["day"]
    types = schema["types"]
    n = len(next(iter(table.values())))
    groups, order = {}, []
    for i in range(n):
        key = tuple(table[c][i] for c in eqcols)
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(i)
    out = []
    for key in order:
        equipment = {c: dec_cell(key[j], types[c]) for j, c in enumerate(eqcols)}
        day = [{c: dec_cell(table[c][i], types[c]) for c in daycols} for i in groups[key]]
        out.append({"equipment": equipment, "day": day})
    return out


# ---- B: duas tabelas ----
def to_two(equipment: dict, day: list[dict]):
    eqcols = list(equipment)
    daycols = list(day[0])
    types = {c: celltype([equipment[c]]) for c in eqcols}
    types.update({c: celltype([r.get(c) for r in day]) for c in daycols})
    t0 = {c: [enc_cell(equipment[c])] for c in eqcols}
    t1 = {"eq_fk": [enc_cell(equipment["id"]) for _ in day]}
    for c in daycols:
        t1[c] = [enc_cell(r.get(c)) for r in day]
    manifest = {
        "blocks": [
            {"pos": 0, "name": "equipment", "rows": 1, "cols": eqcols},
            {"pos": 1, "name": "day", "rows": len(day), "cols": ["eq_fk"] + daycols},
        ],
        "link": {"from": "day.eq_fk", "to": "equipment.id"},
        "nest": "equipment>day", "types": types,
    }
    return t0, t1, manifest


def from_two(t0: dict, t1: dict, manifest: dict):
    eqcols = manifest["blocks"][0]["cols"]
    daycols = manifest["blocks"][1]["cols"][1:]   # tira o eq_fk
    types = manifest["types"]
    n0 = len(next(iter(t0.values())))
    out = []
    for i in range(n0):
        eqid = t0["id"][i]
        equipment = {c: dec_cell(t0[c][i], types[c]) for c in eqcols}
        day = [{c: dec_cell(t1[c][j], types[c]) for c in daycols}
               for j in range(len(t1["eq_fk"])) if t1["eq_fk"][j] == eqid]
        out.append({"equipment": equipment, "day": day})
    return out


# ---- textos compactos p/ contabilidade de bytes (o schema/manifest que "trafega") ----
def schema_text(schema: dict) -> str:
    L = schema["levels"]
    return ("#H nest=" + schema["nest"] + " equipment=" + ",".join(L["equipment"])
            + " day=" + ",".join(L["day"]))


def manifest_text(manifest: dict) -> str:
    b = manifest["blocks"]
    return (f"#H b0=equipment:{b[0]['rows']} b1=day:{b[1]['rows']} "
            f"fk={manifest['link']['from']}->{manifest['link']['to']}")


# ---- síntese p/ escala (M equipamentos compartilhando a mesma série) ----
def synth_equipment(i: int) -> dict:
    return {"id": f"EQP_{i:03d}", "name": f"Equipamento Sintetico {i:02d}", "facility": "FAC_A",
            "area": "AREA_X", "group": "GRP_1", "subgroup": "SUB_1", "variable": "var_a",
            "unit": "unit_a", "phase": "-"}


def synth_docs(day: list[dict], M: int) -> list[dict]:
    """M documentos {equipment_i, day} (mesma série day) — p/ varrer escala."""
    return [{"equipment": synth_equipment(i), "day": day} for i in range(1, M + 1)]


def stack_tabelao(docs: list[dict]):
    """Empilha M documentos num único tabelão (cross de cada equipment × sua série)."""
    eqcols = list(docs[0]["equipment"])
    daycols = list(docs[0]["day"][0])
    types = {c: celltype([docs[0]["equipment"][c]]) for c in eqcols}
    types.update({c: celltype([r.get(c) for r in docs[0]["day"]]) for c in daycols})
    table = {c: [] for c in eqcols + daycols}
    for d in docs:
        for r in d["day"]:
            for c in eqcols:
                table[c].append(enc_cell(d["equipment"][c]))
            for c in daycols:
                table[c].append(enc_cell(r.get(c)))
    schema = {"levels": {"equipment": eqcols, "day": daycols}, "nest": "equipment>day", "types": types}
    return table, schema


def stack_two(docs: list[dict]):
    eqcols = list(docs[0]["equipment"])
    daycols = list(docs[0]["day"][0])
    types = {c: celltype([docs[0]["equipment"][c]]) for c in eqcols}
    types.update({c: celltype([r.get(c) for r in docs[0]["day"]]) for c in daycols})
    t0 = {c: [] for c in eqcols}
    t1 = {"eq_fk": []}
    for c in daycols:
        t1[c] = []
    for d in docs:
        for c in eqcols:
            t0[c].append(enc_cell(d["equipment"][c]))
        for r in d["day"]:
            t1["eq_fk"].append(enc_cell(d["equipment"]["id"]))
            for c in daycols:
                t1[c].append(enc_cell(r.get(c)))
    rows_day = len(t1["eq_fk"])
    manifest = {
        "blocks": [{"pos": 0, "name": "equipment", "rows": len(docs), "cols": eqcols},
                   {"pos": 1, "name": "day", "rows": rows_day, "cols": ["eq_fk"] + daycols}],
        "link": {"from": "day.eq_fk", "to": "equipment.id"}, "nest": "equipment>day", "types": types,
    }
    return t0, t1, manifest

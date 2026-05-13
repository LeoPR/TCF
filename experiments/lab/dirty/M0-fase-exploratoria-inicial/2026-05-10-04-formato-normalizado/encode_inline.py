"""Serializacao inline normalizada — sem comentarios, count=1 omitido
em decls e refs. Mesma regra do encode_separado.
"""

from patricia import No


def encode_inline(nos: dict[int, No], body_rle: list[tuple[int, int]],
                  header: str) -> str:
    proximo_emit = 1
    map_emit: dict[int, int] = {}
    declarado_inline: set[int] = set()

    def emit_id(no_id: int) -> int:
        nonlocal proximo_emit
        if no_id not in map_emit:
            map_emit[no_id] = proximo_emit
            proximo_emit += 1
        return map_emit[no_id]

    def render_forma(no: No) -> str:
        if no.pai_id is None:
            return f'folha "{no.fragmento}"'
        return f'filho_de(no{emit_id(no.pai_id)}) + "{no.fragmento}"'

    out: list[str] = []
    out.append("<body>")

    for no_id, count in body_rle:
        eid = emit_id(no_id)
        if eid not in declarado_inline:
            forma = render_forma(nos[no_id])
            if count == 1:
                out.append(f"  no{eid}: {forma}")
            else:
                out.append(f"  no{eid}: {count}x {forma}")
            declarado_inline.add(eid)
        else:
            if count == 1:
                out.append(f"  ref:no{eid}")
            else:
                out.append(f"  {count}x ref:no{eid}")

    while True:
        pendentes = [(nid, eid) for nid, eid in map_emit.items()
                     if eid not in declarado_inline]
        if not pendentes:
            break
        pendentes.sort(key=lambda x: x[1])
        for nid, eid in pendentes:
            forma = render_forma(nos[nid])
            out.append(f"  no{eid}: decl {forma}")
            declarado_inline.add(eid)

    out.append("</body>")
    return "\n".join(out) + "\n"

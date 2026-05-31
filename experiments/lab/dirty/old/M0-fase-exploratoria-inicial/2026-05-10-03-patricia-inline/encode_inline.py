"""Serializacao inline: declaracao de no embutida na 1a ocorrencia no body.

Sem secao <patricia> separada. Cada string (folha ou pai Patricia) tem
seu id alocado por ordem de aparicao no body. Pais Patricia que nao tem
ocorrencia propria sao declarados ao final como "decl tardia". Refs a
pais que ainda nao foram declarados ficam como forward refs (resolvidos
no decode em 2 passadas).

Marcadores deliberadamente verbosos.
"""

from patricia import No


def encode_inline(nos: dict[int, No], body_rle: list[tuple[int, int]],
                  header: str) -> str:
    """Constroi o TCF inline.

    Algoritmo:
      1. Pass pelo body_rle. Cada vez que encontra um no_id pela 1a vez,
         emite a declaracao inline (folha ou filho). O id de emissao
         (emit_id) e sequencial por ordem de aparicao.
         Ocorrencias subsequentes viram "ref:noN".
      2. Apos o body, emite "decl tardia" para nos que tiveram emit_id
         alocado (porque foram referenciados como pai) mas nao tiveram
         ocorrencia propria. Itera ate estabilizar (cadeias de pais).
    """
    proximo_emit = 1
    map_emit: dict[int, int] = {}        # no_id -> emit_id
    declarado_inline: set[int] = set()   # emit_ids ja emitidos

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

    saida: list[str] = []
    saida.append("#TCF demonstrativo v0.6.exp03 (inline)")
    saida.append(f"# coluna: {header}")
    saida.append("# 1a ocorrencia declara o no; ocorrencias seguintes referenciam.")
    saida.append("# refs a pais ainda nao declarados sao forward refs (decl tardia ao final).")
    saida.append("<body>")

    # Fase 1: percorre o body emitindo decls inline + refs
    for no_id, count in body_rle:
        eid = emit_id(no_id)
        if eid not in declarado_inline:
            forma = render_forma(nos[no_id])
            saida.append(f"  no{eid}: {count}x {forma}")
            declarado_inline.add(eid)
        else:
            saida.append(f"  {count}x ref:no{eid}")

    # Fase 2: decls tardias para pais Patricia ainda nao emitidos.
    # Itera ate estabilizar (cadeias de pais podem alocar novos forward refs).
    while True:
        pendentes = [(nid, eid) for nid, eid in map_emit.items()
                     if eid not in declarado_inline]
        if not pendentes:
            break
        pendentes.sort(key=lambda x: x[1])  # ordem de emit_id
        for nid, eid in pendentes:
            forma = render_forma(nos[nid])
            saida.append(f"  no{eid}: decl {forma}")
            declarado_inline.add(eid)

    saida.append("</body>")
    return "\n".join(saida) + "\n"

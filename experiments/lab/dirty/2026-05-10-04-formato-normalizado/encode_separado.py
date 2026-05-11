"""Serializacao separada normalizada — sem comentarios, count=1 omitido.

Mesma estrutura do exp 02 mas sem comentarios introdutorios e com a
mesma regra do exp 03 (omitir 1x em count=1). Para comparacao justa
com encode_inline.
"""

from patricia import No


def encode_separado(nos: dict[int, No], body_rle: list[tuple[int, int]],
                    header: str) -> str:
    out: list[str] = []
    out.append("<patricia>")
    visitados: set[int] = set()

    def emite(nid: int):
        if nid in visitados:
            return
        n = nos[nid]
        if n.pai_id is not None:
            emite(n.pai_id)
        if n.pai_id is None:
            out.append(f'  no{n.id} = folha "{n.fragmento}"')
        else:
            out.append(
                f'  no{n.id} = filho_de(no{n.pai_id}) + "{n.fragmento}"'
            )
        visitados.add(nid)

    for nid in sorted(nos):
        emite(nid)

    out.append("</patricia>")
    out.append("<body>")
    for no_id, count in body_rle:
        if count == 1:
            out.append(f"  ref:no{no_id}")
        else:
            out.append(f"  {count}x ref:no{no_id}")
    out.append("</body>")
    return "\n".join(out) + "\n"

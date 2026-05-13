"""Serializa (nos, body_rle, header) em texto TCF demonstrativo.

Marcadores exagerados/legiveis por design — este experimento prioriza
clareza, nao tamanho. Otimizacao de byte-economy fica para experimento
posterior.
"""

from patricia import No


def encode(nos: dict[int, No], body_rle: list[tuple[int, int]],
           header: str) -> str:
    linhas: list[str] = []
    linhas.append("#TCF demonstrativo v0.6.exp02")
    linhas.append(f"# coluna: {header}")
    linhas.append("# nos sao declarados em ordem topologica (pais antes de filhos)")
    linhas.append("<patricia>")

    visitados: set[int] = set()

    def emite(no_id: int):
        if no_id in visitados:
            return
        n = nos[no_id]
        if n.pai_id is not None:
            emite(n.pai_id)
        if n.pai_id is None:
            linhas.append(f'  no{n.id} = folha "{n.fragmento}"')
        else:
            linhas.append(
                f'  no{n.id} = filho_de(no{n.pai_id}) + "{n.fragmento}"'
            )
        visitados.add(no_id)

    for nid in sorted(nos):
        emite(nid)

    linhas.append("</patricia>")
    linhas.append("<body>")
    for no_id, rep in body_rle:
        if rep == 1:
            linhas.append(f"  ref:no{no_id}")
        else:
            linhas.append(f"  {rep}x ref:no{no_id}")
    linhas.append("</body>")
    return "\n".join(linhas) + "\n"

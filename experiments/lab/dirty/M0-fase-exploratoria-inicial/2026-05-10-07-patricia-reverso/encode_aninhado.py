"""Serializacao com pai embutido recursivamente.

Diferenca chave vs exp 03/04: pais Patricia nao tem "decl tardia" no
fim do body. Em vez disso, na 1a vez que algum filho precisa do pai,
a decl do pai e EMBUTIDA dentro da propria decl do filho. Se o pai
tem pai (avo) ainda nao declarado, este tambem e embutido,
recursivamente.

Sintaxe:
  no1: folha "Ana"                                  # decl folha simples
  no2: 3x folha "Bob"                               # decl folha com RLE
  no3: filho_de(no4=decl folha "Mar") + "ina"       # decl filho + decl
                                                    # aninhada do pai no4
  no5: filho_de(no4) + "cio"                        # filho usando pai
                                                    # ja declarado
  no6: filho_de(no7=decl filho_de(no8=decl folha "USR00") + "0") + "1"
       # decl filho com pai e avo aninhados em cadeia
"""

from patricia import No


def encode_aninhado(nos: dict[int, No], body_rle: list[tuple[int, int]],
                    header: str) -> str:
    proximo_emit = 1
    map_emit: dict[int, int] = {}
    declarado: set[int] = set()  # eids ja declarados em algum lugar

    def get_eid(no_id: int) -> int:
        nonlocal proximo_emit
        if no_id not in map_emit:
            map_emit[no_id] = proximo_emit
            proximo_emit += 1
        return map_emit[no_id]

    def render_decl_aninhada(no_id: int) -> str:
        """Renderiza decl aninhada do no (sem ser top-level no body).
        Marca eid como declarado. Pode recursar para avos.
        """
        eid = get_eid(no_id)
        n = nos[no_id]
        if n.pai_id is None:
            forma = f'decl folha "{n.fragmento}"'
        else:
            sub = _render_lado_filho(n)
            forma = f"decl {sub}"
        declarado.add(eid)
        return f"no{eid}={forma}"

    def _render_lado_filho(n: No) -> str:
        """Renderiza 'filho_de(...) + "X"' onde (...) pode ser ref ou
        decl aninhada.
        """
        if n.pai_id in declarado_no_ids():
            eid_pai = get_eid(n.pai_id)
            return f'filho_de(no{eid_pai}) + "{n.fragmento}"'
        else:
            pai_decl = render_decl_aninhada(n.pai_id)
            return f'filho_de({pai_decl}) + "{n.fragmento}"'

    def declarado_no_ids() -> set[int]:
        """Retorna o conjunto de no_ids (chaves de nos) cujos eids estao
        em 'declarado'.
        """
        return {nid for nid, eid in map_emit.items() if eid in declarado}

    def render_decl_externa(no_id: int, count: int) -> str:
        eid = get_eid(no_id)
        n = nos[no_id]
        if n.pai_id is None:
            forma = f'folha "{n.fragmento}"'
        else:
            forma = _render_lado_filho(n)
        declarado.add(eid)
        if count == 1:
            return f"  no{eid}: {forma}"
        return f"  no{eid}: {count}x {forma}"

    out: list[str] = []
    out.append("<body>")
    for no_id, count in body_rle:
        eid = get_eid(no_id)
        if eid not in declarado:
            out.append(render_decl_externa(no_id, count))
        else:
            if count == 1:
                out.append(f"  ref:no{eid}")
            else:
                out.append(f"  {count}x ref:no{eid}")
    out.append("</body>")
    return "\n".join(out) + "\n"

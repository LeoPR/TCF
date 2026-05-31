"""Serializacao composta (prefix + middle + suffix) por string.

Namespace unico de eids alocados por ordem de aparicao no body.
Tipos de no distinguidos pela sintaxe da declaracao:

  no1: folha "X"                           # string folha (sem pref nem suf)
  no2: pref:(no3=decl folha "P") + "X"     # string com pref (decl aninhada do pref)
  no4: "X" + suf:(no5=decl folha "S")      # string com suf
  no6: pref:no3 + "X" + suf:no5            # composto (pref e suf ja decl)
  no7: pref:no3 + suf:no5                  # composto com middle vazio

RLE no body:
  3x ref:no1                               # 3 ocorrencias adjacentes de no1
  2x no2: pref:no3 + "X"                   # 1a ocorrencia + decl + 2 RLE
"""

from arvore_bidir import Decomposicao


def encode_composto(linhas: list[str], decomp: dict[str, Decomposicao],
                    header: str) -> str:
    proximo_eid = 1
    map_str: dict[str, int] = {}
    map_pref: dict[str, int] = {}
    map_suf: dict[str, int] = {}
    decl_str: set[int] = set()
    decl_pref: set[int] = set()
    decl_suf: set[int] = set()

    def eid_str(s: str) -> int:
        nonlocal proximo_eid
        if s not in map_str:
            map_str[s] = proximo_eid
            proximo_eid += 1
        return map_str[s]

    def eid_pref(t: str) -> int:
        nonlocal proximo_eid
        if t not in map_pref:
            map_pref[t] = proximo_eid
            proximo_eid += 1
        return map_pref[t]

    def eid_suf(t: str) -> int:
        nonlocal proximo_eid
        if t not in map_suf:
            map_suf[t] = proximo_eid
            proximo_eid += 1
        return map_suf[t]

    def render_pref(t: str) -> str:
        e = eid_pref(t)
        if e in decl_pref:
            return f"pref:no{e}"
        decl_pref.add(e)
        return f'pref:(no{e}=decl folha "{t}")'

    def render_suf(t: str) -> str:
        e = eid_suf(t)
        if e in decl_suf:
            return f"suf:no{e}"
        decl_suf.add(e)
        return f'suf:(no{e}=decl folha "{t}")'

    def render_decl_externa(s: str, count: int) -> str:
        e = eid_str(s)
        d = decomp[s]
        partes: list[str] = []

        # Caso especial: sem pref nem suf — usa sintaxe 'folha'
        if not d.prefix_text and not d.suffix_text:
            forma = f'folha "{d.middle}"'
        else:
            if d.prefix_text:
                partes.append(render_pref(d.prefix_text))
            if d.middle:
                partes.append(f'"{d.middle}"')
            if d.suffix_text:
                partes.append(render_suf(d.suffix_text))
            forma = " + ".join(partes)

        decl_str.add(e)
        if count == 1:
            return f"  no{e}: {forma}"
        return f"  no{e}: {count}x {forma}"

    # RLE adjacente sobre strings
    from arvore_bidir import rle_strings
    body_rle = rle_strings(linhas)

    out: list[str] = ["<body>"]
    for s, count in body_rle:
        e = eid_str(s)
        if e not in decl_str:
            out.append(render_decl_externa(s, count))
        else:
            if count == 1:
                out.append(f"  ref:no{e}")
            else:
                out.append(f"  {count}x ref:no{e}")
    out.append("</body>")
    return "\n".join(out) + "\n"

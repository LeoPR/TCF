"""Serializa Re-Pair em sintaxe TCF inline.

Sintaxe (didatica, verbosa):

  no1: (no2="maria.silva@") + "g" + (no3="mail.com")
  no4: no2 + (no5="hot") + no3
  no6: no2 + (no7="yahoo.com")

Cada string e uma linha "noN: token + token + ...". Cada token e:
  - "X"        — literal
  - noN        — ref a simbolo ja declarado
  - (noN="X")  — decl aninhada (na 1a ocorrencia do simbolo)

Namespace unico de eids. RLE adjacente no body para ocorrencias
repetidas da MESMA string.
"""

from repair import Literal, Ref, Token


def encode_repair(linhas_originais: list[str],
                   strings_unicas: list[str],
                   strings_tok: list[list[Token]],
                   simbolos: dict[int, str],
                   header: str) -> str:
    # Mapeia sym_id (Re-Pair) -> eid no encode
    proximo_eid = 1
    map_sym_to_eid: dict[int, int] = {}
    map_str_to_eid: dict[str, int] = {}
    decl_sym: set[int] = set()
    decl_str: set[int] = set()

    def eid_sym(sym_id: int) -> int:
        nonlocal proximo_eid
        if sym_id not in map_sym_to_eid:
            map_sym_to_eid[sym_id] = proximo_eid
            proximo_eid += 1
        return map_sym_to_eid[sym_id]

    def eid_str(s: str) -> int:
        nonlocal proximo_eid
        if s not in map_str_to_eid:
            map_str_to_eid[s] = proximo_eid
            proximo_eid += 1
        return map_str_to_eid[s]

    def render_token(tok: Token) -> str:
        if isinstance(tok, Literal):
            return f'"{tok.text}"'
        eid = eid_sym(tok.sym_id)
        if eid in decl_sym:
            return f"no{eid}"
        decl_sym.add(eid)
        return f'(no{eid}="{simbolos[tok.sym_id]}")'

    def render_decl_string(s: str, tokens: list[Token],
                           count: int) -> str:
        eid = eid_str(s)
        partes = [render_token(t) for t in tokens]
        forma = " + ".join(partes)
        decl_str.add(eid)
        if count == 1:
            return f"  no{eid}: {forma}"
        return f"  no{eid}: {count}x {forma}"

    # RLE adjacente no body
    body_rle: list[tuple[str, int]] = []
    for s in linhas_originais:
        if body_rle and body_rle[-1][0] == s:
            body_rle[-1] = (s, body_rle[-1][1] + 1)
        else:
            body_rle.append((s, 1))

    str_to_tok = dict(zip(strings_unicas, strings_tok))

    out: list[str] = ["<body>"]
    for s, count in body_rle:
        eid = eid_str(s)
        if eid not in decl_str:
            out.append(render_decl_string(s, str_to_tok[s], count))
        else:
            if count == 1:
                out.append(f"  ref:no{eid}")
            else:
                out.append(f"  {count}x ref:no{eid}")
    out.append("</body>")
    return "\n".join(out) + "\n"

"""Serializa o resultado do online em sintaxe TCF.

Sintaxe (didatica, verbosa):

  no1: "maria.silva@gmail.com"
  no2: no1[0:12] + "hot" + no1[-8:]
  no5: no4[0:11] + no2[-11:]
  ref:no1
  3x ref:no2

  noN[0:K]  primeiros K chars de noN
  noN[-K:]  ultimos K chars de noN
  "X"       literal
  +         concatenacao
  Nx        RLE adjacente de linha repetida no body

Decode em 1 passada (ver decode_online.py).
"""

from online import TokLit, TokRefPref, TokRefSuf, Token


def _render_token(tok: Token) -> str:
    if isinstance(tok, TokLit):
        return f'"{tok.text}"'
    if isinstance(tok, TokRefPref):
        return f'no{tok.string_id}[0:{tok.length}]'
    return f'no{tok.string_id}[-{tok.length}:]'  # TokRefSuf


def _rle_adjacente(linhas: list[str]) -> list[tuple[str, int]]:
    out: list[tuple[str, int]] = []
    for s in linhas:
        if out and out[-1][0] == s:
            out[-1] = (s, out[-1][1] + 1)
        else:
            out.append((s, 1))
    return out


def encode_online(linhas_originais: list[str],
                   strings_unicas: list[str],
                   tokens_por_string: list[list[Token]],
                   header: str) -> str:
    str_to_tokens = dict(zip(strings_unicas, tokens_por_string))
    str_to_eid: dict[str, int] = {}
    decl_emitida: set[int] = set()
    proximo_eid = 1

    out: list[str] = ["<body>"]
    for s, count in _rle_adjacente(linhas_originais):
        if s not in str_to_eid:
            str_to_eid[s] = proximo_eid
            proximo_eid += 1
        eid = str_to_eid[s]
        prefixo = f"{count}x " if count > 1 else ""

        if eid not in decl_emitida:
            forma = " + ".join(_render_token(t) for t in str_to_tokens[s])
            out.append(f"  no{eid}: {prefixo}{forma}")
            decl_emitida.add(eid)
        else:
            out.append(f"  {prefixo}ref:no{eid}")

    out.append("</body>")
    return "\n".join(out) + "\n"

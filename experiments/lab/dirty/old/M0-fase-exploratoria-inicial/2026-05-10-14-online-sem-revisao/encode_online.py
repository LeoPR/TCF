"""Serializa o resultado do online (exp 14) em sintaxe TCF.

Sintaxe (didatica, verbosa):

  no1: "maria.silva@gmail.com"                  # primeira string, literal puro
  no2: no1[0:12] + "hotmail.com"                # pref de no1 (12 chars) + literal
  no3: no1[0:12] + "yahoo.com"
  no4: "joao.souza@gmail.com"
  no5: no4[0:11] + "hotmail.com"
  no6: no4[0:11] + "yahoo.com"
  ...

  noN[0:K]  = primeiros K chars de noN
  noN[-K:]  = ultimos K chars de noN
  "X"       = literal
  +         = concatenacao

Body com RLE adjacente para repeticoes da mesma string.
"""

from online import TokLit, TokRefPref, TokRefSuf, Token


def encode_online(linhas_originais: list[str],
                   strings_unicas: list[str],
                   tokens_por_string: list[list[Token]],
                   header: str) -> str:
    # Mapeia string_id (1-indexed do online) -> eid no encode
    # eid e alocado por ordem de aparicao no body (= ordem de strings_unicas)
    # mas o body pode ter repeticoes (RLE)
    map_str_to_eid: dict[str, int] = {}
    proximo_eid = 1
    decl_emitida: set[int] = set()

    def eid_de(s: str) -> int:
        nonlocal proximo_eid
        if s not in map_str_to_eid:
            map_str_to_eid[s] = proximo_eid
            proximo_eid += 1
        return map_str_to_eid[s]

    # Mapa: string_id (do online, 1-indexed) -> eid (do encode)
    # Note: na primeira ocorrencia de cada string unica, vamos declarar
    # com seus tokens. Por construcao, string_id (do online) coincide
    # com ordem de aparicao das unicas, e eid e alocado quando a string
    # aparece no body pela primeira vez. Como processamos linhas do CSV
    # em ordem, a 1a ocorrencia de cada unica acontece em ordem dos
    # strings_unicas — entao string_id == eid.
    # Para clareza, vamos confirmar isso assumindo essa correspondencia.

    def render_token(tok: Token) -> str:
        if isinstance(tok, TokLit):
            return f'"{tok.text}"'
        if isinstance(tok, TokRefPref):
            return f'no{tok.string_id}[0:{tok.length}]'
        # TokRefSuf
        return f'no{tok.string_id}[-{tok.length}:]'

    # RLE adjacente no body
    body_rle: list[tuple[str, int]] = []
    for s in linhas_originais:
        if body_rle and body_rle[-1][0] == s:
            body_rle[-1] = (s, body_rle[-1][1] + 1)
        else:
            body_rle.append((s, 1))

    str_to_tokens = dict(zip(strings_unicas, tokens_por_string))

    out: list[str] = ["<body>"]
    for s, count in body_rle:
        eid = eid_de(s)
        if eid not in decl_emitida:
            tokens = str_to_tokens[s]
            forma = " + ".join(render_token(t) for t in tokens)
            if count == 1:
                out.append(f"  no{eid}: {forma}")
            else:
                out.append(f"  no{eid}: {count}x {forma}")
            decl_emitida.add(eid)
        else:
            if count == 1:
                out.append(f"  ref:no{eid}")
            else:
                out.append(f"  {count}x ref:no{eid}")
    out.append("</body>")
    return "\n".join(out) + "\n"

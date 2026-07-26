"""Polaridade do corpo — as três formas MATERIALIZADAS (não estimadas).

    NORMAL   `\\168116` = literal          ·  `1`     = referência          (hoje)
    FLIP-A   `168116`   = literal          ·  `\\1`    = referência, com delimitador
                                              SÓ quando um literal-dígito vem colado
    FLIP-B   `168116`   = literal          ·  `\\1;`   = referência, SEMPRE terminada

O delimitador do protótipo é `;` (da lista de zero-ocorrência). É **placeholder** — a escolha
do char é decisão do owner; trocar aqui é uma constante.

Em modo FLIP o `;` passa a ser estrutural, então um `;` literal no dado vira `\\;` (o `\\`
seguido de NÃO-dígito já é o escape comum de char, então isso não inventa gramática).

Cada função `de_*` é a INVERSA da `para_*`, e o lab exige `de_X(para_X(c)) == c`.
"""
BS = chr(92)
DELIM = ";"


# ------------------------------------------------------------------ tokenizador do NORMAL
def tokeniza(resto):
    """Quebra a declaração NORMAL em tokens. Espelha o scanner do `_parse_decl`.

    Devolve lista de `(tipo, texto)`:
      `sep`  separador `*`
      `ref`  grupo de referência (começa com dígito; pode ter `,` `..` `~`)
      `dig`  literal de dígitos (veio de `\\` + dígitos)
      `chr`  literal de caractere (inclui `\\` + não-dígito, já desescapado)
    """
    out, i, n = [], 0, len(resto)
    while i < n:
        c = resto[i]
        if c == "*":
            out.append(("sep", "*"))
            i += 1
        elif c.isdigit():
            j = i
            while j < n:
                d = resto[j]
                if d.isdigit() or d == ",":
                    j += 1
                elif d == "." and j + 1 < n and resto[j + 1] == ".":
                    j += 2
                elif d == "~":
                    j += 1
                else:
                    break
            out.append(("ref", resto[i:j]))
            i = j
        elif c == BS:
            i += 1
            if i < n and resto[i].isdigit():
                j = i
                while j < n and resto[j].isdigit():
                    j += 1
                out.append(("dig", resto[i:j]))
                i = j
            else:
                out.append(("chr", resto[i] if i < n else ""))
                i += 1
        else:
            out.append(("chr", c))
            i += 1
    return out


def _esc_chr(ch, flip, inicio=False):
    """Escapa um literal de CARACTERE conforme a polaridade.

    `inicio` = este é o 1º caractere da declaração. O `^` só é estrutural AÍ (é o namespace
    de referência de LINHA), e o encoder real reflete isso: `['^a']` vira `\\^a`, mas
    `['a^b']` fica `a^b`. A 1ª versão deste módulo tratava escape só por caractere e
    **perdia a barra do `^`** — bug achado na verificação adversarial.
    """
    if ch in ("*", BS, "~"):
        return BS + ch
    if inicio and ch == "^":
        return BS + ch
    if flip and ch == DELIM:                 # em FLIP o delimitador vira estrutural
        return BS + ch
    return ch


# ------------------------------------------------------------------ NORMAL (o de hoje)
def para_normal(toks):
    out = []
    for k, (t, v) in enumerate(toks):
        if t == "sep":
            out.append("*")
        elif t == "ref":
            out.append(v)
        elif t == "dig":
            out.append(BS + v)
        else:
            out.append(_esc_chr(v, flip=False, inicio=(k == 0)))
    return "".join(out)


# ------------------------------------------------------------------ FLIP-A / FLIP-B
def _para_flip(toks, sempre):
    """`sempre=False` → delimita só na adjacência (A). `sempre=True` → toda ref (B)."""
    out = []
    for k, (t, v) in enumerate(toks):
        if t == "sep":
            out.append("*")
        elif t == "dig":
            out.append(v)                                     # literal: NU
        elif t == "chr":
            out.append(_esc_chr(v, flip=True, inicio=(k == 0)))
        else:                                                 # ref: cada corrida ganha `\`
            peca = "".join(BS + p if p.isdigit() else p
                           for p in _partes_ref(v))
            prox = toks[k + 1] if k + 1 < len(toks) else None
            cola = prox is not None and prox[0] == "dig"      # literal-dígito colado
            out.append(peca + (DELIM if (sempre or cola) else ""))
    return "".join(out)


def _partes_ref(v):
    """Separa `1~2`, `0..3`, `1,2` nas corridas numéricas e nos conectores."""
    partes, i, n = [], 0, len(v)
    while i < n:
        if v[i].isdigit():
            j = i
            while j < n and v[j].isdigit():
                j += 1
            partes.append(v[i:j])
            i = j
        else:
            partes.append(v[i])
            i += 1
    return partes


def para_flip_a(toks):
    return _para_flip(toks, sempre=False)


def para_flip_b(toks):
    return _para_flip(toks, sempre=True)


# ------------------------------------------------------------------ leitura do FLIP
def de_flip(resto, sempre):
    """Lê uma declaração em FLIP e devolve os tokens — a INVERSA de `_para_flip`."""
    out, i, n = [], 0, len(resto)
    while i < n:
        c = resto[i]
        if c == "*":
            out.append(("sep", "*"))
            i += 1
        elif c == BS:
            i += 1
            if i < n and resto[i].isdigit():                  # REFERÊNCIA
                # o `\` de ABERTURA já foi consumido — a primeira corrida está aqui.
                j = i
                while j < n and resto[j].isdigit():
                    j += 1
                buf = [resto[i:j]]
                i = j
                while i < n:                                  # conectores + corridas seguintes
                    if resto[i] in (",", "~"):
                        buf.append(resto[i])
                        i += 1
                    elif resto[i] == "." and i + 1 < n and resto[i + 1] == ".":
                        buf.append("..")
                        i += 2
                    else:
                        break
                    if i < n and resto[i] == BS and i + 1 < n and resto[i + 1].isdigit():
                        i += 1
                        j = i
                        while j < n and resto[j].isdigit():
                            j += 1
                        buf.append(resto[i:j])
                        i = j
                if i < n and resto[i] == DELIM:               # consome o delimitador
                    i += 1
                out.append(("ref", "".join(buf)))
            else:                                             # escape de caractere
                out.append(("chr", resto[i] if i < n else ""))
                i += 1
        elif c.isdigit():                                     # LITERAL de dígitos
            j = i
            while j < n and resto[j].isdigit():
                j += 1
            out.append(("dig", resto[i:j]))
            i = j
        else:
            out.append(("chr", c))
            i += 1
    return out


# ------------------------------------------------------------------ corpo inteiro
def _mapeia_linhas(corpo, fn):
    saida = []
    for linha in corpo.split("\n"):
        pre, resto = "", linha
        if linha.startswith("*") and "|" in linha:
            bar = linha.find("|")
            pre, resto = linha[:bar + 1], linha[bar + 1:]
        if resto.startswith("^"):                              # ref de LINHA: outro namespace
            saida.append(linha)
            continue
        saida.append(pre + fn(resto))
    return "\n".join(saida)


def corpo_para_flip(corpo, sempre):
    return _mapeia_linhas(corpo, lambda r: _para_flip(tokeniza(r), sempre))


def corpo_de_flip(corpo, sempre):
    return _mapeia_linhas(corpo, lambda r: para_normal(de_flip(r, sempre)))


# ------------------------------------------------------------------ bloqueadores ESTRUTURAIS
def bloqueadores(corpo_normal, corpo_flip):
    """O que impede o corpo FLIP de ser decodável — **independente** do round-trip.

    A 1ª versão deste lab validava `de_flip(para_flip(c)) == c` e concluía "lossless". Isso é
    CIRCULAR: testa a consistência do par de funções do próprio lab, não a decodabilidade da
    forma flipada. A verificação adversarial mostrou 2 de 12 colunas com RT=OK e wire flipado
    corrompido. Este detector olha o corpo FLIP contra a gramática REAL.

    Devolve `{nome: ocorrências}`.
    """
    b = {"linha_null": 0, "seqrle_perde_escape": 0, "linha_circunflexo": 0}
    for ln_n, ln_f in zip(corpo_normal.split("\n"), corpo_flip.split("\n")):
        if not ln_f:
            continue
        pre_f, resto_f = "", ln_f
        if ln_f.startswith("*") and "|" in ln_f:
            bar = ln_f.find("|")
            pre_f, resto_f = ln_f[:bar + 1], ln_f[bar + 1:]

        # (1) linha inteira `0` = grafia canônica do slot 0 (null). Em FLIP `0` é o literal
        #     "0" — colisão DIRETA, e o delimitador não a resolve (ele desambigua dentro da
        #     declaração, não a linha).
        if resto_f == "0":
            b["linha_null"] += 1
        # (2) O seq-RLE localiza os dígitos a incrementar pelo ESCAPE
        #     (`find_escape_digit_runs`) — e o flip muda o que o escape SIGNIFICA. Dois modos
        #     de quebra, ambos silenciosos:
        #       a) as corridas SOMEM   -> `*10+1|0` expande p/ dez cópias de "0", não 0..9
        #       b) as corridas MUDAM DE TOKEN -> em `*2-10|14\22;c` o delta agia no literal
        #          `22`; no flip `*2-10|\14;22\;c` ele passa a agir na REFERÊNCIA `14`
        #     Comparar só "tem barra?" não pega (b); comparar as CORRIDAS pega os dois.
        if pre_f and ("+" in pre_f or "-" in pre_f[1:]):
            from tcf.composicional.hcc_seqrle import find_escape_digit_runs

            tpl_n = ln_n[ln_n.find("|") + 1:] if "|" in ln_n else ln_n
            rn = [tpl_n[a:z] for a, z in find_escape_digit_runs(tpl_n)]
            rf = [resto_f[a:z] for a, z in find_escape_digit_runs(resto_f)]
            if rn and rn != rf:
                b["seqrle_perde_escape"] += 1
        # (3) linha que PASSA a começar com `^` por causa do flip vira referência de LINHA.
        #     Uma linha `^N` que JÁ era referência de linha no NORMAL não conta — o flip não
        #     a toca (`_mapeia_linhas` a copia verbatim). A 1ª versão deste detector não fazia
        #     essa distinção e acusava 9 de 12 formas; o correto são 2.
        if not pre_f and resto_f.startswith("^") and not ln_n.startswith("^"):
            b["linha_circunflexo"] += 1
    return b

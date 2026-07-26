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


def _esc_chr(ch, flip):
    """Escapa um literal de CARACTERE conforme a polaridade."""
    if ch in ("*", BS, "~"):
        return BS + ch
    if flip and ch == DELIM:                 # em FLIP o delimitador vira estrutural
        return BS + ch
    return ch


# ------------------------------------------------------------------ NORMAL (o de hoje)
def para_normal(toks):
    out = []
    for t, v in toks:
        if t == "sep":
            out.append("*")
        elif t == "ref":
            out.append(v)
        elif t == "dig":
            out.append(BS + v)
        else:
            out.append(_esc_chr(v, flip=False))
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
            out.append(_esc_chr(v, flip=True))
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

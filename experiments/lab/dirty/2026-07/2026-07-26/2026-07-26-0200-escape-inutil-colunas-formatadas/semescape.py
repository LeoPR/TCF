"""Modo SEM-ESCAPE para coluna que não usa referência de fragmento.

Observação do owner sobre `A-cpf-like-n200`: *"tem muitos CPFs únicos, logo não gera nem
referência nem nada, e os escapes ficam inúteis. A ideia era gastar o mínimo possível de
indicação pra que o CPF não tenha escape em nada."*

Medido: **6 de 11 colunas não emitem NENHUMA referência de fragmento**, e pagam 11–21% do
corpo em escape de dígito — protegendo contra uma colisão que não ocorre naquela coluna.

REGRA (dinâmica, e não se mistura): se o corpo não tem nenhuma referência de fragmento, o
cabeçalho declara isso e, **dentro da declaração**, todo dígito é literal — sem escape.

  hoje       `\529.\982.\247-\25`
  sem-escape `529.982.247-25`

O que NÃO muda, porque vive em outro nível (posicional, já hoje):
  - `*N|` e `*N+d|` no INÍCIO da linha (contador RLE / seq-RLE)
  - `^N` no INÍCIO da linha (referência de LINHA)
  - `\*`, `\~`, `\\` (escape estrutural — medido: 0 ocorrências nestas colunas)

O modo é REJEITADO se o corpo tiver qualquer referência de fragmento — daí "não se mistura".
"""
BS = chr(92)


def _partes(linha):
    """(prefixo de marcador, resto). O prefixo é intocado — outro nível."""
    if linha.startswith("*") and "|" in linha:
        bar = linha.find("|")
        return linha[:bar + 1], linha[bar + 1:]
    return "", linha


def perfil(corpo):
    """(escapes de dígito, referências de fragmento) — decide se o modo se aplica."""
    esc = refs = 0
    for linha in corpo.split("\n"):
        _pre, r = _partes(linha)
        if r.startswith("^"):
            continue
        i, n = 0, len(r)
        while i < n:
            if r[i] == BS:
                i += 1
                if i < n and r[i].isdigit():
                    esc += 1
                    while i < n and r[i].isdigit():
                        i += 1
                else:
                    i += 1
            elif r[i].isdigit():
                refs += 1
                while i < n and r[i].isdigit():
                    i += 1
            else:
                i += 1
    return esc, refs


def seqrle_quebra(corpo, corpo_se):
    """Marcadores `*N±d|` que PERDEM os dígitos incrementáveis no modo sem-escape.

    O seq-RLE localiza o que incrementar com `find_escape_digit_runs` — pelo ESCAPE. Tirar o
    escape apaga essa marcação e o marcador expande errado, em silêncio. **É o mesmo
    bloqueador que derrubou o flip** (lab `0038`), e não é específico dele: atinge qualquer
    esquema que remova o escape de dígito.
    """
    from tcf.composicional.hcc_seqrle import find_escape_digit_runs

    n = 0
    for ln_n, ln_f in zip(corpo.split("\n"), corpo_se.split("\n")):
        if not (ln_n.startswith("*") and "|" in ln_n):
            continue
        head = ln_n[1:ln_n.find("|")]
        if "+" not in head and "-" not in head[1:]:
            continue
        tn = ln_n[ln_n.find("|") + 1:]
        tf = ln_f[ln_f.find("|") + 1:] if "|" in ln_f else ln_f
        if find_escape_digit_runs(tn) and not find_escape_digit_runs(tf):
            n += 1
    return n


def aplicavel(corpo):
    """O modo vale se NÃO houver referência de fragmento **e** o seq-RLE sobreviver.

    Binário por coluna, decidido pelo encoder — é o "não se mistura" que o owner pediu.
    """
    _esc, refs = perfil(corpo)
    if refs:
        return False
    return seqrle_quebra(corpo, para_sem_escape(corpo)) == 0


def para_sem_escape(corpo):
    """Remove o `\\` que precede corrida de dígitos. Os outros escapes ficam."""
    saida = []
    for linha in corpo.split("\n"):
        pre, r = _partes(linha)
        if r.startswith("^"):
            saida.append(linha)
            continue
        buf, i, n = [], 0, len(r)
        while i < n:
            if r[i] == BS:
                i += 1
                if i < n and r[i].isdigit():
                    while i < n and r[i].isdigit():
                        buf.append(r[i])
                        i += 1
                else:
                    buf.append(BS + (r[i] if i < n else ""))
                    i += 1
            else:
                buf.append(r[i])
                i += 1
        saida.append(pre + "".join(buf))
    return "\n".join(saida)


# ---------------------------------------------------------------- leitor INDEPENDENTE
def le_sem_escape(corpo):
    """Lê o corpo SEM-ESCAPE e devolve os VALORES — sem passar pela transformação inversa.

    Esta é a lição do lab `0038`: validar com `de_X(para_X(c)) == c` é **circular**. Aqui o
    leitor reimplementa a semântica direto (dígito = literal, `*` = separador, `^N` = linha),
    e é comparado com o `decode` REAL do corpo NORMAL.
    """
    valores, decl = [], []
    for linha in corpo.split("\n"):
        if linha == "" and not valores and not decl:
            continue
        pre, r = _partes(linha)
        count = 1
        if pre:
            head = pre[1:-1]
            if "+" in head or "-" in head[1:]:
                return None                      # seq-RLE: fora do escopo deste leitor
            count = int(head)
        if r.startswith("^"):
            idx = int(r[1:])
            if not 0 <= idx <= len(decl):
                return None
            v = decl[idx - 1] if idx else None
        else:
            v = "".join(c for c in r if c != "*")    # `*` só separa fragmentos
            decl.append(v)
        valores.extend([v] * count)
    if valores and valores[-1] == "" and corpo.endswith("\n"):
        valores.pop()
    return valores

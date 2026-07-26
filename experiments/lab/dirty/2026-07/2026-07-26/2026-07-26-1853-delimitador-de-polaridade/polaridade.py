"""O delimitador de POLARIDADE — a troca barata proposta pelo owner.

    56\\033-\\0910-\\4383      hoje: 1 escape por LITERAL
    56/033-0910-4383          proposta: 1 byte por TRANSIÇÃO

## A regra

Dentro de uma declaração há um estado: o próximo digit-run é **referência** ou **literal**?
O delimitador **inverte** o estado. Ele não marca um valor, marca uma **troca** — e por isso
custa por transição, não por ocorrência.

    56/033-0910-4383       `56` ref · troca · `033`, `0910`, `4383` literais
    56/033-09/10-4383      `10` volta a ser referência
    56/033-0910-4/38/3     troca no meio da última corrida

O estado **reseta no início de cada linha**, para a linha continuar auto-contida.

## Por que resolve a adjacência (o bloqueador do lab 0330)

O escape carrega duas informações: o TIPO e a FRONTEIRA. O delimitador carrega as duas
também — ele *está entre* as duas corridas. `56/033` não funde, porque o `/` separa.

É **mais expressivo** que o escape de hoje: `literal` seguido de `referência` não tem grafia
hoje (`\\03356` lê tudo como literal), e aqui tem — `/033/56`.

## A polaridade inicial é do CABEÇALHO

Se a coluna inteira é literal (CPF), começar em LITERAL zera as transições: **0 bytes**.
É o "flip" do lab `0038`, agora com um delimitador que não é ambíguo.

## O char do delimitador não é fixo

Qualquer char pode aparecer no dado. O `\\` de hoje tem o mesmo problema. Então o char é
escolhido por coluna, pelo `min` de `transições + ocorrências dele no dado` — uma conta, na
mesma passada. Isso é o estilo do formato, não um caso especial.
"""
BS = chr(92)

# candidatos: chars raros em dado tabular, fora da gramática do corpo (`*` `~` `^` `,` `|`)
CANDIDATOS = ["/", "!", "?", "&", "%", "#"]


def _partes(linha):
    """Separa o prefixo seq-RLE (`*N+d|`) da declaração — o prefixo não é tocado."""
    if linha.startswith("*") and "|" in linha:
        bar = linha.find("|")
        return linha[:bar + 1], linha[bar + 1:]
    return "", linha


def corridas(decl):
    """As corridas de dígito de uma declaração, na ordem do parser.

    Devolve `[(kind, texto)]` com `kind in {'L','R'}` e, entre elas, os pedaços literais de
    não-dígito preservados como `('=', texto)`. É a leitura da grafia de HOJE.
    """
    out, buf, i, n = [], [], 0, len(decl)
    while i < n:
        if decl[i] == BS:
            i += 1
            if i < n and decl[i].isdigit():
                if buf:
                    out.append(("=", "".join(buf))); buf = []
                j = i
                while i < n and decl[i].isdigit():
                    i += 1
                out.append(("L", decl[j:i]))
            else:                                    # escape de não-dígito: opaco, intocado
                buf.append(BS + (decl[i] if i < n else ""))
                i += 1
        elif decl[i].isdigit():
            if buf:
                out.append(("=", "".join(buf))); buf = []
            j = i
            while i < n and decl[i].isdigit():
                i += 1
            out.append(("R", decl[j:i]))
        else:
            buf.append(decl[i])
            i += 1
    if buf:
        out.append(("=", "".join(buf)))
    return out


# ------------------------------------------------------------------ os contadores (1 passada)
def transicoes(corpo, inicial):
    """Quantos delimitadores o corpo inteiro custaria, dada a polaridade inicial da coluna.

    Estado reseta a cada linha. Custo = 1 por troca de estado.
    """
    n = 0
    for linha in corpo.split("\n"):
        _pre, decl = _partes(linha)
        if decl.startswith("^") or not decl:
            continue
        est = inicial
        for kind, _txt in corridas(decl):
            if kind == "=":
                continue
            if kind != est:
                n += 1
                est = kind
    return n


def ocorrencias(corpo, char):
    """Quantas vezes o char candidato já aparece no dado — cada uma passaria a custar escape."""
    n = 0
    for linha in corpo.split("\n"):
        _pre, decl = _partes(linha)
        i, m = 0, len(decl)
        while i < m:
            if decl[i] == BS:
                i += 2
            else:
                n += decl[i] == char
                i += 1
    return n


def custo_hoje(corpo):
    """O que se paga hoje: 1 B de `\\` por corrida literal."""
    return sum(1 for linha in corpo.split("\n")
               for kind, _t in corridas(_partes(linha)[1]) if kind == "L")


def plano(corpo):
    """A escolha: `(char, inicial, custo)` — o `min` sobre candidatos × polaridade.

    Não materializa nada. São contadores sobre a mesma varredura que já existe.
    """
    melhor = None
    for char in CANDIDATOS:
        oc = ocorrencias(corpo, char)
        for inicial in ("R", "L"):
            c = transicoes(corpo, inicial) + oc          # oc = escapes do próprio delimitador
            if melhor is None or c < melhor[2]:
                melhor = (char, inicial, c)
    return melhor


# ------------------------------------------------------------------ as duas direções
def para_delim(corpo, char, inicial):
    """Corpo NORMAL -> corpo com delimitador de polaridade."""
    saida = []
    for linha in corpo.split("\n"):
        pre, decl = _partes(linha)
        if decl.startswith("^") or not decl:
            saida.append(linha)
            continue
        est, buf = inicial, []
        for kind, txt in corridas(decl):
            if kind == "=":
                buf.append(txt.replace(char, BS + char))     # o char vira dado: escapa
                continue
            if kind != est:
                buf.append(char)
                est = kind
            buf.append(txt)
        saida.append(pre + "".join(buf))
    return "\n".join(saida)


def de_delim(corpo_d, char, inicial):
    """Corpo com delimitador -> corpo NORMAL (a grafia de hoje, byte a byte)."""
    saida = []
    for linha in corpo_d.split("\n"):
        pre, decl = _partes(linha)
        if decl.startswith("^") or not decl:
            saida.append(linha)
            continue
        est, buf, i, n = inicial, [], 0, len(decl)
        while i < n:
            if decl[i] == BS:
                if i + 1 < n and decl[i + 1] == char:
                    buf.append(char)                         # era dado, não delimitador
                else:
                    buf.append(decl[i:i + 2])                # escape opaco: devolve como está
                i += 2
            elif decl[i] == char:
                est = "L" if est == "R" else "R"
                i += 1
            elif decl[i].isdigit():
                j = i
                while j < n and decl[j].isdigit():
                    j += 1
                buf.append((BS if est == "L" else "") + decl[i:j])
                i = j
            else:
                buf.append(decl[i])
                i += 1
        saida.append(pre + "".join(buf))
    return "\n".join(saida)

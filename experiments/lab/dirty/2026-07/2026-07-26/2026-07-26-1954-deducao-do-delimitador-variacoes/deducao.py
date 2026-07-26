"""Dedução do delimitador — "se eleger um caractere inicial, ela não precisa ser declarada".

    "a ideia é realmente ver onde existe a possibilidade de criar ambiguidade, marcar
     internamente ou deduzir de forma inteligente e depois materializar isso de forma
     inteligente também, seja por inferência ou não. se a gente eleger um caractere inicial
     para ligar com essa ambiguidade ela também não precisa ser declarada. ou seja a marcação
     existe em estrutura interna, a gente pode usar até isso como dedução."

## A regra de eleição

O encoder elege o **menor char livre**: o menor da FAIXA que a coluna **não usa**.

## A regra de dedução (o que o decoder tentaria)

O decoder não tem o dado, só o corpo. A tentativa ingênua é: **o delimitador é o menor char
da FAIXA presente no corpo**.

    dados usam `.` `-`, delimitador eleito `!`  ->  menor no corpo = `!`   OK
    dados usam `!`,      delimitador eleito `"` ->  menor no corpo = `!`   ERRADO

Ou seja, a dedução só fecha quando o char eleito é **menor que todo char de FAIXA do dado** —
e isso equivale a `FAIXA[0] não estar no dado`. Este módulo não decide se isso é frequente:
**mede**.

## As três materializações comparadas

    V0   `d<char><pol>` no cabeçalho          2 B, sempre funciona
    V1   `<pol>` no cabeçalho, char deduzido  1 B, só se a dedução fechar
    V2   polaridade no 1º byte do corpo       0 B de cabeçalho, +1 B de corpo quando pol=L

`src/tcf` intocado.
"""
BS = chr(92)

GRAMATICA = set("*~^,|" + BS + "\n")
FAIXA = [chr(c) for c in range(0x21, 0x7F) if chr(c) not in GRAMATICA]
FAIXA_SET = set(FAIXA)


class _Flip:
    """O marcador VIRTUAL: não é char, não é texto — não pode colidir com dado."""

    __slots__ = ()

    def __repr__(self):
        return "<FLIP>"


FLIP = _Flip()


def _partes(linha):
    if linha.startswith("*") and "|" in linha:
        bar = linha.find("|")
        return linha[:bar + 1], linha[bar + 1:]
    return "", linha


def varredura_unica(corpo):
    """UMA passada: tokens virtuais + alfabeto do dado + 2 contadores de troca."""
    tokens_por_linha, presentes = [], set()
    trocas = {"R": 0, "L": 0}
    literais = 0

    for linha in corpo.split("\n"):
        pre, decl = _partes(linha)
        if decl.startswith("^") or not decl:
            tokens_por_linha.append((pre, [decl] if decl else []))
            continue

        est = {"R": "R", "L": "L"}
        toks, i, n = [], 0, len(decl)
        while i < n:
            c = decl[i]
            if c == BS:
                i += 1
                if i < n and decl[i].isdigit():
                    j = i
                    while i < n and decl[i].isdigit():
                        presentes.add(decl[i])
                        i += 1
                    literais += 1
                    for pol in ("R", "L"):
                        if est[pol] != "L":
                            trocas[pol] += 1
                            est[pol] = "L"
                    toks.append(FLIP)
                    toks.append(("L", decl[j:i]))
                else:
                    if i < n:
                        presentes.add(decl[i])
                        toks.append(("esc", decl[i]))
                        i += 1
            elif c.isdigit():
                j = i
                while i < n and decl[i].isdigit():
                    presentes.add(decl[i])
                    i += 1
                for pol in ("R", "L"):
                    if est[pol] != "R":
                        trocas[pol] += 1
                        est[pol] = "R"
                toks.append(FLIP)
                toks.append(("R", decl[j:i]))
            else:
                presentes.add(c)
                toks.append(("txt", c))
                i += 1
        tokens_por_linha.append((pre, toks))

    return tokens_por_linha, presentes, trocas["R"], trocas["L"], literais


# ------------------------------------------------------------------ eleição e dedução
def elege(presentes):
    """O **menor char livre**: o menor da FAIXA que a coluna não usa. `None` se não há."""
    for c in FAIXA:
        if c not in presentes:
            return c
    return None


def deducao_fecha(presentes):
    """A dedução ingênua funciona? Equivale a `FAIXA[0]` não estar no dado.

    Se o menor char da FAIXA está no dado, ele é menor que o delimitador eleito, e o decoder
    confundiria os dois. Não é opinião — é a condição exata.
    """
    return FAIXA[0] not in presentes


def deduz_do_corpo(corpo_d):
    """O que o decoder faria: o menor char da FAIXA presente no corpo. Sem ver o dado."""
    menor = None
    for linha in corpo_d.split("\n"):
        _pre, decl = _partes(linha)
        i, n = 0, len(decl)
        while i < n:
            if decl[i] == BS:
                i += 2
                continue
            c = decl[i]
            if c in FAIXA_SET and (menor is None or c < menor):
                menor = c
            i += 1
    return menor


# ------------------------------------------------------------------ as duas direções
def resolve(tokens_por_linha, char, inicial):
    """Marcador virtual -> grafia. A única fase que conhece o char."""
    saida = []
    for pre, toks in tokens_por_linha:
        est, buf, pend = inicial, [], False
        for t in toks:
            if t is FLIP:
                pend = True
                continue
            if isinstance(t, str):
                buf.append(t)
                continue
            kind, txt = t
            if kind in ("L", "R"):
                if pend and kind != est:
                    buf.append(char)
                    est = kind
                pend = False
                buf.append(txt)
            elif kind == "esc":
                buf.append(BS + txt)
            else:
                buf.append(txt)
        saida.append(pre + "".join(buf))
    return "\n".join(saida)


def de_grafia(corpo_d, char, inicial):
    """Grafia com delimitador -> corpo CANÔNICO de hoje."""
    saida = []
    for linha in corpo_d.split("\n"):
        pre, decl = _partes(linha)
        if decl.startswith("^") or not decl:
            saida.append(linha)
            continue
        est, buf, i, n = inicial, [], 0, len(decl)
        while i < n:
            if decl[i] == BS:
                buf.append(decl[i:i + 2])
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


def decide(presentes, trocas_R, trocas_L, literais):
    """`(modo, char, inicial, custo_corpo)`. Só lê os acumuladores — nenhuma varredura."""
    char = elege(presentes)
    if char is None:
        return "hoje", None, None, literais
    inicial = "R" if trocas_R <= trocas_L else "L"
    custo = min(trocas_R, trocas_L)
    if custo >= literais:
        return "hoje", None, None, literais
    return "delim", char, inicial, custo


# ------------------------------------------------------------------ V3: caractere inicial
def para_v3(corpo_d, char, inicial):
    """**Auto-declarante por posição**: o corpo começa com o char eleito.

    É a ideia do owner — *"se a gente eleger um caractere inicial para ligar com essa
    ambiguidade ela também não precisa ser declarada"* — e é o idioma posicional que o
    formato já usa (o char de modo no índice 7, o `0` cru para o slot nulo).

    Custo: **1 B** se a polaridade é `R`, **2 B** se é `L` (o char repetido). Nada no
    cabeçalho, e a dedução passa a ser ler o byte 0 — sempre correta, inclusive quando o
    delimitador não é usado em lugar nenhum do corpo.
    """
    return (char * (1 if inicial == "R" else 2)) + "\n" + corpo_d


def de_v3(texto):
    """Lê o prefixo auto-declarante. Devolve `(char, inicial, corpo)`. Zero ambiguidade."""
    pref, _, corpo = texto.partition("\n")
    if not pref:
        raise ValueError("prefixo V3 vazio")
    char = pref[0]
    if any(c != char for c in pref):
        raise ValueError(f"prefixo V3 nao-canonico: {pref!r}")
    return char, ("R" if len(pref) == 1 else "L"), corpo

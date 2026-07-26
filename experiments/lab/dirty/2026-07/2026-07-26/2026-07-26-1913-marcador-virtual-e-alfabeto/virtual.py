"""O marcador VIRTUAL e o alfabeto da coluna — a crítica do owner ao lab `1853`.

    "eu apenas CHUTEI o `/`, pode ser absolutamente qualquer coisa. O importante não é isso,
     o importante é saber ONDE existe a possibilidade de conflito, marcar ele internamente
     com qualquer coisa, uma semântica interna, com uma pseudo gramática, idêntico ao OBAT e
     o HCC (…) não precisamos fazer como uma esteira com batchs serializados (…) enquanto a
     árvore avalia similaridades, a própria avaliação sabe se a string começa com número, e
     isso já é um contador e um indicador."

## Os dois erros do lab `1853`

1. **Lista de candidatos chutada** (`/ ! ? & % #`). Não se pergunta *qual char usar*, se
   pergunta **onde existe conflito** — e isso é o alfabeto que a coluna realmente usa.
   O complemento do alfabeto é o conjunto dos chars com **conflito zero, por construção**.

2. **Esteira serializada**. `plano()` varria o corpo 6 (candidatos) + 2 (polaridades) = **8
   vezes**, depois do núcleo já ter terminado. Faz-uma-coisa, para, analisa, faz outra.

## A reformulação

O marcador é **virtual**: um sentinela na representação intermediária, não um char. Não pode
colidir porque **não é texto** — é o mesmo movimento do OBAT (nós, não strings) e do HCC
(composição, não grafia).

    tokens = ['56', FLIP, '033', '-', '0910', ...]        <- FLIP é objeto, não char
    grafia = resolve(tokens, char='@', inicial='L')       <- char decidido NO FIM

Enquanto o núcleo já percorre char-a-char em `_escape_lit`
(`src/tcf/composicional/syntax.py:173-193` — o **único** laço char-a-char do emit, e
exatamente onde o escape de dígito é decidido, linha 181), acumulam-se **de graça**:

    presentes     bitmap do alfabeto      (1 OR por char, já no laço)
    trocas_R      contador                (1 comparação por corrida)
    trocas_L      contador                (idem, a outra polaridade)

Nenhuma varredura nova. A decisão vira uma leitura de 3 acumuladores no fim.

## Nota de escopo

Este arquivo **simula** o que moraria dentro de `_escape_lit`, percorrendo o corpo canônico
uma única vez. `src/tcf` está intocado. O ponto medido é *quantas varreduras a decisão custa*
e *se sempre existe char livre* — não a solda.
"""
BS = chr(92)

# Grafia do corpo: chars que a gramática já usa e que o delimitador não pode roubar.
GRAMATICA = set("*~^,|" + BS + "\n")

# Faixa de onde tirar o delimitador: ASCII imprimível, fora da gramática.
FAIXA = [chr(c) for c in range(0x21, 0x7F) if chr(c) not in GRAMATICA]


class _Flip:
    """O marcador VIRTUAL. Não é char, não é string — não pode colidir com dado."""

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
    """UMA passada. Devolve `(tokens_por_linha, presentes, trocas_R, trocas_L, literais)`.

    É o que `_escape_lit` acumularia sem laço novo: um `set` de chars vistos e dois
    contadores de troca de polaridade — um por polaridade inicial, computados juntos.
    """
    tokens_por_linha, presentes = [], set()
    trocas = {"R": 0, "L": 0}
    literais = 0

    for linha in corpo.split("\n"):
        pre, decl = _partes(linha)
        if decl.startswith("^") or not decl:
            tokens_por_linha.append((pre, [decl] if decl else []))
            continue

        est = {"R": "R", "L": "L"}           # estado corrente de cada polaridade inicial
        toks, i, n = [], 0, len(decl)
        while i < n:
            c = decl[i]
            if c == BS:
                i += 1
                if i < n and decl[i].isdigit():
                    j = i
                    while i < n and decl[i].isdigit():
                        i += 1
                    literais += 1
                    for pol in ("R", "L"):           # os 2 contadores, no mesmo passo
                        if est[pol] != "L":
                            trocas[pol] += 1
                            est[pol] = "L"
                    toks.append(FLIP)                # marcador VIRTUAL, sem char ainda
                    toks.append(("L", decl[j:i]))    # o token carrega o TIPO, nao a grafia
                else:                                # escape opaco (`\*`, `\\`, `\~`)
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


def livres(presentes):
    """Os chars com **conflito zero por construção**: os que a coluna não usa."""
    return [c for c in FAIXA if c not in presentes]


def decide(presentes, trocas_R, trocas_L, literais):
    """A decisão, lendo só os 3 acumuladores. Nenhuma varredura.

    Devolve `(modo, char, inicial, custo)`. `modo` é `'delim'` ou `'hoje'`.
    """
    livre = livres(presentes)
    if not livre:
        # Sem char livre a proposta exigiria escapar o delimitador — fora do escopo deste
        # lab; recusa e cai no comportamento de hoje. É um resultado, não um buraco.
        return "hoje", None, None, literais
    inicial = "R" if trocas_R <= trocas_L else "L"
    custo = min(trocas_R, trocas_L)
    if custo >= literais:
        return "hoje", None, None, literais
    return "delim", livre[0], inicial, custo


def resolve(tokens_por_linha, char, inicial):
    """Marcador virtual -> grafia. **A única fase que conhece o char.**

    O `FLIP` some aqui: ele vira o delimitador só onde há troca real de estado. É o mesmo
    padrão do OBAT/HCC — a estrutura decide, a grafia é a última etapa.
    """
    saida = []
    for pre, toks in tokens_por_linha:
        est, buf, pend = inicial, [], False
        for t in toks:
            if t is FLIP:
                pend = True
                continue
            if isinstance(t, str):                   # linha `^N`, opaca
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
            else:                                    # txt cru; o char livre não ocorre aqui
                buf.append(txt)
        saida.append(pre + "".join(buf))
    return "\n".join(saida)


def de_grafia(corpo_d, char, inicial):
    """Grafia com delimitador -> corpo CANÔNICO de hoje (com os `\\` de dígito)."""
    saida = []
    for linha in corpo_d.split("\n"):
        pre, decl = _partes(linha)
        if decl.startswith("^") or not decl:
            saida.append(linha)
            continue
        est, buf, i, n = inicial, [], 0, len(decl)
        while i < n:
            if decl[i] == BS:
                buf.append(decl[i:i + 2])            # escape opaco: devolve como está
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

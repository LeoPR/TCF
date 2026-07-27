"""Polaridade × tipos — o delimitador encontrando bool, null, int/float tipados.

    "faça uma avaliação com o que já temos, combinado com os dados booleanos, binários, null
     até o momento. vamos vendo essas situações (…) é só pra ver comportamento e pequenos
     bugs, precisamos testar muita coisa."

## Por que este cruzamento pode quebrar

Os labs `1853`/`1913`/`1954` trataram o corpo como *declarações de string*. Mas desde as
soldas recentes o corpo carrega mais coisas, e **três delas são dígitos que NÃO são dado**:

    `0` sozinho na linha    slot NULO pré-alocado (grafia otimizada de `^0`)
    `^N`                    referência de linha
    `*N|` / `*N+d|`         contador de RLE / seq-RLE (prefixo)

O mecanismo de polaridade classifica corrida de dígito em `L` (literal) ou `R` (referência).
O null é **referência de verdade** — slot 0 — então `R` é a classificação semanticamente
correta. Mas isso precisa ser **verificado**, não assumido: sob polaridade `L` cada linha de
null paga uma troca, e uma reconstrução errada transformaria `0` (null) em `\\0` (a string
`"0"`), que é **corrupção silenciosa** — o RT passaria em tipo mas não em valor.

Também há modos onde o corpo **não é declaração**: `b15` + base64 (bool denso). O mecanismo
tem que recusar, não "funcionar por acaso".

`src/tcf` intocado.
"""
import base64

BS = chr(92)

GRAMATICA = set("*~^,|" + BS + "\n")

# FAIXA = só PONTUAÇÃO ASCII, fora da gramática. Nem dígito, nem letra — e isso não é
# blocklist, é regra, por dois bugs que a auditoria adversarial reproduziu:
#
#   dígito  o delimitador FUNDE com a corrida que deveria delimitar. Com `0` eleito,
#           `1\22.\33` vira `1022.33` e volta como `1022.33`: o scanner de corrida engole
#           o delimitador e o literal vira referência. Reconstrução deixa de ser exata.
#
#   letra   o sufixo V3 pousa no índice 6, que é o slot do DISCRIMINADOR (`#TCF.8b`,
#           `#TCF.8n`, `#TCF.8H`…). Uma coluna de STRING com alfabeto largo elegia `b` e
#           emitia `#TCF.8b` — byte-idêntico ao cabeçalho canônico de uma coluna bool.
#
# Excluir por CLASSE (dígito/letra) e não por lista fecha os dois de uma vez, e continua
# fechado quando surgir tag nova.
FAIXA = [chr(c) for c in range(0x21, 0x7F)
         if chr(c) not in GRAMATICA and not chr(c).isdigit() and not chr(c).isalpha()]

MAGIC = "#TCF.8"

# tags de modo que o mecanismo entende (corpo = declarações, uma por linha)
TAGS_DECL = {"", "b", "n", "s"}


class _Flip:
    __slots__ = ()

    def __repr__(self):
        return "<FLIP>"


FLIP = _Flip()


def parte_wire(wire):
    """`(cabecalho, tag, corpo)`. `tag` é o que vem depois do magic.

    **Verifica o magic** (achado da auditoria): sem isso, um wire órfão (`stamp=False`, sem
    cabeçalho) era aceito e a **primeira linha de dado** era consumida como cabeçalho.
    """
    cab, sep, corpo = wire.partition("\n")
    if not sep or not cab.startswith(MAGIC):
        raise ValueError(f"wire sem magic {MAGIC!r}: {cab[:20]!r}")
    return cab, cab[len(MAGIC):], corpo


def aplicavel(tag):
    """O corpo é uma sequência de declarações? Recusa denso (`b15`) e hierárquico (`H`)."""
    return tag in TAGS_DECL


def _partes(linha):
    if linha.startswith("*") and "|" in linha:
        bar = linha.find("|")
        return linha[:bar + 1], linha[bar + 1:]
    return "", linha


def _opaca(decl):
    """Linhas que o mecanismo NÃO toca: vazia e referência de linha (`^N`).

    **O slot nulo NÃO entra aqui, e isso foi um bug meu.** A primeira versão tratava a linha
    `0` como opaca "porque é o null". Errado: sob polaridade `L` o `0` cru já é o **literal**
    `"0"`, e é o null que precisa da troca (`!0`). Marcar a linha como opaca fazia o literal
    `\\0` voltar como `0`, ou seja **a string `"0"` virando `null`** — corrupção silenciosa que
    só o RT elemento a elemento pega.

    A correção é não ter regra especial: o null é referência ao slot 0, a máquina de
    polaridade já classifica corrida de dígito nu como `R` = referência. Ela acerta sozinha.
    """
    return decl == "" or decl.startswith("^")


def varredura_unica(corpo):
    """UMA passada: tokens virtuais + alfabeto + trocas por polaridade + literais."""
    tokens_por_linha, presentes = [], set()
    trocas = {"R": 0, "L": 0}
    literais = 0

    for linha in corpo.split("\n"):
        pre, decl = _partes(linha)
        if _opaca(decl):
            tokens_por_linha.append((pre, [("op", decl)]))
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


def elege(presentes):
    for c in FAIXA:
        if c not in presentes:
            return c
    return None


# custo do prefixo auto-declarante V3, por polaridade (o char, dobrado quando `L`)
PREFIXO = {"R": 1, "L": 2}


def decide(presentes, tR, tL, literais):
    """`(modo, char, inicial, custo_total)` — FLOOR incluindo o prefixo.

    **Bug corrigido aqui**: a primeira versão comparava só `min(tR, tL)` com os escapes e
    ignorava o custo do próprio prefixo. Em `int-ordenado-null` (7 escapes, 6 trocas) ela
    ativava e o wire **crescia 1 byte**. O FLOOR tem de incluir tudo que a proposta paga —
    é o mesmo padrão do `seq-RLE` (`hcc_seqrle.py`) e do `min(tcf, raw, dict, split)` do
    multi-col. Empate fica com a grafia de hoje.
    """
    char = elege(presentes)
    if char is None:
        return "hoje", None, None, literais
    inicial = min(("R", "L"), key=lambda p: (tR if p == "R" else tL) + PREFIXO[p])
    custo = (tR if inicial == "R" else tL) + PREFIXO[inicial]
    if custo >= literais:
        return "hoje", None, None, literais
    return "delim", char, inicial, custo


def resolve(tokens_por_linha, char, inicial):
    saida = []
    for pre, toks in tokens_por_linha:
        est, buf, pend = inicial, [], False
        for t in toks:
            if t is FLIP:
                pend = True
                continue
            kind, txt = t
            if kind == "op":
                buf.append(txt)
            elif kind in ("L", "R"):
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
    saida = []
    for linha in corpo_d.split("\n"):
        pre, decl = _partes(linha)
        if _opaca(decl):
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


def v3(cab, corpo_d, char, inicial):
    """A materialização auto-declarante que venceu no lab `1954`."""
    return f"{cab}{char * (1 if inicial == 'R' else 2)}\n{corpo_d}"


def de_v3(texto, tag):
    """Lê char e polaridade do sufixo posicional do cabeçalho. Sem receber o eleito."""
    cab, _, corpo = texto.partition("\n")
    base = "#TCF.8" + tag
    suf = cab[len(base):]
    if not suf:
        raise ValueError("sufixo V3 vazio")
    char = suf[0]
    if any(c != char for c in suf):
        raise ValueError(f"sufixo V3 nao-canonico: {suf!r}")
    return char, ("R" if len(suf) == 1 else "L"), corpo


def eh_base64(corpo):
    """Detector grosseiro do modo denso, para o lab conferir que a recusa é pelo motivo certo."""
    s = corpo.strip()
    if not s:
        return False
    try:
        base64.b64decode(s, validate=True)
    except Exception:
        return False
    return True

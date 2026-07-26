"""O escape como MÁSCARA — a decisão literal×referência num canal próprio.

Passo 1 do estudo pedido pelo owner: *"pense na regra mais burra possível"*, focando no CPF.

## A observação

No corpo do CPF, TODO digit-run tem escape e NÃO HÁ um único sem:

    \\000.\\000.\\000-\\00
    \\001.\\007.\\013-\\01

O escape carrega **zero informação** ali. Ele é um bit por ocorrência num fluxo constante.

## A regra (não binária — cobre todos os casos)

O escape é, em cada digit-run, a resposta a uma pergunta binária: **literal ou referência?**
Essa sequência de respostas é um FLUXO — e um fluxo é o que o TCF já sabe comprimir.

    hoje      1 byte por LITERAL, embutido no corpo
    máscara   o fluxo L/R num canal próprio, com RLE

Custo da máscara ≈ `2 × runs`. Custo inline = `count(L)`. **Nenhuma das duas é binária**: as
duas cobrem qualquer mistura, e a mais barata vence — que é o estilo do formato
(`min(tcf, raw, dict, split)` no multi-col, FLOOR do seq-RLE, modo do single-col tipado).

## Por que isto NÃO esbarra no bloqueador do seq-RLE

Flip e sem-escape **apagavam** o escape do corpo, e o seq-RLE localiza os dígitos
incrementáveis *pelo escape* — daí quebravam (labs `0038` e `0200`).

Aqui o escape **não deixa de existir**: ele é reconstruído antes de qualquer coisa. É uma
camada de borda, como o pré-avaliador do slot 0:

    decode:  wire -> re-insere escapes a partir da máscara -> corpo NORMAL -> decode de hoje
    encode:  corpo NORMAL de hoje -> extrai máscara -> wire

O core não muda, o seq-RLE roda sobre o corpo com escape como sempre.
"""
BS = chr(92)


def _partes(linha):
    if linha.startswith("*") and "|" in linha:
        bar = linha.find("|")
        return linha[:bar + 1], linha[bar + 1:]
    return "", linha


def fluxo_decisoes(corpo):
    """A sequência L/R na ordem em que o parser encontra cada digit-run."""
    s = []
    for linha in corpo.split("\n"):
        _pre, r = _partes(linha)
        if r.startswith("^") or not r:
            continue
        i, n = 0, len(r)
        while i < n:
            if r[i] == BS:
                i += 1
                if i < n and r[i].isdigit():
                    s.append("L")
                    while i < n and r[i].isdigit():
                        i += 1
                else:
                    i += 1
            elif r[i].isdigit():
                s.append("R")
                while i < n and r[i].isdigit():
                    i += 1
            else:
                i += 1
    return "".join(s)


def rle(s):
    """RLE mais burro possível: `<count><char>`. Sem otimização nenhuma, de propósito."""
    if not s:
        return ""
    out, cur, n = [], s[0], 1
    for ch in s[1:]:
        if ch == cur:
            n += 1
        else:
            out.append(f"{n}{cur}")
            cur, n = ch, 1
    out.append(f"{n}{cur}")
    return "".join(out)


def des_rle(m):
    out, i, n = [], 0, len(m)
    while i < n:
        j = i
        while j < n and m[j].isdigit():
            j += 1
        out.append(m[j] * int(m[i:j]))
        i = j + 1
    return "".join(out)


# ------------------------------------------------------------------ a decisão, em 1 passada
def custo_inline(fluxo):
    """O que se paga hoje: 1 B de `\\` por literal."""
    return fluxo.count("L")


def custo_mascara(fluxo):
    """O que a máscara custaria — calculado, não materializado."""
    return len(rle(fluxo))


def adjacencias(corpo):
    """Fronteiras que a máscara NÃO consegue reconstruir.

    O escape carrega **duas** informações: o TIPO (literal × referência) e a **fronteira**
    entre corridas de dígito. A máscara captura só o tipo. Onde uma referência encosta num
    literal-dígito, tirar o escape **funde** as duas corridas:

        56\\033-\\0910   ->   56033-0910      `56` e `033` viram `56033`

    Contar isto é o que torna a regra segura — e é a MESMA adjacência que travou o flip
    (lab `0038`) e o sem-escape (lab `0200`). Terceiro esquema, mesmo obstáculo.
    """
    n = 0
    for linha in corpo.split("\n"):
        _pre, r = _partes(linha)
        if r.startswith("^"):
            continue
        i, m = 0, len(r)
        while i < m:
            if r[i] == BS:
                i += 1
                if i < m and r[i].isdigit():
                    while i < m and r[i].isdigit():
                        i += 1
                    if i < m and r[i].isdigit():          # literal colado em ref
                        n += 1
                else:
                    i += 1
            elif r[i].isdigit():
                while i < m and r[i].isdigit():
                    i += 1
                if i < m and r[i] == BS and i + 1 < m and r[i + 1].isdigit():
                    n += 1                                 # ref colada em literal
            else:
                i += 1
    return n


def escolha(fluxo):
    """`'mascara'` ou `'inline'`. UMA passada sobre o fluxo, sem gerar as duas formas.

    É o ponto que responde à restrição do owner sobre os vetores ortogonais: a decisão é
    uma CONTA (contar runs), não um experimento (materializar e comparar).
    """
    return "mascara" if custo_mascara(fluxo) < custo_inline(fluxo) else "inline"


# ------------------------------------------------------------------ as duas direções
def para_mascara(corpo):
    """Corpo NORMAL -> (corpo sem os `\\` de dígito, máscara)."""
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
    return "\n".join(saida), rle(fluxo_decisoes(corpo))


def de_mascara(corpo_sem, mascara):
    """(corpo sem escape, máscara) -> corpo NORMAL. Re-insere o `\\` onde a máscara diz `L`."""
    dec = list(des_rle(mascara))
    k = 0
    saida = []
    for linha in corpo_sem.split("\n"):
        pre, r = _partes(linha)
        if r.startswith("^"):
            saida.append(linha)
            continue
        buf, i, n = [], 0, len(r)
        while i < n:
            if r[i] == BS:                       # escape de NÃO-dígito: intocado
                buf.append(r[i:i + 2])
                i += 2
            elif r[i].isdigit():
                j = i
                while j < n and r[j].isdigit():
                    j += 1
                if k < len(dec) and dec[k] == "L":
                    buf.append(BS)
                k += 1
                buf.append(r[i:j])
                i = j
            else:
                buf.append(r[i])
                i += 1
        saida.append(pre + "".join(buf))
    return "\n".join(saida)

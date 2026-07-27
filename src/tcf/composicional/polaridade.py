"""Delimitador de POLARIDADE — camada de borda sobre o corpo canonico.

O corpo canonico escapa corrida de digito LITERAL com `\\`; digito NU e' REFERENCIA a
fragmento. Isso custa **1 byte por literal**. O delimitador de polaridade troca a pergunta:
em vez de marcar cada literal, marca cada **troca** entre os dois estados. Custa **1 byte por
transicao**.

    canonico   56\\033-\\0910-\\4383      1 escape por LITERAL
    polarizado 56!033-0910-4383         1 byte por TRANSICAO

E, por estar ENTRE as duas corridas, o delimitador carrega tambem a FRONTEIRA: `56!033` nao
funde, enquanto simplesmente apagar o escape fundiria. Foi esse ponto que derrubou 3
propostas anteriores (labs 2026-07-26-0038 / -0200 / -0330).

## Camada de BORDA, nao grafia canonica

    encode:  ... -> corpo canonico (JA' com seq-RLE) -> polariza  -> wire
    decode:  wire -> despolariza -> corpo canonico -> parser de sempre

O `seq-RLE` (`hcc_seqrle.find_escape_digit_runs`) localiza o digito incrementavel PELO
ESCAPE. Como a polarizacao e' a ULTIMA coisa no encode e a PRIMEIRA no decode, ele so' ve
corpo canonico dos dois lados e nao e' tocado. Tornar o delimitador grafia canonica INTERNA
exigiria o seq-RLE achar o digito pela polaridade — questao aberta, fora deste weld.

## A eleicao do char

Nao se pergunta "qual char usar", se pergunta **onde existe conflito**: o alfabeto que a
coluna realmente usa. O complemento tem conflito ZERO por construcao, sem lista e sem escape
do proprio delimitador.

A `FAIXA` e' so' PONTUACAO ASCII fora da gramatica — nem digito, nem letra. Exclusao por
CLASSE, e nao por lista, por dois bugs que a auditoria adversarial do lab 2026-07-26-2126
reproduziu:

    digito  o delimitador FUNDE com a corrida que deveria delimitar: com `0` eleito,
            `1\\22.\\33` vira `1022.33` e a volta deixa de ser exata.
    letra   o sufixo pousa no indice 6, que e' o slot do DISCRIMINADOR (`#TCF.8b`,
            `#TCF.8n`, `#TCF.8H`, `#TCF.8M`). Uma coluna de STRING elegia `b` e emitia
            `#TCF.8b` — byte-identico ao cabecalho canonico de uma coluna bool.

Excluindo por classe, o sufixo nunca colide com discriminador (nenhum e' pontuacao) e nunca
funde com corrida de digito. Continua fechado quando surgir tag nova.

## A decisao e' uma CONTA, nao um experimento

Uma varredura acumula tres coisas; a decisao le' os acumuladores sem tocar no dado de novo:

    presentes   alfabeto da coluna       -> elege o char
    trocas_R    contador                 -> polaridade inicial `R`
    trocas_L    contador                 -> polaridade inicial `L`

FLOOR incluindo o proprio sufixo (mesmo padrao do `hcc_seqrle` e do `min(tcf, raw, dict,
split)` do multi-col). Empate fica com a grafia de hoje.

Fusao desta varredura no laco que `syntax._escape_lit` ja' roda e' otimizacao de .9
(T-POLARIDADE-FUSE), nao muda byte nenhum.

Referencias: labs `experiments/lab/dirty/2026-07/2026-07-26/` — `1853` (a proposta),
`1913` (marcador virtual + alfabeto), `1954` (35 variacoes + auto-declaracao),
`2126` (cruzamento com bool/binario/null + auditoria adversarial).
"""
BS = chr(92)

_GRAMATICA = set("*~^,|" + BS + "\n")

#: Pontuacao ASCII fora da gramatica. Nem digito, nem letra — ver docstring do modulo.
FAIXA = tuple(
    chr(c) for c in range(0x21, 0x7F)
    if chr(c) not in _GRAMATICA and not chr(c).isdigit() and not chr(c).isalpha()
)
_FAIXA_SET = frozenset(FAIXA)

#: Custo em bytes do sufixo auto-declarante, por polaridade inicial (o char, dobrado em `L`).
_PREFIXO = {"R": 1, "L": 2}


def _partes(linha):
    """Separa o prefixo de contador (`*N|`, `*N+d|`) da declaracao. O prefixo nao e' tocado."""
    if linha.startswith("*") and "|" in linha:
        bar = linha.find("|")
        return linha[: bar + 1], linha[bar + 1 :]
    return "", linha


def _opaca(decl):
    """Linhas que a camada nao toca: vazia e referencia de linha (`^N`).

    O slot NULO (`0` cru, grafia otimizada de `^0`) **nao** entra aqui, e isso e' deliberado:
    sob polaridade `L` o `0` cru ja' e' o LITERAL `"0"`, e e' o null que precisa da troca
    (`!0`). Trata-lo como opaco fazia o literal `\\0` voltar como `0` — a string `"0"`
    virando `None`, corrupcao que so' um RT elemento-a-elemento pega (lab 2126). O null e'
    referencia ao slot 0, e a maquina de polaridade classifica digito nu como `R` =
    referencia: ela acerta sozinha, sem caso especial.
    """
    return decl == "" or decl.startswith("^")


def _varre(corpo):
    """`(alfabeto, trocas_R, trocas_L, n_literais)` numa passada."""
    presentes = set()
    trocas = {"R": 0, "L": 0}
    literais = 0

    for linha in corpo.split("\n"):
        _pre, decl = _partes(linha)
        if _opaca(decl):
            continue
        est = {"R": "R", "L": "L"}
        i, n = 0, len(decl)
        while i < n:
            c = decl[i]
            if c == BS:
                i += 1
                if i < n and decl[i].isdigit():
                    while i < n and decl[i].isdigit():
                        presentes.add(decl[i])
                        i += 1
                    literais += 1
                    for pol in ("R", "L"):
                        if est[pol] != "L":
                            trocas[pol] += 1
                            est[pol] = "L"
                elif i < n:
                    presentes.add(decl[i])       # escape opaco (`\\*`, `\\\\`, `\\~`)
                    i += 1
            elif c.isdigit():
                while i < n and decl[i].isdigit():
                    presentes.add(decl[i])
                    i += 1
                for pol in ("R", "L"):
                    if est[pol] != "R":
                        trocas[pol] += 1
                        est[pol] = "R"
            else:
                presentes.add(c)
                i += 1
    return presentes, trocas["R"], trocas["L"], literais


def _elege(presentes):
    """O menor char da FAIXA que a coluna nao usa. `None` se a coluna usa todos."""
    for c in FAIXA:
        if c not in presentes:
            return c
    return None


def polariza(corpo):
    """Corpo canonico -> `(sufixo, corpo)`. Sufixo `""` = a polarizacao nao compensou.

    Nunca-pior: o FLOOR compara `trocas + sufixo` com os escapes que seriam economizados, e
    devolve a grafia de hoje no empate.
    """
    if not corpo:
        return "", corpo
    presentes, tR, tL, literais = _varre(corpo)
    char = _elege(presentes)
    if char is None:
        return "", corpo                              # coluna usa a FAIXA inteira
    inicial = min(("R", "L"), key=lambda p: (tR if p == "R" else tL) + _PREFIXO[p])
    custo = (tR if inicial == "R" else tL) + _PREFIXO[inicial]
    if custo >= literais:
        return "", corpo                              # FLOOR: nao paga
    return char * _PREFIXO[inicial], _emite(corpo, char, inicial)


def _emite(corpo, char, inicial):
    """Corpo canonico -> corpo polarizado."""
    saida = []
    for linha in corpo.split("\n"):
        pre, decl = _partes(linha)
        if _opaca(decl):
            saida.append(linha)
            continue
        est, buf, i, n = inicial, [], 0, len(decl)
        while i < n:
            c = decl[i]
            if c == BS:
                i += 1
                if i < n and decl[i].isdigit():
                    j = i
                    while i < n and decl[i].isdigit():
                        i += 1
                    if est != "L":
                        buf.append(char)
                        est = "L"
                    buf.append(decl[j:i])
                elif i < n:
                    buf.append(BS + decl[i])
                    i += 1
            elif c.isdigit():
                j = i
                while i < n and decl[i].isdigit():
                    i += 1
                if est != "R":
                    buf.append(char)
                    est = "R"
                buf.append(decl[j:i])
            else:
                buf.append(c)
                i += 1
        saida.append(pre + "".join(buf))
    return "\n".join(saida)


def le_sufixo(sufixo):
    """`(char, polaridade_inicial)` a partir do sufixo do cabecalho. Fail-loud."""
    if not sufixo or len(sufixo) > 2:
        raise ValueError(
            f"sufixo de polaridade invalido: {sufixo!r} (esperado 1 ou 2 chars iguais)"
        )
    char = sufixo[0]
    if char not in _FAIXA_SET:
        raise ValueError(
            f"delimitador de polaridade {char!r} fora da FAIXA (pontuacao ASCII, "
            f"sem digito nem letra) — corpo nao-canonico"
        )
    if any(c != char for c in sufixo):
        raise ValueError(f"sufixo de polaridade nao-canonico: {sufixo!r}")
    return char, ("R" if len(sufixo) == 1 else "L")


def despolariza(corpo, sufixo):
    """Corpo polarizado + sufixo -> corpo CANONICO. Inversa exata de `polariza`."""
    char, inicial = le_sufixo(sufixo)
    saida = []
    for linha in corpo.split("\n"):
        pre, decl = _partes(linha)
        if _opaca(decl):
            saida.append(linha)
            continue
        est, buf, i, n = inicial, [], 0, len(decl)
        while i < n:
            c = decl[i]
            if c == BS:
                buf.append(decl[i : i + 2])           # escape opaco: devolve como esta'
                i += 2
            elif c == char:
                est = "L" if est == "R" else "R"
                i += 1
            elif c.isdigit():
                j = i
                while j < n and decl[j].isdigit():
                    j += 1
                buf.append((BS if est == "L" else "") + decl[i:j])
                i = j
            else:
                buf.append(c)
                i += 1
        saida.append(pre + "".join(buf))
    return "\n".join(saida)

"""Grafia final + CAÇA A COLISÕES (owner 2026-07-24).

Owner escolheu o **`0` cru** pelo ganho, com a leitura de que ele é a *representação otimizada*
que "internamente representa `^0`". Se é isso, ele tem que herdar a SEMÂNTICA do `^0` —
endereço RESERVADO que **não declara nó**. Na variante A da rodada anterior o `0` declarava, e
por isso o 2º null virava `^1` (grafia inconsistente). Corrigido aqui:

  A  `0` DECLARA nó       -> 1º null = `0`, demais = `^k`   (inconsistente; forma antiga)
  B  `^0` reservado       -> todo null = `^0`               (proposta inicial do owner)
  C  `0` reservado        -> todo null = `0`                (grafia do owner + semântica do ^0)

REGRA DE DESAMBIGUAÇÃO (posicional, como o char de modo no índice 7): **a linha INTEIRA igual a
`0`** é o especial. Um `0` dentro de composição (`1~0`, `0..3`) continua sendo o espaço de
FRAGMENTO e não vira null — então a classe absurda "compor com null" segue inexprimível.

A caça abaixo é o gate: o encoder pode emitir uma linha `resto == "0"` por algum outro motivo?
"""
import itertools
import pathlib
import sys

RAIZ = pathlib.Path(__file__).parent
sys.path.insert(0, str(RAIZ.parents[5] / "src"))

from tcf import encode, decode  # noqa: E402

CAB = "#TCF.8\n"


def _split(ln):
    if ln.startswith("*") and "|" in ln:
        bar = ln.find("|")
        return ln[:bar + 1], ln[bar + 1:]
    return "", ln


# ==================================================================== 1. CAÇA A COLISÕES
def caca_colisoes():
    """O encoder REAL emite alguma linha cujo `resto` seja exatamente `0`? (sem nulls no jogo)"""
    vocab = ["0", "00", "01", "10", "0.0", "-0", "0x", "a0", "0a", "", "1", "9", "null",
             "true", "0\t", " 0", "0 ", "000", "0,0", "0~0", "^0", "\\0", "*2|0"]
    colisoes, total = [], 0
    casos = []
    for r in (1, 2, 3):                                    # combinações de vocabulário
        casos += [list(c) for c in itertools.permutations(vocab, r)] if r == 1 else []
    for a, b in itertools.product(vocab, repeat=2):        # pares
        casos.append([a, b])
    for a in vocab:                                        # repetição (exercita RLE) e mistura
        casos += [[a] * 3, [a, "x", a], ["x", a, "y", a], [a] * 12, [a, a, "x"]]
    for a, b, c in itertools.product(vocab[:8], repeat=3):
        casos.append([a, b, c])

    for col in casos:
        total += 1
        try:
            w = encode(col, stamp=False)
        except ValueError:
            continue                                        # fail-loud legítimo (ex.: \n embutido)
        if decode(w) != col:
            colisoes.append(("RT QUEBRADO", col, w))
            continue
        for ln in w.split("\n"):
            _pre, r = _split(ln)
            if r == "0":
                colisoes.append(("LINHA '0' EMITIDA", col, w))
                break
    return total, colisoes


# ==================================================================== 2. grafias
def _corpo_com_marca(col):
    return encode(["0" if v is None else v for v in col], stamp=False)


def _nos(linhas):
    """Índice de nó (A) de cada linha declarante; devolve z = nó da declaração do null."""
    z, no = None, 0
    for ln in linhas:
        _pre, r = _split(ln)
        if r.startswith("^") or ln == "":
            continue
        no += 1
        if r == "\\0":
            z = no
    return z


def enc(col, grafia):
    """grafia: 'A' (0 declara) · 'B' (^0 reservado) · 'C' (0 reservado)."""
    linhas = _corpo_com_marca(col).split("\n")
    if grafia == "A":
        return CAB + "\n".join(pre + "0" if r == "\\0" else ln
                               for ln, (pre, r) in ((x, _split(x)) for x in linhas))
    marca = "^0" if grafia == "B" else "0"
    z, out = _nos(linhas), []
    for ln in linhas:
        pre, r = _split(ln)
        if r == "\\0":
            out.append(pre + marca)
        elif r.startswith("^"):
            k = int(r[1:])
            out.append(pre + (marca if k == z else f"^{k - 1 if z and k > z else k}"))
        else:
            out.append(ln)
    return CAB + "\n".join(out)


def dec(wire, grafia):
    """Pré-avaliador: grafia otimizada -> forma explícita -> core REAL -> materializa None."""
    linhas = wire[len(CAB):].split("\n")
    if grafia == "A":
        expl = [pre + "\\0" if r == "0" else ln
                for ln, (pre, r) in ((x, _split(x)) for x in linhas)]
        return [None if v == "0" else v for v in decode("\n".join(expl))]
    marca = "^0" if grafia == "B" else "0"
    m = 0
    for ln in linhas:
        _pre, r = _split(ln)
        if r == marca:
            break
        if r.startswith("^") or ln == "":
            continue
        m += 1
    z, visto, out = m + 1, False, []
    for ln in linhas:
        pre, r = _split(ln)
        if r == marca:
            out.append(pre + ("\\0" if not visto else f"^{z}"))
            visto = True
        elif r.startswith("^"):
            k = int(r[1:])
            out.append(pre + f"^{k + 1 if k >= z else k}")
        else:
            out.append(ln)
    return [None if v == "0" else v for v in decode("\n".join(out))]


# ==================================================================== execução
def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    src = (RAIZ / "run.py").read_text(encoding="utf-8").replace('if __name__ == "__main__":', "if False:")
    ns = {"__file__": str((RAIZ / "run.py").resolve())}
    exec(compile(src, "run.py", "exec"), ns)
    FONTES = ns["FONTES"]

    total, col_ = caca_colisoes()
    out = ["# Grafia final + caça a colisões — `0` cru como null", "",
           "## 1. Caça a colisões (o gate da decisão)", "",
           f"Colunas testadas com o encoder REAL: **{total}** — vocabulário adversarial "
           "(`\"0\"`, `\"00\"`, `\"01\"`, `\"10\"`, `\"-0\"`, `\"0.0\"`, `\"000\"`, `\"^0\"`, "
           "`\"\\\\0\"`, `\"*2|0\"`, `\"0~0\"`, vazia…) em singleton, pares, trios, repetição "
           "(RLE) e intercalado.", "",
           f"**Linhas `0` emitidas pelo encoder: {len([c for c in col_ if c[0] == 'LINHA 0 EMITIDA'])}** "
           f"· RT quebrado: {len([c for c in col_ if c[0] == 'RT QUEBRADO'])}", ""]
    if col_:
        out += ["| tipo | coluna | wire |", "|---|---|---|"]
        out += [f"| {t} | `{c!r}` | `{w!r}` |" for t, c, w in col_[:10]]
        out += [""]
    else:
        out += ["**Zero colisões.** A string `\"0\"` é sempre escapada como `\\0` pelo core, "
                "e a tabela de fragmentos é 1-based — então uma linha cujo conteúdo inteiro é "
                "`0` nunca é emitida por dado. O slot está livre.", ""]

    linhas, falhas = [], 0
    for eid, (col, _n) in FONTES.items():
        ws = {g: enc(col, g) for g in "ABC"}
        oks = {g: dec(ws[g], g) == col for g in "ABC"}
        falhas += sum(not v for v in oks.values())
        linhas.append((eid, sum(v is None for v in col),
                       *(len(ws[g].encode()) for g in "ABC"),
                       "OK" if all(oks.values()) else "FALHOU"))

    out += ["## 2. As três grafias", "",
            "- **A** `0` DECLARA nó → 1º null = `0`, demais = `^k` (grafia inconsistente)",
            "- **B** `^0` reservado, não declara → todo null = `^0`",
            "- **C** `0` reservado, não declara → todo null = `0` "
            "(**grafia do owner + semântica do `^0`**)", "",
            "| id | nulls | A | B | C | C−A | C−B | RT |", "|---|---:|---:|---:|---:|---:|---:|---|"]
    out += [f"| {e} | {k} | {a} | {b} | {c} | {c - a:+} | {c - b:+} | {s} |"
            for e, k, a, b, c, s in linhas]
    ca = sum(c - a for _e, _k, a, _b, c, _s in linhas)
    cb = sum(c - b for _e, _k, _a, b, c, _s in linhas)
    out += ["", f"RT: **{len(linhas) * 3 - falhas}/{len(linhas) * 3}** (as três grafias).",
            f"Total: C é **{ca:+} B** vs A e **{cb:+} B** vs B em {len(linhas)} casos.", ""]

    col = FONTES["A-exemplo-owner"][0]
    out += ["## 3. Exemplo do owner", "", "```",
            f"coluna : {col}"] + [f"{g}      : {enc(col, g)!r}" for g in "ABC"] + ["```", ""]
    out += ["## 4. Regra de desambiguação", "",
            "**Posicional** (mesma classe do char de modo no índice 7): a **linha inteira** igual "
            "a `0` é o especial. Um `0` DENTRO de composição (`1~0`, `0..3`) permanece no espaço "
            "de FRAGMENTO e não vira null — logo a classe absurda \"compor uma string com null\" "
            "continua **inexprimível**, que era a única objeção real ao dígito nu.", ""]
    (RAIZ / "result-grafia-final.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    print("\n".join(out))
    return 0 if (falhas == 0 and not col_) else 1


if __name__ == "__main__":
    sys.exit(main())

"""Lab 2026-07-25-2337 — polaridade do escape: literal x referência.

Ideia do owner (retomada de uma análise antiga): no corpo, **dígito nu é REFERÊNCIA** e o
literal numérico paga `\\` (1 B por run de dígitos). Em coluna cheia de número isso é caro —
o wire `A-ruido1000000-n1000-sem-seqrle.tcfp` tem **998 barras invertidas em 8863 B**.

    "dependendo das condições, se mediria se tem mais escapes que referências, aí só trocar.
     na verdade é sobre os elementos nativos vs os índices das referências — o que tiver
     mais, obviamente troca."

As duas polaridades:

    NORMAL   `\\168116` = literal      ·  `1` = referência ao fragmento 1
    FLIP     `168116`   = literal      ·  `\\1` = referência ao fragmento 1

A troca é uma **involução**: aplicar duas vezes volta ao original. Isso é o que torna o
protótipo verificável — `normal → flip → normal` tem que ser identidade byte a byte.

Economia teórica = (escapes de dígito) − (referências de fragmento). Este lab **materializa**
os dois corpos e mede, em vez de estimar pela contagem.
"""
import json
import pathlib
import sys

RAIZ = pathlib.Path(__file__).parent
REPO = RAIZ.parents[5]
sys.path.insert(0, str(REPO / "src"))

from tcf import decode, encode  # noqa: E402
from tcf.encoder import _encode_column  # noqa: E402

BS = chr(92)

for d in ("inputs", "intermediates", "outputs"):
    (RAIZ / d).mkdir(exist_ok=True)


# ------------------------------------------------------------------ a involução
def flip(corpo):
    """Troca a polaridade do dígito. `normal → flip` e `flip → normal` são a MESMA função.

    Só mexe em dígito: `*`, `~`, `^`, o `\\` de não-dígito e os literais de texto ficam
    exatamente onde estão.
    """
    out = []
    for linha in corpo.split("\n"):
        pre, resto = "", linha
        if linha.startswith("*") and "|" in linha:
            bar = linha.find("|")
            pre, resto = linha[:bar + 1], linha[bar + 1:]
        if resto.startswith("^"):                      # ref de LINHA: outro namespace
            out.append(linha)
            continue
        buf, i, n = [], 0, len(resto)
        while i < n:
            c = resto[i]
            if c == BS:
                i += 1
                if i < n and resto[i].isdigit():       # era LITERAL -> vira nu
                    j = i
                    while j < n and resto[j].isdigit():
                        j += 1
                    buf.append(resto[i:j])
                    i = j
                else:                                  # escape de nao-digito: intocado
                    buf.append(BS + (resto[i] if i < n else ""))
                    i += 1
            elif c.isdigit():                          # era REFERENCIA -> vira escapada
                j = i
                while j < n and resto[j].isdigit():
                    j += 1
                buf.append(BS + resto[i:j])
                i = j
            else:
                buf.append(c)
                i += 1
        out.append(pre + "".join(buf))
    return "\n".join(out)


def adjacencia_ambigua(corpo):
    """Conta as posições onde o FLIP **não é expressável**.

    O escape é GULOSO sobre a corrida de dígitos. Em NORMAL, uma referência nua termina no
    `\\` seguinte, então `1\\2` (ref 1 + literal "2") é inequívoco. Em FLIP isso vira `\\12`,
    que o parser lê como referência **12** — os dois adjacentes colapsam.

    É o mesmo problema espelhado: NORMAL não consegue expressar literal-seguido-de-ref
    (`\\2` + `1` viraria `\\21`), e o encoder evita produzir essa forma.
    """
    n_amb = 0
    for linha in corpo.split("\n"):
        resto = linha.split("|", 1)[1] if linha.startswith("*") and "|" in linha else linha
        if resto.startswith("^"):
            continue
        i, n = 0, len(resto)
        while i < n:
            if resto[i] == BS:
                i += 2
                while i < n and resto[i - 1].isdigit() and resto[i].isdigit():
                    i += 1
            elif resto[i].isdigit():
                while i < n and resto[i].isdigit():
                    i += 1
                if i < n and resto[i] == BS and i + 1 < n and resto[i + 1].isdigit():
                    n_amb += 1                         # ref NUA colada em literal-dígito
            else:
                i += 1
    return n_amb


# ------------------------------------------------------------------ casos
def _lcg(seed):
    x = seed
    while True:
        x = (1103515245 * x + 12345) % (2 ** 31)
        yield x


def ruido(n, k, seed=7):
    g = _lcg(seed)
    return [next(g) % k for _ in range(n)]


CASOS = [
    ("A-ruido1e6-n1000", ruido(1000, 10 ** 6), "inteiros aleatórios (o caso do owner)"),
    ("A-ruido1e6-n100", ruido(100, 10 ** 6), "idem, n=100"),
    ("A-cpf-like-n200", [f"{i:03d}.{i * 7 % 1000:03d}.{i * 13 % 1000:03d}-{i % 100:02d}"
                         for i in range(200)], "documento formatado (string)"),
    ("A-uuid-hex-n200", [f"{i * 2654435761 % (16 ** 8):08x}-a" for i in range(200)],
     "hex pseudo-aleatório (string)"),
    ("A-precos-n200", [f"{1 + (i * 37 % 9999) / 100:.2f}" for i in range(200)],
     "preços formatados (string)"),
    ("B-datas-n200", [f"2026-{(i % 12) + 1:02d}-{(i % 28) + 1:02d}" for i in range(200)],
     "datas ISO — mistura escape e referência"),
    ("C-emails-n200", [f"user{i}@dominio{i % 7}.com" for i in range(200)],
     "emails — mais REFERÊNCIA que escape"),
    ("C-texto-n200", [f"palavra{chr(97 + i % 26)}" for i in range(200)],
     "texto sem dígito — só referência"),
    ("D-seq-n1000", list(range(1000)), "cadência: corpo minúsculo, flip irrelevante"),
    ("D-ruido0a9-n1000", ruido(1000, 10), "baixa cardinalidade: domina o `^N`"),
]


def _wj(p, obj, compacto=False):
    txt = json.dumps(obj, ensure_ascii=False,
                     separators=(",", ":") if compacto else (", ", ": "),
                     indent=None if compacto else 2)
    p.write_text(txt + ("" if compacto else "\n"), encoding="utf-8")
    return len(txt.encode())


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    out = ["# Polaridade do escape — literal x referência (2026-07-25-2337)", "",
           "`NORMAL` = hoje (`\\168116` literal · `1` referência). "
           "`FLIP` = invertido (`168116` literal · `\\1` referência).", "",
           "A troca **deveria** ser uma involução (`normal → flip → normal` = identidade). "
           "Onde não é, o flip é **inexpressável** — ver a seção de adjacência.", "",
           "| id | corpo NORMAL | corpo FLIP | Δ | adjacências ambíguas | flip é seguro? |",
           "|---|---:|---:|---:|---:|---|"]

    linhas, falhas = [], 0
    for eid, dados, nota in CASOS:
        _wj(RAIZ / "inputs" / f"{eid}-fonte.json", {"nota": nota, "dados": dados})
        _wj(RAIZ / "intermediates" / f"{eid}-dataset-consumido.json", dados)

        corpo = _encode_column([str(v) for v in dados])
        flipado = flip(corpo)
        volta = flip(flipado)
        involucao = volta == corpo                     # a prova de que a troca é reversível
        w = encode(dados)
        rt = decode(w) == dados
        falhas += not rt

        (RAIZ / "outputs" / f"{eid}-wire.tcf").write_text(w, encoding="utf-8")
        (RAIZ / "outputs" / f"{eid}-corpo-normal.tcfp").write_text(corpo, encoding="utf-8")
        (RAIZ / "outputs" / f"{eid}-corpo-flip.tcfp").write_text(flipado, encoding="utf-8")
        _wj(RAIZ / "outputs" / f"{eid}-dataset.roundtrip.json", decode(w))

        a, b = len(corpo.encode()), len(flipado.encode())
        amb = adjacencia_ambigua(corpo)
        seguro = amb == 0
        assert seguro == involucao, (eid, amb, involucao)   # a deteccao TEM que casar
        linhas.append((eid, a, b, a - b, seguro))
        out.append(f"| `{eid}` | {a} | {b} | **{b - a:+}** | {amb} | "
                   f"{'sim' if seguro else '**NAO**'} |")

    ganham = [x for x in linhas if x[3] > 0 and x[4]]
    perdem = [x for x in linhas if x[3] < 0 and x[4]]
    inseguras = [x for x in linhas if not x[4]]
    out += ["", "## Leitura", "",
            f"- **{len(ganham)} de {len(linhas)}** colunas ficam menores com o FLIP; "
            f"**{len(perdem)}** ficam maiores.",
            f"- ganho somado onde ganha: **{sum(x[3] for x in ganham)} B** · "
            f"perda somada onde perde: **{sum(x[3] for x in perdem)} B**",
            f"- **{len(inseguras)} coluna(s) NÃO podem ser flipadas** com este esquema "
            "(adjacência ambígua, abaixo)", "",
            "As colunas que **perdem** (emails, texto sem dígito) são a razão de isto não "
            "poder virar default novo — tem que ser **decisão por coluna**, um `min()` como "
            "os outros. É exatamente o que o owner descreveu: *o que tiver mais, troca*.", ""]

    out += ["## Lado a lado — as duas polaridades", "", "```"]
    for eid in ("A-ruido1e6-n100", "C-texto-n200"):
        cn = (RAIZ / "outputs" / f"{eid}-corpo-normal.tcfp").read_text(encoding="utf-8")
        cf = (RAIZ / "outputs" / f"{eid}-corpo-flip.tcfp").read_text(encoding="utf-8")
        out += [f"{eid}", f"  normal: {cn.split(chr(10))[0]!r} …",
                f"  flip  : {cf.split(chr(10))[0]!r} …"]
    out += ["```", ""]

    (RAIZ / "result.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    print("\n".join(out))
    return 0 if falhas == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

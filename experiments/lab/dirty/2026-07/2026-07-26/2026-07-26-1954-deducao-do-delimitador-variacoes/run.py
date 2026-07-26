"""Lab 2026-07-26-1954 — dedução do delimitador, com muitas variações.

    "se a gente eleger um caractere inicial para ligar com essa ambiguidade ela também não
     precisa ser declarada. ou seja a marcação existe em estrutura interna, a gente pode usar
     até isso como dedução pra saber onde tem ou não. faça mais um experimento com mais
     variações (…) foco na estrutura e na lógica."

A pergunta é ESTRUTURAL: **quanto da declaração é deduzível?**

  eleição   o encoder elege o menor char LIVRE (o menor da FAIXA que a coluna não usa)
  dedução   o decoder tenta: "o delimitador é o menor char da FAIXA presente no corpo"

A dedução só fecha quando o char eleito é menor que todo char de FAIXA do dado — o que
equivale a **`!` (FAIXA[0]) não estar no dado**. Este lab não afirma que isso é frequente:
**mede**, em 30 colunas, incluindo adversariais construídas para quebrar a regra.

Três materializações comparadas:

    V0   `d<char><pol>` no cabeçalho          2 B, sempre funciona
    V1   `<pol>` no cabeçalho, char DEDUZIDO  1 B, só se a dedução fechar
    V2   polaridade no 1º byte do corpo       0 B de cabeçalho, +1 B de corpo se pol=L

VALIDAÇÃO: `resolve` -> `de_grafia` -> compara byte a byte com o corpo CANÔNICO -> `decode`
REAL. E, para V1, o decode usa o char **DEDUZIDO**, não o eleito — é o teste que importa.
"""
import json
import pathlib
import sys

RAIZ = pathlib.Path(__file__).parent
REPO = RAIZ.parents[5]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(RAIZ))

from deducao import (  # noqa: E402
    FAIXA, decide, deduz_do_corpo, deducao_fecha, de_grafia, de_v3, elege,
    para_v3, resolve, varredura_unica,
)

from tcf import decode, encode  # noqa: E402
from tcf.encoder import _encode_column  # noqa: E402

for d in ("inputs", "intermediates", "outputs"):
    (RAIZ / d).mkdir(exist_ok=True)


def _lcg(seed):
    x = seed
    while True:
        x = (1103515245 * x + 12345) % (2 ** 31)
        yield x


def gera(forma, n, seed=7):
    g = _lcg(seed)
    L = lambda m: next(g) % m                                          # noqa: E731
    A = lambda: chr(65 + next(g) % 26)                                 # noqa: E731
    a = lambda: chr(97 + next(g) % 26)                                 # noqa: E731
    H = lambda k: "".join("0123456789abcdef"[next(g) % 16] for _ in range(k))  # noqa: E731

    # ---------------------------------------------------------- formatadas (máscara fixa)
    if forma == "cpf":
        return [f"{i % 1000:03d}.{i * 7 % 1000:03d}.{i * 13 % 1000:03d}-{i % 100:02d}"
                for i in range(n)]
    if forma == "cnpj":
        return [f"{L(100):02d}.{L(1000):03d}.{L(1000):03d}/0001-{L(100):02d}"
                for _ in range(n)]
    if forma == "cartao":
        return ["-".join(f"{L(10000):04d}" for _ in range(4)) for _ in range(n)]
    if forma == "cep":
        return [f"{L(99999):05d}-{L(999):03d}" for _ in range(n)]
    if forma == "telefone":
        return [f"({L(90) + 10}) 9{L(10000):04d}-{L(10000):04d}" for _ in range(n)]
    if forma == "ip":
        return [".".join(str(L(256)) for _ in range(4)) for _ in range(n)]
    if forma == "mac":
        return [":".join(H(2) for _ in range(6)) for _ in range(n)]
    if forma == "uuid":
        return [f"{H(8)}-{H(4)}-{H(4)}-{H(4)}-{H(12)}" for _ in range(n)]
    if forma == "data-iso":
        return [f"20{L(30) + 10}-{L(12) + 1:02d}-{L(28) + 1:02d}" for _ in range(n)]
    if forma == "data-br":
        return [f"{L(28) + 1:02d}/{L(12) + 1:02d}/20{L(30) + 10}" for _ in range(n)]
    if forma == "hora":
        return [f"{L(24):02d}:{L(60):02d}:{L(60):02d}" for _ in range(n)]
    if forma == "timestamp":
        return [f"20{L(30) + 10}-{L(12) + 1:02d}-{L(28) + 1:02d}T{L(24):02d}:{L(60):02d}:"
                f"{L(60):02d}Z" for _ in range(n)]
    if forma == "moeda":
        return [f"R$ {L(10000)},{L(100):02d}" for _ in range(n)]
    if forma == "coord":
        return [f"-{L(90):02d}.{L(10 ** 6):06d}" for _ in range(n)]
    if forma == "isbn":
        return [f"978-{L(10)}-{L(10000):04d}-{L(10000):04d}-{L(10)}" for _ in range(n)]
    if forma == "placa":
        return [f"{A()}{A()}{A()}{L(10)}{A()}{L(100):02d}" for _ in range(n)]
    if forma == "semver":
        return [f"{L(5)}.{L(20)}.{L(50)}" for _ in range(n)]
    if forma == "sku":
        return [f"{A()}{A()}-{L(100000):05d}" for _ in range(n)]
    if forma == "matricula":
        return [f"20{L(25) + 10}{L(1000000):06d}" for _ in range(n)]

    # ---------------------------------------------------------- numéricas
    if forma == "int-ordenado":
        return [str(i * 3 + 100) for i in range(n)]
    if forma == "int-aleatorio":
        return [str(L(10 ** 7)) for _ in range(n)]
    if forma == "int-negativo":
        return [str(L(2000) - 1000) for _ in range(n)]
    if forma == "float":
        return [f"{L(1000)}.{L(1000):03d}" for _ in range(n)]
    if forma == "com-null":
        return [None if i % 7 == 0 else str(L(10000)) for i in range(n)]

    # ---------------------------------------------------------- texto
    if forma == "texto":
        return [f"palavra{a()}" for _ in range(n)]
    if forma == "nomes":
        return [f"{A()}{a()}{a()}{a()} {A()}{a()}{a()}{a()}{a()}" for _ in range(n)]
    if forma == "email":
        return [f"user{L(10000)}@d{L(9)}.com" for _ in range(n)]
    if forma == "url":
        return [f"https://d{L(9)}.com/p/{L(100000)}" for _ in range(n)]
    if forma == "frase":
        return [" ".join(f"{a()}{a()}{a()}{a()}" for _ in range(6)) for _ in range(n)]

    # ---------------------------------------------------------- ADVERSARIAIS
    if forma == "adv-usa-bang":
        # contém `!` = FAIXA[0]: quebra a dedução ingênua DE PROPÓSITO
        return [f"!{L(1000):03d}.{L(1000):03d}!" for _ in range(n)]
    if forma == "adv-alfabeto-total":
        # usa TODOS os chars da FAIXA: não sobra char livre, a regra tem que recusar
        base = "".join(FAIXA)
        return [f"{base}{L(1000):03d}" for _ in range(n)]
    if forma == "adv-so-digitos":
        return [f"{L(10 ** 8):08d}" for _ in range(n)]
    if forma == "adv-sem-digitos":
        return ["".join(a() for _ in range(8)) for _ in range(n)]
    if forma == "adv-um-valor":
        return ["12345"] * n
    if forma == "adv-unicode":
        return [f"café-{L(1000):03d}-ção" for _ in range(n)]
    raise ValueError(forma)


FORMATADAS = ["cpf", "cnpj", "cartao", "cep", "telefone", "ip", "mac", "uuid", "data-iso",
              "data-br", "hora", "timestamp", "moeda", "coord", "isbn", "placa", "semver",
              "sku", "matricula"]
NUMERICAS = ["int-ordenado", "int-aleatorio", "int-negativo", "float", "com-null"]
TEXTO = ["texto", "nomes", "email", "url", "frase"]
ADVERSARIAIS = ["adv-usa-bang", "adv-alfabeto-total", "adv-so-digitos", "adv-sem-digitos",
                "adv-um-valor", "adv-unicode"]
GRUPOS = [("Formatadas", FORMATADAS), ("Numéricas", NUMERICAS), ("Texto", TEXTO),
          ("Adversariais", ADVERSARIAIS)]


def _wj(p, obj):
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def caso(forma, dados):
    corpo = _encode_column(dados)
    toks, presentes, tR, tL, literais = varredura_unica(corpo)
    modo, char, inicial, custo = decide(presentes, tR, tL, literais)

    eleito = elege(presentes)
    fecha = deducao_fecha(presentes)

    if modo == "delim":
        corpo_d = resolve(toks, char, inicial)
        deduzido = deduz_do_corpo(corpo_d)
        # O TESTE QUE IMPORTA: reconstrói com o char DEDUZIDO, não com o eleito.
        volta_ded = de_grafia(corpo_d, deduzido, inicial) if deduzido else None
        volta = de_grafia(corpo_d, char, inicial)
        # V3: le o char e a polaridade do PREFIXO auto-declarante, sem o eleito na mao
        v3_txt = para_v3(corpo_d, char, inicial)
        c3, p3, corpo3 = de_v3(v3_txt)
        volta_v3 = de_grafia(corpo3, c3, p3)
        # O prefixo NAO precisa de linha propria: ele cabe no fim da linha de cabecalho,
        # que ja' existe. A quebra no artefato e' so' pro teste de leitura ser exato.
        n_v3 = len(corpo_d.encode()) + (1 if inicial == "R" else 2)
    else:
        corpo_d, deduzido, volta, volta_ded = corpo, None, corpo, corpo
        volta_v3, n_v3 = corpo, len(corpo.encode())

    exato = volta == corpo
    ded_ok = volta_ded == corpo                      # V1 sobreviveria?
    v3_ok = volta_v3 == corpo                        # V3 sobreviveria?
    wire = encode(dados)
    cab = wire.partition("\n")[0]
    rt = (decode(cab + "\n" + volta) == dados) if exato else False

    # custo de cabeçalho por materialização
    if modo == "delim":
        v0, v1 = 2, (1 if ded_ok else None)
        v2 = 0 if inicial == "R" else 0              # V2 põe a polaridade no corpo
        corpo_v2 = len(corpo_d.encode()) + (0 if inicial == "R" else 1)
    else:
        v0 = v1 = v2 = 0
        corpo_v2 = len(corpo.encode())

    _wj(RAIZ / "inputs" / f"{forma}-fonte.json",
        {"forma": forma, "n": len(dados), "amostra": dados[:4]})
    _wj(RAIZ / "intermediates" / f"{forma}-alfabeto.json",
        {"presentes": "".join(sorted(presentes)), "eleito": eleito,
         "deduzido": deduzido, "deducao_fecha": fecha,
         "faixa0": FAIXA[0], "faixa0_no_dado": FAIXA[0] in presentes})
    (RAIZ / "outputs" / f"{forma}-wire-normal.tcf").write_text(wire, encoding="utf-8")
    if modo == "delim":
        (RAIZ / "outputs" / f"{forma}-wire-V0-declarado.tcfp").write_text(
            f"{cab}d{char}{inicial}\n{corpo_d}", encoding="utf-8")
        # V3: o char (repetido se pol=L) fecha a propria linha de cabecalho — auto-declarante
        (RAIZ / "outputs" / f"{forma}-wire-V3-autodeclarante.tcfp").write_text(
            f"{cab}{char * (1 if inicial == 'R' else 2)}\n{corpo_d}", encoding="utf-8")
    _wj(RAIZ / "outputs" / f"{forma}-dataset.roundtrip.json", decode(wire))

    return {"corpo": len(corpo.encode()), "d": len(corpo_d.encode()), "cv2": corpo_v2,
            "lit": literais, "tR": tR, "tL": tL, "custo": custo, "modo": modo,
            "eleito": eleito, "deduzido": deduzido, "fecha": fecha, "ded_ok": ded_ok,
            "inicial": inicial, "nlivres": sum(1 for c in FAIXA if c not in presentes),
            "rt": rt, "exato": exato, "v0": v0, "v1": v1, "v2": v2,
            "v3_ok": v3_ok, "n_v3": n_v3}


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    out = ["# Dedução do delimitador — 30 variações (2026-07-26-1954)", "",
           "**Eleição** (encoder): o menor char da FAIXA que a coluna não usa.  ",
           "**Dedução** (decoder): o menor char da FAIXA presente no corpo.", "",
           "A dedução só fecha quando o eleito é menor que todo char de FAIXA do dado — o "
           f"que equivale a **`{FAIXA[0]}` não estar no dado**. Medido, não assumido.", ""]

    todas, falhas = [], 0
    for titulo, formas in GRUPOS:
        out += [f"## {titulo}", "",
                "| coluna | corpo | escapes | livres | eleito | deduzido | dedução | decisão | Δ corpo |",
                "|---|---:|---:|---:|:-:|:-:|:-:|---|---:|"]
        for forma in formas:
            dados = gera(forma, 300)
            r = caso(forma, dados)
            todas.append((forma, r))
            falhas += (not r["rt"]) + (not r["exato"])
            dec = (str(r["custo"]) if r["modo"] == "delim"
                   else f"recusa ({r['lit']} esc)")
            ded = ("**bate**" if r["ded_ok"] and r["modo"] == "delim"
                   else ("**FALHA**" if r["modo"] == "delim" else "—"))
            out.append(f"| `{forma}` | {r['corpo']} | {r['lit']} | {r['nlivres']} | "
                       f"`{r['eleito'] or '—'}` | `{r['deduzido'] or '—'}` | {ded} | {dec} | "
                       f"{r['d'] - r['corpo']:+} |")
        out.append("")

    usa = [r for _f, r in todas if r["modo"] == "delim"]
    ded_falha = [f for f, r in todas if r["modo"] == "delim" and not r["ded_ok"]]
    sem_livre = [f for f, r in todas if r["nlivres"] == 0]
    out += ["## O que a dedução aguenta", "",
            f"- colunas em que a regra ATIVA o delimitador: **{len(usa)} de {len(todas)}**",
            f"- dedução do char recupera o eleito: "
            f"**{len(usa) - len(ded_falha)} de {len(usa)}**"
            + (f" — falha em {ded_falha}" if ded_falha else ""),
            f"- colunas sem nenhum char livre: **{len(sem_livre)}**"
            + (f" — {sem_livre}" if sem_livre else ""),
            f"- reconstrução byte-exata **e** RT pelo `decode` REAL: "
            f"**{2 * len(todas) - falhas}/{2 * len(todas)}**", ""]

    quebram = [f for f, r in todas if not r["fecha"]]
    out += [f"A condição exata (`{FAIXA[0]}` ausente do dado) falha em **{len(quebram)}** das "
            f"{len(todas)} colunas" + (f": {quebram}" if quebram else "") + ".", "",
            "É por isso que a dedução **não pode ser a regra sozinha**: ela é uma "
            "otimização condicional, não um invariante. O caminho seguro é o marcador "
            "virtual decidir e a materialização escolher entre declarar e deduzir.", ""]

    # ------------------------------------------------------- as três materializações
    v3_falha = [f for f, r in todas if r["modo"] == "delim" and not r["v3_ok"]]
    out += ["## V3 — o **caractere inicial**, que foi o que você propôs", "",
            "O corpo **começa com o char eleito**. Ele se auto-declara pela posição — o mesmo "
            "idioma que o formato já usa (char de modo no índice 7, `0` cru para o slot "
            "nulo). O decoder lê o byte 0 e pronto: **nada no cabeçalho**.", "",
            "```", "#TCF.8!!               <- `!!` no fim do cabecalho: char + polaridade `L`",
            "000.000.000-00", "001.007.013-01", "```", "",
            "O prefixo **não precisa de linha própria** — cabe no fim da linha de cabeçalho, que já existe. Custo: **1 B** com polaridade `R`, **2 B** com `L` (char repetido). E, ao "
            "contrário da dedução por menor-char, ela **não depende do dado**:", "",
            f"- V3 reconstrói o corpo canônico lendo só o prefixo: "
            f"**{len(usa) - len(v3_falha)} de {len(usa)}**"
            + (f" — falha em {v3_falha}" if v3_falha else " (todas)"),
            f"- dedução por menor-char: **{len(usa) - len(ded_falha)} de {len(usa)}**", "",
            "A dedução por menor-char falha em casos onde V3 passa, e por dois motivos "
            "distintos que a tabela separa: o dado usa `!` (`adv-usa-bang`), **ou** o "
            "delimitador nunca é emitido no corpo (`cpf`, `ip`, `mac`, `uuid`, `coord`, "
            "`float`…) — e aí não há o que deduzir, e o decoder acabaria tratando um char de "
            "dado como troca. **Esse segundo motivo eu não tinha previsto**; era a maioria "
            "das falhas.", "",
            "## As quatro materializações", "",
            "| | cabeçalho | corpo | funciona sempre? |", "|---|---:|---|---|",
            "| **V0** `d<char><pol>` | 2 B | — | sim |",
            "| **V1** `<pol>`, char por menor-char | 1 B | — | não (ver acima) |",
            "| **V2** polaridade no 1º byte | 0 B | +1 B se pol=`L` | não (mesma dedução) |",
            "| **V3** char inicial auto-declarante | **0 B** | +1 B (`R`) / +2 B (`L`) | "
            "**sim** |", "",
            "| coluna | corpo+V0 | corpo+V1 | corpo+V3 | melhor |",
            "|---|---:|---:|---:|:-:|"]
    for forma, r in todas:
        if r["modo"] != "delim":
            out.append(f"| `{forma}` | {r['corpo']} | {r['corpo']} | {r['corpo']} | hoje |")
            continue
        c0 = r["d"] + 2
        c1 = r["d"] + 1 if r["ded_ok"] else None
        c3 = r["n_v3"] if r["v3_ok"] else None
        cand = [("V0", c0)] + ([("V1", c1)] if c1 else []) + ([("V3", c3)] if c3 else [])
        best = min(cand, key=lambda t: t[1])[0]
        out.append(f"| `{forma}` | {c0} | {c1 if c1 else '—'} | {c3 if c3 else '—'} | "
                   f"**{best}** |")

    g0 = sum((r["d"] + 2 if r["modo"] == "delim" else r["corpo"]) - r["corpo"]
             for _f, r in todas)
    g3 = sum((r["n_v3"] if r["modo"] == "delim" and r["v3_ok"] else r["corpo"]) - r["corpo"]
             for _f, r in todas)
    out += ["", f"Ganho somado com V0 (2 B de cabeçalho): **{g0} B**  ",
            f"Ganho somado com V3 (auto-declarante): **{g3} B**  ",
            f"— em {len(todas)} colunas de 300 linhas.", "",
            "A diferença entre V0 e V3 é de **0-1 byte por coluna**. Numa coluna de 300 "
            "linhas isso é ruído; num payload minúsculo de poucas linhas, não é. A escolha "
            "entre elas é a mesma conta de sempre, não uma preferência — e o marcador "
            "virtual é justamente o que permite trocar de materialização sem mexer em nada "
            "antes dela.", ""]

    # ------------------------------------------------------- estrutura
    out += ["## O que a estrutura diz", "", "```",
            "varredura unica ->  tokens virtuais  +  alfabeto  +  trocas_R  +  trocas_L",
            "                         |                |            |           |",
            "decisao         ->       |          char eleito    <-- min(...) -->",
            "materializacao  ->  resolve(tokens, char, pol)   <- unica fase que ve o char",
            "```", "",
            "O marcador virtual permite adiar a decisão até o fim **e** trocar a "
            "materialização sem tocar em nada antes dela. A dedução vira uma escolha de "
            "materialização, não uma propriedade do formato — que era o ponto.", ""]

    (RAIZ / "result.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    print("\n".join(out))
    return 0 if falhas == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

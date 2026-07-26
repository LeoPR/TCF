"""Lab 2026-07-26-1853 — o DELIMITADOR DE POLARIDADE, proposta do owner.

    "no caso do  56\\033-\\0910-\\4383  não bastaria usar um  /56/033-0910-4383 ?
     aqui ele separa o 56 como ref, o que vier depois é literal. ainda simplificado
     56/033-0910-4383. e se alguma ref no meio: 56/033-09/10-4383 (…) é disso que falo
     como uma troca barata, rápida."

O delimitador não marca um valor — marca uma **troca de estado**. Custa por TRANSIÇÃO, não
por ocorrência. E, por estar *entre* as duas corridas, carrega também a FRONTEIRA, que era
exatamente o que faltava à máscara do lab `0330`.

As 8 formas do lab `0330` (mesma seed) + 2 que CONTÊM `/`, para exercer a escolha do char.

VALIDAÇÃO: reconstrói a grafia de HOJE byte a byte e passa pelo `decode` REAL do `src/tcf`.
O alvo da comparação é o corpo canônico e o dado original — não a inversa da transformação
(lição do lab `0038`, retratado por circularidade).
"""
import json
import pathlib
import sys

RAIZ = pathlib.Path(__file__).parent
REPO = RAIZ.parents[5]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(RAIZ))

from polaridade import (  # noqa: E402
    CANDIDATOS, custo_hoje, de_delim, ocorrencias, para_delim, plano, transicoes,
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
    """Idêntico ao lab 0330 — mesmas formas, mesma seed, para comparar direto."""
    g = _lcg(seed)
    if forma == "cpf":
        return [f"{i % 1000:03d}.{i * 7 % 1000:03d}.{i * 13 % 1000:03d}-{i % 100:02d}"
                for i in range(n)]
    if forma == "cartao":
        return ["-".join(f"{next(g) % 10000:04d}" for _ in range(4)) for _ in range(n)]
    if forma == "ip":
        return [".".join(str(next(g) % 256) for _ in range(4)) for _ in range(n)]
    if forma == "cep":
        return [f"{next(g) % 99999:05d}-{next(g) % 999:03d}" for _ in range(n)]
    if forma == "telefone":
        return [f"({next(g) % 90 + 10}) 9{next(g) % 10000:04d}-{next(g) % 10000:04d}"
                for _ in range(n)]
    if forma == "email":
        return [f"user{next(g) % 10000}@d{next(g) % 9}.com" for _ in range(n)]
    if forma == "data-iso":
        return [f"20{next(g) % 30 + 10}-{next(g) % 12 + 1:02d}-{next(g) % 28 + 1:02d}"
                for _ in range(n)]
    if forma == "texto":
        return [f"palavra{chr(97 + next(g) % 26)}" for _ in range(n)]
    # as duas abaixo CONTÊM `/` — existem para provar que o `min` troca de candidato
    if forma == "data-br":
        return [f"{next(g) % 28 + 1:02d}/{next(g) % 12 + 1:02d}/20{next(g) % 30 + 10}"
                for _ in range(n)]
    if forma == "cnpj-mascara":
        return [f"{next(g) % 100:02d}.{next(g) % 1000:03d}.{next(g) % 1000:03d}"
                f"/0001-{next(g) % 100:02d}" for _ in range(n)]
    raise ValueError(forma)


FORMAS = ["cpf", "cartao", "ip", "cep", "telefone", "data-iso", "email", "texto",
          "data-br", "cnpj-mascara"]


def _wj(p, obj, compacto=False):
    txt = json.dumps(obj, ensure_ascii=False,
                     separators=(",", ":") if compacto else (", ", ": "),
                     indent=None if compacto else 2)
    p.write_text(txt + ("" if compacto else "\n"), encoding="utf-8")
    return len(txt.encode())


def caso(forma, dados, gravar=True):
    corpo = _encode_column(dados)
    char, inicial, custo = plano(corpo)
    hoje = custo_hoje(corpo)

    corpo_d = para_delim(corpo, char, inicial)
    volta = de_delim(corpo_d, char, inicial)

    exato = volta == corpo                       # reconstruiu a grafia canônica byte a byte?
    wire = encode(dados)
    cab = wire.partition("\n")[0]
    rt = (decode(cab + "\n" + volta) == dados) if exato else False

    if gravar:
        _wj(RAIZ / "inputs" / f"{forma}-fonte.json",
            {"forma": forma, "n": len(dados), "amostra": dados[:4]})
        _wj(RAIZ / "intermediates" / f"{forma}-dataset-consumido.json", dados)
        (RAIZ / "outputs" / f"{forma}-wire-normal.tcf").write_text(wire, encoding="utf-8")
        (RAIZ / "outputs" / f"{forma}-wire-delim.tcfp").write_text(
            f"{cab}d{char}{inicial}\n{corpo_d}", encoding="utf-8")
        _wj(RAIZ / "outputs" / f"{forma}-dataset.roundtrip.json", decode(wire))
    return {"corpo": len(corpo.encode()), "d": len(corpo_d.encode()),
            "hoje": hoje, "custo": custo, "char": char, "inicial": inicial,
            "tR": transicoes(corpo, "R"), "tL": transicoes(corpo, "L"),
            "oc": ocorrencias(corpo, char), "rt": rt, "exato": exato}


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    out = ["# O delimitador de polaridade (2026-07-26-1853)", "",
           "O delimitador marca uma **troca de estado**, não um valor. Custa por "
           "**transição**, não por ocorrência — e, por estar *entre* as duas corridas, "
           "carrega também a **fronteira**.", "",
           "```",
           r"hoje       56\033-\0910-\4383      1 escape por LITERAL",
           "proposta   56/033-0910-4383        1 byte por TRANSIÇÃO",
           "```", "",
           "## Medição — as 8 formas do lab `0330` + 2 que contêm `/`", "",
           "`hoje` = escapes de dígito · `transições` por polaridade inicial · `char` e "
           "`início` são o `min` sobre candidatos × polaridade.", "",
           "| forma | corpo | hoje | transições (R) | transições (L) | char | início | custo | Δ corpo |",
           "|---|---:|---:|---:|---:|:-:|:-:|---:|---:|"]
    linhas, falhas = [], 0
    for forma in FORMAS:
        dados = gera(forma, 500 if forma != "cpf" else 200)
        r = caso(forma, dados)
        linhas.append((forma, r))
        falhas += (not r["rt"]) + (not r["exato"])
        out.append(f"| `{forma}` | {r['corpo']} | {r['hoje']} | {r['tR']} | {r['tL']} | "
                   f"`{r['char']}` | {r['inicial']} | {r['custo']} | "
                   f"{r['d'] - r['corpo']:+} |")

    ganho = sum(r["d"] - r["corpo"] for _f, r in linhas)
    out += ["", f"- reconstrução byte-exata da grafia canônica **e** RT pelo `decode` REAL: "
            f"**{2 * len(linhas) - falhas}/{2 * len(linhas)}**",
            f"- ganho somado nas {len(linhas)} formas: **{ganho} B**",
            f"- formas em que a proposta perde: "
            f"**{sum(1 for _f, r in linhas if r['d'] > r['corpo'])}**", ""]

    # ------------------------------------------------- comparação direta com o lab 0330
    out += ["## Contra a máscara (lab `0330`)", "",
            "A máscara cobria 3 de 8 formas — travava na **adjacência**, porque capturava só "
            "o TIPO e perdia a FRONTEIRA. O delimitador carrega as duas.", "",
            "| forma | escapes hoje | máscara (0330) | delimitador | quem vence |",
            "|---|---:|---|---:|---|"]
    MASCARA = {"cpf": 4, "ip": 4, "texto": 3, "cartao": None, "cep": None,
               "telefone": None, "data-iso": None, "email": None,
               "data-br": "nm", "cnpj-mascara": "nm"}     # "nm" = não medido no lab 0330
    for forma, r in linhas:
        m = MASCARA[forma]
        if m == "nm":
            out.append(f"| `{forma}` | {r['hoje']} | — (não estava no `0330`) | "
                       f"{r['custo']} | — |")
            continue
        ms = str(m) if m is not None else "n/a (adjacência)"
        if m is None:
            quem = "**delimitador**" if r["custo"] < r["hoje"] else "hoje"
        elif m < r["custo"]:
            quem = "máscara"
        elif m > r["custo"]:
            quem = "**delimitador**"
        else:
            quem = "empate"
        out.append(f"| `{forma}` | {r['hoje']} | {ms} | {r['custo']} | {quem} |")
    out += ["", "O `cpf` é o caso que motivou tudo: a coluna é **toda literal**, então "
            "começar em `L` custa **0 transições** — os 800 escapes somem por completo, sem "
            "canal separado e com a linha auto-contida.", ""]

    # ------------------------------------------------- é mais expressivo?
    out += ["## O delimitador é mais expressivo que o escape de hoje", "",
            "Hoje `literal` seguido de `referência` **não tem grafia**: `\\03356` lê tudo "
            "como um literal só. Com o delimitador tem — `/033/56`. Foi essa fronteira "
            "inexistente que travou a máscara e o flip.", "",
            "## Passo 5 — a escolha é online?", "",
            "```", "hoje        = corridas literais",
            "transicoes  = trocas de estado (por polaridade inicial, 2 contadores)",
            "ocorrencias = quantas vezes o char candidato já está no dado",
            "escolha     = min sobre (candidato x polaridade)", "```", "",
            "Todos são contadores da **mesma passada** que já percorre o corpo. Nenhuma "
            "forma é materializada para comparar.", "",
            f"Candidatos varridos: {', '.join('`' + c + '`' for c in CANDIDATOS)}. A tabela "
            "abaixo mostra por que o char não pode ser fixo:", "",
            "| forma | ocorrências no dado, por candidato |", "|---|---|"]
    for forma, _r in linhas:
        dados = gera(forma, 500 if forma != "cpf" else 200)
        corpo = _encode_column(dados)
        oc = " · ".join(f"`{c}`={ocorrencias(corpo, c)}" for c in CANDIDATOS)
        out.append(f"| {forma} | {oc} |")
    out += ["", "Onde o candidato aparece no dado, cada ocorrência passa a custar escape — "
            "por isso ele entra na conta e o `min` decide por coluna.", ""]

    # ------------------------------------------------- o seq-RLE
    from tcf.composicional.hcc_seqrle import find_escape_digit_runs
    quebras = 0
    for forma, r in linhas:
        dados = gera(forma, 500 if forma != "cpf" else 200)
        corpo = _encode_column(dados)
        volta = de_delim(para_delim(corpo, r["char"], r["inicial"]), r["char"], r["inicial"])
        for a, b in zip(corpo.split("\n"), volta.split("\n")):
            if a.startswith("*") and "|" in a and \
                    find_escape_digit_runs(a) != find_escape_digit_runs(b):
                quebras += 1
    out += ["## O seq-RLE", "",
            "Como no lab `0330`, o corpo canônico é **reconstruído** antes de qualquer "
            "coisa — o delimitador é camada de borda, o core não muda. Verificado com "
            "`find_escape_digit_runs` do próprio core: marcadores `*N±d|` com corridas "
            f"divergentes após reconstrução: **{quebras}**.", "",
            "**Aberto**: se o delimitador virar grafia canônica (e não camada de borda), o "
            "seq-RLE precisa localizar o dígito incrementável pela polaridade em vez de pelo "
            "escape. Não medido aqui.", ""]

    (RAIZ / "result.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    print("\n".join(out))
    return 0 if (falhas == 0 and quebras == 0) else 1


if __name__ == "__main__":
    sys.exit(main())

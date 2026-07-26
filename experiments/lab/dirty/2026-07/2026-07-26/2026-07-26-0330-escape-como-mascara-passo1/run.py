"""Lab 2026-07-26-0330 — PASSO 1: o escape como máscara, começando pelo CPF.

Owner: *"regras binárias não são estilo do TCF — a gente precisa sempre ter a função que
aborda todas, e usar a que usa menos. (…) pense na regra mais burra possível. (…) primeiro
achar uma regra que compense pra UM caso, vamos focar no CPF."*

E as etapas que ele pediu, nesta ordem:
  1. o que é POSSÍVEL
  2. como colocar em REGRA
  3. a regra é GENÉRICA?
  4. ela pode ser DINÂMICA (ligar/desligar, outros tipos)?
  5. ela pode ser ONLINE, com poucos loops?

Este lab cobre 1-3 com medição e ataca 4-5 com evidência parcial. **Nada soldado.**

O escape é a resposta a "literal ou referência?" em cada digit-run. Essa sequência é um
FLUXO — e fluxo é o que o formato já sabe comprimir. A máscara não é uma regra binária: ela
cobre qualquer mistura, e custa proporcional aos RUNS.

VALIDAÇÃO: reconstrução da máscara -> corpo NORMAL -> `decode` REAL. Como o escape é
RECONSTRUÍDO (e não apagado), isto não esbarra no bloqueador do seq-RLE que derrubou o flip
(lab `0038`) e o sem-escape (lab `0200`) — e o lab verifica isso explicitamente.
"""
import json
import pathlib
import sys

RAIZ = pathlib.Path(__file__).parent
REPO = RAIZ.parents[5]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(RAIZ))

from mascara import (  # noqa: E402
    adjacencias, custo_inline, custo_mascara, de_mascara, escolha, fluxo_decisoes,
    para_mascara,
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
    raise ValueError(forma)


FORMAS = ["cpf", "cartao", "ip", "cep", "telefone", "data-iso", "email", "texto"]


def _wj(p, obj, compacto=False):
    txt = json.dumps(obj, ensure_ascii=False,
                     separators=(",", ":") if compacto else (", ", ": "),
                     indent=None if compacto else 2)
    p.write_text(txt + ("" if compacto else "\n"), encoding="utf-8")
    return len(txt.encode())


def caso(forma, dados, gravar=True):
    corpo = _encode_column(dados)
    fluxo = fluxo_decisoes(corpo)
    adj = adjacencias(corpo)                    # fronteiras que a máscara não reconstrói
    sem, masc = para_mascara(corpo)
    volta = de_mascara(sem, masc)

    # VALIDAÇÃO: reconstrói e passa pelo decode REAL (não é `de(para())` circular — o alvo
    # da comparação é o dado ORIGINAL, via o parser do src/tcf)
    wire = encode(dados)
    cab = wire.partition("\n")[0]
    exato = volta == corpo                      # a reconstrução bate byte a byte?
    vale = adj == 0                             # a regra só se aplica sem adjacência
    rt = (decode(cab + "\n" + volta) == dados) if exato else False

    ci, cm = custo_inline(fluxo), custo_mascara(fluxo)
    total_masc = len(sem.encode()) + len(masc.encode()) + 1     # +1 do LF que separa
    if gravar:
        _wj(RAIZ / "inputs" / f"{forma}-fonte.json",
            {"forma": forma, "n": len(dados), "amostra": dados[:4]})
        _wj(RAIZ / "intermediates" / f"{forma}-dataset-consumido.json", dados)
        (RAIZ / "outputs" / f"{forma}-wire-normal.tcf").write_text(wire, encoding="utf-8")
        if vale:            # só materializa a proposta onde ela é reconstruível
            (RAIZ / "outputs" / f"{forma}-wire-mascara.tcfp").write_text(
                f"{cab}m\n{masc}\n{sem}", encoding="utf-8")
        else:
            (RAIZ / "outputs" / f"{forma}-NAO-APLICAVEL.txt").write_text(
                f"{adj} adjacencias — a mascara nao reconstroi a fronteira; usa-se o inline "
                f"de hoje ({forma}, n={len(dados)}).\n", encoding="utf-8")
        (RAIZ / "outputs" / f"{forma}-mascara.txt").write_text(masc + "\n", encoding="utf-8")
        _wj(RAIZ / "outputs" / f"{forma}-dataset.roundtrip.json", decode(wire))
    return {"corpo": len(corpo.encode()), "dec": len(fluxo), "L": fluxo.count("L"),
            "runs": sum(1 for i, c in enumerate(fluxo) if i == 0 or c != fluxo[i - 1]),
            "inline": ci, "masc": cm, "escolha": escolha(fluxo) if vale else "inline",
            "total": total_masc, "rt": rt, "exato": exato, "adj": adj, "vale": vale}


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    out = ["# O escape como máscara — passo 1 (2026-07-26-0330)", "",
           "O escape responde *literal ou referência?* em cada digit-run. Essa sequência é um "
           "**fluxo**, e fluxo o formato já comprime.", "",
           "`inline` = o que se paga hoje (1 B por literal) · `máscara` = o fluxo L/R com RLE "
           "burro (`<count><char>`). **Nenhuma é binária** — as duas cobrem qualquer mistura.",
           "", "## Passo 1 e 2 — o que é possível, e a regra", "",
           "A máscara só é **aplicável** onde nenhuma fronteira depende do escape "
           "(coluna `adjac.` = 0). Ver a seção do bloqueador.", "",
           "| forma | corpo | decisões | runs | adjac. | inline | máscara | escolha | Δ |",
           "|---|---:|---:|---:|---:|---:|---:|---|---:|"]
    linhas, falhas = [], 0
    for forma in FORMAS:
        dados = gera(forma, 500 if forma != "cpf" else 200)
        r = caso(forma, dados)
        linhas.append((forma, r))
        if r["vale"]:
            falhas += (not r["rt"]) + (not r["exato"])
        d = r["total"] - r["corpo"]
        out.append(f"| `{forma}` | {r['corpo']} | {r['dec']} | {r['runs']} | {r['adj']} | "
                   f"{r['inline']} | {r['masc']} | **{r['escolha']}** | "
                   f"{d if r['escolha'] == 'mascara' else 0:+} |")

    ganham = [(f, r) for f, r in linhas if r["escolha"] == "mascara"]
    aplic = [(f, r) for f, r in linhas if r["vale"]]
    out += ["", f"- aplicável (adjac. = 0) em **{len(aplic)} de {len(linhas)}** formas",
            f"- entre as aplicáveis, a máscara vence em **{len(ganham)}**",
            f"- reconstrução byte-exata **e** RT pelo `decode` REAL nas aplicáveis: "
            f"**{2 * len(aplic) - falhas}/{2 * len(aplic)}**",
            f"- ganho somado: **{sum(r['total'] - r['corpo'] for _f, r in ganham)} B**", "",
            "O **CPF é o caso que o owner pediu**: 800 decisões, **1 run** — a máscara inteira "
            "é `800L`, 4 bytes contra 800 de escape.", ""]

    # ---------------------------------------------------- passo 5: a decisão é ONLINE?
    out += ["## Passo 5 — a decisão pode ser online, com poucos loops?", "",
            "A escolha **não precisa materializar as duas formas**. Ela é uma conta:", "",
            "```", "adjacencias   = fronteiras que dependem do escape   (0 -> aplicável)",
            "custo_inline  = número de literais",
            "custo_mascara = comprimento do RLE do fluxo  (≈ 2 × runs)",
            "escolha       = o menor dos dois, se aplicável", "```", "",
            "Os **três** são contadores da mesma passada que já percorre o corpo: literais, "
            "trocas L↔R, e fronteiras dígito-encosta-dígito. Nenhum encode extra, nenhuma "
            "forma materializada para comparar.", "",
            "| forma | literais | runs | adjac. | decisão pela conta | medindo os bytes | bate? |",
            "|---|---:|---:|---:|---|---|---|"]
    for forma, r in linhas:
        medida = "mascara" if (r["vale"] and r["total"] < r["corpo"]) else "inline"
        out.append(f"| {forma} | {r['L']} | {r['runs']} | {r['adj']} | {r['escolha']} | "
                   f"{medida} | {'sim' if r['escolha'] == medida else '**NÃO**'} |")
    diverge = [f for f, r in linhas
               if r["escolha"] != ("mascara" if (r["vale"] and r["total"] < r["corpo"])
                                   else "inline")]
    out += ["", f"Divergências entre a conta e a medição: **{len(diverge)}**"
            + (f" — {diverge}" if diverge else " (a conta acerta em todas)."), ""]

    # ---------------------------------------------------- passo 3: genérica?
    out += ["## Passo 3 — a regra é genérica?", "",
            "Ela não conhece CPF, nem tipo, nem formato — só conta literais, trocas e "
            "adjacências. Aplica-se a qualquer coluna, e onde não compensa (ou não é "
            "reconstruível) ela **escolhe o inline**, que é o comportamento de hoje: custo "
            "zero de adoção, nenhum caso de código exclusivo.", "",
            "Genérica sim; **larga não**: pega 2 de 8 formas aqui. O que a limita não é a "
            "conta, é a adjacência.", "",
            "## Passo 4 — dinâmica?", "",
            "Sim por construção: a escolha é por coluna, computada do próprio dado. Um flag no "
            "cabeçalho diz qual forma foi usada. Ligar/desligar é forçar a escolha.", "",
            "**Não testado ainda**: outros tipos (a máscara é sobre digit-runs; um fluxo "
            "análogo existiria para `*`/`~` se algum dia eles pesarem — hoje são 0).", ""]

    # ---------------------------------------------------- o bloqueador dos labs anteriores
    from tcf.composicional.hcc_seqrle import find_escape_digit_runs
    quebras = 0
    for forma, r in linhas:
        if not r["vale"]:
            continue
        dados = gera(forma, 500 if forma != "cpf" else 200)
        corpo = _encode_column(dados)
        volta = de_mascara(*para_mascara(corpo))
        for a, b in zip(corpo.split("\n"), volta.split("\n")):
            if a.startswith("*") and "|" in a and find_escape_digit_runs(a) != find_escape_digit_runs(b):
                quebras += 1
    out += ["## O bloqueador — terceira aparição, e desta vez ele tem nome", "",
            "O seq-RLE **não** é o problema aqui: flip (lab `0038`) e sem-escape (lab `0200`) "
            "**apagavam** o escape, e o marcador `*N±d|` localiza o dígito incrementável *pelo "
            "escape*. A máscara **reconstrói** o escape antes de tudo — é camada de borda, o "
            "core não muda. Verificado: marcadores com corridas divergentes após reconstrução "
            f"nas colunas aplicáveis: **{quebras}**.", "",
            "O que trava é outra coisa, e é a mesma dos dois labs anteriores vista de frente:",
            "", "> O escape carrega **duas** informações — o **tipo** (literal × referência) e "
            "a **fronteira** entre corridas de dígito. A máscara captura só o tipo.", "",
            "Onde uma referência encosta num literal-dígito, tirar o escape **funde** as duas "
            "corridas e nenhuma máscara reconstrói isso:", "", "```",
            r"original   56\033-\0910      (`56` = referência, `033` = literal)",
            "sem escape 56033-0910         <- `56` e `033` fundiram",
            r"volta      56033-\0910       <- fronteira perdida, corpo diferente", "```", "",
            "| forma | adjacências |", "|---|---:|"]
    for forma, r in linhas:
        out.append(f"| {forma} | {r['adj']} |")
    out += ["", "**É por isso que a regra precisa do contador de adjacência** — sem ele o "
            "`cartao` daria −1895 B e um wire corrompido. Com ele, a regra recusa sozinha, e "
            "recusar é escolher o inline de hoje: custo zero.", "",
            "Próximo passo natural (não medido): um **delimitador de fronteira** mais barato "
            "que o escape, pago só nas adjacências — no `cartao` seriam 39 contra 2000.", ""]

    (RAIZ / "result.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    print("\n".join(out))
    return 0 if (falhas == 0 and quebras == 0) else 1


if __name__ == "__main__":
    sys.exit(main())

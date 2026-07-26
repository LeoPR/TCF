"""Lab 2026-07-26-0038 — o delimitador do flip, com as variantes MATERIALIZADAS.

Correção do owner sobre a 1ª rodada: *"mas ganho do que exatamente, as pastas não têm as
variações, sem cabeçalho nem nada. elas ficaram em sua imaginação. preciso de evidências."*

Estava certo — a 1ª rodada estimava (`ganho − contagem × 1 B`) e só gravava o corpo NORMAL.
Agora as três formas são **construídas, gravadas com cabeçalho e round-trip-adas**:

    NORMAL   `\\168116` = literal   ·  `1`    = referência           (o de hoje)
    FLIP-A   `168116`   = literal   ·  `\\1`   = referência, delimitador SÓ na adjacência
    FLIP-B   `168116`   = literal   ·  `\\1;`  = referência SEMPRE terminada

Delimitador `;` é **placeholder** (da lista de zero-ocorrência) — a escolha do char é do owner.

CUSTO DE CABEÇALHO, que a 1ª rodada ignorou: o flag de polaridade mora no char de MODO
(índice 7), que só existe **depois de uma tag**. Então:
  - coluna de NÚMERO já tem a tag `n` -> o flag entra no modo: **+1 B**
  - coluna de STRING é implícita (`#TCF.8`) -> flipar exige torná-la explícita
    (`#TCF.8s` + flag): **+2 B**

RT: cada wire flipado é decodificado de volta (des-flipa -> corpo normal -> `decode` REAL).
"""
import json
import pathlib
import sys

RAIZ = pathlib.Path(__file__).parent
REPO = RAIZ.parents[5]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(RAIZ))

from polaridade import DELIM, corpo_de_flip, corpo_para_flip  # noqa: E402

from tcf import decode, encode  # noqa: E402
from tcf.encoder import _encode_column  # noqa: E402

FLAG = "f"                       # placeholder do flag de polaridade no char de MODO

for d in ("inputs", "intermediates", "outputs"):
    (RAIZ / d).mkdir(exist_ok=True)


def _lcg(seed):
    x = seed
    while True:
        x = (1103515245 * x + 12345) % (2 ** 31)
        yield x


def gera(forma, n, seed=7):
    g = _lcg(seed)
    if forma == "int-ruido":
        return [next(g) % 10 ** 6 for _ in range(n)]
    if forma == "int-seq":
        return list(range(n))
    if forma == "hex":
        return [f"{next(g) % 16 ** 8:08x}" for _ in range(n)]
    if forma == "data-br":
        return [f"{next(g) % 28 + 1:02d}/{next(g) % 12 + 1:02d}/20{next(g) % 30 + 10}"
                for _ in range(n)]
    if forma == "telefone":
        return [f"({next(g) % 90 + 10}) 9{next(g) % 10000:04d}-{next(g) % 10000:04d}"
                for _ in range(n)]
    if forma == "moeda":
        return [f"R$ {next(g) % 10000}.{next(g) % 100:02d}" for _ in range(n)]
    if forma == "versao":
        return [f"{next(g) % 9}.{next(g) % 20}.{next(g) % 50}" for _ in range(n)]
    if forma == "email":
        return [f"user{next(g) % 10000}@d{next(g) % 9}.com" for _ in range(n)]
    if forma == "url":
        return [f"https://site{next(g) % 99}.com/p?id={next(g) % 9999}" for _ in range(n)]
    if forma == "path":
        return [f"/var/log/app{next(g) % 99}/{next(g) % 999}.log" for _ in range(n)]
    if forma == "json-ish":
        return [f'{{"id":{next(g) % 9999},"ok":true}}' for _ in range(n)]
    if forma == "com-delim":
        return [f"a{DELIM}b{next(g) % 999}{DELIM}c" for _ in range(n)]
    raise ValueError(forma)


FORMAS = ["int-ruido", "int-seq", "hex", "data-br", "telefone", "moeda", "versao",
          "email", "url", "path", "json-ish", "com-delim"]


def _wj(p, obj, compacto=False):
    txt = json.dumps(obj, ensure_ascii=False,
                     separators=(",", ":") if compacto else (", ", ": "),
                     indent=None if compacto else 2)
    p.write_text(txt + ("" if compacto else "\n"), encoding="utf-8")
    return len(txt.encode())


def caso(forma, dados):
    """Materializa as TRÊS formas com cabeçalho e valida o RT de cada uma."""
    wire_real = encode(dados)                       # o wire de HOJE, do src/tcf
    cab_real, _sep, _corpo = wire_real.partition("\n")
    tem_tag = len(cab_real) > 6                     # '#TCF.8n' tem tag; '#TCF.8' não

    corpo = _encode_column([str(v) for v in dados])
    corpo_a = corpo_para_flip(corpo, sempre=False)
    corpo_b = corpo_para_flip(corpo, sempre=True)

    # cabeçalho flipado: o flag entra no MODO, que exige uma tag antes.
    cab_flip = (cab_real + FLAG) if tem_tag else ("#TCF.8s" + FLAG)

    wires = {
        "normal": cab_real + "\n" + corpo,
        "flipA": cab_flip + "\n" + corpo_a,
        "flipB": cab_flip + "\n" + corpo_b,
    }
    # RT: des-flipa o corpo, remonta o wire NORMAL e decoda com o `decode` REAL
    rt = {"normal": decode(wires["normal"]) == dados}
    for nome, sempre in (("flipA", False), ("flipB", True)):
        corpo_volta = corpo_de_flip(wires[nome].partition("\n")[2], sempre)
        rt[nome] = decode(cab_real + "\n" + corpo_volta) == dados
    return wires, rt, tem_tag


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    linhas, falhas = [], 0
    for forma in FORMAS:
        dados = gera(forma, 500)
        _wj(RAIZ / "inputs" / f"{forma}-fonte.json",
            {"forma": forma, "n": len(dados), "amostra": dados[:5]})
        _wj(RAIZ / "intermediates" / f"{forma}-dataset-consumido.json", dados)
        nj = _wj(RAIZ / "outputs" / f"{forma}-equivalente.json", dados, compacto=True)

        wires, rt, tem_tag = caso(forma, dados)
        (RAIZ / "outputs" / f"{forma}-wire-normal.tcf").write_text(
            wires["normal"], encoding="utf-8")
        for nome in ("flipA", "flipB"):
            (RAIZ / "outputs" / f"{forma}-wire-{nome}.tcfp").write_text(
                wires[nome], encoding="utf-8")
        _wj(RAIZ / "outputs" / f"{forma}-dataset.roundtrip.json", decode(wires["normal"]))

        b = {k: len(v.encode()) for k, v in wires.items()}
        falhas += sum(not v for v in rt.values())
        linhas.append((forma, "n" if tem_tag else "s", nj, b, rt))

    out = ["# O delimitador do flip — variantes MATERIALIZADAS (2026-07-26-0038)", "",
           "Correção da 1ª rodada: os ganhos eram **estimativa** (`ganho − contagem × 1 B`) e "
           "só o corpo NORMAL ia pra pasta. Agora as três formas são construídas, gravadas "
           "**com cabeçalho** e round-trip-adas.", "",
           "`normal` = wire REAL de hoje · `flipA` = delimitador só na adjacência · "
           "`flipB` = toda referência terminada. Delimitador `;` é **placeholder**.", "",
           "**Bytes do wire INTEIRO** (cabeçalho + corpo), n=500:", "",
           "| forma | tag | JSON | normal | flipA | Δ A | flipB | Δ B | RT |",
           "|---|---|---:|---:|---:|---:|---:|---:|---|"]
    for forma, tag, nj, b, rt in linhas:
        ok = "OK" if all(rt.values()) else "FALHOU"
        out.append(f"| `{forma}` | `{tag}` | {nj} | {b['normal']} | {b['flipA']} | "
                   f"**{b['flipA'] - b['normal']:+}** | {b['flipB']} | "
                   f"**{b['flipB'] - b['normal']:+}** | {ok} |")

    ga = [b["flipA"] - b["normal"] for _f, _t, _j, b, _r in linhas]
    gb = [b["flipB"] - b["normal"] for _f, _t, _j, b, _r in linhas]
    out += ["", f"RT: **{3 * len(linhas) - falhas}/{3 * len(linhas)}** "
                "(as três formas de cada coluna decodam para o dado original).", "",
            f"- **flipA** ganha em {sum(1 for x in ga if x < 0)} de {len(ga)} colunas; "
            f"soma onde ganha **{sum(x for x in ga if x < 0)} B**, "
            f"perde **+{sum(x for x in ga if x > 0)} B** onde perde",
            f"- **flipB** ganha em {sum(1 for x in gb if x < 0)} de {len(gb)}; "
            f"soma onde ganha **{sum(x for x in gb if x < 0)} B**, "
            f"perde **+{sum(x for x in gb if x > 0)} B**", "",
            "O `min(normal, flipA, flipB)` por coluna nunca emite o pior — as linhas positivas "
            "seriam simplesmente descartadas, como já acontece no FLOOR do seq-RLE.", ""]

    out += ["## Custo de cabeçalho (o que a 1ª rodada ignorou)", "",
            "O flag de polaridade mora no char de **modo** (índice 7), que só existe **depois "
            "de uma tag**:", "",
            "| tipo | cabeçalho hoje | com flag | custo |", "|---|---|---|---:|",
            "| número | `#TCF.8n` | `#TCF.8n" + FLAG + "` | **+1 B** |",
            "| string | `#TCF.8` (implícita) | `#TCF.8s" + FLAG + "` | **+2 B** |", "",
            "Flipar uma coluna de string **força torná-la explícita** — a tag `s`, que hoje o "
            "encoder nunca emite, passaria a aparecer. É consequência de desenho, não custo "
            "escondido: já está somado nos números da tabela acima.", ""]

    out += ["## Amostra — as três formas lado a lado", "", "```"]
    for forma in ("int-ruido", "data-br", "email", "com-delim"):
        dados = gera(forma, 500)
        wires, _rt, _t = caso(forma, dados)
        out.append(f"--- {forma}")
        for nome in ("normal", "flipA", "flipB"):
            prim = wires[nome].split("\n")[1] if "\n" in wires[nome] else ""
            out.append(f"  {nome:7} {wires[nome].split(chr(10))[0]!r} + {prim[:38]!r}")
    out += ["```", "",
            "`com-delim` existe para exercitar o caso em que o **delimitador aparece no dado**: "
            "em FLIP o `;` vira estrutural e o literal precisa de escape (`\\;`). O RT dessa "
            "coluna é a prova de que o esquema aguenta o próprio delimitador.", ""]

    (RAIZ / "result.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    print("\n".join(out))
    return 0 if falhas == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

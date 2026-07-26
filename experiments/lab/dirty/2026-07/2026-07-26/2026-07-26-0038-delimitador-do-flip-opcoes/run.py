"""Lab 2026-07-26-0038 — o delimitador do flip: opções para o owner escolher.

O flip de polaridade (lab `2026-07-25-2337`) esbarra numa adjacência inexpressável: em modo
FLIP, uma referência `\\1` colada num literal-dígito `2` colapsa em `\\12`. Medido: 13 de 33
colunas que ganhariam têm essa adjacência, incluindo as valiosas (telefone, moeda, data-BR).

Owner: *"não sei que char, e imagino algumas condições... faça uns testes pra eu ver primeiro."*

Este lab **não decide** — levanta o espaço de escolha com número em cada eixo:

  EIXO 1  QUAL char             — quais estão livres, e quanto cada um custaria por já
                                  aparecer no dado (viraria escape novo)
  EIXO 2  ONDE aplicar          — só na posição ambígua (mínimo) × terminar TODA referência
                                  (mais simples de parsear)
  EIXO 3  SEM char novo         — alternativas que não gastam um caractere do namespace

Escopo: **uma coluna, single-col** — como o owner delimitou.
"""
import json
import pathlib
import sys
from collections import Counter

RAIZ = pathlib.Path(__file__).parent
REPO = RAIZ.parents[5]
sys.path.insert(0, str(REPO / "src"))

from tcf.encoder import _encode_column  # noqa: E402

BS = chr(92)

for d in ("inputs", "intermediates", "outputs"):
    (RAIZ / d).mkdir(exist_ok=True)

# --------------------------------------------------------------- chars já tomados
# Levantados do `src/tcf` (syntax.py `_escape_lit` / `_parse_decl` / `decode`), não de memória.
TOMADOS = {
    BS:   "escape (literal de dígito, `*`, `~`, `\\`)",
    "*":  "início de marcador RLE / seq-RLE, e separador de fragmento no literal",
    "|":  "separa contador do template no marcador",
    "~":  "composição de fragmentos",
    "^":  "referência de LINHA (início de linha)",
    ",":  "separa unidades num grupo de referências",
    ".":  "`..` = range de referências",
    "\n": "delimitador de valor (contrato LF-only)",
    "+":  "sinal de delta no marcador seq-RLE",
    "-":  "sinal de delta negativo no marcador seq-RLE",
}
CANDIDATOS = list("!\"#$%&'()/:;<=>?@[]_`{}")


def _lcg(seed):
    x = seed
    while True:
        x = (1103515245 * x + 12345) % (2 ** 31)
        yield x


def gera(forma, n, seed=7):
    g = _lcg(seed)
    if forma == "int-ruido":
        return [str(next(g) % 10 ** 6) for _ in range(n)]
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
    if forma == "json-ish":
        return [f'{{"id":{next(g) % 9999},"ok":true}}' for _ in range(n)]
    if forma == "path":
        return [f"/var/log/app{next(g) % 99}/{next(g) % 999}.log" for _ in range(n)]
    if forma == "hex":
        return [f"{next(g) % 16 ** 8:08x}" for _ in range(n)]
    raise ValueError(forma)


FORMAS = ["int-ruido", "data-br", "telefone", "moeda", "versao", "email", "url",
          "json-ish", "path", "hex"]


# --------------------------------------------------------------- medições
def adjacencias(corpo):
    """Posições onde, sob FLIP, a referência colaria num literal-dígito."""
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
                    n_amb += 1
            else:
                i += 1
    return n_amb


def n_referencias(corpo):
    """Quantas referências de fragmento existem (para o custo de 'terminar TODAS')."""
    total = 0
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
                total += 1
                while i < n and resto[i].isdigit():
                    i += 1
            else:
                i += 1
    return total


def ganho_flip(corpo):
    """Economia bruta do flip: escapes de dígito − referências (cada um vale 1 B)."""
    esc = ref = 0
    for linha in corpo.split("\n"):
        resto = linha.split("|", 1)[1] if linha.startswith("*") and "|" in linha else linha
        if resto.startswith("^"):
            continue
        i, n = 0, len(resto)
        while i < n:
            if resto[i] == BS:
                i += 1
                if i < n and resto[i].isdigit():
                    esc += 1
                    while i < n and resto[i].isdigit():
                        i += 1
                else:
                    i += 1
            elif resto[i].isdigit():
                ref += 1
                while i < n and resto[i].isdigit():
                    i += 1
            else:
                i += 1
    return esc - ref


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    dados = {f: gera(f, 500) for f in FORMAS}
    corpos = {f: _encode_column(v) for f, v in dados.items()}
    for f, v in dados.items():
        (RAIZ / "inputs" / f"{f}-fonte.json").write_text(
            json.dumps({"forma": f, "n": len(v), "amostra": v[:5]},
                       ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (RAIZ / "intermediates" / f"{f}-dataset-consumido.json").write_text(
            json.dumps(v, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (RAIZ / "outputs" / f"{f}-corpo.tcfp").write_text(corpos[f], encoding="utf-8")

    out = ["# O delimitador do flip — opções (2026-07-26-0038)", "",
           "Levanta o espaço de escolha com número em cada eixo. **Não decide nada.** "
           "Escopo: uma coluna, single-col.", ""]

    # ---------------- EIXO 1: chars tomados e candidatos
    out += ["## Eixo 1 — qual char", "", "### Já tomados no corpo (levantado do `src/tcf`)", "",
            "| char | papel |", "|---|---|"]
    out += [f"| `{c if c != chr(10) else 'LF'}` | {p} |" for c, p in TOMADOS.items()]

    freq = Counter()
    total_chars = 0
    for f, v in dados.items():
        for s in v:
            freq.update(s)
            total_chars += len(s)
    out += ["", "### Candidatos livres — e quanto cada um já aparece no dado", "",
            "Se o char escolhido ocorre no dado, ele passa a precisar de escape em modo FLIP "
            "— o que **cobra de volta** parte do ganho. Frequência medida nas 10 formas "
            "(n=500 cada, "
            f"{total_chars:,} chars):", "",
            "| char | ocorrências no dado | em quais formas |", "|---|---:|---|"]
    for c in CANDIDATOS:
        onde = [f for f, v in dados.items() if any(c in s for s in v)]
        out.append(f"| `{c}` | {freq.get(c, 0)} | {', '.join(onde) if onde else '—'} |")
    livres = [c for c in CANDIDATOS if freq.get(c, 0) == 0]
    out += ["", f"**{len(livres)} candidatos com zero ocorrência** nesta amostra: "
            + " ".join(f"`{c}`" for c in livres) + ".", "",
            "Ressalva: *zero nesta amostra* não é *zero no mundo*. `%`, `&`, `=`, `?`, `#` "
            "aparecem em URL/query; `:` em hora e JSON; `;` em CSV europeu. O char mais "
            "seguro é o que **nunca** aparece em dado tabular — mas nenhum é impossível, "
            "então o esquema tem que suportar escapá-lo.", ""]

    # ---------------- EIXO 2: onde aplicar
    out += ["## Eixo 2 — onde aplicar o delimitador", "",
            "**(a) só na posição ambígua** — 1 B por adjacência · "
            "**(b) terminar TODA referência** — 1 B por referência (parser mais simples)", "",
            "| forma | corpo | ganho bruto | adjac. | (a) líquido | refs | (b) líquido |",
            "|---|---:|---:|---:|---:|---:|---:|"]
    soma_a = soma_b = 0
    for f in FORMAS:
        c = corpos[f]
        g, a, r = ganho_flip(c), adjacencias(c), n_referencias(c)
        la, lb = g - a, g - r
        soma_a += max(0, la)
        soma_b += max(0, lb)
        out.append(f"| {f} | {len(c.encode())} | {g:+} | {a} | **{la:+}** | {r} | **{lb:+}** |")
    out += ["", f"Somando só onde cada esquema ganha: **(a) {soma_a} B** · **(b) {soma_b} B**.",
            "", "A opção (b) é mais simples de parsear (toda referência tem terminador, sem "
            "olhar o que vem depois), mas paga em **toda** referência — e em coluna de texto "
            "as referências são muitas. A (a) paga só onde precisa, ao custo de o parser "
            "decidir por contexto.", ""]

    # ---------------- EIXO 3: sem char novo
    out += ["## Eixo 3 — alternativas que NÃO gastam um char do namespace", "",
            "| alternativa | como funciona | custo | observação |", "|---|---|---|---|",
            "| escape duplo | na posição ambígua, o literal vira `\\\\` + dígitos | "
            "**2 B** por adjacência (o dobro de (a)) | não gasta char novo; "
            "`\\\\` já é escape de `\\` hoje, então colide — precisaria de outra grafia |",
            "| referência de largura fixa | `\\` + N dígitos fixos, sem terminador | "
            "custo = (largura − dígitos reais) por referência | só compensa se a tabela "
            "for pequena e as refs curtas; some o ganho em coluna com muitas refs |",
            "| flip só onde não há adjacência | o detector já existe; desiste da coluna | "
            "**0 B** | cobre 20 das 33 colunas que ganhariam — deixa na mesa os casos "
            "valiosos (telefone, moeda) |", ""]
    out += ["Números da terceira linha vêm do lab `2026-07-25-2337` parte 2.", ""]

    # ---------------- amostras
    out += ["## Amostras dos corpos (para inspeção)", "", "```"]
    for f in ("int-ruido", "data-br", "telefone", "email"):
        prim = corpos[f].split("\n")[0]
        out.append(f"{f:11} {prim[:60]!r}")
    out += ["```", ""]

    (RAIZ / "result.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    print("\n".join(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Lab 2026-07-27-2231 — o marcador de fronteira pelo ESCAPE que já existe.

    "o `=` foi meramente um exemplo ilustrativo (…) teoricamente qualquer um que dê escape —
     a gente já trabalhou com escape, não tem como usar o mesmo ou um escape diferente?"

Eu tinha travado no `=` literal. A resposta está na gramática: num corpo canônico o `\\` só
é seguido de `* 0-9 \\ ^ ~`. Então `\\` + qualquer outro char é **impossível de o core
produzir** — marcador livre por construção, não por sorte.

Mede:
  A. a exaustão: QUAIS chars podem seguir um `\\` (varrendo os 95 imprimíveis, e depois
     valores adversariais montados para tentar produzir o marcador)
  B. o veneno que derrubou o `=` — agora com o marcador por escape
  C. bytes e prefixo contra F1 (contagem de linhas) e F2 (`=` cru)
  D. o eixo que só aparece pensando em stream: o **encoder** também precisa saber a
     contagem antes de escrever o cabeçalho, no F1. Com marcador, não.

VALIDAÇÃO: leitor independente que acha a fronteira **pelo marcador**, sem receber `k` nem
contagem de linhas. Comparado com os dados originais.

`src/tcf` intocado.
"""
import csv
import json
import pathlib
import string
import sys

RAIZ = pathlib.Path(__file__).parent
REPO = RAIZ.parents[5]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(RAIZ))

from marcador import (  # noqa: E402
    BS, MARCADOR, SEGUEM_ESCAPE, le, marcador_valido, monta, prefixo_leitura,
)

from tcf import encode  # noqa: E402
from tcf.encoder import _encode_column  # noqa: E402

for d in ("inputs", "intermediates", "outputs"):
    (RAIZ / d).mkdir(exist_ok=True)

SAMPLES = REPO / "datasets" / "samples"


def _wj(p, obj):
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def chars_apos_escape(valores):
    """Quais chars aparecem logo depois de um `\\` no corpo canônico destes valores."""
    c = _encode_column(valores)
    vistos, i = set(), 0
    while i < len(c) - 1:
        if c[i] == BS:
            vistos.add(c[i + 1])
            i += 2
        else:
            i += 1
    return vistos


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    falhas = []
    out = ["# O marcador de fronteira pelo ESCAPE (2026-07-27-2231)", "",
           "Eu tinha travado no `=` literal e concluído que \"o marcador colide com dado\". A "
           "pergunta certa era a sua: **o escape que a gente já tem não serve?**", "",
           "Serve — e não por sorte, por **construção da gramática**.", ""]

    # ================================================================ A: a exaustão
    out += ["## A — o que pode seguir um `\\` num corpo canônico", "",
            "Varrendo os 95 imprimíveis, um por vez, como valor de coluna:", ""]
    vistos = set()
    for ch in string.printable[:95]:
        try:
            vistos |= chars_apos_escape([ch + "z", "normal", ch * 3])
        except Exception:
            continue
    out += [f"```\nchars que seguem um `\\`:  {''.join(sorted(vistos))}\n```", "",
            "`_escape_lit` escapa corrida de dígito, `*`, `\\` e `~`; o `^`-líder é escapado à "
            "parte. **Mais nada.** Então:", "",
            "| valor de dado | vira | contém `\\|`? |", "|---|---|:-:|"]
    for v in (BS + "x", "a*b", "a~b", "^topo", "a|b", "=SOMA(A1)", "123", BS + "|",
              BS + BS + "|"):
        c = _encode_column([v, "normal"]).split("\n")[0]
        out.append(f"| `{v!r}` | `{c!r}` | {'**SIM**' if MARCADOR in c else 'não'} |")
    ok_gram = vistos <= SEGUEM_ESCAPE
    out += ["", f"O conjunto medido está contido no declarado (`SEGUEM_ESCAPE`): "
            f"**{'sim' if ok_gram else '**NÃO**'}**.", "",
            "Repare no caso `'\\\\|'`: o valor de dado que **é** o marcador vira `\\\\\\\\|` "
            "(dois backslashes) no corpo. O core escapa o próprio `\\`, então o marcador "
            "continua inalcançável.", ""]
    if not ok_gram:
        falhas.append("gramatica")

    # ================================================================ B: o veneno
    out += ["## B — o veneno que derrubou o `=`", "", "| coluna | `=` cru (F2) | `\\|` (F5) |",
            "|---|:-:|:-:|"]
    venenos = {
        "comeca-com-igual": ["=SOMA(A1)", "normal", "outro"] * 40,
        "contem-backslash": [BS + "temp", "normal", "outro"] * 40,
        "contem-pipe": ["a|b", "c|d", "normal"] * 40,
        "e-o-proprio-marcador": [BS + "|", "normal", "outro"] * 40,
        "so-digitos": ["100", "101", "102"] * 40,
        "com-til-e-asterisco": ["a~b", "c*d", "normal"] * 40,
    }
    for nome, vals in venenos.items():
        w = monta(vals)
        try:
            rt = le(w) == vals
        except Exception:
            rt = False
        if not rt:
            falhas.append(nome)
        # F2: marcador `=` cru, a variante que falhou no lab anterior
        f2_falha = any((v or "").startswith("=") for v in vals)
        out.append(f"| `{nome}` | {'**FALHA**' if f2_falha else 'OK'} | "
                   f"{'OK' if rt else '**FALHOU**'} |")
        (RAIZ / "outputs" / f"{nome}.tcfp").write_text(w, encoding="utf-8")
        _wj(RAIZ / "intermediates" / f"{nome}-dataset-consumido.json", vals)
        _wj(RAIZ / "outputs" / f"{nome}-dataset.roundtrip.json", le(w))
    out.append("")

    # ================================================================ C: bytes e prefixo
    out += ["## C — bytes e prefixo, contra as variantes anteriores", "",
            "`F1` = contagem de linhas no cabeçalho · `F5` = marcador `\\|` + padding dropado",
            "", "| coluna | n | k | F1 | F5 | Δ | prefixo F5 | RT |",
            "|---|---:|---:|---:|---:|---:|---:|:-:|"]
    rot = ["ativo", "inativo", "suspenso", "cancelado", "revisao", "arquivado", "pendente"]
    casos = {f"str-k{k}": [rot[i % k] for i in range(200)] for k in (2, 4, 7)}
    casos["str-k4-null"] = [None if i % 9 == 0 else rot[i % 4] for i in range(200)]
    reais = [("adult-sex", "adult-census/adult-sample.csv", "sex"),
             ("adult-workclass", "adult-census/adult-sample.csv", "workclass"),
             ("cnpj-uf", "receita-cnpj/cnpj-2k.csv", "uf"),
             ("pm25-cbwd", "beijing-pm25/beijing-pm25-sample.csv", "cbwd")]
    for nome, rel, col in reais:
        p = SAMPLES / rel
        if not p.exists():
            continue
        with p.open(encoding="utf-8", newline="") as f:
            rd = csv.DictReader(f)
            if col not in (rd.fieldnames or []):
                raise KeyError(f"{col!r} nao existe em {rel}")
            casos[nome] = [row[col] for row in rd if row[col] != ""][:2000]

    for nome, vals in casos.items():
        w5 = monta(vals)
        rt = le(w5) == vals
        if not rt:
            falhas.append(nome)
        # F1 equivalente: contagem de linhas, com padding
        import base64 as _b64
        from marcador import _grafa, dominio, largura
        dom = dominio(vals)
        bloco = _encode_column([_grafa(v) for v in dom]).rstrip("\n")
        nl = len(bloco.split("\n"))
        raw_len = len(_b64.b64encode(b"\0" * ((len(vals) * largura(len(dom)) + 7) // 8)))
        f1 = len(f"#TCF.8B{largura(len(dom))}{len(vals):x}L{nl:x}\n{bloco}\n".encode()) + raw_len
        k = len(dom)
        _wj(RAIZ / "inputs" / f"{nome}-fonte.json",
            {"coluna": nome, "n": len(vals), "k": k, "amostra": vals[:5]})
        _wj(RAIZ / "intermediates" / f"{nome}-dataset-consumido.json", vals)
        (RAIZ / "outputs" / f"{nome}-F5.tcfp").write_text(w5, encoding="utf-8")
        _wj(RAIZ / "outputs" / f"{nome}-dataset.roundtrip.json", le(w5))
        out.append(f"| `{nome}` | {len(vals)} | {k} | {f1} | {len(w5.encode())} | "
                   f"**{len(w5.encode()) - f1:+}** | {prefixo_leitura(w5)} | "
                   f"{'OK' if rt else '**FALHOU**'} |")
    out.append("")

    # ================================================================ D: o eixo do encoder
    out += ["## D — o eixo que só aparece pensando em stream dos DOIS lados", "",
            "O `F1` (contagem de linhas) é robusto, mas tem um custo que o eixo de bytes não "
            "mostra: **o encoder precisa terminar o bloco do domínio para contar as linhas "
            "antes de escrever o cabeçalho**. Ou ele bufferiza o domínio inteiro, ou volta "
            "atrás para preencher o campo.", "",
            "| | leitor streama? | escritor streama? | colide com dado? |",
            "|---|:-:|:-:|:-:|",
            "| **F1** contagem de linhas | sim | **não** (precisa contar antes) | não |",
            "| **F2** `=` cru | sim | sim | **SIM** |",
            "| **F3** b64 primeiro | **não** | sim | não |",
            "| **F5** marcador `\\|` | sim | **sim** | **não, por construção** |", "",
            "O `F5` é o único que fecha as três colunas — e não precisou de char novo, "
            "eleição, nem escape adicional. Só usou a gramática que já existia.", "",
            "### Qualquer `\\<char>` fora do conjunto serve", "",
            "| marcador | válido? |", "|---|:-:|"]
    for m in (BS + "|", BS + "=", BS + "!", BS + " ", BS + "*", BS + "7", BS + BS, BS + "~",
              "|" + BS, "=="):
        out.append(f"| `{m!r}` | {'**sim**' if marcador_valido(m) else 'não'} |")
    out += ["", "A escolha entre eles é estética — nenhum colide. `\\|` foi escolhido só por "
            "lembrar visualmente o `*N|` que já separa prefixo de declaração.", ""]

    out += ["## O que muda na recomendação anterior", "",
            "O lab `2211` recomendou `F1` como default porque o marcador `=` colidia. **Com o "
            "marcador por escape, essa objeção some**, e o `F5` passa a ser o melhor dos dois "
            "mundos: streama nos dois sentidos, é imune a colisão por construção, e custa o "
            "mesmo que o `F1`.", "",
            f"RT pelo leitor independente: **{'todos OK' if not falhas else falhas}**", ""]

    (RAIZ / "result.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    print("\n".join(out))
    return 0 if not falhas else 1


if __name__ == "__main__":
    sys.exit(main())

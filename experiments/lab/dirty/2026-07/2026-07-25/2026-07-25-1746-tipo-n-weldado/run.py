"""Lab 2026-07-25-1746 — DEPOIS do weld da tag `n` (rota tipada GENERALIZADA).

Reexecuta a matriz do lab `2026-07-25-1729` contra o `src/tcf` já com a generalização:
`_tipo_single_col` virou a fonte única de detecção de tipo, `n` (número) passou a ser
emitido, e null passou a conviver com qualquer tag. Mede o que a mudança trocou.

Cada caso grava:
  inputs/<ID>-fonte.json                  o dataset de entrada
  intermediates/<ID>-dataset-consumido.json   o que o TCF consome
  outputs/<ID>-wire.tcf                   o wire REAL emitido pelo encode()
  outputs/<ID>-equivalente.json           o JSON compacto equivalente (referência de escala)
  outputs/<ID>-dataset.roundtrip.json     o decode do wire (prova de RT)

Partes:
  A. ROTAS   — qual rota cada tipo toma hoje, e o tamanho vs JSON
  B. BOOL    — varredura de tamanho: onde o bool cruza o JSON
  C. NULL/NUM— bool+null, multi+null e os casos novos de número
  D. NAMESPACE — quais tags e larguras densas o decode aceita hoje
"""
import json
import pathlib
import sys

RAIZ = pathlib.Path(__file__).parent
REPO = RAIZ.parents[5]
sys.path.insert(0, str(REPO / "src"))

from tcf import decode, encode  # noqa: E402
from tcf.encoder import _encode_column  # noqa: E402
from tcf.hierarchical import _encode_hierarchical as _hier  # noqa: E402

for d in ("inputs", "intermediates", "outputs"):
    (RAIZ / d).mkdir(exist_ok=True)


def _wj(p, obj, compacto=False):
    sep = (",", ":") if compacto else (", ", ": ")
    txt = json.dumps(obj, ensure_ascii=False, separators=sep,
                     indent=None if compacto else 2)
    p.write_text(txt + ("" if compacto else "\n"), encoding="utf-8")
    return len(txt.encode())


def rota(w):
    if w.startswith("#TCF.8H"):
        return ".8H"
    if w.startswith("#TCF.8M"):
        return ".8M"
    if w.startswith("#TCF.8 "):
        return "spec"
    if len(w) > 6 and w[6] not in ("\n", " "):
        return f"tipado '{w[6]}'"
    return "flat"


def caso(eid, dados, nota):
    """Grava o fluxo §3.2 completo e devolve (rota, bytes TCF, bytes JSON, RT)."""
    _wj(RAIZ / "inputs" / f"{eid}-fonte.json", {"nota": nota, "dados": dados})
    _wj(RAIZ / "intermediates" / f"{eid}-dataset-consumido.json", dados)
    w = encode(dados)
    (RAIZ / "outputs" / f"{eid}-wire.tcf").write_text(w, encoding="utf-8")
    nj = _wj(RAIZ / "outputs" / f"{eid}-equivalente.json", dados, compacto=True)
    volta = decode(w)
    _wj(RAIZ / "outputs" / f"{eid}-dataset.roundtrip.json", volta)
    return rota(w), len(w.encode()), nj, volta == dados


# ============================================================ A. rotas por tipo
A = [
    ("A1-str",            ["a", "b", "a"],                         "string nativa (implícita)"),
    ("A2-str-null",       ["a", None, "b"],                        "string + null (slot 0)"),
    ("A3-so-null",        [None, None],                            "coluna 100% null"),
    ("A4-vazio",          [],                                      "lista vazia"),
    ("A5-bool",           [True, False, True],                     "bool (tag `b`)"),
    ("A6-bool-alternado", [bool(i % 2) for i in range(64)],        "bool alternado (força denso)"),
    ("A7-int",            [1, 2, 3],                               "int (tag `n`)"),
    ("A8-float",          [1.5, 2.0],                              "float (tag `n`)"),
    ("A9-multi-str",      {"a": ["x", "y"], "b": ["p", "q"]},      "multi-col de string"),
]

# ============================================================ B. bool: onde cruza o JSON
B = [(f"B{i}-bool-n{n}", d, f"bool, n={n}") for i, (n, d) in enumerate([
    (1, [True]),
    (2, [True, False]),
    (4, [True, False, True, True]),
    (8, [bool(i % 2) for i in range(8)]),
    (16, [bool(i % 3) for i in range(16)]),
    (64, [bool(i % 2) for i in range(64)]),
    (256, [bool(i % 2) for i in range(256)]),
    (1000, [bool((i * 7) % 10 < 5) for i in range(1000)]),
], 1)]

# ============================================================ C. as lacunas
C = [
    ("C1-bool-null-2",    [True, None],                            "bool + null, n=2"),
    ("C2-bool-null-3",    [True, None, False],                     "bool + null, n=3"),
    ("C3-bool-null-16",   [None if i % 4 == 0 else bool(i % 2) for i in range(16)],
                          "bool + null, n=16"),
    ("C4-bool-null-100",  [None if i % 4 == 0 else bool(i % 2) for i in range(100)],
                          "bool + null, n=100"),
    ("C5-multi-null",     {"a": ["x", None], "b": ["p", "q"]},     "multi-col + null"),
    ("C6-int-null",       [1, None, 3],                            "int + null"),
    ("C7-int-100",        list(range(100)),                        "int sequencial n=100"),
    ("C8-float-null",     [1.5, None, 2.5],                        "float + null"),
    ("C9-int-negativos",  [-1, -2, -3],                            "int negativos"),
    ("C10-int-grande",    [10 ** 20, 10 ** 20 + 1],                "int grande (>64 bits)"),
]


def tabela(titulo, casos, nota_col="nota"):
    out = [f"## {titulo}", "",
           "| id | rota | TCF (B) | JSON (B) | vs JSON | RT |",
           "|---|---|---:|---:|---:|---|"]
    linhas = []
    for eid, dados, nota in casos:
        r, b, j, rt = caso(eid, dados, nota)
        linhas.append((eid, r, b, j, 100 * (b - j) / j if j else 0, rt))
        out.append(f"| `{eid}` | {r} | {b} | {j} | **{100 * (b - j) / j:+.0f}%** | "
                   f"{'OK' if rt else 'FALHOU'} |")
    return out + [""], linhas


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    out = ["# Tag `n` weldada — matriz de tipos remedida (2026-07-25-1746)", "",
           "Estado REAL do `src/tcf` DEPOIS da generalização da rota tipada. `JSON` = equivalente compacto "
           "(`separators=(',',':')`). Cada linha tem os arquivos em "
           "`inputs/` · `intermediates/` · `outputs/`.", ""]

    bloco, la = tabela("A. Rota que cada tipo toma HOJE", A)
    out += bloco
    bloco, lb = tabela("B. Bool — varredura de tamanho", B)
    out += bloco
    out += ["O bool cruza o JSON em **~4 elementos**: abaixo disso o cabeçalho de 7 B domina; "
            "acima, o ganho vai a −97%.", ""]
    bloco, lc = tabela("C. Null e número — o que a generalização alcançou", C)
    out += bloco

    # ---- ANTES vs DEPOIS: o que a rota tipada trocou
    out += ["## Antes vs depois do weld da tag `n` (2026-07-25)", "",
            "`antes` = rota `.8H`, que era pra onde toda coluna tipada ia. Reconstruido "
            "forcando a entrada pro envelope hierarquico.", "",
            "| id | antes `.8H` | depois | Δ | vs JSON antes | vs JSON depois |",
            "|---|---:|---:|---:|---:|---:|"]
    for eid, dados, _nota in A + C:
        if not isinstance(dados, list) or not dados:
            continue
        try:
            wa = _hier(dados)
        except Exception:
            continue
        wd = encode(dados)
        if wa == wd:
            continue
        nj = len(json.dumps(dados, ensure_ascii=False, separators=(",", ":")).encode())
        a, d = len(wa.encode()), len(wd.encode())
        out.append(f"| `{eid}` | {a} | {d} | **{100 * (d - a) / a:+.0f}%** | "
                   f"{100 * (a - nj) / nj:+.0f}% | {100 * (d - nj) / nj:+.0f}% |")
    out += [""]

    # ---- custo do ESCAPE de digito sob a tag `n`
    out += ["## Custo do escape de dígito (por que não chega no wire ideal)", "",
            "No corpo, **dígito nu é referência de fragmento**, então o literal `1` precisa "
            "do escape (barra invertida + `1`) para não ser lido como referência.", "",
            "| coluna | corpo real | corpo sem escape (hipotético) | escape custa |",
            "|---|---|---|---:|"]
    for dados in ([1, 2, 3], [1, 2, 3, 4, 5], list(range(10)), [1.5, 2.5]):
        corpo = _encode_column([str(v) for v in dados])
        sem = corpo.replace("\\", "")
        out.append(f"| `{dados if len(dados) < 6 else 'range(10)'}` | `{corpo.strip()!r}` | "
                   f"`{sem.strip()!r}` | **{len(corpo.encode()) - len(sem.encode())} B** |")
    out += ["", "**Custo real é pequeno**: o escape incide por LITERAL EMITIDO, e o seq-RLE "
            "colapsa a sequência num template só — daí 1-2 B no total, não 1 B por elemento. "
            "E ele é **estrutural**, não desperdício: sem ele o decode não distingue o "
            "literal `1` da referência ao fragmento 1. Suprimi-lo exigiria uma gramática de "
            "corpo diferente sob a tag `n` — o oposto de reusar o core intocado.", ""]

    # ---- D. namespace: o que o decode aceita
    out += ["## D. Namespace — o que o decode aceita hoje", "",
            "| grafia | resultado |", "|---|---|"]
    for tag, corpo in [("b", "true\nfalse\n"), ("n", "1\n2\n"), ("s", "foo\nbar\n")]:
        try:
            r = decode(f"#TCF.8{tag}\n{corpo}")
            out.append(f"| `#TCF.8{tag}` | decoda -> `{r}` |")
        except ValueError as e:
            out.append(f"| `#TCF.8{tag}` | **fail-loud**: {str(e)[:52]} |")
    for m in "1248":
        try:
            decode(f"#TCF.8b{m}4\nAA==")
            out.append(f"| `#TCF.8b{m}` (denso w={m}) | aceita |")
        except ValueError as e:
            out.append(f"| `#TCF.8b{m}` (denso w={m}) | **fail-loud**: {str(e)[:44]} |")
    out += [""]

    # ---- veredito factual. A varredura cobre A+B+C (a 1a versao filtrava so' o bloco C e
    # afirmava "todos com null", o que era FALSO: int, float, vazio e bool n<=2 tambem estao).
    todos = la + lb + lc
    piores = sorted([(e, r, b, j, p) for e, r, b, j, p, _rt in todos if p > 0],
                    key=lambda x: -x[4])
    rt_ok = all(x[-1] for x in todos)
    out += ["## Achados (fatos, sem interpretação)", "",
            f"1. **RT: {'todos os {} casos passam'.format(len(todos)) if rt_ok else 'HA FALHA'}** "
            "— nenhuma lacuna abaixo é perda de dado; são bytes.", "",
            f"2. **{len(piores)} de {len(todos)} casos em que o TCF é MAIOR que o JSON "
            "compacto**:", "",
            "| id | rota | TCF | JSON | vs JSON |", "|---|---|---:|---:|---:|"]
    out += [f"| `{e}` | {r} | {b} | {j} | **{p:+.0f}%** |" for e, r, b, j, p in piores]
    out += ["",
            "Eles se separam em **dois grupos**:", "",
            f"   - **rota `.8H`** ({sum(1 for x in piores if x[1] == '.8H')} caso): so' o "
            "`multi-col + null`, que e' a unica rota ainda NAO aberta.",
            f"   - **rota flat/tipada** ({sum(1 for x in piores if x[1] != '.8H')} casos): "
            "todos de payload minusculo, onde os 7 B de cabecalho (ADR-0034) competem com um "
            "JSON de 2-17 B. Consequencia DECLARADA daquela decisao, nao lacuna nova.", "",
            "3. **`bool + null`, `int`, `float` e `int + null` sairam do `.8H`** nesta rodada; "
            "so' `multi-col + null` continua la'.",
            "4. `#TCF.8n` agora e' EMITIDO; `#TCF.8s` decoda mas o encoder nao emite (string "
            "segue implicita por exclusao).",
            "5. O denso do bool so' aceita `w=1` — e com null a coluna usa o modo CORE, porque "
            "1 bit nao comporta o trio {null, false, true}.",
            "6. O bool cruza o JSON em **~4 elementos** (B3); acima disso o ganho vai a -97%. "
            "O numero cruza mais tarde: `C7-int-100` ja' e' -91%, mas `A7-int` (n=3) e' +129%.", ""]

    (RAIZ / "result.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    print("\n".join(out))
    return 0 if rt_ok else 1


if __name__ == "__main__":
    sys.exit(main())

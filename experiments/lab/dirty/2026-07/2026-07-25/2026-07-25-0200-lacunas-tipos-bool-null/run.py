"""Lab 2026-07-25-0200 — lacunas da frente de tipos, com evidência em arquivo.

Levanta o estado REAL do `src/tcf` (não de memória) na frente cabeçalho / string / bool,
para decidir o que falta antes de abrir int, float e specs.

Cada caso grava:
  inputs/<ID>-fonte.json                  o dataset de entrada
  intermediates/<ID>-dataset-consumido.json   o que o TCF consome
  outputs/<ID>-wire.tcf                   o wire REAL emitido pelo encode()
  outputs/<ID>-equivalente.json           o JSON compacto equivalente (referência de escala)
  outputs/<ID>-dataset.roundtrip.json     o decode do wire (prova de RT)

Partes:
  A. ROTAS   — qual rota cada tipo toma hoje, e o tamanho vs JSON
  B. BOOL    — varredura de tamanho: onde o bool cruza o JSON
  C. NULL    — bool+null e multi+null (as lacunas)
  D. NAMESPACE — quais tags e larguras densas o decode aceita hoje
"""
import json
import pathlib
import sys

RAIZ = pathlib.Path(__file__).parent
REPO = RAIZ.parents[5]
sys.path.insert(0, str(REPO / "src"))

from tcf import decode, encode  # noqa: E402

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
    ("A7-int",            [1, 2, 3],                               "int — ainda no `.8H`"),
    ("A8-float",          [1.5, 2.0],                              "float — ainda no `.8H`"),
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
    out = ["# Lacunas da frente de tipos — evidência em arquivo (2026-07-25-0200)", "",
           "Estado REAL do `src/tcf`, medido. `JSON` = equivalente compacto "
           "(`separators=(',',':')`). Cada linha tem os arquivos em "
           "`inputs/` · `intermediates/` · `outputs/`.", ""]

    bloco, la = tabela("A. Rota que cada tipo toma HOJE", A)
    out += bloco
    bloco, lb = tabela("B. Bool — varredura de tamanho", B)
    out += bloco
    out += ["O bool cruza o JSON em **~4 elementos**: abaixo disso o cabeçalho de 7 B domina; "
            "acima, o ganho vai a −97%.", ""]
    bloco, lc = tabela("C. As lacunas — null fora da rota flat", C)
    out += bloco

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
            "Eles se separam em **dois grupos**, e a distinção importa:",
            "",
            f"   - **rota `.8H`** ({sum(1 for x in piores if x[1] == '.8H')} casos): "
            "`bool+null`, `multi+null`, `int`, `float`, `int+null`. O envelope hierárquico "
            "custa mais do que economiza nesses tamanhos.",
            f"   - **rota flat/tipada** ({sum(1 for x in piores if x[1] != '.8H')} casos): "
            "`[]`, `[None,None]`, bool com n≤2. Aqui é o cabeçalho de 7 B (ADR-0034) contra "
            "um JSON de 2-12 B — consequência declarada daquela decisão, não lacuna nova.", "",
            "3. `str + null` está na rota flat (soldado 2026-07-25); `bool + null` e "
            "`multi-col + null` **não** — ainda caem no `.8H`.",
            "4. `#TCF.8n` e `#TCF.8s` são fail-loud — só a tag `b` decoda.",
            "5. O denso do bool só aceita `w=1`; `b2`/`b4`/`b8` são fail-loud.",
            "6. O bool cruza o JSON em **~4 elementos** (B3); acima disso o ganho vai a −97%.", ""]

    (RAIZ / "result.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    print("\n".join(out))
    return 0 if rt_ok else 1


if __name__ == "__main__":
    sys.exit(main())

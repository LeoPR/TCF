"""Lab 2026-07-28-0829 — T-BN-TIPADO: o ganho, MEDIDO.

    "você disse que 'o ganho é bem maior do que eu tinha registrado', cadê o lab pra provar
     isso?"

Justo. Os números que eu apresentei sairam de um probe no terminal — existiam só no meu
scrollback. Este lab materializa a evidência.

Mede:
  A. bool / int / float × `k` × null — o ganho por coluna, contra o `encode` REAL de hoje
  B. os CONTRA-CASOS, onde a proposta deve PERDER (o denso `b1`; alta cardinalidade)
  C. RT estrito: valor, **tipo**, **sinal** e comprimento
  D. varredura de `k` e de `n` — onde vira
  E. colunas REAIS tipadas
  F. impacto nos gates byte-canônicos

VALIDAÇÃO: o protótipo usa `dominio_bn.decode_bn` e `decoder._cast_tipo` **do `src/tcf`** —
não reimplementa nada. O alvo da comparação são os DADOS ORIGINAIS. O `hoje` vem do `encode`
público.

`src/tcf` intocado — proposta, não solda.
"""
import csv
import json
import math
import pathlib
import sys

RAIZ = pathlib.Path(__file__).parent
REPO = RAIZ.parents[5]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(RAIZ))

from tipado_bn import proto_decode, proto_encode  # noqa: E402

from tcf import encode  # noqa: E402
from tcf.encoder import _tipo_single_col  # noqa: E402

for d in ("inputs", "intermediates", "outputs"):
    (RAIZ / d).mkdir(exist_ok=True)

SAMPLES = REPO / "datasets" / "samples"


def _wj(p, obj):
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2, default=str) + "\n",
                 encoding="utf-8")


def rt_estrito(obtido, esperado):
    """Valor **E** tipo **E** sinal, com guarda de comprimento. `-0.0 == 0.0` em Python."""
    if len(obtido) != len(esperado):
        return False
    if obtido != esperado:
        return False
    if not all(type(a) is type(b) for a, b in zip(obtido, esperado)):
        return False
    return all(math.copysign(1, a) == math.copysign(1, b)
               for a, b in zip(obtido, esperado)
               if isinstance(a, float) and isinstance(b, float) and a == 0)


def caso(nome, dados, gravar=True):
    hoje_w = encode(dados)
    hoje = len(hoje_w.encode())
    wire, tag, w = proto_encode(dados)
    if wire is None:
        return {"nome": nome, "n": len(dados), "tag": tag, "hoje": hoje,
                "bn": None, "w": 0, "rt": None, "cab": hoje_w.split("\n")[0]}
    obtido = proto_decode(wire)
    r = {"nome": nome, "n": len(dados), "tag": tag, "hoje": hoje,
         "bn": len(wire.encode()), "w": w, "rt": rt_estrito(obtido, dados),
         "cab": hoje_w.split("\n")[0], "cab_bn": wire.split("\n")[0]}
    if gravar:
        _wj(RAIZ / "inputs" / f"{nome}-fonte.json",
            {"coluna": nome, "n": len(dados), "tag": tag, "w": w, "amostra": dados[:6]})
        _wj(RAIZ / "intermediates" / f"{nome}-dataset-consumido.json", dados)
        (RAIZ / "outputs" / f"{nome}-hoje.tcf").write_text(hoje_w, encoding="utf-8")
        (RAIZ / "outputs" / f"{nome}-bn-tipado.tcfp").write_text(wire, encoding="utf-8")
        _wj(RAIZ / "outputs" / f"{nome}-dataset.roundtrip.json", obtido)
    return r


def linha(r):
    if r["bn"] is None:
        return (f"| `{r['nome']}` | {r['n']} | `{r['tag'] or '—'}` | — | {r['hoje']} | "
                f"— | — | — |")
    d = r["bn"] - r["hoje"]
    return (f"| `{r['nome']}` | {r['n']} | `{r['tag']}` | {r['w']} | {r['hoje']} | "
            f"{r['bn']} | **{d:+}** | {'OK' if r['rt'] else '**FALHOU**'} |")


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    falhas = []
    CAB = ["| coluna | n | tag | w | hoje | bN tipado | Δ | RT |",
           "|---|---:|:-:|---:|---:|---:|---:|:-:|"]
    out = ["# T-BN-TIPADO — o ganho, medido (2026-07-28-0829)", "",
           "O bN de domínio está soldado (ADR-0036) **só na rota flat**. A rota tipada "
           "(`#TCF.8<tag>`) não o alcança porque o wire `#TCF.8B…` devolve **string**, e ali "
           "o tipo tem de ser preservado.", "",
           "```",
           "#TCF.8 b B 2 c8",
           "       │ │ │ └── n em hex",
           "       │ │ └──── w = largura em bits",
           "       │ └────── modo, INDICE 7   <- o slot JA' existe",
           "       └──────── tag de tipo, indice 6",
           "```", "",
           "`_decode_typed` já faz `resto = line1[7:]` e `modo_c = resto[:1]`. Acrescentar "
           "`B` é **um ramo no dispatch existente**, não gramática nova.", ""]

    # ================================================================ A: o ganho
    L = ["ativo", "inativo", "susp", "canc", "revisao", "arq", "pend"]
    casos = {
        "bool-puro": [bool(i % 2) for i in range(200)],
        "bool-null": [None if i % 3 == 0 else bool(i % 2) for i in range(200)],
        "bool-null-esparso": [None if i % 17 == 0 else bool(i % 2) for i in range(200)],
        "int-k2": [[10, 20][i % 2] for i in range(200)],
        "int-k4": [[10, 20, 30, 40][i % 4] for i in range(200)],
        "int-k4-null": [None if i % 9 == 0 else [10, 20, 30, 40][i % 4] for i in range(200)],
        "int-k8": [i % 8 * 11 for i in range(200)],
        "float-k3": [[1.5, 2.5, 3.5][i % 3] for i in range(200)],
        "float-k3-null": [None if i % 8 == 0 else [1.5, 2.5, 3.5][i % 3] for i in range(200)],
        "float-k6": [round(i % 6 * 1.25, 2) for i in range(200)],
        "misto-int-float": [[1, 2.5, 3, 4.5][i % 4] for i in range(200)],
        "float-integral": [[1.0, 2.0][i % 2] for i in range(200)],
        "neg-zero": [[-0.0, 0.0, 1.0][i % 3] for i in range(200)],
    }
    out += ["## A — o ganho, por coluna (n=200)", ""] + CAB
    for nome, dados in casos.items():
        r = caso(nome, dados)
        if r["rt"] is False:
            falhas.append(nome)
        out.append(linha(r))
    ganhos = [caso(n, d, gravar=False) for n, d in casos.items()]
    venc = [r for r in ganhos if r["bn"] is not None and r["bn"] < r["hoje"]]
    out += ["", f"Vence em **{len(venc)} de {len(ganhos)}**; ganho somado nas vencedoras: "
            f"**{sum(r['bn'] - r['hoje'] for r in venc)} B**.", "",
            "Eu tinha registrado só `bool + null` (−452 B). **`int` e `float` de "
            "cardinalidade baixa estavam igualmente descobertos** — e ganham mais.", ""]

    # ================================================================ B: contra-casos
    out += ["## B — onde a proposta deve PERDER", "",
            "Sem estes, a tabela A não significa nada.", ""] + CAB
    contra = {
        "int-k200-unicos": [i * 7 for i in range(200)],
        "int-ordenado": list(range(200)),
        "float-alta-card": [round(i * 1.37, 2) for i in range(200)],
        "bool-constante": [True] * 200,
        "int-k1": [42] * 200,
        "n-pequeno-k2": [10, 20, 10],
        "int-grande-k4": [[10 ** 15, 2 * 10 ** 15, 3 * 10 ** 15, 4 * 10 ** 15][i % 4]
                          for i in range(200)],
    }
    for nome, dados in contra.items():
        r = caso(nome, dados)
        if r["rt"] is False:
            falhas.append(nome)
        out.append(linha(r))
    perdem = [caso(n, d, gravar=False) for n, d in contra.items()]
    ok_perde = sum(1 for r in perdem if r["bn"] is None or r["bn"] >= r["hoje"])
    out += ["", f"Perde ou recusa em **{ok_perde} de {len(perdem)}** — que é o comportamento "
            "correto. O `bool-constante` e o `int-k1` caem no `k<=1`, onde o core já é ótimo "
            "com RLE; os de alta cardinalidade pagam o domínio inteiro.", "",
            "O `bool-puro` da tabela A é o contra-caso mais instrutivo: o **denso `b1` de hoje "
            "tem domínio IMPLÍCITO** (`false`/`true` não viajam) e ganha do bN. Logo o bN é "
            "**mais um candidato do `min()`**, não substituto de nada.", ""]

    # ================================================================ C: varredura
    out += ["## C — onde vira, varrendo `k` e `n`", "",
            "| k | hoje | bN | Δ |", "|---:|---:|---:|---:|"]
    for k in (2, 3, 4, 6, 8, 12, 16, 32, 64, 128):
        dados = [i % k * 3 for i in range(200)]
        r = caso(f"varre-k{k:03d}", dados, gravar=False)
        out.append(f"| {k} | {r['hoje']} | {r['bn']} | **{r['bn'] - r['hoje']:+}** |"
                   if r["bn"] else f"| {k} | {r['hoje']} | — | — |")
    out += ["", "| n | hoje | bN | Δ |", "|---:|---:|---:|---:|"]
    for n in (2, 5, 10, 20, 50, 200, 1000):
        dados = [[10, 20, 30, 40][i % 4] for i in range(n)]
        r = caso(f"varre-n{n:04d}", dados, gravar=False)
        out.append(f"| {n} | {r['hoje']} | {r['bn']} | **{r['bn'] - r['hoje']:+}** |"
                   if r["bn"] else f"| {n} | {r['hoje']} | — | — |")
    out.append("")

    # ================================================================ D: reais
    out += ["## D — colunas REAIS tipadas", "",
            "Os CSV do repo dão string; aqui o lab converte para `int`/`float`/`bool` — que é "
            "exatamente o que um consumidor faria antes de chamar o `encode`.", ""] + CAB
    reais = [
        ("real-adult-sex-bool", "adult-census/adult-sample.csv", "sex",
         lambda v: v.strip() == "Male"),
        ("real-adult-class-bool", "adult-census/adult-sample.csv", "class",
         lambda v: ">" in v),
        ("real-cnpj-matriz-int", "receita-cnpj/cnpj-2k.csv", "matriz_filial", int),
        ("real-pm25-Is-int", "beijing-pm25/beijing-pm25-sample.csv", "Is", int),
        ("real-pm25-Ir-int", "beijing-pm25/beijing-pm25-sample.csv", "Ir", int),
        ("real-pm25-month-int", "beijing-pm25/beijing-pm25-sample.csv", "month", int),
        ("real-adult-eduint", "adult-census/adult-sample.csv", "education-num", int),
        ("real-tpch-acctbal-float", "tpch-sf001/customer-sample.csv", "c_acctbal", float),
    ]
    for nome, rel, col, conv in reais:
        p = SAMPLES / rel
        if not p.exists():
            continue
        with p.open(encoding="utf-8", newline="") as f:
            rd = csv.DictReader(f)
            if col not in (rd.fieldnames or []):
                raise KeyError(f"{col!r} nao existe em {rel}")
            dados = [conv(row[col]) for row in rd if row[col] not in ("", "NA")][:2000]
        if not dados:
            continue
        r = caso(nome, dados)
        if r["rt"] is False:
            falhas.append(nome)
        out.append(linha(r))
    out.append("")

    # ================================================================ E: gates
    sys.path.insert(0, str(REPO / "tests"))
    import test_real_world_snapshots as W  # noqa: E402
    import test_regression_v1_baseline as R  # noqa: E402
    tipadas = []
    for k in R.D1_D9_BYTES_FROZEN:
        if _tipo_single_col(R._load_single_col(k)) is not None:
            tipadas.append(k)
    for k, (_e, rel) in W.REAL_WORLD_BYTES_FROZEN.items():
        if _tipo_single_col(W._load_single_col(rel)) is not None:
            tipadas.append(k)
    out += ["## E — impacto nos gates byte-canônicos", "",
            f"Colunas dos gates que passam pela rota TIPADA: **{len(tipadas)} de 12**"
            + (f" — {tipadas}" if tipadas else " (nenhuma)."), "",
            "Os gates carregam `list[str]` lida de CSV, então vão todos pela rota **flat**. "
            f"**{'Nenhum baseline moveria' if not tipadas else 'ATENCAO: baseline moveria'}** "
            f"— D1-D9 {R.D1_D9_TOTAL}, D17a {R.D17A_INVARIANT}, real-world "
            f"{W.REAL_WORLD_TOTAL}.", ""]

    # ================================================================ F: RT
    todos = len(casos) + len(contra) + len([1 for n, rel, c, _cv in reais
                                            if (SAMPLES / rel).exists()])
    out += ["## F — round-trip", "",
            "`RT` compara **valor, tipo, sinal e comprimento**. O `-0.0` merece nota: em "
            "Python `-0.0 == 0.0`, então só o `copysign` pega a troca de sinal.", "",
            f"- colunas com RT estrito OK: **{todos - len(falhas)}/{todos}**"
            + (f" — falha em {falhas}" if falhas else ""),
            "- o protótipo usa `dominio_bn.decode_bn` e `decoder._cast_tipo` **do `src/tcf`** "
            "— nenhuma reimplementação, então o que se mede aqui é o que a solda produziria.",
            ""]

    # ================================================================ custo
    out += ["## O custo de soldar", "",
            "| ponto | mudança |", "|---|---|",
            "| `encoder.py` rota tipada | injetar a tag e somar aos `candidatos` do `min()` "
            "que já existe |",
            "| `decoder.py` `_decode_typed` | ramo `modo_c == 'B'` |",
            "| conversão de tipo | **zero** — `_cast_tipo` como está |",
            "| `dominio_bn.py` | **zero** — já soldado e testado |", "",
            "É fiação, não mecanismo.", ""]

    (RAIZ / "result.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    print("\n".join(out))
    return 0 if not falhas else 1


if __name__ == "__main__":
    sys.exit(main())

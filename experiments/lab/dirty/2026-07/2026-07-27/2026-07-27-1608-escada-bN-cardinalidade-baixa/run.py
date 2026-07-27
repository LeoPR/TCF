"""Lab 2026-07-27-1608 — a escada bN: densidade por CARDINALIDADE, não por tipo declarado.

Origem: o owner olhou `binario-01-depois.tcf` (200 valores `"0"`/`"1"` = **609 B**) e notou
que a mesma informação como `bool` custa **47 B**.

    "acho que o binário/bool é um bom candidato à escolha automática do tipo, assim como o `n`
     (…) se ao buscar os elementos eles tiverem só 1, já lança um binário/boolean previamente
     com b64 como default, se entrar 2, mesma coisa, se tiver null, aí também vai escalando,
     com 4 etc."

Mede:
  A. a escada `k -> largura` contra o core, varrendo `k`, `n` e o tamanho do valor
  B. onde ela **para** de ganhar (o domínio viaja; valor longo mata a proposta)
  C. `null` — hoje desliga o denso; na escada é só mais um slot (e o slot 0 já é dele)
  D. colunas reais
  E. a decisão é `[stream]`? (os insumos já existem em `analyze_column`)

VALIDAÇÃO: leitor **independente** (`le_bn` reimplementa a semântica), comparado com os
DADOS ORIGINAIS — não com a inversa da transformação. Lição do lab `2026-07-26-0038`.

`src/tcf` intocado — proposta, não solda.
"""
import csv
import json
import pathlib
import sys

RAIZ = pathlib.Path(__file__).parent
REPO = RAIZ.parents[5]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(RAIZ))

from escada import custo_bn, dominio, largura, le_bn, para_bn, soma_dominio  # noqa: E402

from tcf import decode, encode  # noqa: E402

for d in ("inputs", "intermediates", "outputs"):
    (RAIZ / d).mkdir(exist_ok=True)

SAMPLES = REPO / "datasets" / "samples"


def _wj(p, obj):
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def mede(valores, gravar=None):
    """`(hoje, bn, w, k, rt_ok)` — hoje pelo `encode` REAL, bn pelo leitor independente."""
    hoje = len(encode(valores).encode()) if valores else 0
    wire, w, k = para_bn(valores)
    if wire is None:
        return hoje, None, 0, k, None
    lido = le_bn(wire, n_dom=k)
    rt = lido == valores
    if gravar:
        (RAIZ / "outputs" / f"{gravar}-hoje.tcf").write_text(encode(valores), encoding="utf-8")
        (RAIZ / "outputs" / f"{gravar}-bn.tcfp").write_text(wire, encoding="utf-8")
        _wj(RAIZ / "outputs" / f"{gravar}-dataset.roundtrip.json", lido)
    return hoje, len(wire.encode()), w, k, rt


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    out = ["# A escada bN — densidade por cardinalidade (2026-07-27-1608)", "",
           "Você olhou `binario-01-depois.tcf` — 200 valores `\"0\"`/`\"1\"` custando **609 B** "
           "— e perguntou por que não fica compacto. O motivo é de **rota**, não de conteúdo:",
           "", "| entrada | rota | bytes |", "|---|---|---:|",
           "| `['0','1'] * 100` | `_lista_flat` → core | **609** |",
           "| `[False,True] * 100` | `_tipo_single_col` → denso `b1` | **47** |",
           "| `[False,True,None] …` | denso é bool-**sem-null** → core | **546** |", "",
           "A oportunidade é da **cardinalidade da coluna**, não do tipo Python da entrada. "
           "Com `k` distintos bastam `w = ceil(log2(k))` bits por linha.", ""]

    falhas = []

    # ---------------------------------------------------------------- A: a escada
    out += ["## A — a escada, varrendo `k` (n=200, valor curto)", "",
            "| k | w (bits) | hoje | bN | Δ | RT |", "|---:|---:|---:|---:|---:|:-:|"]
    for k in (1, 2, 3, 4, 5, 8, 9, 16, 17, 32, 64, 100, 150):
        vals = [f"v{i % k}" for i in range(200)]
        hoje, bn, w, kk, rt = mede(vals, gravar=f"k{k:03d}-n200" if k in (1, 2, 4, 16) else None)
        if rt is False:
            falhas.append(f"k={k}")
        if bn is None:
            out.append(f"| {k} | 0 | {hoje} | — | — | — |")
            continue
        out.append(f"| {k} | {w} | {hoje} | {bn} | **{bn - hoje:+}** | "
                   f"{'OK' if rt else '**FALHOU**'} |")
    out += ["", "`k=1` é o caso que **não precisa de nada**: o core já resolve com RLE "
            "(`*200|v0` = 16 B). A escada começa em `k=2`.", ""]

    # ---------------------------------------------------------------- B: onde para de ganhar
    out += ["## B — onde ela para de ganhar", "",
            "O domínio **viaja**. Valor longo mata a proposta, mesmo com `k` pequeno:", "",
            "| len(valor) | k=2 | k=4 | k=16 | k=64 |", "|---:|---|---|---|---|"]
    for L in (1, 2, 5, 10, 20, 40):
        cels = []
        for k in (2, 4, 16, 64):
            vals = [("x" * L + str(i % k))[:max(L, 1)] if k <= 10 ** L else f"{i % k:0{L}d}"
                    for i in range(200)]
            vals = [f"{i % k:0{L}d}"[-L:] if L >= len(str(k)) else str(i % k)
                    for i in range(200)]
            if len(set(vals)) != k:
                cels.append("—")
                continue
            hoje, bn, w, kk, rt = mede(vals)
            if rt is False:
                falhas.append(f"L={L},k={k}")
            cels.append(f"{bn - hoje:+}" if bn else "—")
        out.append(f"| {L} | " + " | ".join(cels) + " |")
    out += ["", "Negativo = a escada ganha. O cruzamento é onde `k × len(valor)` (o domínio) "
            "passa a pesar mais do que os `^N` que o core gastaria.", ""]

    # ---------------------------------------------------------------- n
    out += ["## Varrendo `n` (k=2, valor curto)", "",
            "| n | hoje | bN | Δ | Δ/linha |", "|---:|---:|---:|---:|---:|"]
    for n in (2, 5, 10, 20, 50, 100, 500, 2000):
        vals = [f"v{i % 2}" for i in range(n)]
        hoje, bn, w, kk, rt = mede(vals)
        if rt is False:
            falhas.append(f"n={n}")
        out.append(f"| {n} | {hoje} | {bn} | **{bn - hoje:+}** | {(bn - hoje) / n:+.2f} |")
    out += ["", "**`n` pequeno anula a proposta** — abaixo de ~10 linhas o cabeçalho e o "
            "domínio não se pagam. É o mesmo achado que o estudo de `bN-dense` multi-col já "
            "tinha registrado no `STATUS.md`.", ""]

    # ---------------------------------------------------------------- C: null
    out += ["## C — `null` não é caso especial", "",
            "Hoje o `null` **desliga** o denso (`if tag == 'b' and not tem_nulo`). Na escada "
            "ele é só mais um valor do domínio — e o formato **já reserva o slot 0** pra ele, "
            "então a grafia do domínio usa o mesmo `0` cru que o core usa pro `^0`.", "",
            "| coluna | k (c/ null) | w | hoje | bN | Δ | RT |",
            "|---|---:|---:|---:|---:|---:|:-:|"]
    casos_null = {
        "bool-sem-null": [bool(i % 2) for i in range(200)],
        "bool-com-null": [None if i % 3 == 0 else bool(i % 2) for i in range(200)],
        "str01-sem-null": [str(i % 2) for i in range(200)],
        "str01-com-null": [None if i % 3 == 0 else str(i % 2) for i in range(200)],
        "status-4-com-null": [None if i % 7 == 0 else ["ativo", "inativo", "susp", "canc"][i % 4]
                              for i in range(200)],
    }
    for nome, vals in casos_null.items():
        try:
            hoje = len(encode(vals).encode())
        except Exception as e:
            hoje = None
            out.append(f"| `{nome}` | — | — | **{type(e).__name__}** | — | — | — |")
            continue
        v_str = [None if v is None else (str(v).lower() if isinstance(v, bool) else v)
                 for v in vals]
        wire, w, k = para_bn(v_str)
        lido = le_bn(wire, n_dom=k)
        rt = lido == v_str
        if not rt:
            falhas.append(nome)
        bn = len(wire.encode())
        _wj(RAIZ / "inputs" / f"{nome}-fonte.json", {"coluna": nome, "n": len(vals),
                                                     "amostra": vals[:6]})
        _wj(RAIZ / "intermediates" / f"{nome}-dataset-consumido.json", v_str)
        (RAIZ / "outputs" / f"{nome}-hoje.tcf").write_text(encode(vals), encoding="utf-8")
        (RAIZ / "outputs" / f"{nome}-bn.tcfp").write_text(wire, encoding="utf-8")
        _wj(RAIZ / "outputs" / f"{nome}-dataset.roundtrip.json", lido)
        out.append(f"| `{nome}` | {k} | {w} | {hoje} | {bn} | **{bn - hoje:+}** | "
                   f"{'OK' if rt else '**FALHOU**'} |")
    out += ["", "O `bool-com-null` é o caso que mais expõe a lacuna de hoje: o `null` sozinho "
            "faz o wire pular de 47 B para 546 B.", ""]

    # ---------------------------------------------------------------- D: reais
    out += ["## D — colunas reais de cardinalidade baixa", "",
            "| coluna | n | k | w | hoje | bN | Δ | RT |",
            "|---|---:|---:|---:|---:|---:|---:|:-:|"]
    reais = [("adult-sex", "adult-census/adult-sample.csv", "sex"),
             ("adult-class", "adult-census/adult-sample.csv", "class"),
             ("adult-race", "adult-census/adult-sample.csv", "race"),
             ("adult-relationship", "adult-census/adult-sample.csv", "relationship"),
             ("adult-workclass", "adult-census/adult-sample.csv", "workclass"),
             ("cnpj-uf", "receita-cnpj/cnpj-2k.csv", "uf"),
             ("cnpj-situacao", "receita-cnpj/cnpj-2k.csv", "situacao"),
             ("cnpj-matriz", "receita-cnpj/cnpj-2k.csv", "matriz_filial"),
             ("pm25-cbwd", "beijing-pm25/beijing-pm25-sample.csv", "cbwd"),
             ("ibge-uf", "ibge-municipios/ibge-municipios-sample.csv", "uf_sigla")]
    for nome, rel, col in reais:
        p = SAMPLES / rel
        if not p.exists():
            continue
        with p.open(encoding="utf-8", newline="") as f:
            r = csv.DictReader(f)
            if col not in (r.fieldnames or []):
                raise KeyError(f"{col!r} nao existe em {rel}")
            vals = [row[col] for row in r if row[col] != ""][:2000]
        if not vals:
            continue
        hoje, bn, w, k, rt = mede(vals, gravar=nome)
        if rt is False:
            falhas.append(nome)
        _wj(RAIZ / "inputs" / f"{nome}-fonte.json",
            {"coluna": nome, "arquivo": rel, "campo": col, "n": len(vals), "k": k})
        _wj(RAIZ / "intermediates" / f"{nome}-dataset-consumido.json", vals)
        out.append(f"| **`{nome}`** | {len(vals)} | {k} | {w} | {hoje} | {bn} | "
                   f"**{bn - hoje:+}** | {'OK' if rt else '**FALHOU**'} |")
    out.append("")

    # ---------------------------------------------------------------- E: a decisão é [stream]?
    out += ["## E — a decisão é `[stream]`?", "",
            "Pelo guia do `.9`, isto cai em **A (FLOOR de bytes)** com um **gate C** de "
            "cardinalidade. A pergunta é se dá pra decidir **sem materializar**.", "",
            "O custo do bN é uma **fórmula fechada**:", "",
            "```", "w      = ceil(log2(k))",
            "custo  = cabecalho + soma_len(dominio) + k + base64(ceil(n*w/8))", "```", "",
            "E os dois insumos — `k` e a soma dos comprimentos — **já são computados hoje** "
            "por `analyze_column` (`n_unicas`, `avg_len`) e pelo dedupe do `_encode_column` "
            "(`unicas`). Nenhuma varredura nova.", "",
            "| coluna | custo CALCULADO | bN medido | bate? |", "|---|---:|---:|:-:|"]
    div = 0
    for k in (2, 4, 16, 64):
        vals = [f"v{i % k}" for i in range(200)]
        dom = dominio(vals)
        calc = custo_bn(len(dom), 200, soma_dominio(dom))
        _h, bn, _w, _k, _rt = mede(vals)
        div += calc != bn
        out.append(f"| k={k}, n=200 | {calc} | {bn} | {'sim' if calc == bn else '**NÃO**'} |")
    out += ["", f"Divergências entre a fórmula e a medição: **{div}**"
            + (" — a decisão é uma conta, como a da polaridade." if div == 0 else ""), "",
            "Ou seja: entra como candidato do `min()` **sem custo de materialização** — não "
            "repete a dívida dos outros 8 FLOORs.", ""]

    out += ["## O que isto NÃO resolve", "",
            "- **`k=1`**: o core já é ótimo (RLE `*N|valor`). A escada deve recusar.",
            "- **`n` pequeno**: abaixo de ~10 linhas o cabeçalho+domínio não se pagam.",
            "- **valor longo**: o domínio viaja; `k × len(valor)` é o teto real, não `k`.",
            "- **ordem**: o bitpack destrói a estrutura que o OBAT/HCC explorariam — só vale "
            "onde não há composição a achar, que é exatamente o regime de cardinalidade baixa.",
            "- **gzip**: não medido aqui. O estudo multi-col registrou que o gzip encolhe "
            "muito o ganho do bN (`STATUS.md`).", ""]

    (RAIZ / "result.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    print("\n".join(out))
    return 0 if not falhas else 1


if __name__ == "__main__":
    sys.exit(main())

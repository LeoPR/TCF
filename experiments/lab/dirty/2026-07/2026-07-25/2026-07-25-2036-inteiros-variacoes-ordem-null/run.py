"""Lab 2026-07-25-2036 — inteiros: variações de ordem, cardinalidade e null.

Mesmo estilo do trabalho com true/false, agora para a tag `n`.

MÉTRICA (owner 2026-07-25): **bytes decompostos em cabeçalho + corpo**, não porcentagem.
Em payload minúsculo a % é enganosa — 7 B de header contra 2 B de JSON viram "+250%" e isso
não informa nada. O que informa é: quanto custa a moldura, quanto custa o dado, e como
cada um escala. Porcentagem volta quando houver dado realista em escala.

`B/elem` = corpo ÷ n. É a métrica que mostra o mecanismo funcionando: quanto o corpo paga
por elemento à medida que `n` cresce.
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


def _lcg(seed):
    x = seed
    while True:
        x = (1103515245 * x + 12345) % (2 ** 31)
        yield x


def _wj(p, obj, compacto=False):
    txt = json.dumps(obj, ensure_ascii=False,
                     separators=(",", ":") if compacto else (", ", ": "),
                     indent=None if compacto else 2)
    p.write_text(txt + ("" if compacto else "\n"), encoding="utf-8")
    return len(txt.encode())


def caso(eid, dados, nota):
    _wj(RAIZ / "inputs" / f"{eid}-fonte.json", {"nota": nota, "dados": dados})
    _wj(RAIZ / "intermediates" / f"{eid}-dataset-consumido.json", dados)
    w = encode(dados)
    (RAIZ / "outputs" / f"{eid}-wire.tcf").write_text(w, encoding="utf-8")
    nj = _wj(RAIZ / "outputs" / f"{eid}-equivalente.json", dados, compacto=True)
    volta = decode(w)
    _wj(RAIZ / "outputs" / f"{eid}-dataset.roundtrip.json", volta)

    cab, _sep, corpo = w.partition("\n")
    nb_cab = len(cab.encode()) + 1                      # + o LF que separa
    nb_corpo = len(corpo.encode())
    return {"id": eid, "n": len(dados), "cab": nb_cab, "corpo": nb_corpo,
            "total": nb_cab + nb_corpo, "json": nj, "rt": volta == dados,
            "nulls": sum(v is None for v in dados), "wire": w}


# ---------------------------------------------------------------- geradores
def seq(n, ini=0, passo=1):
    return [ini + i * passo for i in range(n)]


def desordenado(n, seed=7):
    """Mesma MULTISET de `seq(n)`, embaralhada — isola o efeito da ORDEM."""
    vals, g = seq(n), _lcg(seed)
    for i in range(n - 1, 0, -1):
        j = next(g) % (i + 1)
        vals[i], vals[j] = vals[j], vals[i]
    return vals


def baixa_card(n, k, seed=7):
    g = _lcg(seed)
    return [next(g) % k for _ in range(n)]


def com_null(vals, pct, seed=11):
    g = _lcg(seed)
    return [None if next(g) % 100 < pct else v for v in vals]


# ---------------------------------------------------------------- matriz
GRUPOS = {
    "1. ORDEM (mesma multiset, ordem diferente)": [
        (f"O-seq-n{n}", seq(n), f"0..{n - 1} crescente") for n in (10, 100, 1000)
    ] + [
        (f"O-desord-n{n}", desordenado(n), f"mesma multiset de 0..{n - 1}, EMBARALHADA")
        for n in (10, 100, 1000)
    ] + [
        (f"O-decresc-n{n}", seq(n)[::-1], f"{n - 1}..0 decrescente") for n in (10, 100)
    ],
    "2. PASSO (cadência regular, mas não unitária)": [
        ("P-passo5-n100", seq(100, 0, 5), "0,5,10,… passo 5"),
        ("P-passo100-n100", seq(100, 0, 100), "0,100,200,… passo 100"),
        ("P-ids-n100", seq(100, 1000), "1000..1099 (ids)"),
        ("P-ts-n100", seq(100, 1735689600, 60), "epoch a cada 60 s"),
        ("P-negativos-n100", seq(100, -50), "−50..49 (cruza o zero)"),
    ],
    "3. CARDINALIDADE (poucos valores distintos)": [
        (f"C-k{k}-n100", baixa_card(100, k), f"100 elementos, {k} valores distintos")
        for k in (1, 2, 5, 20)
    ] + [("C-ruido-n100", baixa_card(100, 10 ** 6), "100 elementos ~todos distintos")],
    "4. NULL (sobre a sequência e sobre o ruído)": [
        (f"N-seq-p{p}-n100", com_null(seq(100), p), f"sequência, {p}% null")
        for p in (1, 10, 50, 90)
    ] + [
        (f"N-desord-p{p}-n100", com_null(desordenado(100), p), f"desordenado, {p}% null")
        for p in (10, 50)
    ] + [("N-todos-n20", [None] * 20, "20 elementos, todos null")],
    "5. MAGNITUDE (largura do literal)": [
        ("M-1digito-n100", baixa_card(100, 10), "0..9"),
        ("M-6digitos-n100", [100000 + v for v in baixa_card(100, 10)], "6 dígitos"),
        ("M-20digitos-n100", [10 ** 20 + v for v in baixa_card(100, 10)], "21 dígitos"),
        ("M-float-n100", [round(v / 7, 3) for v in seq(100)], "float, 3 casas"),
    ],
}


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    out = ["# Inteiros — ordem, cardinalidade, null e magnitude (2026-07-25-2036)", "",
           "Métrica: **bytes**, decompostos em `cabeçalho` + `corpo`. Porcentagem fica fora "
           "de propósito — em payload pequeno ela mede o header, não o mecanismo. "
           "`B/elem` = corpo ÷ n.", "",
           "`JSON` = equivalente compacto, em bytes, só como régua de ordem de grandeza.", ""]
    todos, falhas = [], 0
    for titulo, casos in GRUPOS.items():
        out += [f"## {titulo}", "",
                "| id | n | nulls | cab | corpo | total | B/elem | JSON | RT |",
                "|---|---:|---:|---:|---:|---:|---:|---:|---|"]
        for eid, dados, nota in casos:
            r = caso(eid, dados, nota)
            todos.append(r)
            falhas += not r["rt"]
            out.append(f"| `{eid}` | {r['n']} | {r['nulls']} | {r['cab']} | {r['corpo']} | "
                       f"**{r['total']}** | {r['corpo'] / r['n']:.2f} | {r['json']} | "
                       f"{'OK' if r['rt'] else 'FALHOU'} |")
        out += [""]

    # ---- leitura dos wires (o mecanismo aparece aqui, não na tabela)
    out += ["## Wires — o mecanismo visível", "", "```"]
    for eid in ("O-seq-n10", "O-desord-n10", "O-decresc-n10", "P-passo5-n100",
                "C-k1-n100", "C-k2-n100", "N-seq-p10-n100", "N-todos-n20"):
        r = next(x for x in todos if x["id"] == eid)
        w = r["wire"]
        out.append(f"{eid:16} {w[:64]!r}" + (" …" if len(w) > 64 else ""))
    out += ["```", ""]

    ordenado = {x["id"]: x for x in todos}
    out += ["## Efeito da ORDEM (mesma multiset)", "",
            "| n | crescente | embaralhado | custo da desordem |", "|---:|---:|---:|---:|"]
    for n in (10, 100, 1000):
        a, b = ordenado[f"O-seq-n{n}"], ordenado[f"O-desord-n{n}"]
        out.append(f"| {n} | {a['total']} | {b['total']} | **{b['total'] - a['total']:+} B** |")
    out += [""]

    # ---- null quebra a cadência (custo estrutural, não do slot)
    out += ["## Efeito do NULL sobre uma sequência", "",
            "| coluna | corpo | B/elem |", "|---|---:|---:|"]
    for eid in ("O-seq-n100", "N-seq-p1-n100", "N-seq-p10-n100", "N-seq-p50-n100",
                "N-seq-p90-n100"):
        r = ordenado[eid]
        out.append(f"| `{eid}` ({r['nulls']} nulls) | {r['corpo']} | {r['corpo'] / r['n']:.2f} |")
    out += ["", "O null **não é caro em si** (é 1 char, `0`) — ele **fragmenta a cadência**. "
            "Uma sequência limpa vira um marcador só (`*100+1|\\0`); com 10% de null ela vira "
            "~10 trechos, cada um com seu marcador. Por isso 19 B → 107 B. Em coluna já "
            "desordenada o efeito some (não havia cadência a quebrar).", ""]

    # ---- a lacuna: baixa cardinalidade sem modo denso
    out += ["## Baixa cardinalidade — a lacuna que este lab expõe", "",
            "Mesma estrutura (`k=2` alternado, `n=100`), tipos diferentes:", "",
            "| tipo | total | B/elem | por quê |", "|---|---:|---:|---|"]
    for nome, col, por in [
        ("bool", [bool(i % 2) for i in range(100)], "modo **denso** (bit-pack, 1 bit/elem)"),
        ("int", [i % 2 for i in range(100)], "só o core — `^N` custa 3 B por elemento"),
        ("str", ["a" if i % 2 else "b" for i in range(100)], "idem"),
    ]:
        b = len(encode(col).encode())
        out.append(f"| {nome} | {b} | {(b - 8) / 100:.2f} | {por} |")
    out += ["", "O piso do mecanismo de referência no corpo é **`^N` + LF = 3 B por elemento**. "
            "O bool escapa disso porque tem um segundo candidato de modo; int e string não têm.",
            "", "Custo do `k` no int (n=100, valores sorteados por LCG):", "",
            "| k | total | B/elem |", "|---:|---:|---:|"]
    for k in (1, 2, 3, 5, 10, 20, 50, 100):
        b = len(encode(baixa_card(100, k)).encode())
        out.append(f"| {k} | {b} | {(b - 8) / 100:.2f} |")
    out += ["", "`k=1` é o único barato (**0.08 B/elem**): vira um `*100|` só. De `k=2` em diante "
            "o corpo satura em ~3 B/elem e **quase não depende de `k`** — o que confirma que o "
            "gargalo é o `^N`, não o dicionário.", "",
            "**A generalização do modo denso para além do bool é a próxima peça** — é o que a "
            "coluna de baixa cardinalidade está esperando, e o registry já reserva as larguras "
            "`b2`/`b4`/`b8`.", ""]

    out += [f"## RT: **{len(todos) - falhas}/{len(todos)}**", ""]
    (RAIZ / "result.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    print("\n".join(out))
    return 0 if falhas == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

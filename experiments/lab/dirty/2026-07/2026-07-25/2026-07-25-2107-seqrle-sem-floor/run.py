"""Lab 2026-07-25-2107 — o seq-RLE aplica SEM FLOOR (achado do owner).

O owner olhou `C-ruido-n100-wire.tcf` e viu marcadores de delta em dado aleatório:

    *2+498217|\\168116      18 B   (marcador com delta)
    \\168116⏎\\666333⏎      16 B   (os dois literais crus)

O delta custa +2 B nesse par. A suspeita: o custo do marcador não entra na decisão.

CONFIRMADO no código — `hcc_seqrle.encode` termina com:

    compacted, info = compact_body(body_lines)
    return "\\n".join(compacted) + "\\n"        # sem comparar com body_text

Aplica sempre. Este lab mede as TRÊS formas em cada regime, para dimensionar o FLOOR
antes de soldar.

  bruto   pipeline com `hcc_seq_rle=False` — o corpo que o `super().encode` produz
  sempre  o comportamento ATUAL (compacta incondicionalmente)
  floor   `min(bruto, sempre)` — o que a correção emitiria

Métrica: **bytes** (decisão do owner nesta frente). RT validado nas duas formas reais.
"""
import dataclasses
import json
import pathlib
import sys

RAIZ = pathlib.Path(__file__).parent
REPO = RAIZ.parents[5]
sys.path.insert(0, str(REPO / "src"))

from tcf import decode, encode  # noqa: E402
from tcf.encoder import _encode_column  # noqa: E402
from tcf.pipeline import DEFAULT_PIPELINE  # noqa: E402

SEM_SEQRLE = dataclasses.replace(DEFAULT_PIPELINE, hcc_seq_rle=False)

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
    """Mede as 3 formas. `dados` é list[str] OU list[int] — o wire sai pela rota real."""
    _wj(RAIZ / "inputs" / f"{eid}-fonte.json", {"nota": nota, "dados": dados})
    _wj(RAIZ / "intermediates" / f"{eid}-dataset-consumido.json", dados)

    literais = [str(v) for v in dados]
    corpo_sempre = _encode_column(literais)                      # comportamento ATUAL
    corpo_bruto = _encode_column(literais, cfg=SEM_SEQRLE)       # sem seq-RLE

    w = encode(dados)                                            # wire REAL (rota completa)
    (RAIZ / "outputs" / f"{eid}-wire.tcf").write_text(w, encoding="utf-8")
    cab = w.partition("\n")[0] + "\n"
    # variante hipotética: mesmo cabeçalho, corpo sem seq-RLE (é um wire VÁLIDO — o
    # decode não exige o marcador, ele só o expande quando existe)
    w_bruto = cab + corpo_bruto
    (RAIZ / "outputs" / f"{eid}-sem-seqrle.tcfp").write_text(w_bruto, encoding="utf-8")
    _wj(RAIZ / "outputs" / f"{eid}-equivalente.json", dados, compacto=True)
    volta = decode(w)
    _wj(RAIZ / "outputs" / f"{eid}-dataset.roundtrip.json", volta)

    ns, nb = len(corpo_sempre.encode()), len(corpo_bruto.encode())
    return {"id": eid, "n": len(dados), "sempre": ns, "bruto": nb, "floor": min(ns, nb),
            "rt_sempre": volta == dados, "rt_bruto": decode(w_bruto) == dados,
            "wire": w, "corpo_sempre": corpo_sempre}


# ------------------------------------------------------------------ matriz
def ruido(n, k, seed=7):
    g = _lcg(seed)
    return [next(g) % k for _ in range(n)]


GRUPOS = {
    "A. SENSÍVEIS — onde o marcador de delta não paga": [
        (f"A-ruido{k}-n{n}", ruido(n, k), f"aleatório 0..{k - 1}, n={n}")
        for k in (10, 100, 10 ** 6) for n in (100, 1000)
    ] + [
        ("A-uuid-n200", [f"{i * 2654435761 % (16 ** 8):08x}-a" for i in range(200)],
         "hex pseudo-aleatório (string)"),
        ("A-precos-n200", [round(1 + (i * 37 % 9999) / 100, 2) for i in range(200)],
         "preços com 2 casas, sem ordem"),
    ],
    "B. FAVORÁVEIS — onde o seq-RLE ganha (o FLOOR não pode estragar)": [
        ("B-seq-n1000", list(range(1000)), "0..999 crescente"),
        ("B-passo5-n200", [i * 5 for i in range(200)], "passo 5"),
        ("B-ids-n200", [100000 + i for i in range(200)], "ids consecutivos"),
        ("B-datas-n200", [f"2026-{(i % 12) + 1:02d}-{(i % 28) + 1:02d}" for i in range(200)],
         "datas ISO (string)"),
        ("B-emails-n200", [f"user{i}@dominio{i % 7}.com" for i in range(200)],
         "emails sintéticos (string)"),
    ],
    "C. MISTOS — a fronteira": [
        ("C-seq-com-ruido", [i if i % 3 else ruido(1, 10 ** 6, i + 1)[0] for i in range(200)],
         "sequencial com 1/3 de ruído injetado"),
        ("C-blocos", [i if i < 100 else ruido(1, 10 ** 6, i)[0] for i in range(200)],
         "100 sequenciais + 100 aleatórios"),
        ("C-quase-seq", [i + (1 if i % 50 == 0 else 0) for i in range(200)],
         "sequencial com saltos raros"),
    ],
}


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    out = ["# seq-RLE sem FLOOR — dimensionando a correção (2026-07-25-2107)", "",
           "`bruto` = corpo com `hcc_seq_rle=False` · `sempre` = comportamento ATUAL "
           "(compacta incondicionalmente) · `floor` = `min` dos dois, que é o que a "
           "correção emitiria. Bytes do **corpo**.", ""]
    todos, falhas = [], 0
    for titulo, casos in GRUPOS.items():
        out += [f"## {titulo}", "",
                "| id | n | bruto | sempre | floor | o FLOOR economiza | RT |",
                "|---|---:|---:|---:|---:|---:|---|"]
        for eid, dados, nota in casos:
            r = caso(eid, dados, nota)
            todos.append(r)
            falhas += (not r["rt_sempre"]) + (not r["rt_bruto"])
            econ = r["sempre"] - r["floor"]
            out.append(f"| `{eid}` | {r['n']} | {r['bruto']} | {r['sempre']} | "
                       f"**{r['floor']}** | {('+' + str(econ) + ' B') if econ else '—'} | "
                       f"{'OK' if r['rt_sempre'] and r['rt_bruto'] else 'FALHOU'} |")
        out += [""]

    econ_tot = sum(r["sempre"] - r["floor"] for r in todos)
    piorou = [r for r in todos if r["floor"] < r["sempre"]]
    out += ["## Resumo", "",
            f"- **RT: {2 * len(todos) - falhas}/{2 * len(todos)}** (as duas formas decodam — "
            "o corpo sem marcador é um wire válido, o decode só expande o que existe)",
            f"- o seq-RLE **piorava** em **{len(piorou)} de {len(todos)}** casos",
            f"- economia total do FLOOR nesta matriz: **{econ_tot} B**",
            f"- **em nenhum caso o FLOOR piora** (é `min`, nunca-pior por construção)", ""]

    out += ["## Evidência — o marcador que não paga", "", "```"]
    r = next(x for x in todos if x["id"] == "A-ruido1000000-n100")
    linhas = r["corpo_sempre"].split("\n")[:4]
    for ln in linhas:
        if ln.startswith("*"):
            _pre, _sep, tpl = ln.partition("|")
            out.append(f"{ln!r}")
            out.append(f"    marcador: {len(ln.encode())} B")
    out += ["```", "",
            "Um `*2+<delta>|<template>` só compensa se `len(marcador) < len(as 2 linhas "
            "cruas)`. Com delta de 6 dígitos e template de 6 dígitos, não compensa.", ""]

    (RAIZ / "result.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    print("\n".join(out))
    return 0 if falhas == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

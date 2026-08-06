"""Lab 2026-07-31-2350 — T-DENSO-B2: denso ternário `#TCF.8b2<n>`, ganho MEDIDO.

O denso b1 (bool puro SEM null) está soldado com domínio IMPLÍCITO (`false=0, true=1`) —
47 B para n=200. O bool COM null (ternário) cai no core: 546 B. O lab vizinho
`2026-07-28-0829` mostrou que o bN tipado COM domínio declarado (`#TCF.8bB2c8`) leva o
ternário a 94 B. Mas `true`/`false`/`null` são tipos PUROS do JSON — o domínio é conhecido
a priori, declará-lo é redundante.

Proposta medida aqui: **denso ternário `#TCF.8b2<n>`** — mesma grafia posicional do b1,
modo `2` no índice 7, payload base64 de índices a 2 bits, domínio implícito congelado
`0=null, 1=false, 2=true` (símbolo 3 = reservado, fail-loud).

Mede:
  A. o ganho por coluna — core hoje × bN tipado declarado × denso b2, com RT por coluna
  B. onde o b2 PERDE ou NÃO se aplica (n pequeno; bool-constante; bool-puro usa b1)
  C. colunas REAIS (Adult, nulls injetados deterministicamente)
  D. fail-loud: símbolo 3, payload truncado, b64 não-canônico

`src/tcf` intocado — proposta, não solda.
"""
import base64
import csv
import json
import pathlib
import sys

RAIZ = pathlib.Path(__file__).parent
REPO = RAIZ.parents[5]
VIZINHO = RAIZ.parents[1] / "2026-07-28" / "2026-07-28-0829-bn-tipado-ganho-medido"
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(VIZINHO))

from denso_b2 import proto_decode, proto_encode  # noqa: E402
from tipado_bn import proto_encode as bn_encode  # noqa: E402  (bN tipado do lab vizinho)

from tcf import decode, encode  # noqa: E402
from tcf.bitpack import pack_w  # noqa: E402

for d in ("inputs", "intermediates", "outputs"):
    (RAIZ / d).mkdir(exist_ok=True)

SAMPLES = REPO / "datasets" / "samples"


def _wj(p, obj):
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2, default=str) + "\n",
                 encoding="utf-8")


def rt_estrito(obtido, esperado):
    """Valor **E** tipo, com guarda de comprimento (`zip` trunca — lição 2026-07-26)."""
    if len(obtido) != len(esperado):
        return False
    if obtido != esperado:
        return False
    return all(type(a) is type(b) for a, b in zip(obtido, esperado))


def caso(nome, dados, gravar=True):
    hoje_w = encode(dados)
    hoje = len(hoje_w.encode())
    bn_w, _t, _w = bn_encode(dados)                  # None se o bN recusa/não se aplica
    bn = len(bn_w.encode()) if bn_w else None
    b2_w, tag, _w2 = proto_encode(dados)             # None se bool puro sem null / não-bool
    r = {"nome": nome, "n": len(dados), "tag": tag, "hoje": hoje, "bn": bn,
         "b2": len(b2_w.encode()) if b2_w else None,
         "rt_core": rt_estrito(decode(hoje_w), dados),
         "rt_b2": None, "cab": hoje_w.split("\n")[0]}
    if b2_w:
        obtido = proto_decode(b2_w)
        r["rt_b2"] = rt_estrito(obtido, dados)
        r["cab_b2"] = b2_w.split("\n")[0]
        if gravar:
            (RAIZ / "outputs" / f"{nome}-b2.tcf").write_text(b2_w, encoding="utf-8")
            rt_path = RAIZ / "outputs" / f"{nome}-dataset.roundtrip.json"
            _wj(rt_path, obtido)
            cons = RAIZ / "intermediates" / f"{nome}-dataset-consumido.json"
            _wj(cons, dados)
            # roundtrip é ARQUIVO diffável, byte-idêntico ao consumido
            assert rt_path.read_bytes() == cons.read_bytes(), nome
    elif gravar:
        obtido = decode(hoje_w)
        rt_path = RAIZ / "outputs" / f"{nome}-dataset.roundtrip.json"
        _wj(rt_path, obtido)
        cons = RAIZ / "intermediates" / f"{nome}-dataset-consumido.json"
        _wj(cons, dados)
        assert rt_path.read_bytes() == cons.read_bytes(), nome
    if gravar:
        _wj(RAIZ / "inputs" / f"{nome}-fonte.json",
            {"coluna": nome, "n": len(dados), "tag": tag,
             "w": 2 if b2_w else 0, "amostra": dados[:6]})
        (RAIZ / "outputs" / f"{nome}-hoje.tcf").write_text(hoje_w, encoding="utf-8")
        if bn_w:
            (RAIZ / "outputs" / f"{nome}-bn-tipado.tcfp").write_text(bn_w, encoding="utf-8")
    return r


def _c(v):
    return "—" if v is None else str(v)


def linha(r):
    rt = "—" if r["rt_b2"] is None else ("OK" if r["rt_b2"] else "**FALHOU**")
    deltas = []
    if r["bn"] is not None:
        deltas.append(f"{r['bn'] - r['hoje']:+}")
    if r["b2"] is not None:
        deltas.append(f"**{r['b2'] - r['hoje']:+}**")
    return (f"| `{r['nome']}` | {r['n']} | `{r['tag'] or '—'}` | {r['hoje']} | "
            f"{_c(r['bn'])} | {_c(r['b2'])} | {' / '.join(deltas) or '—'} | {rt} |")


CAB = ["| coluna | n | tag | hoje | bN tipado | b2 | Δ hoje→bN / →b2 | RT b2 |",
       "|---|---:|:-:|---:|---:|---:|---|:-:|"]


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    falhas = []
    out = ["# T-DENSO-B2 — denso ternário `#TCF.8b2<n>`, o ganho medido (2026-07-31-2350)",
           "",
           "O denso **b1** (bool puro SEM null) está soldado com domínio implícito — 47 B "
           "para n=200. O ternário (bool COM null) cai no core — 546 B. O lab vizinho "
           "`2026-07-28-0829` levou o ternário a 94 B com o bN tipado de domínio "
           "**declarado** (`#TCF.8bB2c8`). Este lab mede a pergunta que ficou: se o domínio "
           "é conhecido a priori (`null`/`false`/`true` são tipos puros do JSON), **declarar "
           "o domínio é redundante** — dá pra congelar `0=null, 1=false, 2=true` e ir a "
           "**2 bits/símbolo** na mesma grafia posicional do b1.",
           "",
           "```",
           "#TCF.8 b 2 c8",
           "       │ │ └── n em hex (200)",
           "       │ └──── modo = 2 bits/símbolo, ÍNDICE 7  <- o slot JA' existe",
           "       └──────── tag de tipo, índice 6",
           "```",
           "",
           "Símbolo **3 = reservado** — fail-loud no decode (seção D). O mecanismo é o "
           "MESMO `pack_w`/`unpack_w` soldado do b1 (`src/tcf/bitpack.py`), só com `w=2`.",
           ""]

    # ================================================================ A: o ganho
    out += ["## A — o ganho, por coluna (n=200)", ""] + CAB
    casos = {
        "bool-null": [None if i % 3 == 0 else bool(i % 2) for i in range(200)],
        "bool-null-esparso": [None if i % 17 == 0 else bool(i % 2) for i in range(200)],
        "bool-puro": [bool(i % 2) for i in range(200)],
        "bool-constante": [True] * 200,
    }
    for nome, dados in casos.items():
        r = caso(nome, dados)
        if r["rt_b2"] is False or not r["rt_core"]:
            falhas.append(nome)
        out.append(linha(r))
    out += ["",
            "O `bool-puro` e o `bool-constante` têm `b2 = —` **de propósito**: sem null, o "
            "protótipo RECUSA — o denso b1 soldado é estritamente menor (2 bits vs 1 bit por "
            "símbolo). O b2 só compete onde o b1 não alcança: **bool com null**.", ""]

    # ================================================================ B: onde perde / não se aplica
    out += ["## B — onde o b2 PERDE ou não se aplica", "",
            "Varredura de `n`, densidade de null ~1/3 (ternário completo). Sem estes, a "
            "tabela A não significa nada.", ""] + CAB
    for n in (3, 10, 50, 200, 1000):
        dados = [None if i % 3 == 0 else bool(i % 2) for i in range(n)]
        r = caso(f"bool-varre-n{n:04d}", dados, gravar=(n in (200, 1000)))
        if r["rt_b2"] is False:
            falhas.append(f"bool-varre-n{n:04d}")
        out.append(linha(r))
    out += ["",
            "**O b2 vence em TODO o intervalo medido, inclusive n=3** (14 B vs 21 do core) — "
            "diferente do bN tipado, que perde em n pequeno porque o domínio declarado viaja "
            "(28 B em n=3). O domínio implícito zera esse custo fixo: header de ~11 B + "
            "`ceil(2n/8)` bytes de payload. Onde o b2 NÃO se aplica: bool puro sem null "
            "(recusa — o b1 de 1 bit domina) e `k≤1` sem null (recusa — o RLE do core é "
            "ótimo). O b2 é **mais um candidato do `min()`**, não substituto de nada.", ""]

    # ================================================================ C: reais
    out += ["## C — colunas REAIS", "",
            "Conversão idêntica à do lab vizinho (`datasets/samples/adult-census/"
            "adult-sample.csv`), com nulls injetados **deterministicamente a cada 7º "
            "elemento** para formar o ternário real-ish. Escolha DO LAB, não do dado — "
            "declarado em `datasets-provenance.md`.", ""] + CAB
    reais = [
        ("real-adult-sex-bool-ternario", "adult-census/adult-sample.csv", "sex",
         lambda v: v.strip() == "Male"),
        ("real-adult-class-bool-ternario", "adult-census/adult-sample.csv", "class",
         lambda v: ">" in v),
    ]
    for nome, rel, col, conv in reais:
        p = SAMPLES / rel
        if not p.exists():
            continue
        with p.open(encoding="utf-8", newline="") as f:
            rd = csv.DictReader(f)
            if col not in (rd.fieldnames or []):
                raise KeyError(f"{col!r} nao existe em {rel}")
            vals = [conv(row[col]) for row in rd if row[col] not in ("", "NA")][:2000]
        dados = [None if i % 7 == 0 else v for i, v in enumerate(vals)]
        r = caso(nome, dados)
        if r["rt_b2"] is False:
            falhas.append(nome)
        out.append(linha(r))
    out.append("")

    # ================================================================ D: fail-loud
    base = [None if i % 3 == 0 else bool(i % 2) for i in range(200)]
    wire_ok, _, _ = proto_encode(base)
    b64_ok = wire_ok.split("\n", 1)[1]
    casos_fl = []

    # 1. símbolo 3 = RESERVADO
    idx3 = [0 if x is None else (2 if x else 1) for x in base]
    idx3[5] = 3
    w3 = f"#TCF.8b2{len(base):x}\n" + base64.b64encode(pack_w(idx3, 2)).decode("ascii")
    casos_fl.append(("símbolo 3 no payload (RESERVADO)", w3))
    # 2. payload truncado (1 byte a menos)
    casos_fl.append(("payload truncado (1 byte a menos)",
                     f"#TCF.8b2{len(base):x}\n" + b64_ok[:-4]))
    # 3. b64 não-canônico (caractere fora do alfabeto)
    casos_fl.append(("b64 não-canônico (`!` no payload)",
                     f"#TCF.8b2{len(base):x}\n!" + b64_ok[1:]))

    fl_out = ["# fail-loud — denso b2 (gerado por run.py)", ""]
    ok_fl = 0
    for desc, w in casos_fl:
        try:
            proto_decode(w)
            fl_out.append(f"[FALHOU] {desc}: decodificou calado")
            falhas.append(f"fail-loud: {desc}")
        except ValueError as e:
            fl_out.append(f"[OK] {desc}")
            fl_out.append(f"     ValueError: {e}")
            ok_fl += 1
        except Exception as e:  # noqa: BLE001 — evidencia, mas conta como falha
            fl_out.append(f"[FALHOU] {desc}: excecao nao-ValueError: {type(e).__name__}: {e}")
            falhas.append(f"fail-loud: {desc}")
    (RAIZ / "outputs" / "fail-loud.txt").write_text("\n".join(fl_out) + "\n",
                                                    encoding="utf-8")
    out += ["## D — fail-loud", "",
            "Evidência em `outputs/fail-loud.txt` e assert no `run.py` (sai 1 se qualquer "
            "caso decodificar calado):", "",
            "```", "\n".join(fl_out), "```", ""]

    # ================================================================ resumo + RT
    b200 = caso("bool-null", casos["bool-null"], gravar=False)
    out += ["## Round-trip e resumo", "",
            "`RT` compara **valor, tipo e comprimento**. Roundtrip é ARQUIVO: "
            "`outputs/<nome>-dataset.roundtrip.json` byte-idêntico a "
            "`intermediates/<nome>-dataset-consumido.json` (assert no `run.py`).", "",
            f"- estimativa prévia para n=200: header `#TCF.8b2c8\\n` (11 B) + b64 de "
            f"50 B (68 chars) ≈ **79 B**. Medido: **{b200['b2']} B** "
            f"(core {b200['hoje']} B, bN tipado {b200['bn']} B).",
            f"- fail-loud: **{ok_fl}/{len(casos_fl)}** casos rejeitados com `ValueError`.",
            f"- RT estrito: **{'100%' if not falhas else f'FALHAS: {falhas}'}**.", "",
            "## Limites", "",
            "- **Nada soldado**; `src/tcf` intocado. Os `-b2.tcf` são proposta — o `decode` "
            "público ainda não conhece o modo `2`.",
            "- Domínio congelado `0=null, 1=false, 2=true` — se um dia o b1 mudar a ordem, "
            "o b2 tem de seguir (os dois compartilham o conceito de domínio implícito).",
            "- gzip e CPU não medidos.",
            "- Colunas reais: nulls injetados pelo lab (a cada 7º elemento), não do dado.",
            ""]

    (RAIZ / "result.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    print("\n".join(out))
    return 0 if not falhas else 1


if __name__ == "__main__":
    sys.exit(main())

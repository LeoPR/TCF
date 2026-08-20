"""O `split` explicado com dado de controle — o que ele EXPÕE, e quando não expõe nada.

A IDEIA EM UMA FRASE
--------------------
O `split` não comprime. Ele **descola** valores estruturados para que a redundância
que já existia — mas estava colada — fique alcançável pelo `dict`.

    "123.45"  ->  a repetição de `.45` entre linhas existe, mas está PRESA ao `123`.
                  Nenhum mecanismo a enxerga: cada valor parece único.
    split     ->  campo0=["123", ...]  campo1=["45", ...]
                  agora o campo1 tem 100 valores possíveis, e o `dict` esmaga.

O SLOT (ADR-0026)
-----------------
    %<size>=<nome>                        no meta da coluna
    slot = <ntmpl>\\n<template><subtabela>

    <template>   = (<bytelen>:<bytes>) por parte NÃO-dígito
    <subtabela>  = um multi-col aninhado com os campos c0, c1, ...
                   (cada campo volta a passar pelo min(tcf,raw,dict))

O GATE — por que ele recusa
---------------------------
Template 100% uniforme · ≥2 campos · algum campo não-constante. Sem exceção:
o refinamento mediu 1 near-miss em 80 colunas reais e concluiu que não valia.

CADA CASO AQUI ISOLA UMA LIÇÃO. Valores minúsculos, wire legível.
Evidência em `outputs/` (§RT em tudo). `src/tcf` INTOCADO.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

AQUI = Path(__file__).parent
RAIZ = AQUI.parents[5]
sys.path.insert(0, str(RAIZ / "src"))

IN = AQUI / "inputs"
OUT = AQUI / "outputs"
for d in (IN, OUT):
    d.mkdir(parents=True, exist_ok=True)

from tcf import encode, decode                          # noqa: E402
from tcf.multi.core import _fallback_safe               # noqa: E402
from tcf.multi.dict_v2b import _v2b_encode              # noqa: E402
from tcf.multi.split import _struct_split_encode        # noqa: E402
from tcf.pipeline import DEFAULT_PIPELINE               # noqa: E402


def B(t):
    return len(t.encode("utf-8")) if isinstance(t, str) else len(t)


def candidatos(vals):
    """Os 4 candidatos do min() por coluna, medidos separadamente."""
    c = {"tcf": B(encode(vals, stamp=False))}
    if _fallback_safe(vals):
        c["raw"] = B("\n".join(vals))
    vb = _v2b_encode(vals, cfg=DEFAULT_PIPELINE, min_len=None)
    if vb is not None:
        c["dict"] = len(vb)
    sb = _struct_split_encode(vals, cfg=DEFAULT_PIPELINE, min_len=None)
    if sb is not None:
        c["split"] = len(sb)
    return c


def anatomia_split(vals):
    """Abre o slot do split e devolve (template, campos) em forma legível."""
    b = _struct_split_encode(vals, cfg=DEFAULT_PIPELINE, min_len=None)
    if b is None:
        return None
    nl = b.find(b"\n")
    ntmpl = int(b[:nl])
    tmpl = b[nl + 1:nl + 1 + ntmpl]
    sub = b[nl + 1 + ntmpl:]
    partes, i = [], 0
    while i < len(tmpl):
        c = tmpl.find(b":", i)
        L = int(tmpl[i:c])
        i = c + 1
        partes.append(tmpl[i:i + L].decode("utf-8"))
        i += L
    ftable = decode(sub.decode("utf-8"))
    nf = len(partes) - 1
    campos = [ftable[f"c{k}"] for k in range(nf)]
    return {"partes": partes, "campos": campos, "sub_header": sub.split(b"\n", 1)[0].decode()}


def mostra(cid, titulo, licao, vals):
    print("\n" + "=" * 86)
    print(f"{cid} — {titulo}")
    print("=" * 86)
    print(f"  LIÇÃO: {licao}")
    print(f"  coluna ({len(vals)} valores, {len(set(vals))} distintos):")
    print(f"    {vals[:6]}{' …' if len(vals) > 6 else ''}")

    cand = candidatos(vals)
    a = anatomia_split(vals)

    if a is None:
        print("\n  O GATE RECUSOU — o split não se aplica aqui.")
    else:
        print("\n  COMO O SPLIT DESCOLA:")
        moldura = "  ".join(f"[{p!r}]" if p else "[]" for p in a["partes"])
        print(f"    template (as partes NÃO-dígito): {moldura}")
        for k, campo in enumerate(a["campos"]):
            print(f"    campo c{k}: {campo[:6]}{' …' if len(campo) > 6 else ''}"
                  f"   -> {len(set(campo))} distintos de {len(campo)}")
        print(f"    sub-tabela: {a['sub_header']}")
        print("\n  A REDUNDÂNCIA QUE ESTAVA ESCONDIDA:")
        print(f"    coluna inteira        : {len(set(vals))} distintos de {len(vals)}"
              f"  ({len(set(vals))/len(vals)*100:.0f}%)")
        for k, campo in enumerate(a["campos"]):
            print(f"    campo c{k} isolado     : {len(set(campo))} distintos de {len(campo)}"
                  f"  ({len(set(campo))/len(campo)*100:.0f}%)")

    print("\n  OS CANDIDATOS (o min() escolhe o menor):")
    menor = min(cand, key=cand.get)
    for nome, b in sorted(cand.items(), key=lambda x: x[1]):
        marca = "  <- VENCE" if nome == menor else ""
        print(f"    {nome:6} {b:>6} B{marca}")
    if "split" in cand and menor != "split":
        pior = (cand['split'] / cand[menor] - 1) * 100
        print(f"    (o split existe mas PERDE por {pior:+.0f}%)")

    # evidencia
    wire = encode({cid: vals})
    assert decode(wire) == {cid: vals}, f"{cid}: RT falhou"
    (IN / f"{cid}.json").write_text(json.dumps(vals, ensure_ascii=False),
                                    encoding="utf-8", newline="")
    (OUT / f"{cid}.tcf").write_text(wire, encoding="utf-8", newline="")
    (OUT / f"{cid}.roundtrip.json").write_text(
        json.dumps(decode(wire)[cid], ensure_ascii=False), encoding="utf-8", newline="")
    print(f"\n  WIRE REAL ({B(wire)} B, modo do meta = {wire[7:8]!r}):")
    for ln in wire.split("\n")[:7]:
        print(f"    {ln!r}")
    if wire.count("\n") > 7:
        print("    …")
    return {"caso": cid, "licao": licao, "n": len(vals),
            "distintos": len(set(vals)), "candidatos": cand,
            "vence": menor, "bytes_wire": B(wire),
            "campos_distintos": [len(set(c)) for c in a["campos"]] if a else None}


# ── os casos: cada um isola UMA lição ──────────────────────────────────────
def main():
    print("=" * 86)
    print("O SPLIT, COM DADO DE CONTROLE")
    print("=" * 86)
    print("O split NÃO comprime — ele DESCOLA para que o `dict` alcance o que já era")
    print("redundante. Cada caso abaixo isola uma lição.")

    res = []

    # 1. o caso canônico: decimal
    precos = [f"{p}.{c:02d}" for p in
              [12, 45, 7, 103, 88, 45, 12, 250, 7, 61, 45, 12]
              for c in [0, 50, 99]][:24]
    res.append(mostra(
        "c1-decimal", "decimal — o caso canônico",
        "a fração tem 3 valores; colada no inteiro, some. Descolada, o dict esmaga.",
        precos))

    # 2. data ISO: 3 campos, ano quase-constante
    datas = [f"2026-{m:02d}-{d:02d}" for m in (1, 2, 3) for d in (5, 12, 19, 26)] * 2
    res.append(mostra(
        "c2-data-iso", "data ISO — o ano é quase-constante",
        "c0 (ano) tem 1 distinto; c1 (mês) 3; c2 (dia) 4. Juntos: 12 combinações.",
        datas))

    # 3. onde NÃO há redundância a expor
    import random
    rng = random.Random(7)
    ids = [f"{rng.randrange(10**6):06d}.{rng.randrange(10**6):06d}" for _ in range(24)]
    res.append(mostra(
        "c3-alta-card", "dois campos de ALTA cardinalidade",
        "o split aplica, mas não há repetição em campo nenhum — não expõe nada.",
        ids))

    # 4. o gate recusa: template NÃO-uniforme
    misto = ["12.50", "7.99", "1.234,56", "88.10", "3.00", "R$ 45"]
    res.append(mostra(
        "c4-gate-recusa", "template NÃO-uniforme — o gate recusa",
        "separadores e nº de campos variam. Sem template comum, não há como descolar.",
        misto))

    # 5. 1 campo só: nada a descolar
    inteiros = [str(rng.randrange(1000)) for _ in range(24)]
    res.append(mostra(
        "c5-um-campo", "sem separador — nada a descolar",
        "o gate exige >=2 campos. Um número puro já é um campo só.",
        inteiros))

    # 6. telefone BR: o caso que motivou a pergunta
    fones = [f"(11) 9{rng.randrange(10**4):04d}-{rng.randrange(10**4):04d}"
             for _ in range(12)] + \
            [f"(21) 9{rng.randrange(10**4):04d}-{rng.randrange(10**4):04d}"
             for _ in range(12)]
    res.append(mostra(
        "c6-telefone", "telefone BR — DDD baixo, número alto",
        "c0 (DDD) tem 2 distintos e vira dict; o resto é ruído. Ganho parcial.",
        fones))

    print("\n" + "=" * 86)
    print("RESUMO")
    print("=" * 86)
    print(f"  {'caso':16} {'distintos':>10} {'vence':>8} {'campos (distintos)':>22}")
    for r in res:
        campos = (str(r["campos_distintos"]) if r["campos_distintos"]
                  else "— (gate recusou)")
        print(f"  {r['caso']:16} {r['distintos']:>4}/{r['n']:<5} {r['vence']:>8} {campos:>22}")

    print("\n  A REGRA, em uma linha:")
    print("  o split paga quando ALGUM campo, isolado, tem cardinalidade MUITO menor")
    print("  que a coluna inteira — porque é essa diferença que o `dict` colhe.")

    (AQUI / "resultado.json").write_text(json.dumps(res, ensure_ascii=False, indent=1),
                                         encoding="utf-8", newline="")
    n_tcf = len(list(OUT.glob("*.tcf")))
    assert n_tcf == len(res), f"evidencia incompleta: {n_tcf} de {len(res)}"
    print(f"\n-> {n_tcf} wires + roundtrips em outputs/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

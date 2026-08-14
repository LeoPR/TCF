# -*- coding: utf-8 -*-
"""Um PARÂMETRO de tolerância para float — protótipo e verificação.

    python run.py

## A pergunta (uma só)

> Direção do owner (2026-08-14): *"vamos refazer um para implementar algo com um parâmetro
> complementar pra float caso a gente queira que ele tenha tolerância."*

Então: **dá para declarar tolerância como parâmetro, derivar a precisão dela, e VERIFICAR que
a promessa foi cumprida?**

## Prior art (o owner lembrou certo)

`docs/workbench/_archive/tickets/frozen/H-smart-rounding.md` (2026-04-10, status OPEN)
desenhou `EncodeConfig(max_error_pct=0.001, aggregate_columns=["total"])` e listou a
*"precisão derivada de tolerância"* como a alternativa 3, marcada **(inovação)**. **As 4
tarefas do ticket estão desmarcadas** — nunca foi implementado nem testado. Este lab é o teste.

O que mudou desde lá: o ticket tinha **um** eixo (`max_error_pct`). A medição do lab
`…-2010-perda-propagacao-de-erro` mostrou que a mesma perda vale 66,67% por valor, 0,00029%
na soma e 825,9% numa diferença — então o parâmetro precisa de **4 eixos + `mode`**.

## GATE

**Protótipo em lab, fora de `src/tcf`.** O formato é lossless-puro por decisão do owner
(2026-06-15); nada aqui é proposta de weld. O que se testa é a FORMA do parâmetro.

## O contrato deste lab

Como o valor muda de propósito, o RT contra a origem não se aplica. Valem:
1. **o contrato declarado** — cada eixo pedido é medido e tem de bater;
2. **o formato continua lossless sobre os ajustados** — `decode(encode(x̂)) == x̂`;
3. **fail-loud** — tolerância não realizável **recusa**, nunca entrega dado que viola o
   contrato que ele mesmo declara.
"""
from __future__ import annotations

import json
import math
import pathlib
import shutil
import sqlite3
import sys

RAIZ = pathlib.Path(__file__).parent
REPO = RAIZ.parents[5]
assert (REPO / "src" / "tcf").is_dir(), f"REPO errado: {REPO}"
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(RAIZ))

from tcf import decode, encode                                    # noqa: E402
from tolerancia import Tolerancia, aplica                         # noqa: E402

INP, INT, OUT = RAIZ / "inputs", RAIZ / "intermediates", RAIZ / "outputs"
JSON_KW = {"ensure_ascii": False, "indent": 1}


def _esc(p, t):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(t, encoding="utf-8", newline="")


def _js(p, o):
    _esc(p, json.dumps(o, **JSON_KW))


def B(t):
    return len(t.encode("utf-8"))


# ── os pedidos de tolerância que valem testar ───────────────────────────────
PEDIDOS = [
    ("rel-1pct", Tolerancia(rel=0.01),
     "1% por valor — a forma que o H-smart-rounding propunha (max_error_pct)"),
    ("rel-0-1pct", Tolerancia(rel=0.001), "10× mais apertado"),
    ("abs-meio-centavo", Tolerancia(abs=0.005), "bound absoluto — compõe sob SOMA"),
    ("quantum-centavo", Tolerancia(quantum=0.01),
     "grade de centavos — a forma FINANCEIRA (ISO 4217 minor unit)"),
    ("quantum-decimo", Tolerancia(quantum=0.1), "grade de 10 centavos"),
    ("agg-soma", Tolerancia(agg="soma"),
     "só preservar a soma, sem cortar precisão — realoca o resíduo"),
    ("quantum-decimo-agg", Tolerancia(quantum=0.1, agg="soma"),
     "COMPOSIÇÃO: grade de 0,10 E soma exata — a fatura que fecha"),
    ("rel-1pct-half-up", Tolerancia(rel=0.01, mode="half-up"),
     "mesmo bound, modo com VIÉS — a distinção do HMRC"),
    ("rel-1pct-down", Tolerancia(rel=0.01, mode="down"),
     "truncar: o modo que o HMRC nega a retalhistas"),
    ("apertado-vira-noop", Tolerancia(rel=1e-9),
     "MUITO apertado, mas realizável: deriva ~10 casas e vira NO-OP (lossless)"),
    ("impossivel-rel", Tolerancia(rel=1e-15),
     "deve RECUSAR: exigiria mais casas que o teto (12)"),
    ("impossivel-grade", Tolerancia(quantum=0.03),
     "deve RECUSAR: grade não-decimal (não é potência de 10)"),
]


def avalia(nome_col, vals, ideia, fonte):
    _js(INP / f"{nome_col}.entrada.json", vals)
    _js(INP / f"{nome_col}.fonte.json", fonte)
    w0 = encode(vals)
    assert decode(w0) == vals, f"baseline nao fez RT em {nome_col}"
    _esc(OUT / f"{nome_col}.baseline.tcf", w0)
    _js(OUT / f"{nome_col}.baseline.roundtrip.json", decode(w0))
    base = B(w0)
    print(f"\n  [{nome_col}] n={len(vals)} baseline={base} B — {ideia}")
    print(f"    {'pedido':>20} {'casas':>6} {'bytes':>7} {'red%':>6} "
          f"{'err/val':>9} {'err soma':>10} {'viés':>11} {'veredito':>9}")
    linhas, falhas = [], []
    for nome, tol, ideia_t in PEDIDOS:
        aj, laudo = aplica(vals, tol)
        laudo["coluna"] = nome_col
        laudo["ideia_do_pedido"] = ideia_t
        laudo["CONSTANTE_na_comparacao"] = ("a MESMA coluna e o MESMO encode; "
                                            "só muda a TOLERÂNCIA pedida")
        if aj is None:
            esperava_recusa = nome.startswith("impossivel")
            if not esperava_recusa:
                falhas.append(f"{nome_col}/{nome}: recusou sem ser um caso impossível — "
                              f"{laudo.get('veredito')}")
            print(f"    {nome:>20} {'—':>6} {'—':>7} {'—':>6} {'—':>9} {'—':>10} "
                  f"{'—':>11} {'RECUSA':>9}"
                  f"{'  <- esperado' if esperava_recusa else '  <- INESPERADO'}")
            laudo["bytes"] = None
        else:
            if nome.startswith("impossivel"):
                falhas.append(f"{nome_col}/{nome}: deveria RECUSAR e aceitou")
            w = encode(aj)
            fmt_ok = decode(w) == aj
            if not fmt_ok:
                falhas.append(f"{nome_col}/{nome}: o FORMATO não preservou os ajustados")
            v = laudo["estagio_C_verificar"]
            laudo["bytes"] = B(w)
            laudo["reducao_pct"] = round(100 * (1 - B(w) / base), 2)
            laudo["formato_lossless_sobre_ajustados"] = fmt_ok
            _esc(OUT / f"{nome_col}.{nome}.tcf", w)
            _js(OUT / f"{nome_col}.{nome}.roundtrip.json", decode(w))
            _js(OUT / f"{nome_col}.{nome}.meta.json", {
                "derivado_de": f"inputs/{nome_col}.entrada.json",
                "tolerancia": laudo["tolerancia"], "casas": v["casas_aplicadas"],
                "bytes": B(w), "checks": v["checks"],
                "AVISO": "valores AJUSTADOS de propósito — não são os originais"})
            print(f"    {nome:>20} {v['casas_aplicadas']:>6} {B(w):>7} "
                  f"{laudo['reducao_pct']:>5.1f}% {100*v['erro_rel_max']:>8.3f}% "
                  f"{100*v['erro_soma_rel']:>9.5f}% {v['viés_medio_por_valor']:>+11.2e} "
                  f"{laudo['veredito'][:9]:>9}")
        linhas.append(laudo)
    return linhas, falhas, base


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    for d in (INP, INT, OUT):
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(parents=True)
    todos, falhas = [], []

    print("SINTÉTICO — o controle, onde eu sei a resposta de cabeça")
    sint = [12.9, 3.5, 47.25, 8.0, 129.99, 4.5, 63.7, 21.15, 9.99, 250.0,
            0.07, 17.45, 6.3, 88.8, 33.33, 5.55, 41.2, 74.6, 2.99, 19.9]
    ls, fs, _ = avalia("sint-money", sint,
                       "20 preços, com um 0.07 plantado para AMARRAR o `rel`",
                       {"gerador": "run.py::main", "params": {"n": 20, "plantado": 0.07},
                        "ideia": "o menor valor manda no `rel` — quero ver isso acontecer",
                        "pin": "sintético viesado por construção"})
    todos += ls
    falhas += fs

    print("\nREAIS — do corpus (amostra espalhada, nunca LIMIT puro)")
    REAIS = [
        ("retail-UnitPrice", "online-retail",
         "SELECT UnitPrice FROM online_retail WHERE UnitPrice > 0",
         "money real: 2 casas, cauda inferior em 0,001"),
        ("wine-density", "wine-quality",
         "SELECT density FROM wine WHERE density IS NOT NULL",
         "medida física: 3-6 casas, faixa estreita 0,987-1,039"),
    ]
    for nome, db, sql, ideia in REAIS:
        try:
            con = sqlite3.connect(f"file:Z:/tcf-data/interim/{db}.db?mode=ro", uri=True)
            v = [float(r[0]) for r in con.execute(sql) if r[0] is not None]
            con.close()
        except Exception:
            print(f"  [{nome}] (sem Z: — pulado)")
            continue
        passo = max(1, len(v) // 2000)
        v = v[::passo][:2000]
        ls, fs, _ = avalia(nome, v, ideia,
                           {"gerador": "run.py::main", "db": db, "sql": sql,
                            "amostragem": f"passo espalhado 1-em-{passo}, alvo 2000",
                            "ideia": ideia,
                            "pin": "corpus local Z:/tcf-data/interim — não versionado"})
        todos += ls
        falhas += fs

    _js(INT / "laudos.json", todos)
    _js(RAIZ / "resultado.json", {"laudos": todos, "falhas": falhas})
    linhas = ["# INDEX — parâmetro de tolerância para float", "",
              "**Aviso**: os `.tcf` que não são `.baseline` contêm valores **ajustados de",
              "propósito**. O `roundtrip.json` prova que o FORMATO os preserva — não que são os",
              "originais. O original está em `inputs/<coluna>.entrada.json`.", "",
              "| coluna | pedido | casas | bytes | red% | cumpre? |", "|---|---|---|---|---|---|"]
    for x in todos:
        v = x.get("estagio_C_verificar", {})
        alvo = f"./{x['coluna']}.{'-'.join(k for k, val in x['tolerancia'].items() if val and k != 'mode')}.tcf"
        linhas.append(f"| {x['coluna']} | `{json.dumps({k: v2 for k, v2 in x['tolerancia'].items() if v2})}` "
                      f"| {v.get('casas_aplicadas', '—')} | {x.get('bytes') or '—'} "
                      f"| {x.get('reducao_pct', '—')} | {x['veredito'][:24]} |")
    _esc(OUT / "INDEX.md", "\n".join(linhas) + "\n")

    print(f"\n{len(falhas)} falha(s)")
    for f in falhas[:12]:
        print(f"  FALHA: {f}")
    return 1 if falhas else 0


if __name__ == "__main__":
    raise SystemExit(main())

# -*- coding: utf-8 -*-
"""A PERDA vista por cinco lentes — a mesma perda significa coisas diferentes.

    python run.py

## A pergunta (uma só)

> Direção do owner (2026-08-14): *"talvez fazer o loss ficar orientado à estatística de perdas
> e erros ajudaria. Se a perda significa algo como 1% numa soma ou multiplicação? não só pelo
> valor em si, mas se é financeiramente ou fisicamente coerente arredondar dentro de alguma
> margem dentro da realidade."*

Então: **o mesmo arredondamento, medido por cinco lentes diferentes** — por valor, na soma, na
média, num produto derivado real, e numa diferença de próximos.

## Por que este lab é diferente dos outros

Aqui o contrato **não é RT contra a origem** — o valor por linha MUDA de propósito. O que se
valida é:

1. o **contrato declarado** (a soma fica exata? o erro por linha cabe no bound?);
2. e, ainda assim, que **o formato continua lossless sobre os valores já arredondados** — o
   `encode/decode` dos arredondados tem de fechar idêntico. O PoC de junho não fez essa
   checagem (importou `decode` e nunca chamou), e por isso seus bytes saíram sem §RT.

## GATE

Tudo aqui é **medição**, nunca proposta. O formato é lossless-puro por decisão do owner
(2026-06-15); qualquer perda exige gate real-world N≥5 e decisão explícita. `src/tcf` intocado.
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

from tcf import decode, encode  # noqa: E402

INP, INT, OUT = RAIZ / "inputs", RAIZ / "intermediates", RAIZ / "outputs"
JSON_KW = {"ensure_ascii": False, "indent": 1}


def _esc(p, t):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(t, encoding="utf-8", newline="")


def _js(p, o):
    _esc(p, json.dumps(o, **JSON_KW))


def B(t):
    return len(t.encode("utf-8"))


def rel(a, b):
    return abs(a - b) / abs(b) if b else 0.0


def ingenuo(vals, d):
    return [round(v, d) for v in vals]


def maior_resto(vals, d):
    """Hamilton / largest remainder — preserva a SOMA exata na escala de `d`."""
    esc = 10 ** d
    pisos = [math.floor(v * esc) for v in vals]
    falta = round(sum(vals) * esc) - sum(pisos)
    ordem = sorted(range(len(vals)), key=lambda i: -(vals[i] * esc - pisos[i]))
    incr = set(ordem[:max(0, falta)])
    return [round((p + (1 if i in incr else 0)) / esc, d) for i, p in enumerate(pisos)]


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    for p in (INP, INT, OUT):
        if p.exists():
            shutil.rmtree(p)
        p.mkdir(parents=True)
    falhas = []

    # ── dado real: preco E quantidade, para haver um PRODUTO de verdade ─────
    try:
        con = sqlite3.connect("file:Z:/tcf-data/interim/online-retail.db?mode=ro", uri=True)
        linhas = list(con.execute(
            "SELECT UnitPrice, Quantity FROM online_retail "
            "WHERE UnitPrice > 0 AND Quantity > 0"))
        con.close()
    except Exception:
        print("sem Z:/tcf-data — este lab precisa de dado real com preco E quantidade")
        return 0
    passo = max(1, len(linhas) // 3000)
    linhas = linhas[::passo][:3000]
    preco = [float(r[0]) for r in linhas]
    qtd = [float(r[1]) for r in linhas]

    _js(INP / "retail-preco.entrada.json", preco)
    _js(INP / "retail-quantidade.entrada.json", qtd)
    _js(INP / "retail.fonte.json", {
        "gerador": "run.py", "db": "online-retail", "tabela": "online_retail",
        "colunas": ["UnitPrice", "Quantity"],
        "sql": "SELECT UnitPrice, Quantity ... WHERE UnitPrice > 0 AND Quantity > 0",
        "amostragem": f"passo espalhado 1-em-{passo}, alvo 3000 (nunca LIMIT puro)",
        "ideia": "precisa das DUAS colunas para haver um produto derivado REAL (receita)",
        "pin": "corpus local Z:/tcf-data/interim — nao versionado"})

    soma_ex = sum(preco)
    receita_ex = [p * q for p, q in zip(preco, qtd)]
    receita_total_ex = sum(receita_ex)
    base_w = encode(preco)
    assert decode(base_w) == preco, "baseline nao fez RT"
    _esc(OUT / "retail-preco.baseline.tcf", base_w)
    _js(OUT / "retail-preco.baseline.roundtrip.json", decode(base_w))
    base_b = B(base_w)

    print(f"online-retail: {len(preco)} linhas (passo {passo}); "
          f"soma={soma_ex:.2f}; receita={receita_total_ex:.2f}; baseline={base_b} B")
    print("\nAS CINCO LENTES — a MESMA perda, medida de cinco jeitos")
    print(f"{'d':>2} {'metodo':>12} {'bytes':>7} {'red%':>6} | {'por valor':>10} "
          f"{'SOMA':>10} {'MEDIA':>10} {'RECEITA':>10} {'REC/linha':>10} {'fmt ok':>7}")

    medicoes = []
    for d in (4, 3, 2, 1, 0):
        for rot, fn in (("ingenuo", ingenuo), ("maior-resto", maior_resto)):
            ap = fn(preco, d)
            w = encode(ap)
            # §RT sobre os JA' ARREDONDADOS: a perda e' o round, nao o formato
            fmt_ok = decode(w) == ap
            if not fmt_ok:
                falhas.append(f"d={d} {rot}: o FORMATO nao preservou os valores arredondados")
            rec = [a * q for a, q in zip(ap, qtd)]
            m = {"casas": d, "metodo": rot, "bytes": B(w),
                 "reducao_pct": round(100 * (1 - B(w) / base_b), 2),
                 "erro_max_por_valor_pct": round(100 * max(map(rel, ap, preco)), 4),
                 "erro_soma_pct": round(100 * rel(sum(ap), soma_ex), 6),
                 "erro_media_pct": round(100 * rel(sum(ap) / len(ap),
                                                   soma_ex / len(preco)), 6),
                 "erro_receita_total_pct": round(100 * rel(sum(rec), receita_total_ex), 6),
                 "erro_receita_max_linha_pct": round(100 * max(map(rel, rec, receita_ex)), 4),
                 "soma_exata": round(sum(ap) * 10 ** d) == round(soma_ex * 10 ** d),
                 "formato_lossless_sobre_arredondados": fmt_ok,
                 "CONTRATO": "exato-no-agregado" if rot == "maior-resto" else "por-valor",
                 "CONSTANTE_na_comparacao": "a MESMA coluna, o MESMO d, a MESMA quantidade; "
                                            "so' muda o METODO de arredondar"}
            medicoes.append(m)
            nome = f"d{d}-{rot}"
            _js(INP / f"{nome}.entrada.json", ap)
            _esc(OUT / f"{nome}.tcf", w)
            _js(OUT / f"{nome}.roundtrip.json", decode(w))
            _js(OUT / f"{nome}.meta.json", {
                "derivado_de": "inputs/retail-preco.entrada.json", "casas": d, "metodo": rot,
                "bytes": B(w), "contrato": m["CONTRATO"], "soma_exata": m["soma_exata"],
                "AVISO": "estes valores NAO sao os originais — a perda e' deliberada"})
            print(f"{d:>2} {rot:>12} {B(w):>7} {m['reducao_pct']:>5.1f}% | "
                  f"{m['erro_max_por_valor_pct']:>9.4f}% {m['erro_soma_pct']:>9.5f}% "
                  f"{m['erro_media_pct']:>9.5f}% {m['erro_receita_total_pct']:>9.5f}% "
                  f"{m['erro_receita_max_linha_pct']:>9.4f}% {str(fmt_ok):>7}")

    # ── A LENTE QUE QUEBRA: diferenca de proximos ───────────────────────────
    print("\nA LENTE QUE QUEBRA — margem = venda - custo (cancelamento catastrofico)")
    venda = preco[:500]
    custo = [round(p * 0.97, 6) for p in venda]     # margem estreita de proposito
    margem_ex = [v - c for v, c in zip(venda, custo)]
    _js(INP / "margem-venda.entrada.json", venda)
    _js(INP / "margem-custo.entrada.json", custo)
    _js(INP / "margem.fonte.json", {
        "gerador": "run.py", "params": {"custo": "venda x 0.97", "n": 500},
        "ideia": "duas colunas PROXIMAS: a diferenca delas e' o caso catastrofico",
        "pin": "derivado do preco real; o 0.97 e' sintetico e declarado"})
    canc = []
    for d in (3, 2, 1):
        vd, cd = [round(v, d) for v in venda], [round(c, d) for c in custo]
        marg = [a - b for a, b in zip(vd, cd)]
        fin = [(m, e) for m, e in zip(marg, margem_ex) if e]
        sinal = sum(1 for m, e in zip(marg, margem_ex) if (m > 0) != (e > 0))
        linha = {"casas": d,
                 "erro_max_operandos_pct": round(100 * max(map(rel, vd, venda)), 4),
                 "erro_max_margem_pct": round(100 * max(rel(m, e) for m, e in fin), 2),
                 "margens_que_trocaram_de_sinal": sinal, "n": len(marg),
                 "CONSTANTE_na_comparacao": "as mesmas 500 linhas; so' `d` varia"}
        canc.append(linha)
        _js(OUT / f"margem-d{d}.derivada.json", marg)
        print(f"  d={d}: operandos {linha['erro_max_operandos_pct']:>7.3f}%  ->  "
              f"margem {linha['erro_max_margem_pct']:>9.1f}%   "
              f"trocaram de SINAL: {sinal}/{len(marg)}")

    _js(INT / "cinco-lentes.json", medicoes)
    _js(INT / "cancelamento.json", canc)
    _js(RAIZ / "resultado.json",
        {"lentes": medicoes, "cancelamento": canc, "falhas": falhas,
         "baseline_bytes": base_b, "n": len(preco)})
    _esc(OUT / "INDEX.md", "\n".join(
        ["# INDEX — a perda por cinco lentes", "",
         "**Aviso**: os `.tcf` deste lab contêm valores **arredondados de propósito**. O",
         "`roundtrip.json` prova que o FORMATO é lossless sobre eles — não que o valor é o",
         "original. O original está em `inputs/retail-preco.entrada.json`.", "",
         "| caso | d | método | bytes | soma exata | erro/valor | erro receita |",
         "|---|---|---|---|---|---|---|"] +
        [f"| [`d{m['casas']}-{m['metodo']}`](./d{m['casas']}-{m['metodo']}.tcf) | {m['casas']} |"
         f" {m['metodo']} | {m['bytes']} | {m['soma_exata']} | "
         f"{m['erro_max_por_valor_pct']}% | {m['erro_receita_total_pct']}% |"
         for m in medicoes] +
        ["", "Cancelamento catastrófico em `margem-d*.derivada.json`.", ""]))

    print(f"\n{len(falhas)} falha(s)")
    for f in falhas[:10]:
        print(f"  FALHA: {f}")
    return 1 if falhas else 0


if __name__ == "__main__":
    raise SystemExit(main())

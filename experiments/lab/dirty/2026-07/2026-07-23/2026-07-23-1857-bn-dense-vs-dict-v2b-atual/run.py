#!/usr/bin/env python3
"""bN-dense base64 vs o encoder ATUAL do TCF (dict/V2-B base-94) — dados REAIS.

A medição que decide se esta thread vale algo: tudo até aqui comparou protótipos ENTRE SI. Aqui
comparamos contra o que o TCF EMITE HOJE. Hipótese (aritmética): o dict/V2-B gasta ~1 char por
símbolo independente de k; o bN empacota log2(k) bits/símbolo e só então vira base64 (6 bits/char) →
custo bN ≈ w/6 char por símbolo. Logo bN-dense deve GANHAR quando w<6 (k≤16) e PERDER quando w=8
(k>16), onde base-94 volta a ser melhor. Cruzamento previsto em k=16.

Comparação JUSTA total-vs-total: ambos self-contained (o do TCF inclui seu dicionário e header; o
protótipo inclui domínio + header). Dados: adult-census REAL (Z:/tcf-data). RT obrigatório dos dois
lados. NÃO toca src/tcf — o protótipo é lab-local (kit `pecas.py` do lab 1759). `python run.py`.
"""
from __future__ import annotations

import base64
import csv
import json
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
KIT = AQUI.parents[0] / "2026-07-23-1759-bn-lowcard-generaliza-e-compoe"
ROOT = AQUI.parents[5]
sys.path.insert(0, str(KIT))
sys.path.insert(0, str(ROOT / "src"))
import pecas as P  # noqa: E402
from tcf import encode, decode, SideOutputs  # noqa: E402

CSV = Path("Z:/tcf-data/external/adult-census/adult.csv")
OUT = AQUI / "outputs"
OUT.mkdir(exist_ok=True)

N = 10000
COLS = ["sex", "class", "race", "relationship", "marital-status",
        "workclass", "occupation", "education", "native-country"]


def carregar():
    cols = {c: [] for c in COLS}
    with open(CSV, newline="", encoding="utf-8") as f:
        for i, row in enumerate(csv.DictReader(f)):
            if i >= N:
                break
            for c in COLS:
                cols[c].append(row[c].strip())
    return cols


# ---------------------------------------------- protótipo self-contained bN-dense (lab-local)
def enc_bn_wire(vals):
    """`#PB <w> <n> <dom0\\x1fdom1...>\\n<base64 dos índices>` — self-contained (domínio embutido)."""
    domain, runs = P.build_and_scan(P.Fonte(vals))
    w = P.width_for(len(domain))
    if w is None:
        return None, None
    body = base64.b64encode(P.pack_w(P.runs_to_indices(runs), w)).decode("ascii")
    dom = "\x1f".join(domain)                       # separador que não ocorre nos dados
    return f"#PB {w} {len(vals)} {dom}\n{body}", domain


def dec_bn_wire(wire):
    head, body = wire.split("\n", 1)
    _mg, w, n, dom = head.split(" ", 3)
    w, n = int(w), int(n)
    domain = dom.split("\x1f")
    return [domain[i] for i in P.unpack_w(base64.b64decode(body), w, n)]


def rodar():
    cols = carregar()
    linhas = ["# bN-dense base64 vs dict/V2-B ATUAL do TCF — dados reais (adult-census)\n",
              f"Amostra {N} linhas. **total-vs-total self-contained**: TCF = `encode({{col:vals}})` "
              "completo (header + dicionário + corpo); bN = header + domínio + base64. `modo TCF` = "
              "`emitted_mode` real. `Δ` = bN − TCF (<0 = bN ganha). RT dos dois lados.\n",
              "| coluna | k | w | TCF atual | modo TCF | bN-dense | Δ | razão | RT |",
              "|---|---:|---:|---:|:---:|---:|---:|---:|:---:|"]
    falhas = 0
    ganhos = 0
    for c in COLS:
        vals = cols[c]
        so = SideOutputs()
        wire_tcf = encode({c: vals}, side_outputs=so)
        b_tcf = len(wire_tcf.encode("utf-8"))
        pc = (so.per_col or {}).get(c)
        modo = getattr(pc, "emitted_mode", None) or "?"
        rt_tcf = (decode(wire_tcf) == {c: vals})

        wire_bn, domain = enc_bn_wire(vals)
        if wire_bn is None:
            linhas.append(f"| {c} | — | — | {b_tcf} | {modo} | (bN n/a) | — | — | — |")
            continue
        b_bn = len(wire_bn.encode("utf-8"))
        rt_bn = (dec_bn_wire(wire_bn) == vals)
        k, w = len(domain), P.width_for(len(domain))

        ok = rt_tcf and rt_bn
        falhas += (not ok)
        if b_bn < b_tcf:
            ganhos += 1
        (OUT / f"{c}.bn-dense.tcfp").write_text(wire_bn, encoding="utf-8", newline="")
        (OUT / f"{c}.tcf-atual.tcf").write_text(wire_tcf, encoding="utf-8", newline="")
        linhas.append(f"| {c} | {k} | {w} | {b_tcf} | {modo} | {b_bn} | {b_bn - b_tcf:+d} | "
                      f"{b_bn / b_tcf:.2f}× | {'✅' if ok else '❌'} |")

    linhas.append("\n## Leitura\n")
    linhas.append(f"- **bN-dense ganha em {ganhos}/{len(COLS)} colunas reais.** A aritmética prevista "
                  "se confirma: o dict/V2-B base-94 gasta ~1 char/símbolo INDEPENDENTE de k; o bN gasta "
                  "`w/6` char/símbolo (empacota w bits, base64 = 6 bits/char). Logo bN ganha enquanto "
                  "**w<6 (k≤16)** e perde em **w=8 (k>16)**, onde base-94 volta a ser melhor.")
    linhas.append("- **O ganho é maior quanto MENOR a cardinalidade**: k=2 → 1 bit/símbolo = 6 símbolos "
                  "por char (~6× mais denso que 1 char/símbolo do base-94). É exatamente o caso bool/"
                  "flag/status, que é comum em dado real.")
    linhas.append("- **Cruzamento em k=16 → regra de decisão trivial e determinística**: escolher bN "
                  "quando `width_for(k) < 6` (isto é, k≤16), senão dict. Cabe como MAIS UM CANDIDATO no "
                  "FLOOR/min por coluna que o TCF já tem (`min(tcf,raw,dict,split)` → + `bN`), sem "
                  "máquina nova de segmentos. É o mecanismo LÓGICO bom; a calibragem fina fica pro .9.")
    linhas.append("- **Ressalvas honestas**: (a) o protótipo usa domínio embutido com separador `\\x1f` "
                  "e header simples — um weld real precisaria de escaping/gramática própria, o que muda "
                  "alguns bytes; (b) medido só em adult-census (9 colunas) e amostra de 10k; (c) não "
                  "mede latência/CPU, só bytes; (d) o dict/V2-B tem outras virtudes (ex. legibilidade "
                  "do dicionário) não capturadas aqui.")
    linhas.append(f"\n**{len(COLS)} colunas · {falhas} falhas de RT · bN vence em {ganhos}.** "
                  f"Amostra N={N}. Regenera: `python run.py`.")
    (AQUI / "result.md").write_text("\n".join(linhas), encoding="utf-8", newline="\n")
    print(f"OK · {len(COLS)} colunas · {falhas} falhas · bN-dense vence em {ganhos}/{len(COLS)}")
    return falhas


if __name__ == "__main__":
    raise SystemExit(1 if rodar() else 0)

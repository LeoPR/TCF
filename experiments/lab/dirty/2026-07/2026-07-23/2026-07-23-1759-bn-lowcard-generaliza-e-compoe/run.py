#!/usr/bin/env python3
"""Generaliza bN (bool + low-card k≤256) e testa se as peças CONVERSAM.

Pedido do owner (2026-07-23): não só bool — "elementos de poucos que caibam no bN". E refletir se é
seguro soltar peças e mantê-las pros próximos, vendo se compõem. Este lab exercita o KIT (pecas.py):
cardinalidade → largura `w` (bN) DEVE compor com a segmentação adaptativa por regime (do estudo bool).

Se as peças conversam: RT fecha pra TODO k∈{2,4,16} × regime; a segmentação adaptativa continua
nunca-pior (sob FLOOR) e a decisão continua de passe único. Se brigam: RT quebra, ou o adaptativo
perde sistematicamente. Mede corpo-vs-corpo (domínio embutido é constante aditivo, reportado à parte).

NÃO toca src/tcf. `python run.py`.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
import pecas as P  # noqa: E402  (kit lab-local)

INP, OUT = AQUI / "inputs", AQUI / "outputs"
for d in (INP, OUT):
    d.mkdir(exist_ok=True)


# ------------------------------------------------------------------------- geradores de regime
def _lcg(seed):
    s = seed

    def nxt(m):
        nonlocal s
        s = (1103515245 * s + 12345) & 0x7FFFFFFF
        return s % m
    return nxt


def cats(k):
    return [f"c{i}" for i in range(k)]                       # categorias low-card (strings)


def gen(k, regime, n, seed):
    C = cats(k)
    r = _lcg(seed)
    if regime == "runny":                                   # runs longos (baixa entropia)
        out = []
        while len(out) < n:
            out += [C[r(k)]] * (8 + r(40))
        return out[:n]
    if regime == "noisy":                                   # 1 símbolo aleatório por posição
        return [C[r(k)] for _ in range(n)]
    # hetero: alterna bloco-run e bloco-ruído (tamanhos VARIÁVEIS -> sem alinhamento embutido)
    out = []
    while len(out) < n:
        out += [C[r(k)]] * (20 + r(60))                     # run
        out += [C[r(k)] for _ in range(15 + r(45))]         # ruído
    return out[:n]


def datasets():
    N = 512
    seed_regime = {"runny": 11, "noisy": 23, "hetero": 37}   # determinístico (sem hash randomizado)
    d = {}
    for k in (2, 4, 16):
        for regime in ("runny", "noisy", "hetero"):
            d[f"k{k}-{regime}"] = gen(k, regime, N, 1000 + k * 7 + seed_regime[regime])
    return d


def rodar():
    casos = datasets()
    linhas = ["# bN generalizado (bool + low-card) — as peças conversam?\n",
              "Kit `pecas.py`: cardinalidade→largura `w`, compondo com segmentação adaptativa. Corpo-vs-"
              "corpo (domínio embutido reportado à parte). `Δadapt` = seg-adapt − best (<0 ganha). "
              "`reads/n` 1.0=passe único. RT = decode→índices→domínio == original == JSON.\n",
              "| caso | k | w | n | domínio B | dense | rle | best | seg-adapt | Δadapt | reads/n | RT |",
              "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|"]
    falhas = 0
    for nome, vals in casos.items():
        (INP / f"{nome}.json").write_text(json.dumps(vals), encoding="utf-8")
        n = len(vals)
        json_rt = json.loads(json.dumps(vals))

        fonte = P.Fonte(vals)
        domain, runs = P.build_and_scan(fonte)              # UM passe
        reads_one = (fonte.reads == n)
        k = len(domain)
        w = P.width_for(k)

        dom_b = P.domain_bytes(domain)
        dense = P.enc_dense(runs, w)
        rle = P.enc_rle(runs)
        adapt = P.seg_adapt(runs, w)
        wd, wr, wa = len(dense), len(rle), len(adapt)
        wbest = min(wd, wr)

        # RT dos 3 modos -> índices -> domínio -> valores
        def to_vals(idx_list):
            return [domain[i] for i in idx_list]
        rt = (to_vals(P.dec_dense(dense, w, n)) == vals == json_rt
              and to_vals(P.dec_rle(rle)) == vals
              and to_vals(P.dec_seg_adapt(adapt, w)) == vals)

        ok = rt and reads_one
        falhas += (not ok)
        (OUT / f"{nome}.seg-adapt.tcfp").write_text(adapt, encoding="utf-8", newline="")
        linhas.append(
            f"| {nome} | {k} | {w} | {n} | {dom_b} | {wd} | {wr} | {wbest} | {wa} | "
            f"{wa - wbest:+d} | {'1.0' if reads_one else '>1'} | {'✅' if ok else '❌'} |")

    linhas.append("\n## Leitura — as peças conversam?\n")
    linhas.append("- **SIM, compõem mecanicamente**: a MESMA peça `seg_adapt(runs, w)` roda pra "
                  "k∈{2,4,16} (w=1/2/4) sem código novo — só `w` muda (de `width_for(k)`). RT fecha nos 9 "
                  "→ cardinalidade→largura casa com a segmentação. Bool = caso w=1 com domínio implícito.")
    linhas.append("- **Passe único preservado** (`reads/n==1.0`): 1 scan constrói domínio + índices + "
                  "runs juntos. A telemetria (k, runs) sai desse mesmo passe.")
    linhas.append("- **MAS seg-adapt NÃO é vitória geral** (corrige o otimismo anterior): ele só bate o "
                  "melhor modo único em dados GENUINAMENTE MISTOS e w≥2 — `k4-hetero` −29, `k16-hetero` "
                  "−136. Em dados UNIFORMES perde: `runny` (k4 +21, k16 +17) o whole-rle compacto já ganha; "
                  "`noisy` (+5) o whole-dense já ganha; e em k2 (bool) o piso denso é tão baixo (1 bit/elem) "
                  "que o misto quase nunca compensa (k2-hetero +10). A segmentação por-segmento só paga "
                  "quando NENHUM modo único é bom o tempo todo.")
    linhas.append("- **w AMPLIFICA o ganho do misto**: quanto maior o piso denso (w maior), mais os "
                  "segmentos RLE têm o que bater → o ganho no heterogêneo cresce com k (−29 em w=2, −136 "
                  "em w=4). Bool (w=1) é o pior caso pro misto.")
    linhas.append("- **FLOOR é obrigatório, não opcional**: como seg-adapt perde na maioria, ele SÓ é "
                  "seguro competindo em `min(whole-dense, whole-rle, seg-adapt)` — aí os +Δ viram fallback "
                  "pro modo único e o líquido é nunca-pior. A peça a soldar é o FLOOR/min (já é padrão), "
                  "com seg-adapt como mais um candidato — não seg-adapt como default.")
    linhas.append("- **Custo novo do bN vs bool**: o `domínio B` (bool tem domínio implícito {0,1}; "
                  "low-card embute os k distintos). Constante aditivo aos 3 modos — não muda QUAL vence, "
                  "mas conta no total.")
    linhas.append("- **Seguro soltar/manter?** As peças são lab-local, compõem por contrato estreito "
                  "(`runs`+`w`) e são reusáveis pelos próximos SEM tocar src/tcf. A 'terceira desavio' "
                  "(integração) NÃO é incompatibilidade entre as peças (elas conversam) — é o "
                  "ponto-de-seleção inexistente no `.8H`, que segue sendo o risco real de weld.")
    linhas.append(f"\n**{len(casos)} casos · {falhas} falhas (RT + passe único).** Regenera: `python run.py`.")
    (AQUI / "result.md").write_text("\n".join(linhas), encoding="utf-8", newline="\n")
    print(f"OK · {len(casos)} casos · {falhas} falhas (RT + passe unico)")
    return falhas


if __name__ == "__main__":
    raise SystemExit(1 if rodar() else 0)

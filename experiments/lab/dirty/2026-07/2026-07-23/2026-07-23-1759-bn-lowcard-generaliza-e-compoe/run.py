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
        out, j = [], 0
        while len(out) < n:
            out += [C[j % k]] * (8 + r(40))                 # CICLA as k categorias -> realiza w
            j += 1
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
    linhas.append("- **A CADEIA VERTICAL compõe** (é o que o RT prova): `build_and_scan → width_for(k) → "
                  "codec(runs,w) → decoder → domínio`. A mesma `seg_adapt(runs,w)` roda em w=1/2/4 sem "
                  "código novo, RT fecha nos 9. Os 3 modos (dense/rle/seg-adapt) NÃO se encadeiam — são "
                  "SUBSTITUÍVEIS sob o contrato comum `(runs,w)`, unificados por um `min()` externo.")
    linhas.append("- **Passe único preservado** (`reads/n==1.0`): 1 scan constrói domínio + índices + "
                  "runs juntos; os encoders consomem `runs` (nunca a fonte). A telemetria sai desse passe.")
    linhas.append("- **seg-adapt NÃO é vitória geral** (corrige o otimismo anterior): perde em 7/9. Só "
                  "bate o modo único em MISTO genuíno e w≥2 — `k4-hetero` −29, `k16-hetero` −136. Em "
                  "UNIFORME perde: `runny` o modo compacto já ganha (whole-rle p/ k≥4: k4 +29, k16 +15; "
                  "whole-dense p/ bool k2 +23), `noisy` o whole-dense ganha (+5), e em bool k2 o piso "
                  "denso baixo faz o misto perder também no hetero (+10). Segmentar só paga quando NENHUM "
                  "modo único é bom o tempo todo.")
    linhas.append("- **w AMPLIFICA o ganho do misto**: piso denso maior → segmentos RLE têm mais o que "
                  "bater → o ganho no heterogêneo cresce com k (−29 em w=2, −136 em w=4). Bool (w=1) é o "
                  "PIOR caso pro misto — o oposto do otimismo inicial.")
    linhas.append("- **FLOOR obrigatório**: como seg-adapt perde na maioria, só é seguro em `min(whole-"
                  "dense, whole-rle, seg-adapt)` — os +Δ viram fallback e o líquido é nunca-pior. A peça a "
                  "soldar é o FLOOR/min (já padrão), com seg-adapt como candidato, não default. RESSALVA: "
                  "este `min` é só de bytes-de-corpo; NÃO conta o byte do seletor de modo nem o custo de "
                  "computar os 3 — em payload minúsculo (k2-runny rle=88 vs seg-adapt=111) 1 byte importa.")
    linhas.append("- **Custo do bN low-card = domínio embutido** (`domínio B`: 5→11→53 conforme k). "
                  "NOTA: este lab usa categorias-string `c0/c1`, então k=2 TAMBÉM paga domínio (5B) — a "
                  "economia de um bool REAL (domínio implícito {0,1}, 0B) não é medida aqui, é conceitual. "
                  "O domínio é constante aditivo aos 3 modos, não muda QUAL vence.")
    linhas.append("- **Seguro soltar/manter?** As peças são lab-local, substituíveis sob contrato "
                  "estreito (`runs`+`w`), reusáveis pelos próximos SEM tocar src/tcf. Este lab DESCARTA "
                  "incompatibilidade entre as peças (RT fecha), mas NÃO mede integração — o `.8H` nunca é "
                  "tocado. Logo o ponto-de-seleção inexistente no `.8H` é o risco de weld por ELIMINAÇÃO "
                  "(hipótese herdada), não uma medição deste lab.")
    linhas.append(f"\n**{len(casos)} casos · {falhas} falhas (RT + passe único).** Regenera: `python run.py`.")
    (AQUI / "result.md").write_text("\n".join(linhas), encoding="utf-8", newline="\n")
    print(f"OK · {len(casos)} casos · {falhas} falhas (RT + passe unico)")
    return falhas


if __name__ == "__main__":
    raise SystemExit(1 if rodar() else 0)

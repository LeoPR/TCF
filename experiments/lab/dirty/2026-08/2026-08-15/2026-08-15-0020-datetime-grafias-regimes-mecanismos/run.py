# -*- coding: utf-8 -*-
"""DATETIME — o que o TCF faz hoje, por GRAFIA e por REGIME, com cada mecanismo isolado.

    python run.py

## O pedido (owner, 2026-08-15)

> *"gere uma variedade provável de datetimes, com os tipos e variações de formato para ver o
> comportamento do que se tem do TCF, e aí vemos como melhorar algum deles. Foco no datetime
> agora, não misture tipos pois dificulta minha análise. Também pode fazer variações de
> compressão para esse formato, e aí estudamos algo que seja uma mistura do datetime ou um
> mais específico ainda pra datetime."*

**Só datetime.** Nenhuma régua de int/float/string — o eixo é grafia × regime × mecanismo.

## O enquadramento que a direção do owner fixou

> *"os tipos são comportados, já que têm origem em bancos de dados que já tratam esse tipo de
> dado como canônico; seria muito raro ter misturas, e mesmo nessas condições provavelmente
> seriam corrupções de transmissão."*

Logo: **grafia uniforme por coluna**. Este lab não testa robustez a lixo misturado — testa o
comportamento de cada grafia canônica, que é o que o mundo emite.

## Os três blocos

- **BLOCO 1 — grafias**: 13 formas, regime fixo (comercial). Qual grafia o núcleo trata bem?
- **BLOCO 2 — regimes**: 8 distribuições, grafia fixa (a do corpus). Qual estrutura ele acha?
- **BLOCO 3 — transformações**: epoch, separado e campos-6, nos dois eixos. O que o dev
  ganharia fazendo à mão o que o formato não faz sozinho.

Cada mecanismo é medido **isolado** (o `encode()` público só mostra o vencedor).
"""
from __future__ import annotations

import json
import pathlib
import shutil
import sys

RAIZ = pathlib.Path(__file__).parent
REPO = RAIZ.parents[5]
assert (REPO / "src" / "tcf").is_dir(), f"REPO errado: {REPO}"
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(RAIZ))

import casos as C                                                  # noqa: E402
import mecanismos as M                                             # noqa: E402

INP, INT, OUT = RAIZ / "inputs", RAIZ / "intermediates", RAIZ / "outputs"
JSON_KW = {"ensure_ascii": False, "indent": 1}
N = 2000


def _esc(p, t):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(t, encoding="utf-8", newline="")


def _js(p, o):
    _esc(p, json.dumps(o, **JSON_KW))


def mede(nome, vals, grafia, ideia, fonte, falhas, com_transf=True):
    """Roda todos os candidatos e transformações sobre UMA coluna, e grava tudo."""
    _js(INP / f"{nome}.entrada.json", vals)
    _js(INP / f"{nome}.fonte.json", fonte)
    linha = {"caso": nome, "grafia": grafia, "ideia": ideia, "n": len(vals),
             "distintos": len(set(vals)), "chars": sum(map(len, vals)),
             "CONSTANTE_na_comparacao": "a MESMA coluna; só muda o MECANISMO"}
    for rot, fn in M.CANDIDATOS:
        try:
            w, rt, hdr = fn(vals)
        except Exception as e:
            linha[rot] = None
            linha[f"{rot}_nota"] = f"erro: {type(e).__name__}: {str(e)[:50]}"
            continue
        linha[rot] = M.B(w) if w is not None else None
        linha[f"{rot}_hdr"] = hdr
        if rt is False:
            falhas.append(f"{nome}/{rot}: RT não fechou")
        if w is not None:
            _esc(OUT / f"{nome}.{rot.replace('(', '-').replace(')', '')}.tcf", w)
    if com_transf:
        for rot, fn in M.TRANSFORMACOES:
            try:
                w, rt, hdr = fn(vals, grafia)
            except Exception as e:
                linha[rot] = None
                linha[f"{rot}_nota"] = f"erro: {type(e).__name__}: {str(e)[:50]}"
                continue
            linha[rot] = M.B(w) if w is not None else None
            linha[f"{rot}_hdr"] = hdr
            if rt is False:
                falhas.append(f"{nome}/{rot}: RT não fechou")
            if w is not None:
                _esc(OUT / f"{nome}.{rot}.tcf", w)
    cands = {k: v for k, v in linha.items()
             if k in [c for c, _ in M.CANDIDATOS] + [t for t, _ in M.TRANSFORMACOES]
             and isinstance(v, int)}
    if cands:
        venc = min(cands, key=cands.get)
        linha["vencedor"] = venc
        linha["melhor_bytes"] = cands[venc]
        linha["vs_raw_pct"] = round(100 * (1 - cands[venc] / linha["raw"]), 1) \
            if linha.get("raw") else None
    _js(OUT / f"{nome}.meta.json", linha)
    return linha


def _tab(linhas, cols, titulo):
    print(f"\n{titulo}")
    cab = f"  {'caso':>26} {'k':>6} " + " ".join(f"{c:>9}" for c in cols) + f" {'vencedor':>16}"
    print(cab)
    for x in linhas:
        cel = " ".join(f"{(x.get(c) if isinstance(x.get(c), int) else '—'):>9}" for c in cols)
        print(f"  {x['caso']:>26} {x['distintos']:>6} {cel} {x.get('vencedor', '?'):>16}")


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    for d in (INP, INT, OUT):
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(parents=True)
    falhas, b1, b2 = [], [], []
    COLS = ["raw", "core", "bN", "dict", "split", "multi(_best_of)"]
    COLT = ["epoch-s", "separado", "campos-6"]

    # ── BLOCO 1 — as 13 GRAFIAS, regime FIXO (comercial, o do corpus) ───────
    instantes = C.r_comercial(N)
    for nome, fn, ideia in C.GRAFIAS:
        vals = [fn(d) for d in instantes]
        b1.append(mede(f"b1-{nome}", vals, nome, ideia,
                       {"gerador": "casos.py::GRAFIAS x r_comercial", "grafia": nome,
                        "regime": "r1-comercial (FIXO)", "n": N,
                        "seed": "LCG determinístico, sem random",
                        "ideia": ideia, "pin": "sintético; grafia uniforme por coluna "
                                               "(origem canônica de banco)"},
                       falhas))
    _tab(b1, COLS, "BLOCO 1 — as 13 GRAFIAS (regime FIXO = comercial). Bytes por mecanismo:")
    _tab(b1, COLT, "  … e as transformações à mão (só onde há parser):")

    # ── BLOCO 2 — os 8 REGIMES, grafia FIXA (a do corpus) ──────────────────
    for nome, fn, ideia, par in C.REGIMES:
        vals = [C.g_sql_espaco(d) for d in fn(N)]
        b2.append(mede(f"b2-{nome}", vals, "g01-sql-espaco", ideia,
                       {"gerador": "casos.py::REGIMES x g_sql_espaco", "regime": nome,
                        "grafia": "g01-sql-espaco (FIXA)", "n": N, "par": par,
                        "seed": "LCG determinístico, sem random",
                        "ideia": ideia, "pin": "sintético viesado por construção"},
                       falhas))
    _tab(b2, COLS, "BLOCO 2 — os 8 REGIMES (grafia FIXA = `YYYY-MM-DD HH:MM:SS`):")
    _tab(b2, COLT, "  … e as transformações à mão:")

    # ── BLOCO 3 — o par de contra-prova, isolado ───────────────────────────
    print("\nBLOCO 3 — o par de contra-prova: quanto do ganho é do `*N|` (RLE adjacente)?")
    r1 = next(x for x in b2 if x["caso"] == "b2-r1-comercial")
    r8 = next(x for x in b2 if x["caso"] == "b2-r8-comercial-embaralhado")
    print(f"  {'mecanismo':>16} {'ordenado':>10} {'embaralhado':>12} {'delta':>10}")
    contra = {}
    for c in COLS + COLT:
        a, b = r1.get(c), r8.get(c)
        if isinstance(a, int) and isinstance(b, int):
            contra[c] = {"ordenado": a, "embaralhado": b, "delta_pct": round(100 * (b - a) / a, 1)}
            print(f"  {c:>16} {a:>10} {b:>12} {contra[c]['delta_pct']:>9.1f}%")

    _js(INT / "bloco1-grafias.json", b1)
    _js(INT / "bloco2-regimes.json", b2)
    _js(INT / "bloco3-contraprova.json", contra)
    _js(RAIZ / "resultado.json", {"grafias": b1, "regimes": b2, "contraprova": contra,
                                  "falhas": falhas})
    _esc(OUT / "INDEX.md", "\n".join(
        ["# INDEX — datetime: grafias × regimes × mecanismos", "",
         "Cada `<caso>.<mecanismo>.tcf` é o wire daquele candidato **isolado** — o `encode()`",
         "público só mostraria o vencedor.", "",
         "## Bloco 1 — grafias (regime fixo)", "",
         "| caso | grafia | k | raw | core | split | multi | vencedor |",
         "|---|---|---|---|---|---|---|---|"] +
        [f"| [`{x['caso']}`](./{x['caso']}.core.tcf) | {x['ideia'][:44]} | {x['distintos']} | "
         f"{x.get('raw','—')} | {x.get('core','—')} | {x.get('split','—')} | "
         f"{x.get('multi(_best_of)','—')} | **{x.get('vencedor','?')}** |" for x in b1] +
        ["", "## Bloco 2 — regimes (grafia fixa)", "",
         "| caso | regime | k | raw | core | split | multi | vencedor |",
         "|---|---|---|---|---|---|---|---|"] +
        [f"| [`{x['caso']}`](./{x['caso']}.core.tcf) | {x['ideia'][:44]} | {x['distintos']} | "
         f"{x.get('raw','—')} | {x.get('core','—')} | {x.get('split','—')} | "
         f"{x.get('multi(_best_of)','—')} | **{x.get('vencedor','?')}** |" for x in b2] +
        [""]))

    print(f"\n{len(falhas)} falha(s)")
    for f in falhas[:15]:
        print(f"  FALHA: {f}")
    return 1 if falhas else 0


if __name__ == "__main__":
    raise SystemExit(main())

"""compare.py — junta a rodada .8 (baseline) com a .9 (candidata) por case_id.

Esta e' a ferramenta que o owner pediu: "o processo precisa repetir de forma
statisticamente similar pro .9 pra gente ter comparacao depois." Ela existe
AGORA (nao em 2027) e ja' e' auto-testada, senao o formato de armazenamento nao
esta' validado.

Tres salvaguardas contra concluir bobagem:

1. JOIN POR case_id, nao por posicao. Coordenada igual = comparavel; ausente de
   um lado = reportado, nunca casado errado.

2. NORMALIZACAO PELO CALIBRADOR. Cada rodada mede C1/C2/C3 (a propria maquina).
   fator = mediana(C_.9 / C_.8). O tempo do .9 e' dividido pelo fator antes de
   comparar — senao uma maquina 38% mais lenta (situacao real desta sessao) vira
   "regressao" fantasma.

3. SINAL vs RUIDO. Um delta so' e' REAL se passa do maior entre: o MDE do tier
   daquele caso e o noise_floor_cv da rodada. Abaixo disso: veredito RUIDO, nunca
   "ganho de 3%".

    python -m bench_perf.compare baseline.jsonl candidato.jsonl
    python -m bench_perf.compare --self baseline.jsonl   # auto-teste: tudo IGUAL
"""

from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path


def _carrega(p: Path):
    regs, resumo = [], {}
    for line in p.read_text(encoding="utf-8").splitlines():
        regs.append(json.loads(line))
    rp = p.with_suffix(".run.json")
    if rp.exists():
        resumo = json.loads(rp.read_text(encoding="utf-8"))
    return {r["case_id"]: r for r in regs}, resumo


def _fator_calibrador(res_a: dict, res_b: dict) -> float:
    """mediana(C_b / C_a) sobre os 3 calibradores. 1.0 se faltar."""
    ca, cb = res_a.get("calibradores", {}), res_b.get("calibradores", {})
    razoes = []
    for nome in ca:
        if nome in cb:
            a = ca[nome].get("point_ns")
            b = cb[nome].get("point_ns")
            if a and b:
                razoes.append(b / a)
    return statistics.median(razoes) if razoes else 1.0


def _limiar(rec_a: dict, res_a: dict) -> float:
    """maior entre MDE do tier e noise_floor da rodada (fracao)."""
    mde = rec_a.get("encode", {}).get("mde_pct", 10.0) / 100.0
    piso = res_a.get("drift", {}).get("noise_floor_cv", 0.0) or 0.0
    return max(mde, piso)


def comparar(base: Path, cand: Path) -> dict:
    ra, resa = _carrega(base)
    rb, resb = _carrega(cand)
    fator = _fator_calibrador(resa, resb)

    so_base = sorted(set(ra) - set(rb))
    so_cand = sorted(set(rb) - set(ra))
    linhas, contagem = [], {"MELHOR": 0, "PIOR": 0, "IGUAL": 0, "RUIDO": 0, "n/a": 0}
    for cid in sorted(set(ra) & set(rb)):
        a, b = ra[cid], rb[cid]
        ea, eb = a.get("encode"), b.get("encode")
        if a.get("status") != "ok" or b.get("status") != "ok" or not ea or not eb:
            contagem["n/a"] += 1
            continue
        ta = ea["point_ns"]
        tb = eb["point_ns"] / fator                       # normaliza a maquina do .9
        delta = (tb - ta) / ta if ta else 0.0             # >0 = .9 mais lento
        lim = _limiar(a, resa)
        if abs(delta) <= lim:
            verdict = "RUIDO" if abs(delta) > 0.005 else "IGUAL"
        else:
            verdict = "PIOR" if delta > 0 else "MELHOR"
        contagem[verdict] += 1
        linhas.append({"case_id": cid, "delta_pct": round(delta * 100, 2),
                       "limiar_pct": round(lim * 100, 2), "verdict": verdict,
                       "base_ns": ta, "cand_ns_norm": round(tb)})
    return {
        "fator_calibrador": round(fator, 4),
        "contagem": contagem,
        "so_no_baseline": so_base, "so_no_candidato": so_cand,
        "linhas": sorted(linhas, key=lambda x: x["delta_pct"]),
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Compara baseline .8 vs candidato .9")
    ap.add_argument("baseline")
    ap.add_argument("candidato", nargs="?")
    ap.add_argument("--self", dest="autoteste", action="store_true",
                    help="auto-teste: baseline vs si mesmo -> tudo IGUAL, fator 1.0")
    args = ap.parse_args(argv)

    base = Path(args.baseline)
    cand = base if args.autoteste else Path(args.candidato)
    r = comparar(base, cand)

    print(f"fator_calibrador (maquina .9/.8) = {r['fator_calibrador']}")
    print(f"veredictos: {r['contagem']}")
    if r["so_no_baseline"]:
        print(f"  so' no baseline ({len(r['so_no_baseline'])}): {r['so_no_baseline'][:3]}...")
    if r["so_no_candidato"]:
        print(f"  so' no candidato ({len(r['so_no_candidato'])}): {r['so_no_candidato'][:3]}...")
    piores = [l for l in r["linhas"] if l["verdict"] == "PIOR"][-5:]
    melhores = [l for l in r["linhas"] if l["verdict"] == "MELHOR"][:5]
    for l in melhores:
        print(f"  MELHOR {l['delta_pct']:+6.1f}% (lim {l['limiar_pct']}%)  {l['case_id'][:50]}")
    for l in piores:
        print(f"  PIOR   {l['delta_pct']:+6.1f}% (lim {l['limiar_pct']}%)  {l['case_id'][:50]}")

    if args.autoteste:
        # auto-teste: mesmo arquivo -> fator 1.0, zero PIOR/MELHOR
        ok = (r["fator_calibrador"] == 1.0 and r["contagem"]["PIOR"] == 0
              and r["contagem"]["MELHOR"] == 0)
        print("AUTO-TESTE:", "PASSOU" if ok else "FALHOU")
        return 0 if ok else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

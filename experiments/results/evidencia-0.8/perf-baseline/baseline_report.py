"""Relatorio FIRST-ORDER do baseline .8 (proposital: grandeza + pontos quentes, nao precisao).

Um protótipo com fita adesiva nao merece CI por celula. O que ancora o .9:
  1. ORDEM DE GRANDEZA por celula (us / ms / s)
  2. PONTOS QUENTES (o que domina o tempo)
  3. COMPORTAMENTO DE ESCALA (encode vs R) -> linear? super-linear? = o alvo do .9
Ruido run-a-run ~±5% (piloto K=7) — abaixo do que importa aqui.

  python baseline_report.py <nucleo-baseline.jsonl>
"""
from __future__ import annotations
import json, math, sys
from pathlib import Path
from collections import defaultdict

def carrega(p):
    recs=[]
    for line in p.read_text(encoding="utf-8").splitlines():
        if line.strip(): recs.append(json.loads(line))
    return recs

def mag(ns):
    if ns is None: return "?"
    if ns < 1e3: return "<1us"
    if ns < 1e6: return "us"        # 1us .. 1ms
    if ns < 1e8: return "ms"        # 1ms .. 100ms
    if ns < 1e9: return "100ms"     # 100ms .. 1s
    return "s+"                     # >=1s

def fmt(ns):
    if ns is None: return "?"
    if ns>=1e9: return f"{ns/1e9:.2f}s"
    if ns>=1e6: return f"{ns/1e6:.1f}ms"
    if ns>=1e3: return f"{ns/1e3:.1f}us"
    return f"{ns:.0f}ns"

def main(argv):
    p=Path(argv[0]); recs=carrega(p)
    oks=[r for r in recs if r.get("status")=="ok" and r.get("encode",{}).get("point_ns")]
    print(f"=== BASELINE .8 (nucleo) — {len(oks)} celulas medidas · ruido run-a-run ~±5% (piloto) ===\n")

    # 1. ORDEM DE GRANDEZA
    buckets=defaultdict(int)
    for r in oks: buckets[mag(r["encode"]["point_ns"])]+=1
    ordem=["us","ms","100ms","s+"]
    print("1) ORDEM DE GRANDEZA (encode):")
    for b in ordem:
        if buckets.get(b): print(f"   {b:>6}: {buckets[b]:2d} celulas")
    print()

    # 2. PONTOS QUENTES (top 10 por tempo)
    print("2) PONTOS QUENTES (top 10 por tempo de encode):")
    for r in sorted(oks,key=lambda x:-x["encode"]["point_ns"])[:10]:
        cid=r["case_id"]
        print(f"   {fmt(r['encode']['point_ns']):>9}  {cid[:66]}")
    print()

    # 3. ESCALA: encode vs R (linhas) por caminho+forma, slope log-log
    # agrupa por (caminho, forma) variando a escala
    grp=defaultdict(list)  # (caminho,forma) -> [(R, ns)]
    for r in oks:
        v=r.get("vectors",{})
        R=v.get("escala",{}).get("R"); cam=v.get("caminho"); fo=v.get("forma")
        # so' variacoes de R "puras" (mesma C/L/K do base) — usa knobs vazio/serial
        if R and cam and fo and v.get("granularidade")=="call" and v.get("compressao")=="none":
            grp[(cam,fo)].append((R, r["encode"]["point_ns"]))
    print("3) ESCALA encode vs R (linhas) — slope log-log (~1=linear, >1=super-linear=alvo .9):")
    for (cam,fo),pts in sorted(grp.items()):
        pts=sorted(set(pts))
        if len(pts)<2: continue
        # slope entre menor e maior R (aproximado, first-order)
        (r0,t0),(r1,t1)=pts[0],pts[-1]
        if r0>0 and r1>r0 and t0>0 and t1>0:
            slope=math.log(t1/t0)/math.log(r1/r0)
            faixa=" ".join(f"{R//1000 if R>=1000 else R}{'k' if R>=1000 else ''}:{fmt(t)}" for R,t in pts)
            tag="LINEAR" if slope<1.2 else ("super-linear" if slope<1.8 else "~QUADRATICO")
            print(f"   {cam:<13} {fo:<11} slope~{slope:.2f} [{tag}]   {faixa}")
    print()
    print("Nota: numeros aproximados (±~5% run-a-run). Extremos/cross-tech/precisao -> .9/1.0.")
    return 0

if __name__=="__main__":
    raise SystemExit(main(sys.argv[1:]))

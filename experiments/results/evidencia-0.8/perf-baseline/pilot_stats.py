"""Caracterizacao de variancia ENTRE-runs de um piloto (Georges 2007 / Kalibera 2013).

K invocacoes independentes do mesmo conjunto -> por celula, K estimativas de point_ns.
A variacao entre elas E' o ruido do ambiente (proc/OS/freq). Reporta media, CV e o
intervalo de confianca 95% (t-Student, df=K-1). Se o CV entre-runs e' pequeno e o CI
e' estreito, o desempenho esta' estabelecido com >95% de confianca.

  python pilot_stats.py <run_1.jsonl> <run_2.jsonl> ...
"""
from __future__ import annotations
import json, math, sys
from pathlib import Path

# t de Student, bicaudal 95% (t_{0.975, df}); df>=30 -> ~1.96
_T = {1:12.706,2:4.303,3:3.182,4:2.776,5:2.571,6:2.447,7:2.365,8:2.306,9:2.262,
      10:2.228,11:2.201,12:2.179,13:2.160,14:2.145,15:2.131,16:2.120,17:2.110,
      18:2.101,19:2.093,20:2.086,25:2.060,29:2.045}
def tval(df):
    if df in _T: return _T[df]
    ks=[k for k in _T if k<=df]
    return _T[max(ks)] if ks else 1.96

def carrega(p: Path):
    pts={}
    for line in p.read_text(encoding="utf-8").splitlines():
        if not line.strip(): continue
        r=json.loads(line)
        e=r.get("encode")
        if r.get("status")=="ok" and e and e.get("point_ns"):
            pts[r["case_id"]]=e["point_ns"]
    rp=p.with_suffix(".run.json")
    resumo=json.loads(rp.read_text(encoding="utf-8")) if rp.exists() else {}
    return pts, resumo

def main(argv):
    files=[Path(a) for a in argv]
    if len(files)<3:
        print("precisa de >=3 runs p/ CI util"); return 2
    runs=[carrega(f) for f in files]
    K=len(runs)
    # calibradores por run (estabilidade da maquina entre runs)
    print(f"K = {K} invocacoes · t_{{0.975,{K-1}}} = {tval(K-1)}\n")
    print("=== calibradores (point_ns) por run — estabilidade da maquina ===")
    for nome in ("C1_aritmetica","C2_hash","C3_alloc"):
        vals=[res.get("calibradores",{}).get(nome,{}).get("point_ns") for _,res in runs]
        vals=[v for v in vals if v]
        if vals:
            m=sum(vals)/len(vals); sd=(sum((x-m)**2 for x in vals)/(len(vals)-1))**.5 if len(vals)>1 else 0
            print(f"  {nome:<14} media={m/1e6:8.3f}ms  CV_entre_runs={sd/m*100:5.2f}%")
    print()
    # por celula
    todas=set().union(*[set(r.keys()) for r,_ in runs])
    print(f"=== {len(todas)} celulas · variancia ENTRE {K} runs ===")
    print(f"{'celula':<52} {'media':>10} {'CV%':>6} {'CI95±%':>7}  veredito")
    cvs=[]; ci_pcts=[]
    linhas=[]
    for cid in sorted(todas):
        vals=[r[cid] for r,_ in runs if cid in r]
        n=len(vals)
        if n<2: continue
        m=sum(vals)/n
        sd=(sum((x-m)**2 for x in vals)/(n-1))**.5
        cv=sd/m*100 if m else 0
        ci=tval(n-1)*sd/math.sqrt(n)          # meia-largura do CI95 da MEDIA
        ci_pct=ci/m*100 if m else 0
        cvs.append(cv); ci_pcts.append(ci_pct)
        ver = "estavel" if ci_pct<=5 else ("aceitavel" if ci_pct<=10 else "RUIDOSO")
        linhas.append((cid,m,cv,ci_pct,ver,n))
    for cid,m,cv,ci_pct,ver,n in sorted(linhas,key=lambda x:-x[3]):
        unit = f"{m/1e6:.3f}ms" if m>=1e6 else f"{m/1e3:.1f}us"
        print(f"{cid[:52]:<52} {unit:>10} {cv:6.2f} {ci_pct:7.2f}  {ver}"+("" if n==K else f" (n={n})"))
    # sumario
    if cvs:
        import statistics as st
        print(f"\n=== SUMARIO ===")
        print(f"CV entre-runs:  mediana={st.median(cvs):.2f}%  max={max(cvs):.2f}%")
        print(f"CI95 (±% da media): mediana={st.median(ci_pcts):.2f}%  max={max(ci_pcts):.2f}%")
        n_ok=sum(1 for c in ci_pcts if c<=5); n_ac=sum(1 for c in ci_pcts if 5<c<=10)
        print(f"celulas com CI95 <=5%: {n_ok}/{len(ci_pcts)} · <=10%: {n_ok+n_ac}/{len(ci_pcts)}")
        veredito = ("REPRODUZIVEL (>95% conf.): a variacao entre runs e' ruido do processador"
                    if max(ci_pcts)<=10 else
                    "PARCIAL: algumas celulas ainda ruidosas — mais reps ou mais pinning")
        print(f"\n{veredito}")
    return 0

if __name__=="__main__":
    raise SystemExit(main(sys.argv[1:]))

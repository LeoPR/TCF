"""Gate N>=5 — roda o B2 prototype nas 5 fontes same-domain reais.

share (B2 vs V1) = valor REAL do cross-dict (isolado do dict-vs-OBAT/HCC). Grafos grandes
amostrados (cap 40k arestas) por velocidade. READ-ONLY.
"""
import csv
import sys
from pathlib import Path

LAB = Path(__file__).resolve().parent
sys.path.insert(0, str(LAB))
from run import measure, load_grqc, load_openflights, EXT   # noqa: E402


def load_football():
    rows = list(csv.DictReader((EXT / "football-results" / "results.csv").open(encoding="utf-8")))
    return {"home_team": [r["home_team"] for r in rows],
            "away_team": [r["away_team"] for r in rows]}


def load_edges(path, cap=40000):
    src, dst = [], []
    for line in path.open(encoding="utf-8"):
        if line.startswith("#") or not line.strip():
            continue
        p = line.split()
        if len(p) < 2:
            continue
        src.append(p[0]); dst.append(p[1])
        if len(src) >= cap:
            break
    return {"from_id": src, "to_id": dst}


if __name__ == "__main__":
    print("=== GATE N>=5 — share (B2 vs V1) = valor REAL do cross-dict ===\n")
    of = load_openflights()
    R = [
        ("SNAP ca-GrQc (colaboracao)", measure("SNAP ca-GrQc from~to", load_grqc())),
        ("OpenFlights (transporte)", measure("OpenFlights IATA s~d",
                                             {"s": of["source_airport"], "d": of["dest_airport"]})),
        ("futebol (esporte, NAO-grafo)", measure("futebol home~away", load_football())),
        ("cit-HepTh (citacao)", measure("cit-HepTh from~to [40k]",
                                        load_edges(EXT / "snap-cit-hepth" / "cit-HepTh.txt"))),
        ("email-Enron (comunicacao)", measure("email-Enron from~to [40k]",
                                              load_edges(EXT / "snap-email-enron" / "email-Enron.txt"))),
    ]
    print("\n=== VEREDITO DO GATE ===")
    ge15 = sum(1 for _, r in R if -r["share"] >= 15)
    struct = sum(1 for _, r in R if r["vB_dec"] < r["v0_dec"])
    print(f"fontes distintas = {len(R)} (5 morfologias; 1 NAO-grafo)")
    print(f"share >= 15% (byte) : {ge15}/{len(R)}")
    print(f"porta estrutural (decodes C->1) : {struct}/{len(R)}")
    print(f"share sobrevive controle (gzip) : "
          f"{sum(1 for _, r in R if r['br_share'] < 0)}/{len(R)}\n")
    for label, r in R:
        flag = ">=15%" if -r["share"] >= 15 else ("estrutural" if r["vB_dec"] < r["v0_dec"] else "-")
        print(f"  {label:32} share={r['share']:+6.1f}%  gzip-share={r['br_share']:+6.1f}%  "
              f"dec {r['v0_dec']}->{r['vB_dec']}  [{flag}]")

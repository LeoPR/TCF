"""T-DATA-1 — baixa datasets same-domain-ref REAIS pro gate N>=5 do B2/B3.

Raw vai pra Z:/tcf-data/external/ (dado baixado NAO entra no repo; regra do projeto).
Morfologias DIVERSAS (contra overfit-a-grafo): 2 nao-grafo tabulares (esportes) + 1 grafo
de citacao. Com SNAP ca-GrQc + OpenFlights (ja' em Z:) -> 5 fontes distintas.
"""
import gzip
import os
import urllib.request

BASE = "Z:/tcf-data/external"
UA = {"User-Agent": "Mozilla/5.0 (research; TCF same-domain gate)"}

JOBS = [
    # (subdir, url, fname, decompress)  — same-domain cols anotadas no provenance
    ("football-results",
     "https://raw.githubusercontent.com/martj42/international_results/master/results.csv",
     "results.csv", None),                                    # home_team ~ away_team (times)
    ("tennis-atp",
     "https://raw.githubusercontent.com/JeffSackmann/tennis_atp/master/atp_matches_2019.csv",
     "atp_matches_2019.csv", None),                           # winner_name ~ loser_name (jogadores)
    ("tennis-atp",
     "https://raw.githubusercontent.com/JeffSackmann/tennis_atp/master/atp_matches_2018.csv",
     "atp_matches_2018.csv", None),
    ("snap-cit-hepth",
     "https://snap.stanford.edu/data/cit-HepTh.txt.gz",
     "cit-HepTh.txt", "gz"),                                  # from_paper ~ to_paper (citacao)
]

for sub, url, fname, comp in JOBS:
    d = os.path.join(BASE, sub)
    os.makedirs(d, exist_ok=True)
    dst = os.path.join(d, fname)
    if os.path.exists(dst):
        print(f"skip (existe): {dst}")
        continue
    try:
        raw = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=90).read()
        if comp == "gz":
            raw = gzip.decompress(raw)
        with open(dst, "wb") as f:
            f.write(raw)
        print(f"OK   {dst}  ({len(raw)} bytes)")
    except Exception as e:
        print(f"FALHA {url}\n      {type(e).__name__}: {e}")

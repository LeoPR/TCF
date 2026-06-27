"""Compara bytes do encode com accel=True (.pyd) vs accel=False (pure-Python).
Rode 2x (com e sem o .pyd) e compare os hashes -> prova T-CI-3."""
import csv, glob, hashlib, os
from tcf import encode
from tcf.composicional.syntax import M8AVirtualRefsSyntax as M
print(f"accel={M._detect_compositions_accelerated}")
for path in sorted(glob.glob("datasets/synthetic/*.csv")):
    with open(path, encoding="utf-8") as f:
        r = csv.reader(f); hdr = next(r); cols = {h: [] for h in hdr}
        for row in r:
            for h, v in zip(hdr, row): cols[h].append(v)
    if not cols or not next(iter(cols.values())): continue
    out = encode(cols).encode("utf-8")
    print(f"{os.path.basename(path):42}{len(out):6} {hashlib.sha256(out).hexdigest()[:16]}")

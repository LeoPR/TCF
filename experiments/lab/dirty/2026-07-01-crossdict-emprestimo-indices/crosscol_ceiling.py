"""TETO do cross-column sharing — vale insistir no HCC ref-share?

Barra corrigida (DICT-HIGHCARD): o per-coluna JA' e' min(tcf,raw,dict). O share so' vale se bater isso.
Teste-TETO (ignora a fronteira de coluna, entao e' um UPPER-BOUND do que qualquer share cross-coluna
poderia ganhar): encode(A ++ B) numa passada so' (OBAT/HCC ve as duas -> pode cross-referenciar) vs
min(A)+min(B). Se nem o teto bate o per-col-min, o HCC ref-share nao tem o que capturar. READ-ONLY.
"""
from __future__ import annotations

import csv
import gzip
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
from tcf.encoder import _encode_column                          # noqa: E402
from tcf.pipeline import PipelineConfig                          # noqa: E402
from tcf.multi.dict_v2b import _v2b_width, _v2b_idx_chars        # noqa: E402

CFG = PipelineConfig()
try:
    import brotli
    _bz = lambda b: len(brotli.compress(b)); CN = "brotli"       # noqa: E731
except ImportError:
    _bz = lambda b: len(gzip.compress(b, 9)); CN = "gzip"        # noqa: E731

CAP = 8000
EXT = Path("Z:/tcf-data/external")


def enc_tcf(vals):
    return _encode_column(vals, header="val", cfg=CFG, min_len=None).encode("utf-8")


def enc_dict(vals):
    seen, uni = {}, []
    for v in vals:
        if v not in seen:
            seen[v] = len(uni); uni.append(v)
    K = len(uni)
    if not (2 <= K < len(vals)):
        return None
    tb = _encode_column(uni, header="val", cfg=CFG, min_len=None).encode("utf-8")
    w = _v2b_width(K)
    return f"{len(tb)}\n".encode("utf-8") + tb + "".join(_v2b_idx_chars(seen[v], w) for v in vals).encode("utf-8")


def enc_raw(vals):
    return ("\n".join(vals) + "\n").encode("utf-8")


def best(vals):
    """min(tcf, raw, dict) — o per-coluna otimo. Retorna (bytes, modo)."""
    cands = [(enc_tcf(vals), "tcf"), (enc_raw(vals), "raw")]
    d = enc_dict(vals)
    if d is not None:
        cands.append((d, "dict"))
    b, m = min(cands, key=lambda x: len(x[0]))
    return b, m


def run(label, A, B, same_domain=True):
    A, B = [str(x) for x in A[:CAP]], [str(x) for x in B[:CAP]]
    bA, mA = best(A)
    bB, mB = best(B)
    percol = len(bA) + len(bB)
    concat = A + B
    bC, mC = best(concat)
    ceil_gain = 100 * (len(bC) - percol) / percol          # <0 = teto (share) bate per-col
    # controle
    gz_percol = _bz(bA) + _bz(bB)
    gz_concat = _bz(bC)
    gz_gain = 100 * (gz_concat - gz_percol) / gz_percol
    tag = "same-domain" if same_domain else "CONTROLE-disjunto"
    print(f"{label:30}[{tag}]  per-col={percol:7} ({mA}+{mB})  teto-concat={len(bC):7} ({mC})  "
          f"TETO={ceil_gain:+6.1f}%  {CN}={gz_gain:+6.1f}%", flush=True)
    return ceil_gain


def edges(path, cap=CAP):
    s, d = [], []
    for ln in path.open(encoding="utf-8"):
        if ln.startswith("#") or not ln.strip():
            continue
        p = ln.split()
        if len(p) >= 2:
            s.append(p[0]); d.append(p[1])
        if len(s) >= cap:
            break
    return s, d


if __name__ == "__main__":
    print(f"controle={CN}  CAP={CAP}\n")
    print("TETO<0 => share cross-coluna PODE ganhar (perseguir). TETO>=0 => beco sem saida.\n")
    res = []

    s, d = edges(EXT / "snap-ca-grqc" / "ca-GrQc.txt")
    res.append(run("SNAP from~to", s, d))
    s, d = edges(EXT / "snap-cit-hepth" / "cit-HepTh.txt")
    res.append(run("cit-HepTh from~to", s, d))
    s, d = edges(EXT / "snap-email-enron" / "email-Enron.txt")
    res.append(run("email-Enron from~to", s, d))
    of = [ln.split(",") for ln in (EXT / "openflights" / "routes.dat")
          .read_text(encoding="utf-8", errors="replace").splitlines() if len(ln.split(",")) >= 6]
    res.append(run("OpenFlights src~dst", [r[2] for r in of], [r[4] for r in of]))
    fb = list(csv.DictReader((EXT / "football-results" / "results.csv").open(encoding="utf-8")))
    res.append(run("football home~away", [r["home_team"] for r in fb], [r["away_team"] for r in fb]))

    # CONTROLE disjunto: 2 colunas de dominios diferentes (nao deve ganhar)
    res.append(run("CONTROLE home~tournament", [r["home_team"] for r in fb],
                   [r["tournament"] for r in fb], same_domain=False))

    print(f"\n=== VEREDITO ===")
    wins = sum(1 for g in res[:5] if g < 0)
    print(f"same-domain com TETO<0 (share PODE ganhar): {wins}/5")
    print("Se ~0/5: o per-col min ja' captura tudo; HCC ref-share nao tem alvo -> encostar cross-dict.")
    print("Se >0/5: ha' headroom; desenhar formato lazy-preservando que capture o teto.")

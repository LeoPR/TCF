"""(a) DESCAPAR V2-B — prototipo read-only (monkeypatch do cap; src/tcf INTOCADO).

Descapar = deixar o dict V2-B ser candidato do min() por coluna tambem p/ high-card (K>1024).
Byte-safe (o encoder ja' faz min(tcf,raw,v2b,split), core.py:178-191 -> min nunca regride).
Mede: (1) ganho de bytes multi-col nas tabelas reais; (2) os pins byte-canonicos INALTERADOS
(D1-D9/D17a/real-world sao single-col/low-card -> V2-B nem entra); (3) custo de compute + heuristica
de skip barata; RT em tudo.
"""
from __future__ import annotations

import csv
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
import tcf.multi.dict_v2b as v2b                                 # noqa: E402
from tcf import encode, decode                                   # noqa: E402
from tcf.multi.dict_v2b import _v2b_width                        # noqa: E402
from dataset_reader import DatasetReader                         # noqa: E402

ORIG_CAP = v2b._V2B_MAX_CARD
UNCAP = 10 ** 9
LIMIT = 5000


def _enc(cols, cap):
    v2b._V2B_MAX_CARD = cap
    t = time.perf_counter()
    blob = encode(cols)
    dt = time.perf_counter() - t
    v2b._V2B_MAX_CARD = ORIG_CAP
    return blob, dt


def _strcols(cols):
    return {k: [str(x) for x in v] for k, v in cols.items()}


def measure_table(label, cols):
    cols = _strcols(cols)
    cap, t_cap = _enc(cols, ORIG_CAP)
    unc, t_unc = _enc(cols, UNCAP)
    bc, bu = len(cap.encode("utf-8")), len(unc.encode("utf-8"))
    delta = 100 * (bu - bc) / bc
    # RT do uncapped
    try:
        got = decode(unc)
        rt = all(got.get(k) == cols[k] for k in cols) and set(got) == set(cols)
    except Exception as e:
        rt = f"ERRO {e}"
    print(f"  {label:34} cap={bc:8} unc={bu:8} delta={delta:+6.2f}%  "
          f"t_cap={t_cap:5.2f}s t_unc={t_unc:5.2f}s (x{t_unc/max(t_cap,1e-9):.2f})  RT={rt}",
          flush=True)
    return dict(label=label, bc=bc, bu=bu, delta=delta, t_cap=t_cap, t_unc=t_unc, rt=rt)


# ---------- (2) pins byte-canonicos ----------
def check_pins():
    SYN = ROOT / "datasets" / "synthetic"
    SAMP = ROOT / "datasets" / "samples"
    print("\n(2) PINS byte-canonicos (devem ser IDENTICOS capped vs uncapped):")

    def single(name, path):
        with path.open(encoding="utf-8") as f:
            r = csv.reader(f); next(r); vals = [row[0] for row in r if row]
        c, _ = _enc(vals, ORIG_CAP)         # single-col: encode(list)
        u, _ = _enc(vals, UNCAP)
        bc, bu = len(c.encode()), len(u.encode())
        print(f"    {name:26} cap={bc:7} unc={bu:7}  {'IGUAL' if bc == bu else '*** MUDOU ***'}")

    for n in ["D1-emails-simples", "D5-timestamps", "D8-tags-repetidas"]:
        p = SYN / f"{n}.csv"
        if p.exists():
            single(n, p)
    for n, rel in [("retail-description-2k", "online-retail/description-2k.csv"),
                   ("retail-stockcode-2k", "online-retail/stockcode-2k.csv"),
                   ("lineitem-comment-2k", "tpch-sf001/lcomment-2k.csv")]:
        p = SAMP / rel
        if p.exists():
            single(n, p)
    # D17a multi-col (deve seguir 303)
    p = SYN / "D17a-multi-column-mixed.csv"
    if p.exists():
        with p.open(encoding="utf-8") as f:
            r = csv.reader(f); hdr = next(r); rows = list(r)
        cols = {h: [row[i] for row in rows] for i, h in enumerate(hdr)}
        c, _ = _enc(cols, ORIG_CAP); u, _ = _enc(cols, UNCAP)
        print(f"    {'D17a (multi, 303 esperado)':26} cap={len(c.encode()):7} unc={len(u.encode()):7}  "
              f"{'IGUAL' if c == u else '*** MUDOU ***'}")


# ---------- (3) heuristica de skip barata ----------
def skip_analysis(hubcols):
    """skip = pular o dict-encode se N*w(K) >= tcf_bytes (o stream sozinho ja' perde -> dict perde).
    Sound (nunca pula vencedor). Mede quantos dict-encodes de high-card a heuristica evitaria."""
    from tcf.encoder import _encode_column
    from tcf.pipeline import PipelineConfig
    cfg = PipelineConfig()
    print("\n(3) HEURISTICA DE SKIP (N*w(K) >= tcf -> pular dict-encode; sound):")
    tried = skipped = wins_kept = 0
    for label, cols in hubcols:
        for cn, vals in cols.items():
            vals = [str(x) for x in vals]
            K = len(set(vals))
            if not (1024 < K < len(vals)):     # so' high-card (acima do cap) e' o novo custo
                continue
            tried += 1
            tcf = len(_encode_column(vals, header="val", cfg=cfg, min_len=None).encode())
            floor = len(vals) * _v2b_width(K)  # stream sozinho (cheap)
            if floor >= tcf:
                skipped += 1                    # dict nao pode ganhar -> skip evita o encode
    print(f"    colunas high-card (K>1024) que pagariam dict-encode: {tried}")
    print(f"    skip barato (N*w(K)>=tcf) evita: {skipped}/{tried} "
          f"({100*skipped/max(tried,1):.0f}%) SEM perder vencedor")


if __name__ == "__main__":
    print(f"cap original={ORIG_CAP}  UNCAP={UNCAP}  LIMIT={LIMIT}\n")
    print("(1) GANHO multi-col (uncapped vs capped; delta<=0 = descapar melhora; byte-safe):")
    hubcols = []
    for hub, tbls in [("br-identidades", ["pessoas", "empresas"]),
                      ("receita-cnpj", ["estabelecimentos"]),
                      ("tpch-sf001", ["lineitem", "orders", "partsupp", "customer"]),
                      ("adult-census", ["adult"])]:
        try:
            r = DatasetReader(hub)
        except Exception as e:
            print(f"  (hub {hub}: {e})"); continue
        for t in tbls:
            try:
                cols = r.columns(t, limit=LIMIT)
            except Exception as e:
                print(f"  ({hub}/{t}: {e})"); continue
            if cols:
                measure_table(f"{hub[:10]}/{t}", cols)
                hubcols.append((f"{hub}/{t}", cols))
        r.close()

    check_pins()
    skip_analysis(hubcols)

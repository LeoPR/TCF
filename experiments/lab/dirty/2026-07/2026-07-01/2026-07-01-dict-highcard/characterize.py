"""DICT-HIGHCARD — dict-per-col SEM cap vs OBAT/HCC, por N/K. Curado + incremental.

gain < 0 => dict VENCE OBAT/HCC. Controle = brotli/gzip. READ-ONLY (src/tcf intocado).
Colunas curadas da introspeccao (introspect.py): zona high-card+repeticao vs contrastes.
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
from dataset_reader import DatasetReader                         # noqa: E402

CFG = PipelineConfig()
try:
    import brotli
    _bz = lambda b: len(brotli.compress(b)); CN = "brotli"       # noqa: E731
except ImportError:
    _bz = lambda b: len(gzip.compress(b, 9)); CN = "gzip"        # noqa: E731

N_CAP = 12000
EXT = Path("Z:/tcf-data/external")

# curadas: (hub, tabela, coluna, rotulo-de-zona)
HUB_COLS = [
    ("tpch-sf001", "lineitem", "l_orderkey", "highK+rep"),
    ("tpch-sf001", "lineitem", "l_partkey", "highK+rep"),
    ("tpch-sf001", "lineitem", "l_shipdate", "highK+rep(data)"),
    ("tpch-sf001", "orders", "o_orderdate", "highK+rep(data)"),
    ("tpch-sf001", "orders", "o_custkey", "lowK+rep"),
    ("tpch-sf001", "partsupp", "ps_partkey", "highK+rep"),
    ("receita-cnpj", "estabelecimentos", "municipio_cod", "highK+rep"),
    ("receita-cnpj", "estabelecimentos", "data_inicio", "highK+rep(data)"),
    ("receita-cnpj", "estabelecimentos", "cnae_principal", "lowK+rep"),
    ("br-identidades", "pessoas", "municipio_id", "highK+rep"),
    ("br-identidades", "pessoas", "data_cadastro", "highK+rep(data)"),
    ("br-identidades", "empresas", "razao_social", "highK+rep(txt)"),
    ("br-identidades", "empresas", "socio_cpf", "highK+rep(cpf)"),
    ("ibge-municipios", "municipios", "microrregiao", "lowK+rep"),
    ("tpch-sf001", "lineitem", "l_comment", "highK+baixaRep"),
    ("br-identidades", "pessoas", "email", "highK+baixaRep"),
    ("adult-census", "adult", "fnlwgt", "highK+baixaRep"),
    ("adult-census", "adult", "occupation", "lowK(V2-B)"),
    ("tpch-sf001", "lineitem", "l_shipmode", "lowK(V2-B)"),
]


def uniques(vals):
    seen, uni = {}, []
    for v in vals:
        if v not in seen:
            seen[v] = len(uni); uni.append(v)
    return uni, seen


def enc_tcf(vals):
    return _encode_column(vals, header="val", cfg=CFG, min_len=None).encode("utf-8")


def enc_dict(vals):
    uni, seen = uniques(vals)
    K = len(uni)
    if not (2 <= K < len(vals)):
        return None, K
    tb = _encode_column(uni, header="val", cfg=CFG, min_len=None).encode("utf-8")
    w = _v2b_width(K)
    stream = "".join(_v2b_idx_chars(seen[v], w) for v in vals).encode("utf-8")
    return f"{len(tb)}\n".encode("utf-8") + tb + stream, K


def measure(src, name, zone, vals):
    vals = [str(v) for v in vals[:N_CAP]]
    d, K = enc_dict(vals)
    if d is None:
        return None
    tcf = enc_tcf(vals)
    r = dict(src=src, name=name[:20], zone=zone, N=len(vals), K=K, NK=len(vals) / K,
             tcf=len(tcf), dict=len(d),
             gain=100 * (len(d) - len(tcf)) / len(tcf),
             gz=100 * (_bz(d) - _bz(tcf)) / _bz(tcf))
    print(f"{src:16}{name[:20]:20}{zone:16}K={K:6} N/K={r['NK']:6.1f}  "
          f"gain={r['gain']:+6.1f}%  {CN}={r['gz']:+6.1f}%", flush=True)
    return r


def edges(path, cap=N_CAP):
    s = []
    for ln in path.open(encoding="utf-8"):
        if ln.startswith("#") or not ln.strip():
            continue
        p = ln.split()
        if len(p) >= 2:
            s.append(p[0])
        if len(s) >= cap:
            break
    return s


if __name__ == "__main__":
    print(f"controle={CN}  N_CAP={N_CAP}\n")
    rows = []
    readers = {}
    for hub, tbl, col, zone in HUB_COLS:
        try:
            if hub not in readers:
                readers[hub] = DatasetReader(hub)
            vals = readers[hub].columns(tbl, limit=N_CAP).get(col)
            if vals:
                m = measure(hub[:14], col, zone, vals)
                if m:
                    rows.append(m)
        except Exception as e:
            print(f"  (falha {hub}/{tbl}/{col}: {e})", flush=True)
    for r in readers.values():
        r.close()

    print("\n--- same-domain (as 5 fontes) ---", flush=True)
    try:
        rows.append(measure("snap-grqc", "from_node", "highK+rep", edges(EXT / "snap-ca-grqc" / "ca-GrQc.txt")))
        rows.append(measure("cit-hepth", "from_paper", "highK+rep", edges(EXT / "snap-cit-hepth" / "cit-HepTh.txt")))
        rows.append(measure("email-enron", "from_node", "highK+rep", edges(EXT / "snap-email-enron" / "email-Enron.txt")))
        of = [ln.split(",") for ln in (EXT / "openflights" / "routes.dat")
              .read_text(encoding="utf-8", errors="replace").splitlines() if len(ln.split(",")) >= 6]
        rows.append(measure("openflights", "src_airport", "highK+rep", [r[2] for r in of]))
        fb = list(csv.DictReader((EXT / "football-results" / "results.csv").open(encoding="utf-8")))
        rows.append(measure("football", "home_team", "lowK+rep", [r["home_team"] for r in fb]))
    except Exception as e:
        print(f"  (same-domain parcial: {e})", flush=True)
    rows = [r for r in rows if r]

    # artifact + resumo
    rows.sort(key=lambda r: r["gain"])
    hdr = f"{'fonte':16}{'coluna':20}{'zona':16}{'N':>7}{'K':>7}{'N/K':>7}{'tcf':>8}{'dict':>8}{'gain%':>8}{CN+'%':>8}"
    lines = [hdr, "-" * len(hdr)]
    for r in rows:
        lines.append(f"{r['src']:16}{r['name']:20}{r['zone']:16}{r['N']:>7}{r['K']:>7}{r['NK']:>7.1f}"
                     f"{r['tcf']:>8}{r['dict']:>8}{r['gain']:>+8.1f}{r['gz']:>+8.1f}")
    Path(__file__).parent.joinpath("artifacts", "sweep-full.txt").write_text("\n".join(lines), encoding="utf-8")

    def bucket(cond, lab):
        sub = [r for r in rows if cond(r)]
        if not sub:
            return
        w = sum(1 for r in sub if r["gain"] < 0)
        gw = sum(1 for r in sub if r["gz"] < 0)
        avg = sum(r["gain"] for r in sub) / len(sub)
        print(f"  {lab:34} n={len(sub):2}  dict-vence={w}/{len(sub)}  gz-vence={gw}/{len(sub)}  media={avg:+.1f}%")

    print(f"\n=== RESUMO (dict vs OBAT/HCC; gain<0 = dict vence) — {len(rows)} colunas ===")
    bucket(lambda r: r["K"] <= 1024, "K<=1024 (V2-B ja' cobre)")
    bucket(lambda r: r["K"] > 1024 and r["NK"] >= 3, "K>1024 & N/K>=3  (a HIPOTESE)")
    bucket(lambda r: r["K"] > 1024 and r["NK"] < 3, "K>1024 & N/K<3   (baixa repet)")
    print("\n  (full: artifacts/sweep-full.txt)")

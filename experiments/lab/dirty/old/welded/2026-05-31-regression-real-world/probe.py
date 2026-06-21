"""T-REGRESSION-REAL-WORLD — probe de poder discriminante.

Pergunta: quais fixtures real-world fazem o candidato #03 (prune-k-03,
known-bad: regrediu +0.59% em online-retail 20k) DIVERGIR do baseline,
enquanto #15 (topK-heap, byte-safe) MANTEM? Isso mede se o fixture tem
poder de pegar a regressao do regime n_tam_est>=3.

Roda baseline (src/tcf atual), depois patcha #03 e #15 (em-memoria,
restaurando entre cada), e compara bytes por coluna/tabela.

NAO modifica src/tcf. Patch em-memoria, restaurado.
"""
from __future__ import annotations

import csv
import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]  # .../TCF
SRC = REPO / "src"
SCRIPTS = REPO / "scripts"
for p in (str(SRC), str(SCRIPTS)):
    if p not in sys.path:
        sys.path.insert(0, p)

SAMPLES = REPO / "datasets" / "samples"
RETAIL_CSV = Path("Z:/tcf-data/external/online-retail/online_retail.csv")

FASE_A = REPO / "experiments" / "lab" / "dirty" / "2026-05-27-h-perf-06-v2-fase-a"
VARIANT_03 = FASE_A / "03-prune-k-03-adaptive-min-k-by-iter" / "syntax_variant.py"
VARIANT_15 = FASE_A / "15-tier-scoring-02-topK-heap-with-safe-skip" / "syntax_variant.py"


def load_variant_detect(path: Path, modname: str):
    spec = importlib.util.spec_from_file_location(modname, str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.M8AVirtualRefsSyntax._detect_compositions


def encode_str(values):
    from tcf import encode
    return encode([("" if v is None else str(v)) for v in values])


def col_bytes(values):
    out = encode_str(values)
    return len(out.encode("utf-8")), out


def rt_ok(values):
    from tcf import encode, decode
    sv = [("" if v is None else str(v)) for v in values]
    return decode(encode(sv)) == sv


# ---- fixtures --------------------------------------------------------------

def sample_columns(rel: str) -> dict[str, list[str]]:
    with (SAMPLES / rel).open(encoding="utf-8", newline="") as f:
        r = csv.reader(f)
        header = next(r)
        cols = {h: [] for h in header}
        for row in r:
            if len(row) != len(header):
                continue
            for h, v in zip(header, row):
                cols[h].append(v)
    return cols


def retail_columns(limit: int) -> dict[str, list[str]]:
    cols: dict[str, list[str]] = {}
    if not RETAIL_CSV.exists():
        return cols
    with RETAIL_CSV.open(encoding="utf-8", errors="replace", newline="") as f:
        r = csv.reader(f)
        header = next(r)
        cols = {h: [] for h in header}
        for i, row in enumerate(r):
            if i >= limit:
                break
            if len(row) != len(header):
                continue
            for h, v in zip(header, row):
                cols[h].append(v)
    return cols


def reader_columns(dataset: str, table: str, limit: int) -> dict[str, list[str]]:
    try:
        from dataset_reader import DatasetReader
        with DatasetReader(dataset) as rd:
            raw = rd.columns(table, limit=limit)
        return {k: [("" if v is None else str(v)) for v in vs] for k, vs in raw.items()}
    except Exception as e:  # noqa: BLE001
        print(f"  [reader {dataset}.{table} indisponivel: {e}]")
        return {}


# ---- probe core ------------------------------------------------------------

PROBES = []  # (label, columns_dict, focus_cols)

def register(label, cols, focus):
    if cols:
        PROBES.append((label, cols, [c for c in focus if c in cols]))


def main() -> int:
    from tcf.composicional.syntax import M8AVirtualRefsSyntax
    ORIG = M8AVirtualRefsSyntax._detect_compositions
    det_03 = load_variant_detect(VARIANT_03, "syntax_v03")
    det_15 = load_variant_detect(VARIANT_15, "syntax_v15")

    # committed 100-row samples
    register("retail-sample-100", sample_columns("online-retail/online-retail-sample.csv"),
             ["Description", "StockCode", "Country"])
    register("adult-sample-100", sample_columns("adult-census/adult-sample.csv"),
             ["occupation", "education", "native-country", "workclass"])
    register("lineitem-sample-100", sample_columns("tpch-sf001/lineitem-sample.csv"),
             ["l_comment", "l_shipinstruct", "l_shipmode"])

    # larger reads from Z: to find discrimination threshold
    for n in (500, 1000, 2000):
        register(f"retail-Z-{n}", retail_columns(n), ["Description", "StockCode"])
        register(f"adult-Z-{n}", reader_columns("adult-census", "adult", n),
                 ["occupation", "education", "native-country"])
        register(f"lineitem-Z-{n}", reader_columns("tpch-sf001", "lineitem", n),
                 ["l_comment", "l_shipinstruct"])

    print(f"{'fixture/col':<42} {'rows':>5} {'base':>7} {'#03':>7} {'#15':>7}  flags")
    print("-" * 90)
    any_disc = False
    for label, cols, focus in PROBES:
        for c in focus:
            vals = cols[c]
            n = len(vals)
            # baseline
            M8AVirtualRefsSyntax._detect_compositions = ORIG
            base, _ = col_bytes(vals)
            rt = rt_ok(vals)
            # #03
            M8AVirtualRefsSyntax._detect_compositions = det_03
            b03, _ = col_bytes(vals)
            # #15
            M8AVirtualRefsSyntax._detect_compositions = det_15
            b15, _ = col_bytes(vals)
            M8AVirtualRefsSyntax._detect_compositions = ORIG

            flags = []
            if not rt:
                flags.append("RT-FAIL")
            if b03 != base:
                flags.append(f"#03-DIFF({b03-base:+d})")
                any_disc = True
            if b15 != base:
                flags.append(f"#15-DIFF({b15-base:+d})")
            tag = f"{label}/{c}"
            print(f"{tag:<42} {n:>5} {base:>7} {b03:>7} {b15:>7}  {' '.join(flags)}")

    print("-" * 90)
    print(f"DISCRIMINANTE (algum #03-DIFF): {'SIM' if any_disc else 'NAO'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

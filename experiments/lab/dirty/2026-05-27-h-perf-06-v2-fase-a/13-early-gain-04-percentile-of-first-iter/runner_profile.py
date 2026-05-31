"""Profile runner para candidato early-gain-04-percentile-of-first-iter.

Replica setup do baseline (online-retail 20k linhas, 8 colunas) mas
APOS monkey-patch do variant. Salva variant.prof, imprime top 20 funcs
+ tempo total.

Default early_gain_peak_ratio=0 -> curto-circuita guard, byte-canonical
preservado. Objetivo: medir overhead introduzido pelo `max_net_seen`
tracking + guard (mesmo no caminho default).
"""
from __future__ import annotations

import cProfile
import csv
import importlib.util
import pstats
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[4]  # .../TCF
SRC = REPO / "src"
DATASET = Path("Z:/tcf-data/external/online-retail/online_retail.csv")
N_ROWS = 20000

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


# ---- Step 1: importar variant via importlib ----
VARIANT_PATH = HERE / "syntax_variant.py"
spec = importlib.util.spec_from_file_location(
    "syntax_variant_eg04_profile", str(VARIANT_PATH))
variant_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(variant_mod)


# ---- Step 2: monkey-patch M8AVirtualRefsSyntax ----
from tcf.composicional import syntax as canonical_syntax  # noqa: E402

canonical_syntax.M8AVirtualRefsSyntax.__init__ = (
    variant_mod.M8AVirtualRefsSyntax.__init__
)
canonical_syntax.M8AVirtualRefsSyntax._detect_compositions = (
    variant_mod.M8AVirtualRefsSyntax._detect_compositions
)

from tcf.composicional.hcc_seqrle import HCCSeqRLE  # noqa: E402
assert HCCSeqRLE._detect_compositions is canonical_syntax.M8AVirtualRefsSyntax._detect_compositions, \
    "HCCSeqRLE override de _detect_compositions detectado — patch incompleto"

from tcf import encode  # noqa: E402


# ---- Step 3: carregar dataset (mesmo do baseline) ----
def load_online_retail(path: Path, n_rows: int) -> dict[str, list[str]]:
    with path.open("r", encoding="utf-8", newline="") as fp:
        reader = csv.reader(fp)
        header = next(reader)
        cols: dict[str, list[str]] = {h: [] for h in header}
        loaded = 0
        for row in reader:
            if len(row) != len(header):
                continue
            for h, v in zip(header, row):
                cols[h].append(v)
            loaded += 1
            if loaded >= n_rows:
                break
    return cols


def main() -> int:
    print(f"[profile] variant = {VARIANT_PATH}")
    print(f"[profile] dataset = {DATASET} (first {N_ROWS} rows)")

    cols = load_online_retail(DATASET, N_ROWS)
    total_chars = sum(sum(len(v) for v in vals) for vals in cols.values())
    n_rows = len(next(iter(cols.values())))
    print(f"[profile] loaded {len(cols)} cols, {n_rows} rows, "
          f"{total_chars:,} chars total")
    print(f"[profile] default early_gain_peak_ratio = "
          f"{canonical_syntax.M8AVirtualRefsSyntax().early_gain_peak_ratio}")

    prof_path = HERE / "variant.prof"
    profiler = cProfile.Profile()

    t0 = time.perf_counter()
    profiler.enable()
    text = encode(cols)
    profiler.disable()
    elapsed = time.perf_counter() - t0

    out_bytes = len(text.encode("utf-8"))
    print(f"[profile] encode -> {out_bytes:,} bytes in {elapsed:.3f}s")

    profiler.dump_stats(str(prof_path))
    print(f"[profile] saved {prof_path}")

    stats = pstats.Stats(profiler).sort_stats("cumulative")
    print("\n[profile] TOP 20 functions (cumulative):")
    stats.print_stats(20)

    # Imprimir explicitamente o tempo de _detect_compositions
    print("\n[profile] _detect_compositions detail:")
    stats.print_stats("_detect_compositions")

    print(f"\n[profile] RESULT total_time_sec={elapsed:.6f} "
          f"out_bytes={out_bytes}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""H-PERF-06-v2 Fase A — profile runner for prune-k-01-skipK2-enumeration.

Mirrors 00-baseline/runner.py setup exactly (same dataset, same encode call,
same N_ROWS), but FIRST monkey-patches M8AVirtualRefsSyntax to use the
variant's _detect_compositions + patched __init__ (default min_k=2 =
byte-identical canonical). Then runs cProfile, saves variant.prof, prints
top 20 by cumtime + tottime.

Compare variant.prof against 00-baseline/baseline.prof.
"""
from __future__ import annotations

import cProfile
import csv
import importlib.util
import io
import pstats
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[4]  # .../TCF
SRC = REPO / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

# --- Load the variant module dynamically (same pattern as runner_regression) ---
VARIANT_PATH = HERE / "syntax_variant.py"
spec = importlib.util.spec_from_file_location(
    "syntax_variant_prune_k_01", str(VARIANT_PATH)
)
variant_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(variant_mod)

# --- Monkey-patch the canonical class (BEFORE importing encode) ---
from tcf.composicional import syntax as canon_syntax  # noqa: E402

_ORIG_INIT = canon_syntax.M8AVirtualRefsSyntax.__init__


def _patched_init(self, min_k=2):
    _ORIG_INIT(self)
    self._min_k = min_k


canon_syntax.M8AVirtualRefsSyntax._detect_compositions = (
    variant_mod.M8AVirtualRefsSyntax._detect_compositions
)
canon_syntax.M8AVirtualRefsSyntax.__init__ = _patched_init

from tcf import encode  # noqa: E402

# --- Dataset constants (mirror 00-baseline/runner.py) ---
DATASET_CSV = Path(r"Z:/tcf-data/external/online-retail/online_retail.csv")
N_ROWS = 20_000
PROF_PATH = HERE / "variant.prof"
TOP_N = 20


def load_dataset(path: Path, n_rows: int) -> dict[str, list[str]]:
    """Same loader as baseline: utf-8 then latin-1 fallback."""
    if not path.exists():
        raise FileNotFoundError(f"Dataset nao encontrado: {path}")
    for enc in ("utf-8", "latin-1"):
        try:
            with path.open("r", encoding=enc, newline="") as fp:
                reader = csv.reader(fp)
                header = next(reader)
                cols: dict[str, list[str]] = {h: [] for h in header}
                for i, row in enumerate(reader):
                    if i >= n_rows:
                        break
                    if len(row) != len(header):
                        continue
                    for h, v in zip(header, row):
                        cols[h].append(v)
            return cols
        except UnicodeDecodeError:
            continue
    raise RuntimeError("Falha ao decodificar CSV em utf-8 ou latin-1")


def main() -> int:
    print(f"[variant] dataset = {DATASET_CSV}")
    print(f"[variant] n_rows alvo = {N_ROWS}")
    print(f"[variant] patched class: {canon_syntax.M8AVirtualRefsSyntax.__module__}."
          f"{canon_syntax.M8AVirtualRefsSyntax.__name__}")
    print(f"[variant] patched _detect_compositions from: {variant_mod.__name__}")

    data = load_dataset(DATASET_CSV, N_ROWS)
    n_cols = len(data)
    n_rows_real = len(next(iter(data.values()))) if data else 0
    print(f"[variant] carregado: {n_cols} colunas, {n_rows_real} linhas")
    total_chars = sum(sum(len(v) for v in vs) for vs in data.values())
    print(f"[variant] total chars dado = {total_chars}")

    profiler = cProfile.Profile()
    print("[variant] iniciando profile de encode(...)")
    profiler.enable()
    out = encode(data)
    profiler.disable()
    print(f"[variant] encode OK. bytes saida = {len(out.encode('utf-8'))}")

    profiler.dump_stats(str(PROF_PATH))
    print(f"[variant] profile salvo em {PROF_PATH}")

    # Top N by cumulative time
    sio = io.StringIO()
    stats = pstats.Stats(profiler, stream=sio).sort_stats("cumulative")
    stats.print_stats(TOP_N)
    print(sio.getvalue())

    # Top N by tottime
    sio2 = io.StringIO()
    pstats.Stats(profiler, stream=sio2).sort_stats("tottime").print_stats(TOP_N)
    print("[variant] === top por TOTTIME ===")
    print(sio2.getvalue())

    # Print total time (sum of all cumtime of root = encoder.py:53 encode)
    # We grab the absolute clock time of the whole profile via stats.total_tt
    print(f"[variant] TOTAL_TIME_SEC={stats.total_tt:.6f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

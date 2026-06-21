"""Profile runner for candidate tier-scoring-01-cheap-upper-bound-prune.

Replicates the baseline setup (00-baseline/runner.py) but monkey-patches
M8AVirtualRefsSyntax._detect_compositions with the variant version before
profiling. Saves variant.prof and prints top 20 funcs + total time.

Dataset: Z:/tcf-data/external/online-retail/online_retail.csv (20k rows).
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

VARIANT_PATH = HERE / "syntax_variant.py"

DATASET_CSV = Path(r"Z:/tcf-data/external/online-retail/online_retail.csv")
N_ROWS = 20_000
PROF_PATH = HERE / "variant.prof"
TOP_N = 20


def load_variant_module():
    spec = importlib.util.spec_from_file_location(
        "syntax_variant_mod", str(VARIANT_PATH),
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def apply_monkey_patch():
    """Replace M8AVirtualRefsSyntax._detect_compositions on the canonical
    class so HCCSeqRLE (which inherits) also uses the variant."""
    variant_mod = load_variant_module()
    from tcf.composicional import syntax as canonical_mod
    variant_method = variant_mod.M8AVirtualRefsSyntax._detect_compositions
    canonical_mod.M8AVirtualRefsSyntax._detect_compositions = variant_method
    return variant_method


def load_dataset(path: Path, n_rows: int) -> dict[str, list[str]]:
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
    print(f"[variant] patching M8AVirtualRefsSyntax._detect_compositions ...")
    apply_monkey_patch()
    # Import encode AFTER patch so HCC pipeline uses variant method
    from tcf import encode  # noqa: E402

    print(f"[variant] dataset = {DATASET_CSV}")
    print(f"[variant] n_rows alvo = {N_ROWS}")
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

    # Total cumulative time = encoder.py:encode (entry point cumtime)
    stats = pstats.Stats(profiler)
    total_time = stats.total_tt
    print(f"[variant] TOTAL_TIME_SEC={total_time:.4f}")

    # Top 20 by cumulative time
    sio = io.StringIO()
    pstats.Stats(profiler, stream=sio).sort_stats("cumulative").print_stats(TOP_N)
    print(sio.getvalue())

    sio2 = io.StringIO()
    pstats.Stats(profiler, stream=sio2).sort_stats("tottime").print_stats(TOP_N)
    print("[variant] === top por TOTTIME ===")
    print(sio2.getvalue())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

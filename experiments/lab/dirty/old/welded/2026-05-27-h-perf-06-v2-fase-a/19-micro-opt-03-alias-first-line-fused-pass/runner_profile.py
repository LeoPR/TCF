"""H-PERF-06-v2 Fase A - variant cProfile do encode TCF.

Replica setup do baseline (00-baseline/runner.py), mas monkey-patches
M8AVirtualRefsSyntax._detect_compositions com a versao do
syntax_variant.py (micro-opt-03: fusao do alias_first_line scan no
primeiro pass).

Roda cProfile pelo mesmo dataset (online-retail 20k), salva
`variant.prof` e imprime top 20 funcoes por cumtime + tempo total.

Uso:
    python runner_profile.py
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

# --- Load the variant module dynamically (mesmo padrao do runner_regression) ---
VARIANT_PATH = HERE / "syntax_variant.py"
spec = importlib.util.spec_from_file_location(
    "syntax_variant_micro_opt_03", str(VARIANT_PATH)
)
variant_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(variant_mod)

# --- Monkey-patch the canonical class BEFORE importing encode ---
from tcf.composicional import syntax as canon_syntax  # noqa: E402

canon_syntax.M8AVirtualRefsSyntax._detect_compositions = (
    variant_mod.M8AVirtualRefsSyntax._detect_compositions
)

from tcf import encode  # noqa: E402

DATASET_CSV = Path(r"Z:/tcf-data/external/online-retail/online_retail.csv")
N_ROWS = 20_000
PROF_PATH = HERE / "variant.prof"
TOP_N = 20


def load_dataset(path: Path, n_rows: int) -> dict[str, list[str]]:
    """Le n_rows do CSV em formato multi-col dict {col: [str, ...]}."""
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
    print("[variant] micro-opt-03-alias-first-line-fused-pass")
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

    # Total time (sum of tottime across all functions == wall time of profile)
    stats = pstats.Stats(profiler)
    total_tt = stats.total_tt
    print(f"[variant] TOTAL TIME (sec) = {total_tt:.4f}")

    # Top 20 por cumulative time
    sio = io.StringIO()
    pstats.Stats(profiler, stream=sio).sort_stats("cumulative").print_stats(TOP_N)
    print("[variant] === top por CUMULATIVE TIME ===")
    print(sio.getvalue())

    # Top 20 por tottime
    sio2 = io.StringIO()
    pstats.Stats(profiler, stream=sio2).sort_stats("tottime").print_stats(TOP_N)
    print("[variant] === top por TOTTIME ===")
    print(sio2.getvalue())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

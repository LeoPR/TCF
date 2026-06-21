"""H-PERF-06-v2 Fase A — cProfile do encode TCF para variant
07-prune-singleton-03-pair-prefilter-anchor.

Replica setup do baseline (00-baseline/runner.py): mesma amostra 20k
de online-retail. Monkey-patches igual ao runner_regression.py:
substitui `M8AVirtualRefsSyntax._detect_compositions` pela versao do
variant (HCCSeqRLE herda, entao basta patch na base).

Salva `variant.prof` ao lado deste arquivo. Imprime top 20 por
cumulative time + total wall time do encode.

Uso:
    python runner_profile.py
"""
from __future__ import annotations

import cProfile
import csv
import importlib.util
import io
import os
import pstats
import sys
import time
from pathlib import Path

# Determinismo de hash igual ao runner_regression.py
os.environ.setdefault("PYTHONHASHSEED", "0")

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[4]  # .../TCF
SRC = REPO / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

# --- 1. Carregar syntax_variant.py via importlib --------------------
VARIANT_PATH = HERE / "syntax_variant.py"
spec = importlib.util.spec_from_file_location(
    "syntax_variant_pruneSingleton03_profile", str(VARIANT_PATH)
)
variant_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(variant_mod)

# --- 2. Monkey-patch _detect_compositions na classe canonical -------
from tcf.composicional import syntax as canonical_syntax  # noqa: E402

canonical_syntax.M8AVirtualRefsSyntax._detect_compositions = (
    variant_mod.M8AVirtualRefsSyntax._detect_compositions
)

# --- 3. Import encode DEPOIS do patch -------------------------------
from tcf import encode  # noqa: E402


DATASET_CSV = Path(r"Z:/tcf-data/external/online-retail/online_retail.csv")
N_ROWS = 20_000
PROF_PATH = HERE / "variant.prof"
TOP_N = 20


def load_dataset(path: Path, n_rows: int) -> dict[str, list[str]]:
    """Identico ao baseline runner: 20k linhas multi-col dict."""
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
    print(f"[variant-profile] variant = {VARIANT_PATH.name}")
    print(f"[variant-profile] dataset = {DATASET_CSV}")
    print(f"[variant-profile] n_rows alvo = {N_ROWS}")
    data = load_dataset(DATASET_CSV, N_ROWS)
    n_cols = len(data)
    n_rows_real = len(next(iter(data.values()))) if data else 0
    print(f"[variant-profile] carregado: {n_cols} colunas, {n_rows_real} linhas")
    total_chars = sum(sum(len(v) for v in vs) for vs in data.values())
    print(f"[variant-profile] total chars dado = {total_chars}")

    profiler = cProfile.Profile()
    print("[variant-profile] iniciando profile de encode(...)")
    t_wall_start = time.perf_counter()
    profiler.enable()
    out = encode(data)
    profiler.disable()
    t_wall_end = time.perf_counter()
    wall_sec = t_wall_end - t_wall_start
    out_bytes = len(out.encode("utf-8"))
    print(f"[variant-profile] encode OK. bytes saida = {out_bytes}")
    print(f"[variant-profile] wall-time encode = {wall_sec:.6f} s")

    profiler.dump_stats(str(PROF_PATH))
    print(f"[variant-profile] profile salvo em {PROF_PATH}")

    # Top N por cumulative
    sio = io.StringIO()
    stats = pstats.Stats(profiler, stream=sio).sort_stats("cumulative")
    stats.print_stats(TOP_N)
    print(sio.getvalue())

    # Tempo total observado pelo profiler (somatorio cumtime da raiz)
    sio2 = io.StringIO()
    pstats.Stats(profiler, stream=sio2).sort_stats("tottime").print_stats(TOP_N)
    print("[variant-profile] === top por TOTTIME ===")
    print(sio2.getvalue())

    # Imprime linha machine-readable
    print(
        f"::RESULT:: wall_sec={wall_sec:.6f} out_bytes={out_bytes} "
        f"prof_path={PROF_PATH}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

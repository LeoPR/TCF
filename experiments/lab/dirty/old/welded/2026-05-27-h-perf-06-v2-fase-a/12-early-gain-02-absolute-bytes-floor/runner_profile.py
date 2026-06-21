"""H-PERF-06-v2 Fase A — runner profile early-gain-02-absolute-bytes-floor.

Replica o setup do baseline (00-baseline/runner.py): mesmo dataset
online-retail 20k linhas, mesmo encode multi-col. Monkey-patches o
variant (igual runner_regression.py) e roda cProfile, salvando
variant.prof + imprimindo top 20 por cumtime + tottime + tempo total.

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
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[4]  # .../TCF
SRC = REPO / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

# ---- 1) Carrega variante via importlib ----
VARIANT_PATH = HERE / "syntax_variant.py"
spec = importlib.util.spec_from_file_location(
    "syntax_variant_early_gain_02", VARIANT_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError(f"Falha ao criar spec pra {VARIANT_PATH}")
variant_mod = importlib.util.module_from_spec(spec)
sys.modules["syntax_variant_early_gain_02"] = variant_mod
spec.loader.exec_module(variant_mod)

VariantClass = variant_mod.M8AVirtualRefsSyntax

# ---- 2) Monkey-patch a classe canonical ----
import tcf.composicional.syntax as canonical_syntax  # noqa: E402

canonical_syntax.M8AVirtualRefsSyntax.__init__ = VariantClass.__init__
canonical_syntax.M8AVirtualRefsSyntax._detect_compositions = (
    VariantClass._detect_compositions)

import tcf.composicional.hcc_seqrle as canonical_seqrle  # noqa: E402
assert canonical_seqrle.M8AVirtualRefsSyntax is canonical_syntax.M8AVirtualRefsSyntax, \
    "Subclass HCCSeqRLE deve compartilhar parent class object"

from tcf import encode  # noqa: E402

DATASET_CSV = Path(r"Z:/tcf-data/external/online-retail/online_retail.csv")
N_ROWS = 20_000
PROF_PATH = HERE / "variant.prof"
TOP_N = 20


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
    print(f"[variant] dataset = {DATASET_CSV}")
    print(f"[variant] n_rows alvo = {N_ROWS}")
    print(f"[variant] variant = {VARIANT_PATH}")
    print(f"[variant] patched class id = {id(canonical_syntax.M8AVirtualRefsSyntax)}")
    data = load_dataset(DATASET_CSV, N_ROWS)
    n_cols = len(data)
    n_rows_real = len(next(iter(data.values()))) if data else 0
    print(f"[variant] carregado: {n_cols} colunas, {n_rows_real} linhas")
    total_chars = sum(sum(len(v) for v in vs) for vs in data.values())
    print(f"[variant] total chars dado = {total_chars}")

    profiler = cProfile.Profile()
    print("[variant] iniciando profile de encode(...)")
    t0 = time.perf_counter()
    profiler.enable()
    out = encode(data)
    profiler.disable()
    elapsed = time.perf_counter() - t0
    print(f"[variant] encode OK. bytes saida = {len(out.encode('utf-8'))}")
    print(f"[variant] WALL elapsed = {elapsed:.3f} sec")

    profiler.dump_stats(str(PROF_PATH))
    print(f"[variant] profile salvo em {PROF_PATH}")

    # Tempo total cProfile
    stats_all = pstats.Stats(profiler)
    print(f"[variant] cProfile total time = {stats_all.total_tt:.3f} sec")

    # Top 20 por cumulative time
    sio = io.StringIO()
    stats = pstats.Stats(profiler, stream=sio).sort_stats("cumulative")
    stats.print_stats(TOP_N)
    print("[variant] === top por CUMTIME ===")
    print(sio.getvalue())

    # top por tottime
    sio2 = io.StringIO()
    pstats.Stats(profiler, stream=sio2).sort_stats("tottime").print_stats(TOP_N)
    print("[variant] === top por TOTTIME ===")
    print(sio2.getvalue())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

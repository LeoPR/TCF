"""H-PERF-06-v2 Fase A — Candidate 16 tier-scoring-04-remove-wasted-sort-trace
cProfile profile runner.

Espelha 08-prune-singleton-04/runner_profile.py mas com monkey-patch de
_detect_compositions E _build_trace aplicado ANTES do encode
(igual a runner_regression.py).

Steps:
1. Carrega syntax_variant.py via importlib.util.
2. Monkey-patches M8AVirtualRefsSyntax._detect_compositions e _build_trace.
3. Roda cProfile pelo mesmo dataset do baseline (online-retail 20k linhas).
4. Salva variant.prof + imprime top 20 funcs por cumtime e tottime.

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

# Garantir que `src/` esta no path (rodar standalone, sem instalar pacote).
HERE = Path(__file__).resolve().parent
REPO = HERE.parents[4]  # .../TCF
SRC = REPO / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

# ---- Step 1: load variant module ----
VARIANT_PATH = HERE / "syntax_variant.py"
spec = importlib.util.spec_from_file_location(
    "syntax_variant_16_tier_scoring_04", str(VARIANT_PATH))
variant_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(variant_mod)

# ---- Step 2: monkey-patch _detect_compositions + _build_trace on canonical class ----
import tcf.composicional.syntax as canon_syntax  # noqa: E402

canon_syntax.M8AVirtualRefsSyntax._detect_compositions = (
    variant_mod.M8AVirtualRefsSyntax._detect_compositions
)
canon_syntax.M8AVirtualRefsSyntax._build_trace = (
    variant_mod.M8AVirtualRefsSyntax._build_trace
)
import tcf.composicional.hcc_seqrle as hcc_seqrle  # noqa: E402
assert hcc_seqrle.HCCSeqRLE._detect_compositions is (
    variant_mod.M8AVirtualRefsSyntax._detect_compositions
), "HCCSeqRLE nao herdou patch de _detect_compositions"
assert hcc_seqrle.HCCSeqRLE._build_trace is (
    variant_mod.M8AVirtualRefsSyntax._build_trace
), "HCCSeqRLE nao herdou patch de _build_trace"

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
    print(f"[variant] dataset = {DATASET_CSV}")
    print(f"[variant] n_rows alvo = {N_ROWS}")
    print(f"[variant] patched _detect_compositions + _build_trace on M8AVirtualRefsSyntax + HCCSeqRLE")
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

    # total time
    stats_all = pstats.Stats(profiler)
    total_time = stats_all.total_tt
    print(f"[variant] TOTAL TIME = {total_time:.3f}s")

    # Top 20 por cumulative time
    sio = io.StringIO()
    stats = pstats.Stats(profiler, stream=sio).sort_stats("cumulative")
    stats.print_stats(TOP_N)
    print(sio.getvalue())

    # por tottime
    sio2 = io.StringIO()
    pstats.Stats(profiler, stream=sio2).sort_stats("tottime").print_stats(TOP_N)
    print("[variant] === top por TOTTIME ===")
    print(sio2.getvalue())

    # machine-readable summary
    print(f"VARIANT_TOTAL_TIME_SEC {total_time:.6f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

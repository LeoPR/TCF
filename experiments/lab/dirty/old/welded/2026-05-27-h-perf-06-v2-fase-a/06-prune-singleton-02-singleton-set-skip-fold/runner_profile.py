"""H-PERF-06-v2 Fase A — cProfile do encode TCF com variant aplicado.

Replica o setup do baseline (00-baseline/runner.py):
  - mesmo dataset (Z:/tcf-data/external/online-retail/online_retail.csv, 20k linhas)
  - mesmo encode (from tcf import encode)
  - mesma estrategia de carga (multi-col dict, fallback utf-8/latin-1)

Antes do encode, aplica monkey-patch igual ao runner_regression.py:
  - substitui M8AVirtualRefsSyntax._detect_compositions pelo do
    syntax_variant.py (singleton-set skip-fold, 2-pass)
  - force-bind em HCCSeqRLE para garantir override mesmo se a subclasse
    re-binder o metodo.

Roda cProfile, salva variant.prof, imprime top 20 + tempo total.
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

DATASET_CSV = Path(r"Z:/tcf-data/external/online-retail/online_retail.csv")
N_ROWS = 20_000
PROF_PATH = HERE / "variant.prof"
TOP_N = 20


def load_variant_module():
    variant_path = HERE / "syntax_variant.py"
    spec = importlib.util.spec_from_file_location(
        "syntax_variant_prune_singleton_02", str(variant_path)
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def apply_monkey_patch():
    """Patch _detect_compositions on canonical M8AVirtualRefsSyntax
    so subclasses (HCCSeqRLE) inherit the new method automatically.
    Identico ao runner_regression.py."""
    variant = load_variant_module()
    import tcf.composicional.syntax as canonical_syntax
    import tcf.composicional.hcc_seqrle as canonical_hcc

    canonical_syntax.M8AVirtualRefsSyntax._detect_compositions = (
        variant.M8AVirtualRefsSyntax._detect_compositions
    )
    if hasattr(canonical_hcc.HCCSeqRLE, "_detect_compositions"):
        canonical_hcc.HCCSeqRLE._detect_compositions = (
            variant.M8AVirtualRefsSyntax._detect_compositions
        )
    return variant


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
    print("[variant-profile] aplicando monkey-patch (singleton-set skip-fold)")
    apply_monkey_patch()

    # IMPORTANTE: importar `encode` apenas APOS o patch, para garantir
    # que qualquer cache de bound-method na cadeia resolva ao novo metodo.
    # (Mesmo assim, classes resolvem metodos por lookup dinamico, mas
    # importar apos patch nao prejudica e e' mais defensivo.)
    from tcf import encode  # noqa: E402

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
    profiler.enable()
    out = encode(data)
    profiler.disable()
    print(f"[variant-profile] encode OK. bytes saida = {len(out.encode('utf-8'))}")

    profiler.dump_stats(str(PROF_PATH))
    print(f"[variant-profile] profile salvo em {PROF_PATH}")

    # Tempo total (cumtime do entry point) via stats
    stats_obj = pstats.Stats(profiler)
    total_time = stats_obj.total_tt
    print(f"[variant-profile] TOTAL TIME (pstats.total_tt) = {total_time:.4f} s")

    # Top N por cumulative time
    sio = io.StringIO()
    stats = pstats.Stats(profiler, stream=sio).sort_stats("cumulative")
    stats.print_stats(TOP_N)
    print(sio.getvalue())

    sio2 = io.StringIO()
    pstats.Stats(profiler, stream=sio2).sort_stats("tottime").print_stats(TOP_N)
    print("[variant-profile] === top por TOTTIME ===")
    print(sio2.getvalue())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""H-PERF-06-v2 Fase A — micro-opt-04 cProfile do encode TCF (variant).

Espelho de 00-baseline/runner.py, mas com monkey-patch do
`_detect_compositions` em M8AVirtualRefsSyntax pelo variant
(`syntax_variant.py`) que difere o sort de candidates.

Carrega mesma amostra 20k do online-retail, roda `from tcf import encode`
sob cProfile, salva `variant.prof` e imprime top 20 funcoes por cumtime.

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

# Garantir que `src/` esta no path
HERE = Path(__file__).resolve().parent
REPO = HERE.parents[4]  # .../TCF
SRC = REPO / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def load_variant():
    """Load variant module from sibling syntax_variant.py via importlib."""
    variant_path = HERE / "syntax_variant.py"
    spec = importlib.util.spec_from_file_location(
        "syntax_variant_micro04", str(variant_path)
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def patch_syntax(variant_mod):
    """Monkey-patch _detect_compositions on canonical M8AVirtualRefsSyntax.
    HCCSeqRLE inherits via subclass, so the single class-level patch covers
    both code paths used during multi-col encode."""
    from tcf.composicional import syntax as canonical
    canonical.M8AVirtualRefsSyntax._detect_compositions = (
        variant_mod.M8AVirtualRefsSyntax._detect_compositions
    )
    canonical._LazyIterInfo = variant_mod._LazyIterInfo


# Aplica patch ANTES de importar tcf.encode pra garantir que qualquer
# resolucao de simbolos use a versao patched.
_variant_mod = load_variant()
patch_syntax(_variant_mod)

from tcf import encode  # noqa: E402

# Sanity: confirma patch antes de rodar
from tcf.composicional.syntax import M8AVirtualRefsSyntax  # noqa: E402
assert (
    M8AVirtualRefsSyntax._detect_compositions
    is _variant_mod.M8AVirtualRefsSyntax._detect_compositions
), "monkey-patch nao persistiu"

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

    # Top 20 por cumulative time
    sio = io.StringIO()
    stats = pstats.Stats(profiler, stream=sio).sort_stats("cumulative")
    stats.print_stats(TOP_N)
    print(sio.getvalue())

    # tambem por tottime (ajuda diagnostico)
    sio2 = io.StringIO()
    pstats.Stats(profiler, stream=sio2).sort_stats("tottime").print_stats(TOP_N)
    print("[variant] === top por TOTTIME ===")
    print(sio2.getvalue())

    # Tempo total do encode (cumtime do encode root)
    total_cum = 0.0
    detect_cum = 0.0
    raw_stats = pstats.Stats(profiler)
    for (_file, _line, fname), (_cc, _nc, _tt, ct, _callers) in raw_stats.stats.items():
        # encode publica
        if fname == "encode" and "encoder.py" in _file:
            total_cum = max(total_cum, ct)
        if fname == "_detect_compositions" and "syntax.py" in _file:
            detect_cum = max(detect_cum, ct)
    print(f"[variant] TOTAL_ENCODE_CUMTIME={total_cum:.4f}s")
    print(f"[variant] DETECT_COMPOSITIONS_CUMTIME={detect_cum:.4f}s")
    if total_cum > 0:
        print(f"[variant] DETECT_PCT={detect_cum/total_cum*100:.2f}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

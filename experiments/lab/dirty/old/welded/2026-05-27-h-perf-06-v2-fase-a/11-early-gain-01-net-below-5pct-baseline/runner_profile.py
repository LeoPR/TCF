"""H-PERF-06-v2 Fase A — runner de profile (variant early-gain-01).

Replica setup do baseline (00-baseline/runner.py):
- Mesmo dataset (Z:/tcf-data/external/online-retail/online_retail.csv, 20k linhas)
- Mesmo `encode(data)` API
- Antes do encode, monkey-patcha M8AVirtualRefsSyntax com syntax_variant
  (igual runner_regression.py)

Saida:
- variant.prof (cProfile dump)
- top 20 funcs por cumtime impresso em stdout
- tempo total encode

Nota: este runner usa o threshold DEFAULT (0.0 = no-op), conforme o
escopo do prototype (validar preservacao byte-canonical). Speedup
versus baseline mede o overhead PURO do guard `if self.early_gain_threshold > 0`
no caminho quente (que deveria ser ~zero ja' que e' uma comparacao
contra atributo de instancia).
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


DATASET_CSV = Path(r"Z:/tcf-data/external/online-retail/online_retail.csv")
N_ROWS = 20_000
PROF_PATH = HERE / "variant.prof"
TOP_N = 20


def load_variant_module():
    """Carrega syntax_variant.py como modulo standalone."""
    variant_path = HERE / "syntax_variant.py"
    spec = importlib.util.spec_from_file_location(
        "syntax_variant_h_perf_06_early_gain_01", variant_path
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def apply_monkey_patch():
    """Monkey-patcha M8AVirtualRefsSyntax com __init__ + _detect_compositions
    do variant. HCCSeqRLE (subclasse) herda automatic."""
    variant = load_variant_module()
    import tcf.composicional.syntax as canonical_mod

    variant_cls = variant.M8AVirtualRefsSyntax
    canonical_cls = canonical_mod.M8AVirtualRefsSyntax

    canonical_cls.__init__ = variant_cls.__init__
    canonical_cls._detect_compositions = variant_cls._detect_compositions
    return canonical_cls


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
    print(f"[variant-profile] REPO    = {REPO}")
    print(f"[variant-profile] dataset = {DATASET_CSV}")
    print(f"[variant-profile] n_rows alvo = {N_ROWS}")

    print("[variant-profile] Aplicando monkey-patch (variant)...")
    patched_cls = apply_monkey_patch()
    print(f"[variant-profile] Patched class: {patched_cls}")
    print(f"[variant-profile] Method _detect_compositions: "
          f"{patched_cls._detect_compositions.__module__}."
          f"{patched_cls._detect_compositions.__qualname__}")
    inst = patched_cls()
    if not hasattr(inst, "early_gain_threshold"):
        print("[variant-profile] FAILED_BUILD: instancia nao tem early_gain_threshold")
        return 2
    print(f"[variant-profile] early_gain_threshold default = "
          f"{inst.early_gain_threshold}")

    # Importar encode DEPOIS do patch.
    from tcf import encode

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

    # Top 20 por cumulative time
    sio = io.StringIO()
    stats = pstats.Stats(profiler, stream=sio).sort_stats("cumulative")
    stats.print_stats(TOP_N)
    print(sio.getvalue())

    # tambem por tottime (ajuda diagnostico)
    sio2 = io.StringIO()
    pstats.Stats(profiler, stream=sio2).sort_stats("tottime").print_stats(TOP_N)
    print("[variant-profile] === top por TOTTIME ===")
    print(sio2.getvalue())

    # Tempo total = cumtime do root frame (encode chamada).
    # Strategy: pegar total_tt do pstats.
    total_tt = stats.total_tt
    print(f"[variant-profile] TOTAL_TIME_SEC={total_tt:.6f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

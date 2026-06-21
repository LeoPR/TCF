"""H-PERF-06-v2 Fase A — variant cProfile do encode TCF.

Replica setup do baseline (00-baseline/runner.py): mesma amostra
20k linhas do online-retail, mesma chamada `from tcf import encode`.
Diferenca: monkey-patches o `M8AVirtualRefsSyntax._detect_compositions`
canonical com a versao variant deste lab (mesma logica do
runner_regression.py), salva `variant.prof` e imprime top 20.

Nota: defaults OFF — variant roda byte-canonical exato. Este profile
mede overhead estrutural do bloco gating (esperado ~0%).
"""
from __future__ import annotations

import cProfile
import csv
import importlib.util
import io
import pstats
import sys
from pathlib import Path

# --- paths ---
HERE = Path(__file__).resolve().parent
REPO = HERE.parents[4]  # .../TCF
SRC = REPO / "src"
VARIANT = HERE / "syntax_variant.py"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

# --- carregar variant via importlib ---
spec = importlib.util.spec_from_file_location(
    "syntax_variant_h_perf_06_v2_09", str(VARIANT)
)
variant_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(variant_mod)
VariantSyntax = variant_mod.M8AVirtualRefsSyntax

# --- monkey-patch canonical M8AVirtualRefsSyntax ANTES de importar encode ---
import tcf.composicional.syntax as canonical_syntax  # noqa: E402

canonical_syntax.M8AVirtualRefsSyntax._detect_compositions = (
    VariantSyntax._detect_compositions
)

_orig_init = canonical_syntax.M8AVirtualRefsSyntax.__init__


def _patched_init(self):
    _orig_init(self)
    if not hasattr(self, "hcc_early_stop_streak"):
        self.hcc_early_stop_streak = None
    if not hasattr(self, "hcc_early_stop_threshold"):
        self.hcc_early_stop_threshold = None


canonical_syntax.M8AVirtualRefsSyntax.__init__ = _patched_init

# Agora importa encode (apos patch nas classes canonical)
from tcf import encode  # noqa: E402

# patch referencias no modulo encoder (caso ja' tenham sido bindadas)
import tcf.encoder as enc_mod  # noqa: E402

enc_mod.M8AVirtualRefsSyntax._detect_compositions = (
    VariantSyntax._detect_compositions
)
enc_mod.M8AVirtualRefsSyntax.__init__ = _patched_init

# Patch HCCSeqRLE __init__ caso tenha override (consistencia c/ regression)
import tcf.composicional.hcc_seqrle as seqrle_mod  # noqa: E402

if "__init__" in seqrle_mod.HCCSeqRLE.__dict__:
    _orig_seq_init = seqrle_mod.HCCSeqRLE.__init__

    def _patched_seq_init(self):
        _orig_seq_init(self)
        if not hasattr(self, "hcc_early_stop_streak"):
            self.hcc_early_stop_streak = None
        if not hasattr(self, "hcc_early_stop_threshold"):
            self.hcc_early_stop_threshold = None

    seqrle_mod.HCCSeqRLE.__init__ = _patched_seq_init


# --- dataset (IDENTICO ao baseline) ---
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
    print(f"[variant] monkey-patch ativo (defaults OFF — byte-canonical)")
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
    out_bytes = len(out.encode("utf-8"))
    print(f"[variant] encode OK. bytes saida = {out_bytes}")

    profiler.dump_stats(str(PROF_PATH))
    print(f"[variant] profile salvo em {PROF_PATH}")

    # Tempo total via pstats.total_tt
    stats = pstats.Stats(profiler)
    total_tt = stats.total_tt
    print(f"[variant] total_tt = {total_tt:.4f}s")

    # Top 20 por cumulative time
    sio = io.StringIO()
    stats2 = pstats.Stats(profiler, stream=sio).sort_stats("cumulative")
    stats2.print_stats(TOP_N)
    print(sio.getvalue())

    sio2 = io.StringIO()
    pstats.Stats(profiler, stream=sio2).sort_stats("tottime").print_stats(TOP_N)
    print("[variant] === top por TOTTIME ===")
    print(sio2.getvalue())

    # Machine-readable line
    print(f"RESULT variant_bytes={out_bytes} variant_total_tt={total_tt:.6f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

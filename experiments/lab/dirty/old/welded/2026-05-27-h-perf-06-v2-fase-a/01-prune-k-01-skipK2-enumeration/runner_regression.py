"""H-PERF-06-v2 Fase A — regression runner for prune-k-01-skipK2-enumeration.

Monkey-patches M8AVirtualRefsSyntax._detect_compositions with the version
from syntax_variant.py (with default min_k=2 = canonical byte behavior),
then runs `from tcf import encode` on D1-D9 + D17a, comparing bytes against
the canonical baselines (D1-D9 = 1523, D17a = 322).

Default min_k=2: should produce byte-identical output to canonical.
"""
from __future__ import annotations

import csv
import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[4]  # .../TCF
SRC = REPO / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

# --- Load the variant module dynamically ---
VARIANT_PATH = HERE / "syntax_variant.py"
spec = importlib.util.spec_from_file_location(
    "syntax_variant_prune_k_01", str(VARIANT_PATH)
)
variant_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(variant_mod)

# --- Monkey-patch the canonical class ---
from tcf.composicional import syntax as canon_syntax  # noqa: E402

# Save original for diagnostics
_ORIG_DETECT = canon_syntax.M8AVirtualRefsSyntax._detect_compositions
_ORIG_INIT = canon_syntax.M8AVirtualRefsSyntax.__init__


def _patched_init(self, min_k=2):
    _ORIG_INIT(self)
    # H-PERF-06-v2 prune-k-01: floor de K na enumeracao. Default 2 = canonical.
    self._min_k = min_k


# Replace the method on the canonical class. The variant's method reads
# self._min_k; we ensure _min_k is set via patched __init__.
canon_syntax.M8AVirtualRefsSyntax._detect_compositions = (
    variant_mod.M8AVirtualRefsSyntax._detect_compositions
)
canon_syntax.M8AVirtualRefsSyntax.__init__ = _patched_init

# HCCSeqRLE inherits from M8AVirtualRefsSyntax via canonical module, so
# it picks up the patched method automatically. Same for any other consumer.

from tcf import encode  # noqa: E402

# --- Datasets ---
DATASETS_DIR = REPO / "datasets" / "synthetic"

D1_D9_FILES = [
    "D1-emails-simples.csv",
    "D2-emails-quote-id.csv",
    "D3-stress-substring.csv",
    "D4-caos-mix.csv",
    "D5-padroes-multiplos.csv",
    "D6-poucos-em-ruido.csv",
    "D7-aninhamento.csv",
    "D8-cabeca-cauda.csv",
    "D9-frequencia-alta.csv",
]
D17A_FILE = "D17a-multi-column-mixed.csv"

BASELINE_D1_D9 = 1523
BASELINE_D17A = 322


def load_single_col(path: Path) -> list[str]:
    """D1-D9 are single-column CSVs with a header line that we skip."""
    with path.open("r", encoding="utf-8", newline="") as fp:
        reader = csv.reader(fp)
        next(reader)  # skip header
        return [row[0] for row in reader if row]


def load_multi_col(path: Path) -> dict[str, list[str]]:
    """D17a is multi-column."""
    with path.open("r", encoding="utf-8", newline="") as fp:
        reader = csv.reader(fp)
        header = next(reader)
        cols: dict[str, list[str]] = {h: [] for h in header}
        for row in reader:
            if len(row) != len(header):
                continue
            for h, v in zip(header, row):
                cols[h].append(v)
    return cols


def encode_bytes(out: str) -> int:
    return len(out.encode("utf-8"))


def main() -> int:
    print("[regression] variant: prune-k-01-skipK2-enumeration (min_k=2 default)")
    print(f"[regression] datasets dir: {DATASETS_DIR}")

    # D1-D9: encode each single-col, sum bytes
    total_d1_d9 = 0
    per_d_bytes: list[tuple[str, int]] = []
    for fname in D1_D9_FILES:
        path = DATASETS_DIR / fname
        values = load_single_col(path)
        out = encode(values)
        b = encode_bytes(out)
        total_d1_d9 += b
        per_d_bytes.append((fname, b))
        print(f"  {fname:32s} -> {b:5d} bytes ({len(values)} rows)")

    print(f"[regression] D1-D9 total: {total_d1_d9} (baseline = {BASELINE_D1_D9})")

    # D17a: multi-col
    d17a_data = load_multi_col(DATASETS_DIR / D17A_FILE)
    d17a_out = encode(d17a_data)
    d17a_bytes = encode_bytes(d17a_out)
    print(
        f"  {D17A_FILE:32s} -> {d17a_bytes:5d} bytes "
        f"({len(d17a_data)} cols, {len(next(iter(d17a_data.values())))} rows)"
    )
    print(f"[regression] D17a: {d17a_bytes} (baseline = {BASELINE_D17A})")

    ok_d1_d9 = total_d1_d9 == BASELINE_D1_D9
    ok_d17a = d17a_bytes == BASELINE_D17A
    overall = "PASS" if (ok_d1_d9 and ok_d17a) else "FAIL"
    print()
    print(f"[regression] D1-D9: {'PASS' if ok_d1_d9 else 'FAIL'} "
          f"(got {total_d1_d9}, expected {BASELINE_D1_D9})")
    print(f"[regression] D17a:  {'PASS' if ok_d17a else 'FAIL'} "
          f"(got {d17a_bytes}, expected {BASELINE_D17A})")
    print(f"[regression] OVERALL: {overall}")

    # Machine-readable trailer
    print()
    print(f"RESULT_D1_D9={total_d1_d9}")
    print(f"RESULT_D17A={d17a_bytes}")
    print(f"RESULT_OVERALL={overall}")
    return 0 if overall == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

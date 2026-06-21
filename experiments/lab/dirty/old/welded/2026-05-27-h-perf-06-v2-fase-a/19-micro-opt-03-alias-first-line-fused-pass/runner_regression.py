"""H-PERF-06-v2 Fase A — regression runner for
micro-opt-03-alias-first-line-fused-pass.

Monkey-patches M8AVirtualRefsSyntax._detect_compositions com a versao do
syntax_variant.py (fusao do alias_first_line scan no primeiro pass),
roda `from tcf import encode` em D1-D9 + D17a, compara com baselines
(D1-D9 = 1523, D17a = 322).

Esperado: byte-identico (a fusao preserva semantica trivialmente).
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
    "syntax_variant_micro_opt_03", str(VARIANT_PATH)
)
variant_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(variant_mod)

# --- Monkey-patch the canonical class ---
from tcf.composicional import syntax as canon_syntax  # noqa: E402

canon_syntax.M8AVirtualRefsSyntax._detect_compositions = (
    variant_mod.M8AVirtualRefsSyntax._detect_compositions
)

# HCCSeqRLE inherits/uses M8AVirtualRefsSyntax through canonical module.

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
    with path.open("r", encoding="utf-8", newline="") as fp:
        reader = csv.reader(fp)
        next(reader)  # skip header
        return [row[0] for row in reader if row]


def load_multi_col(path: Path) -> dict[str, list[str]]:
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
    print("[regression] variant: micro-opt-03-alias-first-line-fused-pass")
    print(f"[regression] datasets dir: {DATASETS_DIR}")

    total_d1_d9 = 0
    for fname in D1_D9_FILES:
        path = DATASETS_DIR / fname
        values = load_single_col(path)
        out = encode(values)
        b = encode_bytes(out)
        total_d1_d9 += b
        print(f"  {fname:32s} -> {b:5d} bytes ({len(values)} rows)")

    print(f"[regression] D1-D9 total: {total_d1_d9} (baseline = {BASELINE_D1_D9})")

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

    print()
    print(f"RESULT_D1_D9={total_d1_d9}")
    print(f"RESULT_D17A={d17a_bytes}")
    print(f"RESULT_OVERALL={overall}")
    return 0 if overall == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

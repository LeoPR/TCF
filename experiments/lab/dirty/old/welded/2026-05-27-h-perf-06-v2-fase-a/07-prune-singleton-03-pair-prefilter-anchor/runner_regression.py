"""Regression runner for candidate prune-singleton-03-pair-prefilter-anchor.

Loads syntax_variant.py via importlib, monkey-patches
src.tcf.composicional.syntax.M8AVirtualRefsSyntax._detect_compositions
(also covers HCCSeqRLE via inheritance), encodes D1-D9 + D17a, and
checks byte totals:

    D1-D9 single-col concat == 1523 bytes
    D17a multi-col           == 322  bytes

Outputs PASS/FAIL + measured bytes.
"""
from __future__ import annotations

import csv
import importlib.util
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[4]  # .../TCF
SRC = REPO / "src"
DATASETS = REPO / "datasets" / "synthetic"

# Determinismo de hash (proteger tie-breaks de dict/Counter)
os.environ.setdefault("PYTHONHASHSEED", "0")

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

# Carrega variant module
VARIANT_PATH = HERE / "syntax_variant.py"
spec = importlib.util.spec_from_file_location(
    "syntax_variant_pruneSingleton03", str(VARIANT_PATH)
)
variant_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(variant_mod)

# Monkey-patch _detect_compositions na classe canonical
from tcf.composicional import syntax as canonical_syntax  # noqa: E402

canonical_syntax.M8AVirtualRefsSyntax._detect_compositions = (
    variant_mod.M8AVirtualRefsSyntax._detect_compositions
)

# IMPORTANTE: importar encode DEPOIS do patch
from tcf import encode  # noqa: E402


D1_D9 = [
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
D17A = "D17a-multi-column-mixed.csv"

EXPECTED_D1_D9 = 1523
EXPECTED_D17A = 322


def load_single_col_csv(path: Path) -> list[str]:
    """Le CSV de 1 coluna como lista de strings (skip header)."""
    with path.open("r", encoding="utf-8", newline="") as fp:
        reader = csv.reader(fp)
        next(reader)  # skip header
        return [row[0] if row else "" for row in reader]


def load_multi_col_csv(path: Path) -> dict[str, list[str]]:
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


def main() -> int:
    print(f"[runner] variant = {VARIANT_PATH.name}")
    print(f"[runner] patched: M8AVirtualRefsSyntax._detect_compositions")

    # D1-D9: encode cada um single-col, somar bytes
    total_d1_d9 = 0
    for name in D1_D9:
        path = DATASETS / name
        if not path.exists():
            print(f"[runner] FALTANDO dataset: {path}")
            return 2
        values = load_single_col_csv(path)
        out = encode(values)
        b = len(out.encode("utf-8"))
        total_d1_d9 += b
        print(f"  {name:35s} bytes={b}")
    print(f"[runner] TOTAL D1-D9 = {total_d1_d9} (esperado {EXPECTED_D1_D9})")

    # D17a multi-col
    d17a_path = DATASETS / D17A
    if not d17a_path.exists():
        print(f"[runner] FALTANDO dataset: {d17a_path}")
        return 2
    multi = load_multi_col_csv(d17a_path)
    out_d17a = encode(multi)
    b_d17a = len(out_d17a.encode("utf-8"))
    print(f"  {D17A:35s} bytes={b_d17a} (esperado {EXPECTED_D17A})")

    ok_d1_d9 = total_d1_d9 == EXPECTED_D1_D9
    ok_d17a = b_d17a == EXPECTED_D17A
    ok_all = ok_d1_d9 and ok_d17a
    print()
    print(f"D1-D9   : {'PASS' if ok_d1_d9 else 'FAIL'}  ({total_d1_d9} vs {EXPECTED_D1_D9})")
    print(f"D17a    : {'PASS' if ok_d17a else 'FAIL'}  ({b_d17a} vs {EXPECTED_D17A})")
    print(f"OVERALL : {'PASS' if ok_all else 'FAIL'}")

    # Machine-readable line (parsed by harness if needed)
    print(f"::RESULT:: d1_d9={total_d1_d9} d17a={b_d17a} pass={int(ok_all)}")
    return 0 if ok_all else 1


if __name__ == "__main__":
    raise SystemExit(main())

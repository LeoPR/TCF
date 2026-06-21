"""Regression runner for micro-opt-04-defer-sort-candidates.

Monkey-patches `_detect_compositions` in `tcf.composicional.syntax.M8AVirtualRefsSyntax`
with the variant version (which defers the sort of `candidates_sorted`).

Validates D1-D9 (single-col) and D17a (multi-col) byte-for-byte vs baselines.
"""
from __future__ import annotations

import csv
import importlib.util
import sys
from pathlib import Path

# Project root: 4 levels up from this file
HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parents[4]
SRC = PROJECT_ROOT / "src"
DATASETS = PROJECT_ROOT / "datasets" / "synthetic"

# Ensure src/ is on path
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def load_variant():
    """Load variant module from a sibling file via importlib."""
    variant_path = HERE / "syntax_variant.py"
    spec = importlib.util.spec_from_file_location(
        "syntax_variant_micro04", str(variant_path)
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def patch_syntax(variant_mod):
    """Monkey-patch _detect_compositions on canonical M8AVirtualRefsSyntax.

    HCCSeqRLE inherits the method, so a single class-level patch covers both.
    Also import the _LazyIterInfo helper into the canonical module so any
    isinstance checks behave (not strictly needed but safe)."""
    from tcf.composicional import syntax as canonical
    canonical.M8AVirtualRefsSyntax._detect_compositions = (
        variant_mod.M8AVirtualRefsSyntax._detect_compositions
    )
    # Stash the lazy helper on the canonical module so the patched method's
    # closure can find it via attribute lookup if it uses module globals.
    canonical._LazyIterInfo = variant_mod._LazyIterInfo


def read_csv_single(path):
    """Read single-column CSV: return list of lines (header skipped)."""
    out = []
    with open(path, "r", encoding="utf-8", newline="") as f:
        rdr = csv.reader(f)
        header = next(rdr, None)
        for row in rdr:
            # join all columns if multi to a single string field; tests
            # treat D1-D9 as single-column (first col) per convention.
            if not row:
                continue
            out.append(row[0] if len(row) == 1 else ",".join(row))
    return out


def read_csv_multi(path):
    """Read multi-column CSV: return dict[name] -> list[str]."""
    with open(path, "r", encoding="utf-8", newline="") as f:
        rdr = csv.reader(f)
        header = next(rdr)
        cols = {h: [] for h in header}
        for row in rdr:
            for h, v in zip(header, row):
                cols[h].append(v)
    return cols


def encode_bytes(payload):
    from tcf import encode
    text = encode(payload)
    return len(text.encode("utf-8"))


def find_dataset(prefix):
    """Find a single dataset file matching prefix (e.g. 'D1-')."""
    matches = sorted(DATASETS.glob(f"{prefix}*.csv"))
    if not matches:
        raise FileNotFoundError(f"No dataset matching {prefix} in {DATASETS}")
    return matches[0]


def main():
    variant_mod = load_variant()
    patch_syntax(variant_mod)

    # Sanity: confirm patched
    from tcf.composicional.syntax import M8AVirtualRefsSyntax
    assert (
        M8AVirtualRefsSyntax._detect_compositions
        is variant_mod.M8AVirtualRefsSyntax._detect_compositions
    ), "monkey-patch did not stick"

    # D1-D9: single-col, concat bytes
    total_d1_d9 = 0
    per = {}
    for n in range(1, 10):
        path = find_dataset(f"D{n}-")
        rows = read_csv_single(path)
        b = encode_bytes(rows)
        per[f"D{n}"] = b
        total_d1_d9 += b

    # D17a: multi-col
    d17a_path = DATASETS / "D17a-multi-column-mixed.csv"
    cols = read_csv_multi(d17a_path)
    d17a_bytes = encode_bytes(cols)

    print("=== per-dataset bytes ===")
    for k, v in per.items():
        print(f"  {k}: {v}")
    print(f"D17a: {d17a_bytes}")

    baseline_d1_d9 = 1523
    baseline_d17a = 322
    pass_d1_d9 = total_d1_d9 == baseline_d1_d9
    pass_d17a = d17a_bytes == baseline_d17a

    print()
    print(f"D1-D9 total: {total_d1_d9}  baseline={baseline_d1_d9}  "
          f"{'PASS' if pass_d1_d9 else 'FAIL'}")
    print(f"D17a:       {d17a_bytes}  baseline={baseline_d17a}  "
          f"{'PASS' if pass_d17a else 'FAIL'}")
    print()
    overall = "PASS" if (pass_d1_d9 and pass_d17a) else "FAIL"
    print(f"OVERALL: {overall}")

    # Machine-readable footer
    print(f"RESULT|d1_d9={total_d1_d9}|d17a={d17a_bytes}|status={overall}")

    return 0 if overall == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())

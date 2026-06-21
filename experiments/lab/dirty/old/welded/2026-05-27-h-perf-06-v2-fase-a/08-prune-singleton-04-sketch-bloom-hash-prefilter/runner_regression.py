"""H-PERF-06-v2 Fase A — Candidate 08 prune-singleton-04-sketch-bloom-hash-prefilter
regression runner.

Steps:
1. Load syntax_variant.py (same dir) via importlib.util.spec_from_file_location.
2. Monkey-patch tcf.composicional.syntax.M8AVirtualRefsSyntax._detect_compositions
   with the variant's implementation BEFORE encode/decode is invoked.
3. Run `from tcf import encode` against D1-D9 (single-col) and D17a (multi-col).
4. Compare totals to canonical M10 baseline: D1-D9 = 1523B, D17a = 322B.
5. Print PASS/FAIL.
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

SYNTH_DIR = REPO / "datasets" / "synthetic"

# ---- Step 1: load variant module ----
VARIANT_PATH = HERE / "syntax_variant.py"
spec = importlib.util.spec_from_file_location(
    "syntax_variant_08_sketch_bloom", str(VARIANT_PATH))
variant_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(variant_mod)

# ---- Step 2: monkey-patch _detect_compositions on canonical class ----
import tcf.composicional.syntax as canon_syntax  # noqa: E402

canon_syntax.M8AVirtualRefsSyntax._detect_compositions = (
    variant_mod.M8AVirtualRefsSyntax._detect_compositions
)
# HCCSeqRLE herda de M8AVirtualRefsSyntax sem sobrescrever _detect_compositions,
# entao a patch acima propaga automaticamente.
import tcf.composicional.hcc_seqrle as hcc_seqrle  # noqa: E402
assert hcc_seqrle.HCCSeqRLE._detect_compositions is (
    variant_mod.M8AVirtualRefsSyntax._detect_compositions
), "HCCSeqRLE nao herdou patch — provavelmente subclass override existe"

from tcf import encode  # noqa: E402


def load_single_col_csv(path: Path) -> list[str]:
    """Le CSV single-col (header + 1 coluna) como lista de strings.
    Se tiver mais de 1 coluna, concatena por linha como single col?
    D1-D9 sao single-col tipicamente."""
    rows = []
    with path.open("r", encoding="utf-8", newline="") as fp:
        reader = csv.reader(fp)
        try:
            header = next(reader)
        except StopIteration:
            return rows
        if len(header) == 1:
            # single col simples
            for row in reader:
                if row:
                    rows.append(row[0])
                else:
                    rows.append("")
        else:
            # fallback: pega primeira coluna
            for row in reader:
                rows.append(row[0] if row else "")
    return rows


def load_multi_col_csv(path: Path) -> dict[str, list[str]]:
    with path.open("r", encoding="utf-8", newline="") as fp:
        reader = csv.reader(fp)
        header = next(reader)
        cols: dict[str, list[str]] = {h: [] for h in header}
        for row in reader:
            if len(row) != len(header):
                # skip mismatched
                continue
            for h, v in zip(header, row):
                cols[h].append(v)
    return cols


D1_D9_NAMES = [
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

D17A_NAME = "D17a-multi-column-mixed.csv"

EXPECTED_D1_D9 = 1523
EXPECTED_D17A = 322


def main() -> int:
    print(f"[runner] variant = {VARIANT_PATH.name}")
    print(f"[runner] synth dir = {SYNTH_DIR}")
    print(f"[runner] patched _detect_compositions on M8AVirtualRefsSyntax + HCCSeqRLE")
    print()

    # --- D1-D9 single-col ---
    total_d1_d9 = 0
    per_ds = []
    for name in D1_D9_NAMES:
        path = SYNTH_DIR / name
        if not path.exists():
            print(f"[runner] MISSING dataset: {path}")
            return 2
        values = load_single_col_csv(path)
        out = encode(values)
        nbytes = len(out.encode("utf-8"))
        total_d1_d9 += nbytes
        per_ds.append((name, nbytes))
        print(f"  {name:35s} -> {nbytes:5d} B  (rows={len(values)})")
    print(f"[runner] D1-D9 TOTAL = {total_d1_d9} B  (expected {EXPECTED_D1_D9})")

    # --- D17a multi-col ---
    path = SYNTH_DIR / D17A_NAME
    if not path.exists():
        print(f"[runner] MISSING dataset: {path}")
        return 2
    cols = load_multi_col_csv(path)
    out = encode(cols)
    d17a_bytes = len(out.encode("utf-8"))
    print(f"  {D17A_NAME:35s} -> {d17a_bytes:5d} B  "
          f"(cols={len(cols)}, rows={len(next(iter(cols.values()))) if cols else 0})")
    print(f"[runner] D17a TOTAL    = {d17a_bytes} B  (expected {EXPECTED_D17A})")
    print()

    pass_d1_d9 = total_d1_d9 == EXPECTED_D1_D9
    pass_d17a = d17a_bytes == EXPECTED_D17A
    pass_all = pass_d1_d9 and pass_d17a

    print(f"[runner] D1-D9 : {'PASS' if pass_d1_d9 else 'FAIL'} "
          f"(actual={total_d1_d9}, expected={EXPECTED_D1_D9})")
    print(f"[runner] D17a  : {'PASS' if pass_d17a else 'FAIL'} "
          f"(actual={d17a_bytes}, expected={EXPECTED_D17A})")
    print(f"[runner] OVERALL: {'PASS' if pass_all else 'FAIL'}")

    # machine-readable summary line
    print(f"RESULT_JSON {{\"d1_d9\": {total_d1_d9}, \"d17a\": {d17a_bytes}, "
          f"\"pass\": {str(pass_all).lower()}}}")
    return 0 if pass_all else 1


if __name__ == "__main__":
    raise SystemExit(main())

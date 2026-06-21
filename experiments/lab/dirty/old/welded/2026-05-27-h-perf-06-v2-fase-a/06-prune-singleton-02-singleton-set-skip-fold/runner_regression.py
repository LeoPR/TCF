"""Regression runner for prune-singleton-02-singleton-set-skip-fold.

Loads syntax_variant.py via importlib, monkey-patches the canonical
_detect_compositions on M8AVirtualRefsSyntax (and inherited HCCSeqRLE),
then runs `tcf.encode` over D1-D9 and D17a, comparing total bytes
to the baseline (D1-D9 = 1523, D17a = 322).

Exit: prints PASS/FAIL and bytes per dataset.
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

DATASETS_DIR = REPO / "datasets" / "synthetic"


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
    so subclasses (HCCSeqRLE) inherit the new method automatically."""
    variant = load_variant_module()
    import tcf.composicional.syntax as canonical_syntax
    import tcf.composicional.hcc_seqrle as canonical_hcc

    canonical_syntax.M8AVirtualRefsSyntax._detect_compositions = (
        variant.M8AVirtualRefsSyntax._detect_compositions
    )
    # HCCSeqRLE inherits via MRO; but in case any local re-bound
    # method exists, force-bind too.
    if hasattr(canonical_hcc.HCCSeqRLE, "_detect_compositions"):
        canonical_hcc.HCCSeqRLE._detect_compositions = (
            variant.M8AVirtualRefsSyntax._detect_compositions
        )
    return variant


def read_csv_as_data(csv_path: Path):
    """Read CSV as either single-col list (1 column) or multi-col dict."""
    with csv_path.open("r", encoding="utf-8", newline="") as fp:
        reader = csv.reader(fp)
        rows = list(reader)
    if not rows:
        return []
    header = rows[0]
    body = rows[1:]
    if len(header) == 1:
        return [r[0] if r else "" for r in body]
    cols: dict[str, list[str]] = {h: [] for h in header}
    for r in body:
        if len(r) != len(header):
            continue
        for h, v in zip(header, r):
            cols[h].append(v)
    return cols


def encode_dataset(csv_path: Path) -> int:
    from tcf import encode
    data = read_csv_as_data(csv_path)
    out = encode(data)
    return len(out.encode("utf-8"))


def main() -> int:
    apply_monkey_patch()
    print("[regression] monkey-patch applied: _detect_compositions -> variant")

    d_files = {
        "D1": DATASETS_DIR / "D1-emails-simples.csv",
        "D2": DATASETS_DIR / "D2-emails-quote-id.csv",
        "D3": DATASETS_DIR / "D3-stress-substring.csv",
        "D4": DATASETS_DIR / "D4-caos-mix.csv",
        "D5": DATASETS_DIR / "D5-padroes-multiplos.csv",
        "D6": DATASETS_DIR / "D6-poucos-em-ruido.csv",
        "D7": DATASETS_DIR / "D7-aninhamento.csv",
        "D8": DATASETS_DIR / "D8-cabeca-cauda.csv",
        "D9": DATASETS_DIR / "D9-frequencia-alta.csv",
        "D17a": DATASETS_DIR / "D17a-multi-column-mixed.csv",
    }
    for name, p in d_files.items():
        if not p.exists():
            print(f"[regression] FAIL missing dataset: {p}")
            return 2

    bytes_per = {}
    for name, path in d_files.items():
        b = encode_dataset(path)
        bytes_per[name] = b
        print(f"[regression] {name}: {b} bytes ({path.name})")

    d1_d9 = sum(bytes_per[n] for n in ["D1","D2","D3","D4","D5","D6","D7","D8","D9"])
    d17a = bytes_per["D17a"]
    print(f"[regression] D1-D9 total = {d1_d9} (expected 1523)")
    print(f"[regression] D17a       = {d17a} (expected 322)")

    ok_d19 = (d1_d9 == 1523)
    ok_d17a = (d17a == 322)
    if ok_d19 and ok_d17a:
        print("[regression] PASS")
        return 0
    print(f"[regression] FAIL (d1_d9_ok={ok_d19}, d17a_ok={ok_d17a})")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

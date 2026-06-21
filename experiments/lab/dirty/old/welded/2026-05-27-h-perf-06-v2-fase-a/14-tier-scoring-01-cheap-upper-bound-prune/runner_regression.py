"""Regression runner for candidate tier-scoring-01-cheap-upper-bound-prune.

Loads syntax_variant.py, monkey-patches M8AVirtualRefsSyntax._detect_compositions
with the variant version, then encodes D1-D9 + D17a and compares bytes.

Targets:
- D1-D9 total = 1523 bytes (canonical baseline)
- D17a       =  322 bytes (canonical baseline)
"""

from __future__ import annotations

import csv
import importlib.util
import pathlib
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parents[5]
LAB_DIR = pathlib.Path(__file__).resolve().parent
VARIANT_PATH = LAB_DIR / "syntax_variant.py"

# Add src/ to path so `import tcf` works
SRC_DIR = REPO_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))


def load_variant_module():
    """Load syntax_variant.py as an isolated module so we can extract
    its _detect_compositions implementation without polluting sys.modules
    (we don't want to replace `tcf.composicional.syntax` wholesale —
    just patch the method on the existing class)."""
    spec = importlib.util.spec_from_file_location(
        "syntax_variant_mod", str(VARIANT_PATH),
    )
    module = importlib.util.module_from_spec(spec)
    # The variant imports `from tcf.core.online import ...` etc. — those
    # already loaded once tcf is on sys.path. Safe to execute.
    spec.loader.exec_module(module)
    return module


def apply_monkey_patch():
    """Replace M8AVirtualRefsSyntax._detect_compositions (and any subclass
    use of it via super()) with variant's version."""
    variant_mod = load_variant_module()
    from tcf.composicional import syntax as canonical_mod
    variant_method = variant_mod.M8AVirtualRefsSyntax._detect_compositions
    canonical_mod.M8AVirtualRefsSyntax._detect_compositions = variant_method
    return variant_method


def read_csv_column(path: pathlib.Path) -> list[str]:
    """Read a single-column CSV (header on row 0)."""
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        rows = list(reader)
    if not rows:
        return []
    # Skip header
    return [row[0] for row in rows[1:] if row]


def read_csv_multi(path: pathlib.Path) -> dict[str, list[str]]:
    """Read a multi-column CSV (header on row 0) into dict[col, list]."""
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        rows = list(reader)
    if not rows:
        return {}
    header = rows[0]
    cols: dict[str, list[str]] = {h: [] for h in header}
    for row in rows[1:]:
        if not row:
            continue
        for i, h in enumerate(header):
            cols[h].append(row[i] if i < len(row) else "")
    return cols


def encode_dataset(path: pathlib.Path) -> bytes:
    """Encode CSV. If single column -> list. Else -> dict."""
    from tcf import encode
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        try:
            header = next(reader)
        except StopIteration:
            return b""
    if len(header) == 1:
        values = read_csv_column(path)
        text = encode(values)
    else:
        cols = read_csv_multi(path)
        text = encode(cols)
    return text.encode("utf-8")


def main() -> int:
    apply_monkey_patch()

    synth_dir = REPO_ROOT / "datasets" / "synthetic"

    # D1-D9 baseline
    d1_d9_names = [
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
    d17a_name = "D17a-multi-column-mixed.csv"

    print(f"REPO_ROOT={REPO_ROOT}")
    print(f"VARIANT  ={VARIANT_PATH}")
    print(f"SYNTH    ={synth_dir}")
    print()

    total_d1_d9 = 0
    per_dataset = {}
    for name in d1_d9_names:
        path = synth_dir / name
        if not path.exists():
            print(f"MISSING: {path}")
            return 2
        b = encode_dataset(path)
        per_dataset[name] = len(b)
        total_d1_d9 += len(b)
        print(f"  {name:40s} -> {len(b):5d} bytes")

    print()
    print(f"D1-D9 TOTAL: {total_d1_d9} bytes (expected 1523)")

    # D17a
    d17a_path = synth_dir / d17a_name
    if not d17a_path.exists():
        print(f"MISSING: {d17a_path}")
        return 2
    d17a_bytes = len(encode_dataset(d17a_path))
    print(f"D17a:        {d17a_bytes} bytes (expected 322)")
    print()

    ok_d1_d9 = (total_d1_d9 == 1523)
    ok_d17a = (d17a_bytes == 322)
    if ok_d1_d9 and ok_d17a:
        print("RESULT: PASS  (byte-canonical preserved on D1-D9 + D17a)")
        print(f"ACTUAL_D1_D9={total_d1_d9}")
        print(f"ACTUAL_D17A={d17a_bytes}")
        return 0
    print("RESULT: FAIL  (byte-canonical regression)")
    if not ok_d1_d9:
        print(f"  D1-D9 delta: {total_d1_d9 - 1523:+d}")
    if not ok_d17a:
        print(f"  D17a  delta: {d17a_bytes - 322:+d}")
    print(f"ACTUAL_D1_D9={total_d1_d9}")
    print(f"ACTUAL_D17A={d17a_bytes}")
    return 1


if __name__ == "__main__":
    sys.exit(main())

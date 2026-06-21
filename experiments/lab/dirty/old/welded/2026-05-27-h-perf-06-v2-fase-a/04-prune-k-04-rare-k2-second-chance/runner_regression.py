"""Regression runner for prune-k-04-rare-k2-second-chance variant.

Carrega o syntax_variant.py via importlib, monkey-patches
M8AVirtualRefsSyntax._detect_compositions (e tambem o metodo herdado
em HCCSeqRLE), roda `tcf.encode` em D1-D9 + D17a, compara bytes:
  D1-D9 total: deve ser 1523
  D17a: deve ser 322
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

DATASETS = REPO / "datasets" / "synthetic"

# ---- 1. Load variant module ----
VARIANT_PATH = HERE / "syntax_variant.py"
spec = importlib.util.spec_from_file_location(
    "syntax_variant_prune_k_04", VARIANT_PATH)
variant_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(variant_mod)

VariantSyntax = variant_mod.M8AVirtualRefsSyntax
variant_detect = VariantSyntax._detect_compositions

# ---- 2. Monkey-patch into canonical class hierarchy ----
from tcf.composicional import syntax as canonical_syntax
from tcf.composicional import hcc_seqrle as canonical_seqrle

# Backup originals
_orig_detect = canonical_syntax.M8AVirtualRefsSyntax._detect_compositions

# Patch
canonical_syntax.M8AVirtualRefsSyntax._detect_compositions = variant_detect
# HCCSeqRLE herda de M8AVirtualRefsSyntax — patch base e' suficiente
# se HCCSeqRLE nao overrida (verificado: nao overrida).

# ---- 3. Import encode AFTER patch ----
from tcf import encode  # noqa: E402


def read_csv_single_col(path: Path) -> list[str]:
    """Le CSV de UMA coluna como list[str]. Pula header."""
    with path.open("r", encoding="utf-8", newline="") as fp:
        reader = csv.reader(fp)
        next(reader, None)  # header
        return [row[0] for row in reader if row]


def read_csv_multi_col(path: Path) -> dict[str, list[str]]:
    """Le CSV multi-col como dict[col -> list[str]]. Inclui header."""
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


def encode_dataset(path: Path) -> int:
    """Encode dataset (single-col list ou multi-col dict) e retorna bytes."""
    # D17a e' multi-column; resto e' single-column
    if "multi-column" in path.name or "D17" in path.name:
        data = read_csv_multi_col(path)
    else:
        data = read_csv_single_col(path)
    text = encode(data)
    return len(text.encode("utf-8"))


def main() -> int:
    d_files = {
        "D1": "D1-emails-simples.csv",
        "D2": "D2-emails-quote-id.csv",
        "D3": "D3-stress-substring.csv",
        "D4": "D4-caos-mix.csv",
        "D5": "D5-padroes-multiplos.csv",
        "D6": "D6-poucos-em-ruido.csv",
        "D7": "D7-aninhamento.csv",
        "D8": "D8-cabeca-cauda.csv",
        "D9": "D9-frequencia-alta.csv",
    }
    print(f"[prune-k-04] DATASETS = {DATASETS}")
    print(f"[prune-k-04] variant patched on "
          f"{canonical_syntax.M8AVirtualRefsSyntax.__name__}._detect_compositions")
    print(f"[prune-k-04] detect func = "
          f"{canonical_syntax.M8AVirtualRefsSyntax._detect_compositions}")
    print()

    total_d1_d9 = 0
    per = {}
    for label, fname in d_files.items():
        path = DATASETS / fname
        if not path.exists():
            print(f"  [WARN] {label}: missing {path}")
            continue
        n = encode_dataset(path)
        per[label] = n
        total_d1_d9 += n
        print(f"  {label}: {n} bytes  ({fname})")
    print(f"  -- D1-D9 total = {total_d1_d9} (target 1523)")

    d17a_path = DATASETS / "D17a-multi-column-mixed.csv"
    d17a_bytes = encode_dataset(d17a_path) if d17a_path.exists() else -1
    print(f"  D17a: {d17a_bytes} bytes  (target 322)")

    d1_d9_ok = (total_d1_d9 == 1523)
    d17a_ok = (d17a_bytes == 322)
    overall = d1_d9_ok and d17a_ok

    print()
    print(f"[RESULT] D1-D9: {'PASS' if d1_d9_ok else 'FAIL'} "
          f"({total_d1_d9} vs 1523)")
    print(f"[RESULT] D17a:  {'PASS' if d17a_ok else 'FAIL'} "
          f"({d17a_bytes} vs 322)")
    print(f"[RESULT] OVERALL: {'PASS' if overall else 'FAIL'}")
    return 0 if overall else 1


if __name__ == "__main__":
    raise SystemExit(main())

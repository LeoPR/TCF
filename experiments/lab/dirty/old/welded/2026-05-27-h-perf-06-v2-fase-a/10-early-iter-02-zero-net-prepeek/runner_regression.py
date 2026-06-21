"""Regression runner — early-iter-02-zero-net-prepeek.

Monkey-patches tcf.composicional.syntax.M8AVirtualRefsSyntax with the
variant version (que tem o pre-peek MIN_USEFUL_NET=2), roda
`from tcf import encode` em D1-D9 (single col) e D17a (multi col),
compara bytes:

- D1-D9 concat baseline: 1523
- D17a baseline: 322

PASS sse ambos batem. FAIL caso contrario.
"""
from __future__ import annotations

import csv
import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[4]  # .../TCF
SRC = REPO / "src"
DATASETS = REPO / "datasets" / "synthetic"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


# ---- 1) Load variant module ----
VARIANT_PATH = HERE / "syntax_variant.py"
spec = importlib.util.spec_from_file_location(
    "syntax_variant_early_iter_02", str(VARIANT_PATH)
)
variant_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(variant_mod)


# ---- 2) Monkey-patch the canonical class ----
# HCCSeqRLE herda de M8AVirtualRefsSyntax, entao trocar o metodo na
# classe canonica afeta os dois caminhos do encoder.
from tcf.composicional import syntax as canonical_syntax  # noqa: E402

# Substituicao: pega o metodo do variant e injeta na classe canonica.
canonical_syntax.M8AVirtualRefsSyntax._detect_compositions = (
    variant_mod.M8AVirtualRefsSyntax._detect_compositions
)

# Forca reload do hcc_seqrle pra garantir que ele veja a classe patched
# (na verdade ja' herda por nome — mas garantimos).
import tcf.composicional.hcc_seqrle as hcc_seqrle_mod  # noqa: E402

# Patch tambem por seguranca (caso HCCSeqRLE tenha shadowed o metodo)
if hasattr(hcc_seqrle_mod, "HCCSeqRLE"):
    if "_detect_compositions" in hcc_seqrle_mod.HCCSeqRLE.__dict__:
        hcc_seqrle_mod.HCCSeqRLE._detect_compositions = (
            variant_mod.M8AVirtualRefsSyntax._detect_compositions
        )

from tcf import encode  # noqa: E402


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


def main() -> int:
    # ---- D1-D9 single column ----
    d_files = sorted(DATASETS.glob("D[1-9]-*.csv"))
    # filtra apenas D1..D9 (uma letra), nao D10..D17
    d_files = [
        p for p in d_files
        if p.name[:3] in {f"D{i}-" for i in range(1, 10)}
    ]
    print(f"[regression] D1-D9 files = {[p.name for p in d_files]}")
    assert len(d_files) == 9, f"esperado 9 arquivos D1-D9, achei {len(d_files)}"

    total_bytes_d1_d9 = 0
    per_file = []
    for p in d_files:
        values = load_single_col(p)
        out = encode(values)
        nbytes = len(out.encode("utf-8"))
        per_file.append((p.name, nbytes))
        total_bytes_d1_d9 += nbytes

    print("[regression] per-file bytes (D1-D9):")
    for name, b in per_file:
        print(f"  {name}: {b}")
    print(f"[regression] TOTAL D1-D9 bytes = {total_bytes_d1_d9}  (expected 1523)")

    # ---- D17a multi column ----
    d17a_path = DATASETS / "D17a-multi-column-mixed.csv"
    table = load_multi_col(d17a_path)
    out_d17a = encode(table)
    bytes_d17a = len(out_d17a.encode("utf-8"))
    print(f"[regression] D17a bytes = {bytes_d17a}  (expected 322)")

    # ---- Verdict ----
    ok_d1_d9 = (total_bytes_d1_d9 == 1523)
    ok_d17a = (bytes_d17a == 322)
    if ok_d1_d9 and ok_d17a:
        print("[regression] PASS")
        return 0
    else:
        print(f"[regression] FAIL  (d1_d9_ok={ok_d1_d9}, d17a_ok={ok_d17a})")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

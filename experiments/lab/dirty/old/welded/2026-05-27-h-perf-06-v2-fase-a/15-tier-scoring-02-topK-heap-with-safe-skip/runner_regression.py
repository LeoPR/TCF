"""H-PERF-06 v2 Fase A — candidato
tier-scoring-02-topK-heap-with-safe-skip (variante SAFE / CAVEAT).

Regressao byte-canonical D1-D9 + D17a, monkey-patching o metodo
_detect_compositions da classe M8AVirtualRefsSyntax do
src/tcf/composicional/syntax.py pelo metodo do syntax_variant.py.

Targets:
- D1-D9 (single-col, list[str]) — sum bytes UTF-8 == 1523
- D17a (multi-col, dict[str, list[str]]) — bytes UTF-8 == 322
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

# Importa o modulo do TCF original primeiro (registra classe canonica).
from tcf import encode  # noqa: E402
from tcf.composicional import syntax as canonical_syntax  # noqa: E402

# Carrega o variant como modulo isolado.
VARIANT_PATH = HERE / "syntax_variant.py"
spec = importlib.util.spec_from_file_location(
    "syntax_variant_tier_scoring_02", str(VARIANT_PATH))
variant_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(variant_mod)

# Monkey-patch: substitui _detect_compositions na classe canonica
# pelo metodo do variant. Pegamos o function unbound do variant.
VariantCls = variant_mod.M8AVirtualRefsSyntax
CanonicalCls = canonical_syntax.M8AVirtualRefsSyntax

# Salva original e patch
_orig_detect = CanonicalCls._detect_compositions
CanonicalCls._detect_compositions = VariantCls._detect_compositions

DATASETS_DIR = REPO / "datasets" / "synthetic"

# D1-D9 single-col list
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

TARGET_D1_D9 = 1523
TARGET_D17A = 322


def load_single_col(path: Path) -> list[str]:
    """Le CSV single-col (1 coluna), retorna list de valores (sem header)."""
    with path.open("r", encoding="utf-8", newline="") as fp:
        reader = csv.reader(fp)
        next(reader)  # skip header
        return [row[0] for row in reader if row]


def load_multi_col(path: Path) -> dict[str, list[str]]:
    """Le CSV multi-col, retorna dict col->list."""
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
    print("[regression] variante: tier-scoring-02-topK-heap-with-safe-skip")
    print(f"[regression] variant module: {VARIANT_PATH}")
    print(f"[regression] patched: tcf.composicional.syntax."
          f"M8AVirtualRefsSyntax._detect_compositions")
    print()

    # D1-D9
    total_d1_d9 = 0
    per_dataset = []
    for name in D1_D9_NAMES:
        path = DATASETS_DIR / name
        if not path.exists():
            print(f"[regression] FAIL: dataset nao encontrado {path}")
            return 1
        data = load_single_col(path)
        out = encode(data)
        b = len(out.encode("utf-8"))
        per_dataset.append((name, b))
        total_d1_d9 += b
        print(f"  {name:35s}  rows={len(data):4d}  bytes={b}")

    print(f"\n[regression] D1-D9 total bytes: {total_d1_d9}")
    print(f"[regression] D1-D9 target     : {TARGET_D1_D9}")
    d1_d9_pass = (total_d1_d9 == TARGET_D1_D9)
    print(f"[regression] D1-D9 result     : "
          f"{'PASS' if d1_d9_pass else 'FAIL'}")

    # D17a
    print()
    path = DATASETS_DIR / D17A_NAME
    if not path.exists():
        print(f"[regression] FAIL: dataset nao encontrado {path}")
        return 1
    data = load_multi_col(path)
    out = encode(data)
    bytes_d17a = len(out.encode("utf-8"))
    n_rows = len(next(iter(data.values()))) if data else 0
    print(f"  {D17A_NAME:35s}  cols={len(data)} rows={n_rows}  "
          f"bytes={bytes_d17a}")
    print(f"\n[regression] D17a bytes : {bytes_d17a}")
    print(f"[regression] D17a target: {TARGET_D17A}")
    d17a_pass = (bytes_d17a == TARGET_D17A)
    print(f"[regression] D17a result: "
          f"{'PASS' if d17a_pass else 'FAIL'}")

    print()
    all_pass = d1_d9_pass and d17a_pass
    print(f"[regression] OVERALL: {'PASS' if all_pass else 'FAIL'}")
    print(f"[regression] actual_bytes_d1_d9 = {total_d1_d9}")
    print(f"[regression] actual_bytes_d17a = {bytes_d17a}")
    return 0 if all_pass else 2


if __name__ == "__main__":
    raise SystemExit(main())

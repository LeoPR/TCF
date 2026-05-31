"""Regression runner for PRUNE-SINGLETON-01 (two-pass discover/skip).

Carrega o syntax_variant.py via importlib, monkey-patches o metodo
`_detect_compositions` de `M8AVirtualRefsSyntax` (que HCCSeqRLE herda),
e roda `from tcf import encode` em D1-D9 (single-column) + D17a (multi-col).

Compara bytes totais com baselines canonicos:
- D1-D9 concatenados: 1523B
- D17a sozinho: 322B

Imprime PASS/FAIL e bytes observados.
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

# Carrega variant via importlib SEM colidir com tcf.composicional.syntax
VARIANT_PATH = HERE / "syntax_variant.py"
spec = importlib.util.spec_from_file_location(
    "syntax_variant_prune_singleton_01", VARIANT_PATH
)
variant_mod = importlib.util.module_from_spec(spec)
# Importar tcf.core antes pra que `from tcf.core.online import ...` funcione
import tcf.core.online  # noqa: E402,F401
import tcf.core.syntax_base  # noqa: E402,F401
spec.loader.exec_module(variant_mod)

# Monkey-patch: substitui o metodo _detect_compositions da classe canonica
# pelo metodo do variant. HCCSeqRLE herda de M8AVirtualRefsSyntax, entao
# todas as instancias passam a usar o detector com 2-pass.
from tcf.composicional.syntax import M8AVirtualRefsSyntax  # noqa: E402

M8AVirtualRefsSyntax._detect_compositions = (
    variant_mod.M8AVirtualRefsSyntax._detect_compositions
)

from tcf import encode  # noqa: E402

# Datasets D1-D9 sao single-column (lista de strings); leitura da
# coluna 0 do CSV (sem header — sao linhas brutas conforme convencao
# do M10 baseline D1-D9 = 1523B).
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

BASELINE_D1_D9 = 1523
BASELINE_D17A = 322


def load_single_col(path: Path) -> list[str]:
    """D1-D9 CSV single-col with header line (skipped). Matches sibling
    runner_regression convention (e.g. 01-prune-k-01)."""
    with path.open("r", encoding="utf-8", newline="") as fp:
        reader = csv.reader(fp)
        next(reader)  # skip header
        return [row[0] for row in reader if row]


def load_multi_col(path: Path) -> dict[str, list[str]]:
    """Le CSV multi-col em dict {col: [str, ...]} (com header)."""
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


def encode_d1_d9() -> int:
    """Encode cada D1-D9, soma bytes UTF-8 dos outputs."""
    total = 0
    for name in D1_D9:
        path = DATASETS / name
        values = load_single_col(path)
        out = encode(values)
        n = len(out.encode("utf-8"))
        total += n
        print(f"  {name}: {n}B  (n_rows={len(values)})")
    return total


def encode_d17a() -> int:
    """Encode D17a multi-col, retorna bytes UTF-8."""
    path = DATASETS / D17A
    cols = load_multi_col(path)
    out = encode(cols)
    n = len(out.encode("utf-8"))
    print(f"  {D17A}: {n}B  (n_cols={len(cols)}, "
          f"n_rows={len(next(iter(cols.values())))})")
    return n


def main() -> int:
    print("=" * 70)
    print("PRUNE-SINGLETON-01 regression — D1-D9 + D17a")
    print("=" * 70)
    print()
    print("[D1-D9] (single-column, sum of UTF-8 bytes)")
    bytes_d1_d9 = encode_d1_d9()
    print(f"  TOTAL D1-D9: {bytes_d1_d9}B  (baseline={BASELINE_D1_D9}B)")
    print()
    print("[D17a] (multi-column)")
    bytes_d17a = encode_d17a()
    print(f"  D17a: {bytes_d17a}B  (baseline={BASELINE_D17A}B)")
    print()

    ok_d1_d9 = (bytes_d1_d9 == BASELINE_D1_D9)
    ok_d17a = (bytes_d17a == BASELINE_D17A)
    all_ok = ok_d1_d9 and ok_d17a

    print("=" * 70)
    print(f"D1-D9: {'PASS' if ok_d1_d9 else 'FAIL'}  "
          f"({bytes_d1_d9} vs {BASELINE_D1_D9})")
    print(f"D17a:  {'PASS' if ok_d17a else 'FAIL'}  "
          f"({bytes_d17a} vs {BASELINE_D17A})")
    print(f"OVERALL: {'PASS' if all_ok else 'FAIL'}")
    print("=" * 70)

    # Marcadores que o orquestrador parseia
    print(f"RESULT_D1_D9_BYTES={bytes_d1_d9}")
    print(f"RESULT_D17A_BYTES={bytes_d17a}")
    print(f"RESULT_REGRESSION_PASSED={'true' if all_ok else 'false'}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

"""H-PERF-06-v2 Fase A — runner regressao early-gain-02-absolute-bytes-floor.

Carrega variante syntax_variant.py via importlib, monkey-patcha
src.tcf.composicional.syntax.M8AVirtualRefsSyntax com a versao do
variant (preservando subclasse HCCSeqRLE), e roda encode em D1-D9
(single-col) + D17a (multi-col).

Aceitacao byte-canonical (default early_gain_min_bytes=0):
- D1-D9 somados = 1523 bytes
- D17a sozinho = 322 bytes

Imprime PASS/FAIL.
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

# ---- 1) Carrega variante via importlib ----
VARIANT_PATH = HERE / "syntax_variant.py"
spec = importlib.util.spec_from_file_location(
    "syntax_variant_early_gain_02", VARIANT_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError(f"Falha ao criar spec pra {VARIANT_PATH}")
variant_mod = importlib.util.module_from_spec(spec)
# Sub-modulo precisa enxergar tcf.core.online + tcf.core.syntax_base
sys.modules["syntax_variant_early_gain_02"] = variant_mod
spec.loader.exec_module(variant_mod)

VariantClass = variant_mod.M8AVirtualRefsSyntax

# ---- 2) Monkey-patch a classe canonical ----
# HCCSeqRLE eh subclasse de M8AVirtualRefsSyntax. Patchando __init__
# e _detect_compositions na PARENT class atinge subclasse via MRO.
import tcf.composicional.syntax as canonical_syntax  # noqa: E402

canonical_syntax.M8AVirtualRefsSyntax.__init__ = VariantClass.__init__
canonical_syntax.M8AVirtualRefsSyntax._detect_compositions = (
    VariantClass._detect_compositions)
# tambem garantir patch em referencia importada via hcc_seqrle (mesma class)
import tcf.composicional.hcc_seqrle as canonical_seqrle  # noqa: E402
assert canonical_seqrle.M8AVirtualRefsSyntax is canonical_syntax.M8AVirtualRefsSyntax, \
    "Subclass HCCSeqRLE deve compartilhar parent class object"

from tcf import encode  # noqa: E402


# ---- 3) Helpers de loading ----
def load_single_col_csv(path: Path) -> list[str]:
    """Le CSV de 1 coluna, retorna lista de strings (sem header)."""
    with path.open("r", encoding="utf-8", newline="") as fp:
        reader = csv.reader(fp)
        next(reader)  # skip header
        return [row[0] if row else "" for row in reader]


def load_multi_col_csv(path: Path) -> dict[str, list[str]]:
    """Le CSV multi-col, retorna dict[col_name -> values]."""
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


# ---- 4) Executa encode em D1-D9 + D17a ----
EXPECTED_D1_D9_TOTAL = 1523
EXPECTED_D17A = 322

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


def main() -> int:
    print(f"[runner] variant = {VARIANT_PATH}")
    print(f"[runner] patched class id = {id(canonical_syntax.M8AVirtualRefsSyntax)}")

    # D1-D9 single-col
    total_d1_d9 = 0
    per_dataset = []
    for fname in D1_D9_FILES:
        path = DATASETS / fname
        if not path.exists():
            print(f"[runner] FAIL: dataset nao encontrado {path}")
            return 1
        values = load_single_col_csv(path)
        out = encode(values)
        nb = len(out.encode("utf-8"))
        per_dataset.append((fname, nb))
        total_d1_d9 += nb
        print(f"  {fname:35s} bytes={nb}")
    print(f"[runner] total D1-D9 = {total_d1_d9} (esperado {EXPECTED_D1_D9_TOTAL})")

    # D17a multi-col
    d17a_path = DATASETS / "D17a-multi-column-mixed.csv"
    if not d17a_path.exists():
        print(f"[runner] FAIL: D17a nao encontrado {d17a_path}")
        return 1
    table = load_multi_col_csv(d17a_path)
    out_d17a = encode(table)
    bytes_d17a = len(out_d17a.encode("utf-8"))
    print(f"[runner] D17a = {bytes_d17a} (esperado {EXPECTED_D17A})")

    # Verdict
    pass_d1_d9 = (total_d1_d9 == EXPECTED_D1_D9_TOTAL)
    pass_d17a = (bytes_d17a == EXPECTED_D17A)
    if pass_d1_d9 and pass_d17a:
        print("[runner] PASS — byte-canonical preservado em default mode")
        return 0
    else:
        print(f"[runner] FAIL — D1-D9 ok={pass_d1_d9} D17a ok={pass_d17a}")
        print(f"[runner] ACTUAL_D1_D9={total_d1_d9} ACTUAL_D17A={bytes_d17a}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

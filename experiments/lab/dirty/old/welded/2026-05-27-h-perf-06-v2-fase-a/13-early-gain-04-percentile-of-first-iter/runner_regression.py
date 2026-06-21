"""Regression runner para candidato early-gain-04-percentile-of-first-iter.

H-PERF-06-v2 Fase A — verifica byte-canonicity quando o variant roda com
default `early_gain_peak_ratio = 0` (curto-circuito esperado). Compara:

- D1-D9 (single-col CSVs): bytes totais concatenados == 1523
- D17a-multi-column-mixed (multi-col CSV): bytes == 322

Patch strategy:
- Importa variant via importlib.util.spec_from_file_location.
- Monkey-patches `M8AVirtualRefsSyntax.__init__` E `M8AVirtualRefsSyntax._detect_compositions`
  no modulo canonical `tcf.composicional.syntax` ANTES do primeiro `from tcf import encode`.
- `HCCSeqRLE` herda de `M8AVirtualRefsSyntax`, entao patch da parent classe afeta os dois.

NAO modifica src/tcf/.
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


# ---- Step 1: importar variant via importlib ----
VARIANT_PATH = HERE / "syntax_variant.py"
spec = importlib.util.spec_from_file_location(
    "syntax_variant_eg04", str(VARIANT_PATH))
variant_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(variant_mod)


# ---- Step 2: monkey-patch M8AVirtualRefsSyntax ----
from tcf.composicional import syntax as canonical_syntax  # noqa: E402

# Patch __init__ pra garantir que self.early_gain_peak_ratio exista (default=0).
canonical_syntax.M8AVirtualRefsSyntax.__init__ = (
    variant_mod.M8AVirtualRefsSyntax.__init__
)
# Patch o detector com a versao variant (que tem o guard early-stop).
canonical_syntax.M8AVirtualRefsSyntax._detect_compositions = (
    variant_mod.M8AVirtualRefsSyntax._detect_compositions
)

# Sanity check: HCCSeqRLE herda __init__/_detect_compositions de M8A?
from tcf.composicional.hcc_seqrle import HCCSeqRLE  # noqa: E402
assert HCCSeqRLE._detect_compositions is canonical_syntax.M8AVirtualRefsSyntax._detect_compositions, \
    "HCCSeqRLE override de _detect_compositions detectado — patch incompleto"

# Agora importa encode (APOS patches).
from tcf import encode  # noqa: E402


# ---- Step 3: utilitarios de carregamento ----
def load_single_col_csv(path: Path) -> list[str]:
    """CSV single-col: header na linha 1, valores nas demais."""
    with path.open("r", encoding="utf-8", newline="") as fp:
        reader = csv.reader(fp)
        next(reader)  # skip header
        return [row[0] for row in reader if row]


def load_multi_col_csv(path: Path) -> dict[str, list[str]]:
    """CSV multi-col: header define columns; valores empilhados por col."""
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


# ---- Step 4: rodar D1-D9 e D17a ----
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


def main() -> int:
    print(f"[regression] variant = {VARIANT_PATH}")
    print(f"[regression] datasets dir = {DATASETS}")
    print(f"[regression] default early_gain_peak_ratio = "
          f"{canonical_syntax.M8AVirtualRefsSyntax().early_gain_peak_ratio}")

    total_d1_d9 = 0
    for name in D1_D9:
        path = DATASETS / name
        values = load_single_col_csv(path)
        text = encode(values)
        b = len(text.encode("utf-8"))
        total_d1_d9 += b
        print(f"[regression] {name}: {b} bytes ({len(values)} linhas)")
    print(f"[regression] D1-D9 total = {total_d1_d9} (esperado {EXPECTED_D1_D9})")

    path17 = DATASETS / D17A
    cols17 = load_multi_col_csv(path17)
    text17 = encode(cols17)
    b17 = len(text17.encode("utf-8"))
    print(f"[regression] D17a = {b17} bytes "
          f"({len(cols17)} cols, {len(next(iter(cols17.values())))} linhas)")
    print(f"[regression] D17a total = {b17} (esperado {EXPECTED_D17A})")

    d1d9_ok = total_d1_d9 == EXPECTED_D1_D9
    d17a_ok = b17 == EXPECTED_D17A

    if d1d9_ok and d17a_ok:
        print("[regression] PASS — byte-canonical preservado")
        print(f"[regression] RESULT bytes_d1_d9={total_d1_d9} bytes_d17a={b17}")
        return 0
    print("[regression] FAIL — byte-canonical regrediu")
    print(f"[regression] RESULT bytes_d1_d9={total_d1_d9} bytes_d17a={b17}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

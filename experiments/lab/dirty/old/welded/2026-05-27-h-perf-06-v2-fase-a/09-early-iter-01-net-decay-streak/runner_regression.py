"""H-PERF-06-v2 Fase A — regressao byte-canonical do candidato
09-early-iter-01-net-decay-streak.

Carrega `syntax_variant.py` (copia + mod do M8AVirtualRefsSyntax),
monkey-patches `tcf.composicional.syntax.M8AVirtualRefsSyntax` com a
versao variant (default OFF), roda `from tcf import encode` em D1-D9
e D17a (datasets/synthetic), e valida bytes vs baseline:

    D1-D9 (sum)  = 1523
    D17a         = 322

Saida: PASS/FAIL + bytes reais.
"""
from __future__ import annotations

import csv
import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[4]  # .../TCF
SRC = REPO / "src"
SYN = REPO / "datasets" / "synthetic"
VARIANT = HERE / "syntax_variant.py"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

# --- carregar variant via importlib ---
spec = importlib.util.spec_from_file_location(
    "syntax_variant_h_perf_06_v2_09", str(VARIANT)
)
variant_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(variant_mod)

VariantSyntax = variant_mod.M8AVirtualRefsSyntax

# --- monkey-patch o M8AVirtualRefsSyntax em src/tcf ---
import tcf.composicional.syntax as canonical_syntax  # noqa: E402

# preserva HCCSeqRLE chain — patch o _detect_compositions no class canonical
# por substituicao direta do metodo. HCCSeqRLE herda dele, entao tambem
# herda o patch.
canonical_syntax.M8AVirtualRefsSyntax._detect_compositions = (
    VariantSyntax._detect_compositions
)

# tambem patch __init__ pra trazer os atributos de gating (default None = OFF)
_orig_init = canonical_syntax.M8AVirtualRefsSyntax.__init__


def _patched_init(self):
    _orig_init(self)
    if not hasattr(self, "hcc_early_stop_streak"):
        self.hcc_early_stop_streak = None
    if not hasattr(self, "hcc_early_stop_threshold"):
        self.hcc_early_stop_threshold = None


canonical_syntax.M8AVirtualRefsSyntax.__init__ = _patched_init

# precisa importar tcf APOS o patch nas referencias do encoder
# (encoder faz `from tcf.composicional.syntax import M8AVirtualRefsSyntax`
# no top-level). Como o nome do attr na class fica linkado, o encoder
# instancia a class patched — o monkey-patch de metodo de class e' seguro.

from tcf import encode  # noqa: E402

# Tambem patch a referencia que ja' foi importada no encoder
import tcf.encoder as enc_mod  # noqa: E402

enc_mod.M8AVirtualRefsSyntax._detect_compositions = (
    VariantSyntax._detect_compositions
)
enc_mod.M8AVirtualRefsSyntax.__init__ = _patched_init

# Patch HCCSeqRLE tambem (heranca via class; ja' herda, mas se houver
# override de __init__ na subclass, mantemos consistencia)
import tcf.composicional.hcc_seqrle as seqrle_mod  # noqa: E402

# HCCSeqRLE herda. Validar que nao tem override de __init__.
if "__init__" in seqrle_mod.HCCSeqRLE.__dict__:
    # tem override; precisamos aplicar a logica do patched_init la' tambem
    _orig_seq_init = seqrle_mod.HCCSeqRLE.__init__

    def _patched_seq_init(self):
        _orig_seq_init(self)
        if not hasattr(self, "hcc_early_stop_streak"):
            self.hcc_early_stop_streak = None
        if not hasattr(self, "hcc_early_stop_threshold"):
            self.hcc_early_stop_threshold = None

    seqrle_mod.HCCSeqRLE.__init__ = _patched_seq_init


# --- loaders ---


def load_single_col_csv(path: Path) -> list[str]:
    """D1-D9 sao single-column. Skip header, retorna lista de strings."""
    out: list[str] = []
    with path.open("r", encoding="utf-8", newline="") as fp:
        reader = csv.reader(fp)
        next(reader, None)  # header
        for row in reader:
            if not row:
                continue
            out.append(row[0])
    return out


def load_multi_col_csv(path: Path) -> dict[str, list[str]]:
    """D17a e' multi-column. Retorna dict {col: [str, ...]}."""
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


# --- datasets ---

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


def encode_bytes_single(name: str) -> int:
    values = load_single_col_csv(SYN / name)
    out = encode(values)
    return len(out.encode("utf-8"))


def encode_bytes_multi(name: str) -> int:
    cols = load_multi_col_csv(SYN / name)
    out = encode(cols)
    return len(out.encode("utf-8"))


def main() -> int:
    print("=== H-PERF-06-v2 Fase A: regressao 09-early-iter-01-net-decay-streak ===")
    print(f"variant = {VARIANT}")
    print(f"datasets = {SYN}")
    print(f"monkey-patch ativo (default OFF — sem flags em PipelineConfig)")
    print()

    per_d = {}
    total_d1_d9 = 0
    for name in D1_D9:
        b = encode_bytes_single(name)
        per_d[name] = b
        total_d1_d9 += b
        print(f"  {name:32s} = {b:5d} B")
    print(f"  ---")
    print(f"  D1-D9 SUM                       = {total_d1_d9:5d} B "
          f"(esperado {EXPECTED_D1_D9})")

    d17a_bytes = encode_bytes_multi(D17A)
    print(f"  {D17A:32s} = {d17a_bytes:5d} B "
          f"(esperado {EXPECTED_D17A})")

    pass_d1_d9 = total_d1_d9 == EXPECTED_D1_D9
    pass_d17a = d17a_bytes == EXPECTED_D17A
    overall = pass_d1_d9 and pass_d17a

    print()
    print(f"  D1-D9 : {'PASS' if pass_d1_d9 else 'FAIL'} "
          f"({total_d1_d9} vs {EXPECTED_D1_D9})")
    print(f"  D17a  : {'PASS' if pass_d17a else 'FAIL'} "
          f"({d17a_bytes} vs {EXPECTED_D17A})")
    print(f"  OVERALL: {'PASS' if overall else 'FAIL'}")

    # Output machine-readable line for parsing
    print(f"RESULT actual_d1_d9={total_d1_d9} actual_d17a={d17a_bytes} "
          f"regression_passed={'true' if overall else 'false'}")

    return 0 if overall else 1


if __name__ == "__main__":
    raise SystemExit(main())

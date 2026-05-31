"""H-PERF-06-v2 prune-k-03 — regression runner D1-D9 + D17a.

Monkey-patcha `_detect_compositions` da classe M8AVirtualRefsSyntax
(canonical) com a versao do `syntax_variant.py` (este sub-exp). Depois
roda `from tcf import encode` sobre D1-D9 (single-col) concatenando
bytes e comparando com 1523, e D17a (multi-col) comparando com 322.

Imprime PASS/FAIL e bytes reais.

NUNCA modifica src/tcf/. Patch e' em-memoria.
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

DATA_DIR = REPO / "datasets" / "synthetic"

# Baselines canonical (M10, single-col D1..D9; multi-col D17a)
BASELINE_D1_D9 = 1523
BASELINE_D17A = 322

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


def load_variant_detect():
    """Importa syntax_variant.py via spec_from_file_location e retorna
    a funcao _detect_compositions do variant (unbound).
    """
    variant_path = HERE / "syntax_variant.py"
    spec = importlib.util.spec_from_file_location(
        "syntax_variant_prune_k03", str(variant_path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    # Retornar o metodo da classe variant (unbound function)
    return mod.M8AVirtualRefsSyntax._detect_compositions


def patch():
    """Substitui M8AVirtualRefsSyntax._detect_compositions na arvore
    canonical em src/tcf/composicional/syntax.py. HCCSeqRLE herda
    desta classe entao tambem usa a versao patched (a menos que
    override, que nao faz)."""
    from tcf.composicional.syntax import M8AVirtualRefsSyntax
    variant_detect = load_variant_detect()
    M8AVirtualRefsSyntax._detect_compositions = variant_detect


def load_single_col(path: Path) -> list[str]:
    """D1..D9 sao single-col: 1 header + 1 valor por linha (ou sem
    header). Lemos como CSV e pegamos a coluna 0, descartando header
    se presente."""
    with path.open("r", encoding="utf-8", newline="") as fp:
        reader = csv.reader(fp)
        rows = list(reader)
    if not rows:
        return []
    # Se 1a linha tem 1 campo e parece header (no valor numerico/email),
    # ainda incluimos? Nos labs aqui o sentido CSV trata 1a linha
    # como header e os outros como dados — para se manter consistente
    # com baseline 1523 (que ja' foi medido com header), usaremos
    # AS LINHAS de coluna 0 INCLUSIVE 1a linha como string. Mas isso
    # pode estar errado: vamos checar primeiro descartando header.
    # Vamos seguir o approach padrao: skip first row (header).
    values = [r[0] for r in rows[1:] if r]
    return values


def load_multi_col(path: Path) -> dict[str, list[str]]:
    """D17a: multi-col CSV com header."""
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


def encode_dataset_single(path: Path) -> int:
    from tcf import encode
    values = load_single_col(path)
    out = encode(values)
    return len(out.encode("utf-8"))


def encode_dataset_multi(path: Path) -> int:
    from tcf import encode
    cols = load_multi_col(path)
    out = encode(cols)
    return len(out.encode("utf-8"))


def main() -> int:
    print(f"[prune-k-03] Monkey-patching M8AVirtualRefsSyntax._detect_compositions...")
    patch()

    # D1-D9
    total_d1_d9 = 0
    per_dataset = []
    for name in D1_D9_NAMES:
        path = DATA_DIR / name
        if not path.exists():
            print(f"[prune-k-03] MISSING {name}")
            per_dataset.append((name, None))
            continue
        n = encode_dataset_single(path)
        per_dataset.append((name, n))
        total_d1_d9 += n
        print(f"  {name}: {n}B")
    print(f"[prune-k-03] D1-D9 total = {total_d1_d9}B (baseline {BASELINE_D1_D9}B)")

    # D17a
    d17a_path = DATA_DIR / D17A_NAME
    if not d17a_path.exists():
        print(f"[prune-k-03] MISSING D17a")
        d17a_bytes = -1
    else:
        d17a_bytes = encode_dataset_multi(d17a_path)
        print(f"[prune-k-03] D17a = {d17a_bytes}B (baseline {BASELINE_D17A}B)")

    d1_d9_ok = (total_d1_d9 == BASELINE_D1_D9)
    d17a_ok = (d17a_bytes == BASELINE_D17A)
    passed = d1_d9_ok and d17a_ok

    print()
    print(f"[prune-k-03] D1-D9 byte-canonical: {'PASS' if d1_d9_ok else 'FAIL'} "
          f"({total_d1_d9} vs {BASELINE_D1_D9})")
    print(f"[prune-k-03] D17a  byte-canonical: {'PASS' if d17a_ok else 'FAIL'} "
          f"({d17a_bytes} vs {BASELINE_D17A})")
    print(f"[prune-k-03] OVERALL: {'PASS' if passed else 'FAIL'}")

    # Marker for parent script parsing
    print()
    print(f"RESULT_D1_D9={total_d1_d9}")
    print(f"RESULT_D17A={d17a_bytes}")
    print(f"RESULT_PASS={'1' if passed else '0'}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())

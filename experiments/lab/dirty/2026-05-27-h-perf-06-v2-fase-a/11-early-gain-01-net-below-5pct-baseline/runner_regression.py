"""H-PERF-06-v2 Fase A — runner de regressao byte-canonical.

Candidato: early-gain-01-net-below-5pct-baseline.

Estrategia:
1. Importa syntax_variant.py via importlib (arquivo COPIADO de src/tcf,
   modificado com early-gain check).
2. Monkey-patcha src.tcf.composicional.syntax.M8AVirtualRefsSyntax:
   - substitui `__init__` (pra inicializar `early_gain_threshold = 0`)
   - substitui `_detect_compositions` (pra usar a versao do variant)
   Subclasse HCCSeqRLE herda automaticamente.
3. Roda `from tcf import encode` em D1-D9 (single-col) e D17a (multi-col).
4. Compara bytes vs snapshots canonical:
   - D1-D9 total esperado = 1523B
   - D17a esperado = 322B
5. Imprime PASS/FAIL e bytes reais.

Default `early_gain_threshold = 0.0` (no-op) deve preservar byte-canonical.
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

# Garantir src/ no path antes de importar tcf.
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def load_variant_module():
    """Carrega syntax_variant.py como modulo standalone."""
    variant_path = HERE / "syntax_variant.py"
    spec = importlib.util.spec_from_file_location(
        "syntax_variant_h_perf_06_early_gain_01", variant_path
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def apply_monkey_patch():
    """Monkey-patcha M8AVirtualRefsSyntax com __init__ + _detect_compositions
    do variant. HCCSeqRLE (subclasse) herda automatic."""
    variant = load_variant_module()
    import tcf.composicional.syntax as canonical_mod

    variant_cls = variant.M8AVirtualRefsSyntax
    canonical_cls = canonical_mod.M8AVirtualRefsSyntax

    # Substituir __init__ (adiciona early_gain_threshold)
    canonical_cls.__init__ = variant_cls.__init__
    # Substituir _detect_compositions (logica modificada)
    canonical_cls._detect_compositions = variant_cls._detect_compositions
    return canonical_cls


def _load_single_col(name: str) -> list[str]:
    with (DATASETS / f"{name}.csv").open(encoding="utf-8") as f:
        r = csv.reader(f)
        next(r)
        return [row[0] for row in r if row]


def _load_multi_col(name: str) -> dict[str, list[str]]:
    with (DATASETS / f"{name}.csv").open(encoding="utf-8") as f:
        r = csv.reader(f)
        header = next(r)
        cols = {h: [] for h in header}
        for row in r:
            for h, v in zip(header, row):
                cols[h].append(v)
    return cols


D1_D9_BYTES_FROZEN = {
    "D1-emails-simples":    118,
    "D2-emails-quote-id":   166,
    "D3-stress-substring":  177,
    "D4-caos-mix":          113,
    "D5-padroes-multiplos": 281,
    "D6-poucos-em-ruido":   287,
    "D7-aninhamento":       215,
    "D8-cabeca-cauda":      100,
    "D9-frequencia-alta":    66,
}
D1_D9_TOTAL_EXPECTED = 1523
D17A_NAME = "D17a-multi-column-mixed"
D17A_EXPECTED = 322


def main() -> int:
    print(f"[runner] REPO    = {REPO}")
    print(f"[runner] DATASETS= {DATASETS}")
    print("[runner] Aplicando monkey-patch (variant)...")
    patched_cls = apply_monkey_patch()
    print(f"[runner] Patched class: {patched_cls}")
    print(f"[runner] Method _detect_compositions: "
          f"{patched_cls._detect_compositions.__module__}."
          f"{patched_cls._detect_compositions.__qualname__}")

    # Sanity: instancia tem o atributo novo?
    inst = patched_cls()
    if not hasattr(inst, "early_gain_threshold"):
        print("[runner] FAILED_BUILD: instancia nao tem early_gain_threshold")
        return 2
    print(f"[runner] early_gain_threshold default = {inst.early_gain_threshold}")

    # Import encode DEPOIS do patch (mas tcf ja' pode estar cached; nao
    # importa pq monkey-patch e' no class object compartilhado).
    from tcf import encode

    # ---- D1-D9 single-col ----
    print()
    print("=== D1-D9 single-col ===")
    d1d9_total = 0
    per_dataset_pass = []
    for name, expected in D1_D9_BYTES_FROZEN.items():
        values = _load_single_col(name)
        text = encode(values)
        actual = len(text.encode("utf-8"))
        ok = (actual == expected)
        per_dataset_pass.append(ok)
        d1d9_total += actual
        tag = "PASS" if ok else "FAIL"
        print(f"  [{tag}] {name:25s} esperado={expected:4d}B  obtido={actual:4d}B")

    d1d9_pass = (d1d9_total == D1_D9_TOTAL_EXPECTED)
    print(f"  TOTAL D1-D9: esperado={D1_D9_TOTAL_EXPECTED}B  "
          f"obtido={d1d9_total}B  [{'PASS' if d1d9_pass else 'FAIL'}]")

    # ---- D17a multi-col ----
    print()
    print("=== D17a multi-col ===")
    cols = _load_multi_col(D17A_NAME)
    text = encode(cols)
    d17a_actual = len(text.encode("utf-8"))
    d17a_pass = (d17a_actual == D17A_EXPECTED)
    tag = "PASS" if d17a_pass else "FAIL"
    print(f"  [{tag}] {D17A_NAME:25s} esperado={D17A_EXPECTED}B  obtido={d17a_actual}B")

    # ---- Resumo final ----
    print()
    print("=== RESUMO ===")
    overall_pass = d1d9_pass and d17a_pass
    print(f"  D1-D9 total      : {d1d9_total}B  expected={D1_D9_TOTAL_EXPECTED}B  "
          f"{'PASS' if d1d9_pass else 'FAIL'}")
    print(f"  D17a             : {d17a_actual}B  expected={D17A_EXPECTED}B  "
          f"{'PASS' if d17a_pass else 'FAIL'}")
    print(f"  REGRESSION       : {'PASS' if overall_pass else 'FAIL'}")
    # Machine-readable line
    print(f"RESULT actual_bytes_d1_d9={d1d9_total} actual_bytes_d17a={d17a_actual} "
          f"pass={'true' if overall_pass else 'false'}")
    return 0 if overall_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())

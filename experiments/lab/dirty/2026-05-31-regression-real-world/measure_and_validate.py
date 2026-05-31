"""T-REGRESSION-REAL-WORLD — mede bytes baseline das fixtures committadas
e valida poder discriminante + safety do #15 (Fase 4).

Le as fixtures de datasets/samples/ (committadas, NAO Z:), encoda com:
  - baseline (src/tcf atual)  -> bytes a CONGELAR no teste + RT
  - #03 (known-bad)           -> deve DIVERGIR (fixture pega a regressao)
  - #15 (topK-heap)           -> deve MANTER (re-validacao byte-safe)

NAO modifica src/tcf (patch em-memoria, restaurado).
"""
from __future__ import annotations

import csv
import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
SRC = REPO / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

SAMPLES = REPO / "datasets" / "samples"
FASE_A = REPO / "experiments" / "lab" / "dirty" / "2026-05-27-h-perf-06-v2-fase-a"
VARIANT_03 = FASE_A / "03-prune-k-03-adaptive-min-k-by-iter" / "syntax_variant.py"
VARIANT_15 = FASE_A / "15-tier-scoring-02-topK-heap-with-safe-skip" / "syntax_variant.py"

FIXTURES = [
    ("retail-description-2k", "online-retail/description-2k.csv"),
    ("retail-stockcode-2k",   "online-retail/stockcode-2k.csv"),
    ("lineitem-comment-2k",   "tpch-sf001/lcomment-2k.csv"),
]


def load(rel: str) -> list[str]:
    with (SAMPLES / rel).open(encoding="utf-8", newline="") as f:
        r = csv.reader(f)
        next(r)
        return [row[0] for row in r if row]


def variant_detect(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.M8AVirtualRefsSyntax._detect_compositions


def main() -> int:
    from tcf import encode, decode
    from tcf.composicional.syntax import M8AVirtualRefsSyntax
    ORIG = M8AVirtualRefsSyntax._detect_compositions
    d03 = variant_detect(VARIANT_03, "v03")
    d15 = variant_detect(VARIANT_15, "v15")

    print(f"{'fixture':<24} {'rows':>5} {'baseline':>9} {'RT':>4} {'#03':>9} {'#15':>9}  verdict")
    print("-" * 86)
    frozen = {}
    all_disc = True
    all_safe = True
    for name, rel in FIXTURES:
        vals = load(rel)
        M8AVirtualRefsSyntax._detect_compositions = ORIG
        out = encode(vals)
        base = len(out.encode("utf-8"))
        rt = "OK" if decode(out) == vals else "FAIL"
        M8AVirtualRefsSyntax._detect_compositions = d03
        b03 = len(encode(vals).encode("utf-8"))
        M8AVirtualRefsSyntax._detect_compositions = d15
        b15 = len(encode(vals).encode("utf-8"))
        M8AVirtualRefsSyntax._detect_compositions = ORIG

        frozen[name] = base
        disc = b03 != base
        safe = b15 == base
        all_disc = all_disc and disc
        all_safe = all_safe and safe
        verdict = []
        verdict.append("DISC" if disc else "no-disc")
        verdict.append("#15-safe" if safe else "#15-UNSAFE")
        if rt != "OK":
            verdict.append("RT-FAIL")
        print(f"{name:<24} {len(vals):>5} {base:>9} {rt:>4} {b03:>9} {b15:>9}  {' '.join(verdict)}")

    print("-" * 86)
    print(f"Fixtures discriminam #03: {'TODAS' if all_disc else 'NEM TODAS'}")
    print(f"#15 byte-safe nas fixtures: {'SIM' if all_safe else 'NAO'}")
    print()
    print("=== FROZEN bytes (colar no teste) ===")
    for k, v in frozen.items():
        print(f'    "{k}": {v},')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""H-PERF-06-v2 prune-k-04-rare-k2-second-chance — variant cProfile do encode TCF.

Replica EXATAMENTE o setup do baseline (00-baseline/runner.py):
- Mesmo dataset (Z:/tcf-data/external/online-retail/online_retail.csv, 20k rows)
- Mesmo encode (from tcf import encode, multi-col dict)
- Mesmo cProfile + dump_stats + top 20

Diferenca: ANTES do encode, monkey-patcha
`M8AVirtualRefsSyntax._detect_compositions` com a versao do
`syntax_variant.py` deste sub-exp (two-pass com upper-bound prefilter
conservador pra K=2; pass B re-enumera completo se net_upper_k2 supera
best_net_peek de K>=3).

Salva `variant.prof` no mesmo dir e imprime top 20 funcs + tempo total
+ tempo de _detect_compositions com pct relativo.
"""
from __future__ import annotations

import cProfile
import csv
import importlib.util
import io
import pstats
import sys
from pathlib import Path

# Garantir que `src/` esta no path (rodar standalone, sem instalar pacote).
HERE = Path(__file__).resolve().parent
REPO = HERE.parents[4]  # .../TCF
SRC = REPO / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

DATASET_CSV = Path(r"Z:/tcf-data/external/online-retail/online_retail.csv")
N_ROWS = 20_000
PROF_PATH = HERE / "variant.prof"
TOP_N = 20


def load_variant_detect():
    """Importa syntax_variant.py via spec_from_file_location e retorna
    a funcao _detect_compositions do variant (unbound)."""
    variant_path = HERE / "syntax_variant.py"
    spec = importlib.util.spec_from_file_location(
        "syntax_variant_prune_k04_profile", str(variant_path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.M8AVirtualRefsSyntax._detect_compositions


def patch():
    """Substitui _detect_compositions na arvore canonical."""
    from tcf.composicional.syntax import M8AVirtualRefsSyntax
    variant_detect = load_variant_detect()
    M8AVirtualRefsSyntax._detect_compositions = variant_detect


def load_dataset(path: Path, n_rows: int) -> dict[str, list[str]]:
    """Le n_rows do CSV em formato multi-col dict {col: [str, ...]}."""
    if not path.exists():
        raise FileNotFoundError(f"Dataset nao encontrado: {path}")
    for enc in ("utf-8", "latin-1"):
        try:
            with path.open("r", encoding=enc, newline="") as fp:
                reader = csv.reader(fp)
                header = next(reader)
                cols: dict[str, list[str]] = {h: [] for h in header}
                for i, row in enumerate(reader):
                    if i >= n_rows:
                        break
                    if len(row) != len(header):
                        continue
                    for h, v in zip(header, row):
                        cols[h].append(v)
            return cols
        except UnicodeDecodeError:
            continue
    raise RuntimeError("Falha ao decodificar CSV em utf-8 ou latin-1")


def main() -> int:
    print(f"[variant] dataset = {DATASET_CSV}")
    print(f"[variant] n_rows alvo = {N_ROWS}")

    print("[variant] Monkey-patching M8AVirtualRefsSyntax._detect_compositions...")
    patch()

    # Import APOS o patch para garantir que encode() vai resolver a classe
    # patched. (Como o patch e' in-place no atributo da classe, qualquer
    # import posterior pega a versao nova.)
    from tcf import encode

    data = load_dataset(DATASET_CSV, N_ROWS)
    n_cols = len(data)
    n_rows_real = len(next(iter(data.values()))) if data else 0
    print(f"[variant] carregado: {n_cols} colunas, {n_rows_real} linhas")
    total_chars = sum(sum(len(v) for v in vs) for vs in data.values())
    print(f"[variant] total chars dado = {total_chars}")

    profiler = cProfile.Profile()
    print("[variant] iniciando profile de encode(...)")
    profiler.enable()
    out = encode(data)
    profiler.disable()
    print(f"[variant] encode OK. bytes saida = {len(out.encode('utf-8'))}")

    profiler.dump_stats(str(PROF_PATH))
    print(f"[variant] profile salvo em {PROF_PATH}")

    # Top 20 por cumulative time
    sio = io.StringIO()
    stats = pstats.Stats(profiler, stream=sio).sort_stats("cumulative")
    stats.print_stats(TOP_N)
    print(sio.getvalue())

    # Total time = cumtime do encode (top-level call). Pegar via pstats.
    full_stats = pstats.Stats(profiler)
    encode_cumtime = None
    detect_cumtime = None
    for func_key, (cc, nc, tt, ct, callers) in full_stats.stats.items():
        filename, lineno, funcname = func_key
        # encode publica em encoder.py
        if funcname == "encode" and filename.endswith("encoder.py"):
            if encode_cumtime is None or ct > encode_cumtime:
                encode_cumtime = ct
        if funcname == "_detect_compositions" and "syntax" in filename:
            if detect_cumtime is None or ct > detect_cumtime:
                detect_cumtime = ct

    print("[variant] === RESUMO ===")
    if encode_cumtime is not None:
        print(f"VARIANT_TOTAL_SEC={encode_cumtime:.4f}")
    else:
        print("VARIANT_TOTAL_SEC=0")
    if detect_cumtime is not None and encode_cumtime:
        pct = (detect_cumtime / encode_cumtime) * 100.0
        print(f"VARIANT_DETECT_SEC={detect_cumtime:.4f}")
        print(f"VARIANT_DETECT_PCT={pct:.2f}")
    else:
        print("VARIANT_DETECT_SEC=0")
        print("VARIANT_DETECT_PCT=0")

    print(f"VARIANT_OUTPUT_BYTES={len(out.encode('utf-8'))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

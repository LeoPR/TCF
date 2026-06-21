"""A3 — performance do lazy na CAMADA DO ALGORITMO (v0.8). Lab read-only.

FOCO (diretriz do owner): diminuir o CAMINHO na camada de ABSTRACAO do algoritmo —
metrica language-agnostic = numero de operacoes de DECODE (passes sobre os dados) +
bytes decodados. Tempo (Python) e' so' sanity, NAO o foco. Otimizacao de linguagem
(loops, Cython, bytes vs str) fica pra depois.

Instrumenta os 3 decoders que o lazy usa (no namespace do gadget) e conta chamadas +
bytes por OP, comparando com o caminho do decode() completo (o baseline).
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from tcf import encode, decode               # noqa: E402
import tcf_lazy.lazy as L                     # noqa: E402
from tcf_lazy import view                     # noqa: E402

# --- instrumento: conta decodes (o "caminho") ---
COUNT = {"col_decode": 0, "v2b_full": 0, "split_full": 0, "bytes": 0}
_orig = {}


def _install_counters():
    for nm, key in [("_decode_column", "col_decode"), ("_decode_v2b", "v2b_full"),
                    ("_decode_struct_split", "split_full")]:
        fn = getattr(L, nm)
        _orig[nm] = fn

        def make(fn=fn, key=key):
            def wrapped(arg, *a, **k):
                COUNT[key] += 1
                try:
                    COUNT["bytes"] += len(arg)
                except Exception:
                    pass
                return fn(arg, *a, **k)
            return wrapped
        setattr(L, nm, make())


def _reset():
    for k in COUNT:
        COUNT[k] = 0


def bench(label, fn, repeat=5):
    _reset()
    t0 = time.perf_counter()
    for _ in range(repeat):
        _reset()           # contamos 1 execucao (decodes), tempo e' media
        fn()
    dt = (time.perf_counter() - t0) / repeat * 1000
    print(f"   {label:<42} decodes: col={COUNT['col_decode']:<3} v2b={COUNT['v2b_full']:<3} "
          f"split={COUNT['split_full']:<3} | bytes={COUNT['bytes']:<8} | {dt:.2f} ms")


def main():
    _install_counters()
    from dataset_reader import DatasetReader
    r = DatasetReader("adult-census")
    raw = r.columns("adult", limit=10000)
    cols = {c: [("" if v is None else str(v)) for v in vals] for c, vals in raw.items()}
    blob = encode(cols)
    blob_s = encode(cols, sort_by="workclass")
    print(f"# A3 — caminho (decodes) por op | adult 10k x {len(cols)} cols | blob {len(blob.encode())}B\n")

    print("BASELINE (caminho do decode completo):")
    bench("decode(blob) — materializa TUDO", lambda: decode(blob))

    print("\nLAZY (view fresca por op — o caminho minimo):")
    bench("count()", lambda: view(blob).count())
    bench("group_count('workclass')  [dict]", lambda: view(blob).group_count("workclass"))
    bench("where('workclass','Private').count()", lambda: view(blob).where("workclass", "Private").count())
    bench("where('workclass','Private').sum('fnlwgt')",
          lambda: view(blob).where("workclass", "Private").sum("fnlwgt"))
    bench("agg_by('workclass','fnlwgt','sum') [sort]", lambda: view(blob_s).agg_by("workclass", "fnlwgt", "sum"))

    print("\nREDUNDANCIA (mesma view, ops repetidas na MESMA coluna dict):")
    def repeated():
        v = view(blob)
        v.group_count("workclass")   # decoda a tabela
        v.where("workclass", "Private")  # decoda a tabela DE NOVO?
        v.group_count("workclass")   # e DE NOVO?
    bench("group_count + where + group_count (workclass)", repeated)


if __name__ == "__main__":
    main()

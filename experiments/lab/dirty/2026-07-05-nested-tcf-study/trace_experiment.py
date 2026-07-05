"""Experimento de sempre — amostra de entrada/saida + trace OBAT/HCC por coluna.

Ferramenta de INSPECAO (nao mede tese; o nested_bench.py mede bytes). Para cada "cell" mostra:
  - entrada (colunas + primeiras linhas)
  - saida TCF (truncada)
  - por coluna: cadence/min_len, OBAT log, HCC trace, seq-RLE runs, body_bytes
  - RT (string-level) + bytes raw/brotli

Cobre (a) os BLOCOS do nested-study (forecast, series) e (b) as celulas forma-tx da matriz de
transmissao (upload-small config, download-bulk adult, download-cadenced forecast, download-narrow
high-card pessoas). Deterministico. NAO toca src/tcf.
"""
from __future__ import annotations
import sys
import gzip
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")  # evita mojibake de em-dash no console Windows
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(HERE))
from tcf import encode, decode, SideOutputs   # noqa: E402
import brotli                                 # noqa: E402
from nested_bench import gen_forecast, gen_request, flatten_pairs  # noqa: E402


def _trunc(s, n):
    s = s or ""
    return s if len(s) <= n else s[:n] + f" …(+{len(s)-n}ch)"


def show_trace(label, table, sample_rows=6, body_chars=700, trace_chars=400):
    cols = list(table)
    n = len(next(iter(table.values()))) if table else 0
    print("\n" + "=" * 100)
    print(f"CELL: {label}  ({len(cols)} col x {n} linhas)")
    print("=" * 100)

    # entrada
    print("--- entrada (amostra) ---")
    print(" | ".join(cols))
    for i in range(min(sample_rows, n)):
        print(" | ".join(_trunc(str(table[c][i]), 28) for c in cols))
    if n > sample_rows:
        print(f"... (+{n - sample_rows} linhas)")

    # encode + side outputs
    side = SideOutputs()
    text = encode(table, side_outputs=side)

    # RT string-level
    try:
        g = decode(text)
        rt = isinstance(g, dict) and all(list(map(str, g[k])) == list(map(str, table[k])) for k in table)
    except Exception as e:
        rt = f"FAIL:{e}"

    raw = len("\n".join("\t".join(str(table[c][i]) for c in cols) for i in range(n)).encode())
    tb = len(text.encode()); br = len(brotli.compress(text.encode(), quality=11))
    print(f"\n--- saida TCF ({tb}B raw / {br}B brotli-q11; TSV-in ~{raw}B; RT={rt}) ---")
    print(_trunc(text, body_chars))

    # trace por coluna
    print("\n--- trace por coluna (OBAT + HCC) ---")
    per = side.per_col or {}
    for c in cols:
        s = per.get(c)
        if s is None:
            print(f"  [{c}] (sem per_col)"); continue
        cad = s.cadence_info.get("rule_hit") if s.cadence_info else None
        srle = len(s.seq_rle_runs or [])
        print(f"  [{c}] cadence={s.cadence_detected}({cad}) min_len={s.min_len} "
              f"hint={s.obat_used_hint} seq_rle_runs={srle} body={s.body_bytes}B")
        print(f"      OBAT : {_trunc(s.obat_log, trace_chars)}")
        print(f"      HCC  : {_trunc(s.hcc_trace, trace_chars)}")


def cols_str(reader_cols):
    return {k: [("" if v is None else str(v)) for v in vals] for k, vals in reader_cols.items()}


def main():
    # ============ BLOCOS do nested-study ============
    print("\n#################### BLOCOS DO NESTED-STUDY ####################")
    ds, yhat = gen_forecast(24)
    show_trace("nested/forecast-block (download-cadenced)", {"ds": ds, "yhat": [str(y) for y in yhat]})

    series = gen_request(20)["series"]
    show_trace("nested/series-block (upload-batch)", {
        "asset": [r["asset"] for r in series],
        "variable": [r["variable"] for r in series],
        "unit": [r["unit"] for r in series],
        "weight": [str(r["weight"]) for r in series],
    })

    # ============ CELULAS forma-tx da MATRIZ ============
    print("\n\n#################### CELULAS FORMA-TX DA MATRIZ ####################")

    # upload-small: config escalar como (path, value)
    cfg = gen_request(1)
    del cfg["series"]  # so' o esqueleto de config (a instrucao multi-camada)
    pairs = flatten_pairs(cfg)
    show_trace("matrix/upload-small config (path,value)",
               {"path": [p for p, _ in pairs], "value": [v for _, v in pairs]}, sample_rows=12)

    try:
        from dataset_reader import DatasetReader
        # download-bulk: adult (low-card largo) — o caso forte
        with DatasetReader("adult-census") as r:
            show_trace("matrix/download-bulk adult[:200] (low-card largo)",
                       cols_str(r.columns("adult", limit=200)), sample_rows=4, body_chars=500)
        # download-narrow high-card (limite): pessoas (CPF/nomes)
        with DatasetReader("br-identidades") as r:
            show_trace("matrix/download-narrow high-card pessoas[:200] (LIMITE)",
                       cols_str(r.columns("pessoas", limit=200)), sample_rows=4, body_chars=500)
    except Exception as e:
        print(f"[dataset cells skipped: {e}]")


if __name__ == "__main__":
    main()

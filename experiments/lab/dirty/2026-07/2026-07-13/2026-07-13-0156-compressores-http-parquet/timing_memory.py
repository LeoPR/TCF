"""Parte 2 do lab: TEMPO (compress/descompress, proporcional ao volume) e
MEMORIA (view seletivo vs decode/descompressao total). 2026-07-13.

CAVEAT DE PORTABILIDADE (CLAUDE.md F0-3): tempos ABSOLUTOS sao especificos
desta maquina. O que e' invariante e' (a) a PROPORCAO ao volume — throughput
MB/s — e (b) o fato estrutural: descomprimir menos custa proporcionalmente
menos tempo e menos memoria. Reportamos throughput + ms (mediana de N, com
warmup); NUNCA pinar tempo em teste.

Metodo tempo: perf_counter, 1 warmup descartado, mediana de N=9 repeticoes.
Metodo memoria: (1) view().report() -> materialized_bytes/total_bytes (bytes
logicos que cada caminho materializa); (2) tracemalloc peak (memoria Python
real alocada) pra view-query vs decode-total no MESMO blob.
"""
from __future__ import annotations

import csv
import gzip
import json
import statistics
import sys
import time
import tracemalloc
from pathlib import Path

import brotli
import lz4.frame
import snappy
import zstandard as zstd

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
from tcf import encode, decode  # noqa: E402
from tcf_lazy import view  # noqa: E402

SAMPLES = ROOT / "datasets" / "samples"
ART = Path(__file__).resolve().parent / "artifacts"

_zc = zstd.ZstdCompressor(level=19)
_zd = zstd.ZstdDecompressor()

# (nome, compress, decompress) — HTTP + Parquet
CODECS = [
    ("gzip",   lambda b: gzip.compress(b, 6),        gzip.decompress),
    ("brotli", lambda b: brotli.compress(b, quality=11), brotli.decompress),
    ("zstd",   lambda b: _zc.compress(b),            lambda b: _zd.decompress(b)),
    ("snappy", snappy.compress,                       snappy.decompress),
    ("lz4",    lz4.frame.compress,                    lz4.frame.decompress),
]
N = 9


def _median_ms(fn, arg) -> float:
    fn(arg)  # warmup descartado
    ts = []
    for _ in range(N):
        t0 = time.perf_counter()
        fn(arg)
        ts.append((time.perf_counter() - t0) * 1000.0)
    return statistics.median(ts)


def _mbps(nbytes: int, ms: float) -> float:
    if ms <= 0:
        return float("inf")
    return (nbytes / 1e6) / (ms / 1000.0)


def load_col(rel: str) -> list[str]:
    with (SAMPLES / rel).open(encoding="utf-8", newline="") as f:
        r = csv.reader(f)
        next(r)
        return [row[0] for row in r if row]


def load_table(rel: str) -> dict:
    with (SAMPLES / rel).open(encoding="utf-8", newline="") as f:
        r = csv.reader(f)
        header = next(r)
        cols = {h: [] for h in header}
        for row in r:
            if not row:
                continue
            for h, v in zip(header, row):
                cols[h].append(v)
    return cols


def time_dataset(name: str, text: str):
    """Tempos de compress/descompress por codec sobre o texto TCF (proporcional ao volume)."""
    data = text.encode("utf-8")
    rows = []
    for cname, comp, decomp in CODECS:
        blob = comp(data)
        c_ms = _median_ms(comp, data)
        d_ms = _median_ms(decomp, blob)
        assert decomp(blob) == data, f"RT compressor {cname} quebrou em {name}"
        rows.append({
            "codec": cname,
            "in_bytes": len(data),
            "comp_bytes": len(blob),
            "comp_ms": round(c_ms, 4),
            "decomp_ms": round(d_ms, 4),
            "comp_mbps": round(_mbps(len(data), c_ms), 1),
            "decomp_mbps": round(_mbps(len(blob), d_ms), 1),
        })
    return rows


def memory_demo(name: str, table: dict, filt_col: str, filt_val: str, agg_col: str):
    """Memoria: view seletivo vs decode total no MESMO blob multi-col."""
    blob = encode(table)
    assert decode(blob) == table, f"RT quebrou em {name}"

    # (1) bytes logicos materializados por caminho (view.report)
    v = view(blob); v.count()
    r_count = v.report()
    v2 = view(blob); v2.where(filt_col, filt_val).sum(agg_col)
    r_filt = v2.report()

    total_logical = r_filt["total_bytes"]

    # (2) memoria Python real (tracemalloc peak) — descomprimir/materializar
    def do_view_query():
        vv = view(blob)
        return vv.where(filt_col, filt_val).sum(agg_col)

    def do_full_decode():
        t = decode(blob)               # materializa TODAS as colunas
        # ...e ainda faz a mesma conta, filtrando em memoria (o que um gzip forca)
        idx = [i for i, c in enumerate(t[filt_col]) if c == filt_val]
        return sum(float(t[agg_col][i]) for i in idx if t[agg_col][i])

    def peak_of(fn):
        tracemalloc.start()
        fn()
        _cur, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        return peak

    peak_view = peak_of(do_view_query)
    peak_decode = peak_of(do_full_decode)

    return {
        "dataset": name,
        "n_rows": len(next(iter(table.values()))),
        "n_cols": len(table),
        "blob_bytes": len(blob.encode("utf-8")),
        "query": f"where({filt_col}={filt_val!r}).sum({agg_col})",
        "count_materialized_bytes": r_count["materialized_bytes"],
        "count_pct": r_count["pct"],
        "filter_materialized_bytes": r_filt["materialized_bytes"],
        "filter_pct": r_filt["pct"],
        "filter_touched": r_filt["touched"],
        "total_logical_bytes": total_logical,
        "peak_view_bytes": peak_view,
        "peak_decode_bytes": peak_decode,
        "peak_ratio": round(peak_decode / peak_view, 2) if peak_view else None,
    }


def main():
    # ---- TEMPO: sobre os datasets do driver (mesmo texto TCF) ----
    timing = {}
    for name, rel in [
        ("retail-description-2k", "online-retail/description-2k.csv"),
        ("lineitem-comment-2k",   "tpch-sf001/lcomment-2k.csv"),
    ]:
        timing[name] = time_dataset(name, encode(load_col(rel)))

    # cadastro multi-col (reconstruido igual ao driver, seed 20260713)
    import random
    rnd = random.Random(20260713)
    cidades = ["Sao Paulo", "Rio de Janeiro", "Belo Horizonte", "Curitiba", "Recife"]
    planos = ["Premium", "Basic", "Enterprise", "Free"]
    dominios = ["acme.com.br", "example.org", "mail.com"]
    n = 2000
    cadastro = {
        "cliente": [f"Cliente {i:04d}" for i in range(n)],
        "email":   [f"user{i:04d}@{rnd.choice(dominios)}" for i in range(n)],
        "cidade":  [rnd.choice(cidades) for _ in range(n)],
        "plano":   [rnd.choice(planos) for _ in range(n)],
        "valor":   [str(rnd.randint(50, 500)) for _ in range(n)],
    }
    timing["cadastro-multi-2k"] = time_dataset("cadastro-multi-2k", encode(cadastro))

    # ---- MEMORIA: view seletivo vs decode total ----
    retail = load_table("online-retail/online-retail-sample.csv")
    mem = [
        memory_demo("online-retail-100x8", retail, "Country", "United Kingdom", "Quantity"),
        memory_demo("cadastro-multi-2k", cadastro, "cidade", "Sao Paulo", "valor"),
    ]

    out = {"timing": timing, "memory": mem}
    (ART / "timing_memory.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()

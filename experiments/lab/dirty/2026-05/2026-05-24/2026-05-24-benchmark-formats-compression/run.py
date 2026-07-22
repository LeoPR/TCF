"""Benchmark formats x compressao — TCF vs CSV vs JSON x gzip/brotli/zstd.

Owner pediu (mencao recorrente): benchmark grande comparando TCF em
varias modalidades contra formats baseline + transport compression
tipo HTTP.

Matrix:
- Formats: CSV, JSON Lines, TCF M10, TCF M10 + nature (CPF/IP padded)
- Transport: raw, gzip, brotli, zstd
- Datasets: D17a sint, Adult Census 5k, TPC-H customer/orders,
  D-CPF-uniform 1k, D-CPF-clustered 1k, D-IP-subnet 1k

Metricas: bytes per cell, ratio vs raw_csv baseline, tempo encode

Outputs heavy: salvar TODOS os arquivos gerados (encoded + comprimido)
em out_files/ pra auditoria visual.
"""

from __future__ import annotations

import csv
import gzip
import io
import json
import sys
import time
from pathlib import Path

import brotli
import zstandard

THIS = Path(__file__).parent
LAB_CPF = THIS.parent / "2026-05-24-cpf-templated-checked"
ROOT = THIS.parents[3]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from tcf import encode, SPEC_CPF  # noqa: E402


# ===========================================================================
# Format encoders
# ===========================================================================

def to_csv_bytes(table: dict[str, list[str]]) -> bytes:
    """Serialize table -> CSV bytes."""
    out = io.StringIO()
    cols = list(table.keys())
    n_rows = len(next(iter(table.values())))
    w = csv.writer(out, lineterminator='\n')
    w.writerow(cols)
    for i in range(n_rows):
        w.writerow([table[c][i] for c in cols])
    return out.getvalue().encode("utf-8")


def to_jsonl_bytes(table: dict[str, list[str]]) -> bytes:
    """Serialize table -> JSON Lines (1 row dict per line)."""
    cols = list(table.keys())
    n_rows = len(next(iter(table.values())))
    out = io.StringIO()
    for i in range(n_rows):
        row = {c: table[c][i] for c in cols}
        out.write(json.dumps(row, ensure_ascii=False))
        out.write('\n')
    return out.getvalue().encode("utf-8")


def to_tcf_bytes(table: dict[str, list[str]], nature_per_col=None) -> bytes:
    """Serialize via TCF (M10 + nature opcional)."""
    text = encode(table, nature_per_col=nature_per_col)
    return text.encode("utf-8")


# ===========================================================================
# Transport compressors
# ===========================================================================

def compress_gzip(data: bytes, level: int = 9) -> bytes:
    return gzip.compress(data, compresslevel=level)


def compress_brotli(data: bytes, quality: int = 11) -> bytes:
    return brotli.compress(data, quality=quality)


def compress_zstd(data: bytes, level: int = 22) -> bytes:
    cctx = zstandard.ZstdCompressor(level=level)
    return cctx.compress(data)


# ===========================================================================
# Dataset loaders
# ===========================================================================

def load_csv_as_dict(path: Path, limit: int = None) -> dict[str, list[str]]:
    with path.open(encoding="utf-8") as f:
        r = csv.reader(f)
        header = next(r)
        cols = {h: [] for h in header}
        for i, row in enumerate(r):
            if limit and i >= limit:
                break
            for h, v in zip(header, row):
                cols[h].append(v)
    return cols


def load_dcpf_uniform() -> dict[str, list[str]]:
    return load_csv_as_dict(LAB_CPF / "data" / "D-CPF-uniform.csv")


def load_dcpf_clustered() -> dict[str, list[str]]:
    return load_csv_as_dict(LAB_CPF / "data" / "D-CPF-clustered.csv")


def load_dip_subnet() -> dict[str, list[str]]:
    return load_csv_as_dict(LAB_CPF / "data" / "D-IP-subnet.csv")


def load_d17a() -> dict[str, list[str]]:
    return load_csv_as_dict(ROOT / "datasets" / "synthetic" / "D17a-multi-column-mixed.csv")


def load_adult(limit: int = 5000) -> dict[str, list[str]]:
    """Adult Census via DatasetReader (SQLite)."""
    sys.path.insert(0, str(ROOT / "scripts"))
    from dataset_reader import DatasetReader
    with DatasetReader("adult-census") as r:
        cols = r.columns("adult", limit=limit)
    return {c: ["" if v is None else str(v) for v in vals]
            for c, vals in cols.items()}


def load_tpch(table: str, limit: int = None) -> dict[str, list[str]]:
    sys.path.insert(0, str(ROOT / "scripts"))
    from dataset_reader import DatasetReader
    with DatasetReader("tpch-sf001") as r:
        cols = r.columns(table, limit=limit)
    return {c: ["" if v is None else str(v) for v in vals]
            for c, vals in cols.items()}


# ===========================================================================
# Benchmark engine
# ===========================================================================

def bench_one(name: str, table: dict, nature_per_col=None, save_files=False) -> list[dict]:
    """Roda matriz formato x transporte. Retorna lista de results."""
    n_rows = len(next(iter(table.values())))
    n_cols = len(table)
    n_cells = n_rows * n_cols

    # Format produtos
    formats = {
        "csv": to_csv_bytes(table),
        "jsonl": to_jsonl_bytes(table),
        "tcf": to_tcf_bytes(table),
    }
    if nature_per_col:
        formats["tcf+nature"] = to_tcf_bytes(table, nature_per_col=nature_per_col)

    # Transport produtos
    transports = {
        "raw": lambda b: b,
        "gzip": compress_gzip,
        "brotli": compress_brotli,
        "zstd": compress_zstd,
    }

    results = []
    raw_csv_bytes = len(formats["csv"])

    out_dir = THIS / "out_files" / name
    if save_files:
        out_dir.mkdir(parents=True, exist_ok=True)

    for fmt_name, fmt_bytes in formats.items():
        for tx_name, tx_fn in transports.items():
            t0 = time.perf_counter()
            try:
                final = tx_fn(fmt_bytes)
            except Exception as e:
                results.append({
                    "dataset": name, "format": fmt_name, "transport": tx_name,
                    "error": str(e),
                })
                continue
            elapsed = time.perf_counter() - t0
            n_bytes = len(final)
            results.append({
                "dataset": name,
                "n_rows": n_rows,
                "n_cols": n_cols,
                "n_cells": n_cells,
                "format": fmt_name,
                "transport": tx_name,
                "bytes": n_bytes,
                "ratio_vs_raw_csv": round(n_bytes / raw_csv_bytes * 100, 2),
                "bytes_per_cell": round(n_bytes / n_cells, 4),
                "time_s": round(elapsed, 3),
            })
            if save_files:
                ext = "" if tx_name == "raw" else f".{tx_name}"
                (out_dir / f"{fmt_name}{ext}").write_bytes(final)

    return results


def main():
    print("=== Benchmark formats x compression ===\n")

    tasks = [
        ("D17a-sint", load_d17a(), None),
        ("D-CPF-uniform-1k", load_dcpf_uniform(),
         {"cpf": SPEC_CPF}),  # com nature pra CPF
        ("D-CPF-clustered-1k", load_dcpf_clustered(),
         {"cpf": SPEC_CPF}),
        ("D-IP-subnet-1k", load_dip_subnet(), None),
    ]

    # Real-world se disponiveis
    try:
        tasks.append(("adult-5k", load_adult(5000), None))
    except Exception as e:
        print(f"adult-5k skipped: {e}")
    try:
        tasks.append(("tpch-customer-1500", load_tpch("customer"), None))
    except Exception as e:
        print(f"tpch-customer skipped: {e}")

    all_results = []
    for name, table, nature_per_col in tasks:
        print(f"\nRunning {name} ({len(next(iter(table.values())))}rows x {len(table)}cols)...")
        results = bench_one(name, table, nature_per_col=nature_per_col, save_files=True)
        all_results.extend(results)

    # Print tabela compacta
    print("\n" + "=" * 105)
    print(f"{'dataset':24s} {'format':12s} {'transport':10s} "
          f"{'bytes':>9} {'%vs raw_csv':>12} {'b/cell':>8} {'time':>7}")
    print("-" * 105)
    for r in all_results:
        if "error" in r:
            continue
        print(f"{r['dataset']:24s} {r['format']:12s} {r['transport']:10s} "
              f"{r['bytes']:>9} {r['ratio_vs_raw_csv']:>11.2f}% "
              f"{r['bytes_per_cell']:>8.4f} {r['time_s']:>6.2f}s")

    # Manifest
    manifest = THIS / "manifest.jsonl"
    manifest.write_text(
        "\n".join(json.dumps(r) for r in all_results) + "\n",
        encoding="utf-8",
    )

    # Best-per-dataset summary
    print("\n=== Vencedor por dataset (menor bytes) ===\n")
    by_ds = {}
    for r in all_results:
        if "error" in r:
            continue
        by_ds.setdefault(r['dataset'], []).append(r)
    for ds, results in by_ds.items():
        winner = min(results, key=lambda x: x['bytes'])
        raw_csv = next(r for r in results if r['format'] == 'csv' and r['transport'] == 'raw')
        print(f"  {ds:24s}: {winner['format']:12s} + {winner['transport']:8s} = "
              f"{winner['bytes']:>9}B "
              f"({winner['ratio_vs_raw_csv']:.2f}% vs csv raw {raw_csv['bytes']}B)")

    print(f"\nManifest: {manifest}")
    print(f"Outputs:  {THIS / 'out_files'}/")


if __name__ == "__main__":
    main()

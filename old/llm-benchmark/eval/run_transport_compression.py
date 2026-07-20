"""P-transport-compression — compare gzip/brotli/zstd across all formats and scales.

No LLM needed — purely deterministic compression benchmark.

Usage:
    python experiments/eval/run_transport_compression.py
"""

from __future__ import annotations
import gzip
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from tcf import encode as tcf_encode, EncodeConfig
from tests.fixtures import _write_fixture
from tests.fixtures.synthetic_v2 import retail_sales

RESULTS_DIR = ROOT / "experiments" / "results" / "transport_compression"
SEED = 42
SCALES = [50, 200, 500, 1000, 5000]
TCF_LEVELS = [0, 2, 3]


def _try_brotli(data: bytes) -> int | None:
    try:
        import brotli
        return len(brotli.compress(data))
    except ImportError:
        return None


def _try_zstd(data: bytes) -> int | None:
    try:
        import zstandard as zstd
        return len(zstd.ZstdCompressor().compress(data))
    except ImportError:
        return None


def run():
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    results = []

    for scale in SCALES:
        tables, meta = retail_sales(n_orders=scale, seed=SEED)
        clientes = {c["id"]: c["nome"] for c in tables["clientes"]}
        produtos = {p["id"]: p["nome"] for p in tables["produtos"]}
        vendas = tables["vendas"]

        # CSV
        csv_lines = ["pessoa,produto,dt,qtd,preco_unit,total"]
        for v in vendas:
            csv_lines.append(f"{clientes.get(v['id_cliente'],'')},"
                             f"{produtos.get(v['id_produto'],'')},"
                             f"{v['dt']},{v['qtd']},{v['preco_unit']},{v['total']}")
        csv_text = "\n".join(csv_lines)

        # JSONL
        jsonl_lines = []
        for v in vendas:
            jsonl_lines.append(json.dumps({
                "pessoa": clientes.get(v["id_cliente"], ""),
                "produto": produtos.get(v["id_produto"], ""),
                "dt": v["dt"], "qtd": v["qtd"],
                "preco_unit": v["preco_unit"], "total": v["total"],
            }, ensure_ascii=False))
        jsonl_text = "\n".join(jsonl_lines)

        # TCF levels
        meta_path, data_dir = _write_fixture(tables, meta)
        tcf_texts = {}
        for level in TCF_LEVELS:
            tcf_texts[f"tcf_L{level}"] = tcf_encode(
                str(meta_path), str(data_dir),
                EncodeConfig(level=level, include_stats=True)
            )

        all_formats = {"csv": csv_text, "jsonl": jsonl_text, **tcf_texts}

        for fmt_name, text in all_formats.items():
            raw_bytes = text.encode("utf-8")
            raw_size = len(raw_bytes)
            gz_size = len(gzip.compress(raw_bytes))
            br_size = _try_brotli(raw_bytes)
            zstd_size = _try_zstd(raw_bytes)

            row = {
                "scale": scale, "rows": len(vendas), "format": fmt_name,
                "raw_bytes": raw_size,
                "gzip_bytes": gz_size, "gzip_ratio": round(gz_size / raw_size, 3),
            }
            if br_size is not None:
                row["brotli_bytes"] = br_size
                row["brotli_ratio"] = round(br_size / raw_size, 3)
            if zstd_size is not None:
                row["zstd_bytes"] = zstd_size
                row["zstd_ratio"] = round(zstd_size / raw_size, 3)

            results.append(row)

    # Print results
    print(f"\n{'='*90}")
    print(f"TRANSPORT COMPRESSION BENCHMARK")
    print(f"{'='*90}")

    print(f"\n{'Scale':>6} {'Format':>8} {'Raw':>8} {'gzip':>8} {'ratio':>6}", end="")
    has_brotli = any(r.get("brotli_bytes") for r in results)
    has_zstd = any(r.get("zstd_bytes") for r in results)
    if has_brotli:
        print(f" {'brotli':>8} {'ratio':>6}", end="")
    if has_zstd:
        print(f"  {'zstd':>8} {'ratio':>6}", end="")
    print()
    print("-" * 90)

    for r in results:
        print(f"{r['scale']:>6} {r['format']:>8} {r['raw_bytes']:>8} {r['gzip_bytes']:>8} {r['gzip_ratio']:>6.3f}", end="")
        if has_brotli:
            print(f" {r.get('brotli_bytes', ''):>8} {r.get('brotli_ratio', ''):>6}", end="")
        if has_zstd:
            print(f"  {r.get('zstd_bytes', ''):>8} {r.get('zstd_ratio', ''):>6}", end="")
        print()

    # Key comparison: format+gzip vs format+gzip
    print(f"\n{'='*70}")
    print(f"KEY COMPARISON: raw size after gzip (bytes)")
    print(f"{'='*70}")
    print(f"{'Scale':>6} {'csv+gz':>10} {'jsonl+gz':>10} {'L0+gz':>10} {'L2+gz':>10} {'L3+gz':>10}")
    print("-" * 60)
    for scale in SCALES:
        sr = {r["format"]: r for r in results if r["scale"] == scale}
        print(f"{scale:>6}", end="")
        for fmt in ["csv", "jsonl", "tcf_L0", "tcf_L2", "tcf_L3"]:
            gz = sr.get(fmt, {}).get("gzip_bytes", 0)
            print(f" {gz:>10}", end="")
        print()

    # Save
    (RESULTS_DIR / "results.json").write_text(
        json.dumps(results, indent=2), encoding="utf-8"
    )
    print(f"\nSaved to {RESULTS_DIR / 'results.json'}")


if __name__ == "__main__":
    run()

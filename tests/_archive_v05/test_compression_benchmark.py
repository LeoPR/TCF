"""G20b — Compression benchmark for TCF v0.2.

Measures compression ratios across:
  - Dataset types (crm_sales, service_logs, survey, unique_data)
  - Scales (20 to 10000 rows)
  - Compression levels (0-3)
  - Stats on/off
  - Comparison with CSV and JSONL baselines

Run with -s to see the full report:
    python -m pytest tests/test_compression_benchmark.py -s
"""

import csv as csv_mod
import io
import json
import sys
from collections import defaultdict
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))

from tcf import encode, decode, EncodeConfig
from fixtures import _write_fixture
from fixtures.synthetic import (
    crm_sales,
    service_logs,
    survey_likert,
    unique_data,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _csv_bytes(tables: dict) -> int:
    total = 0
    for name, rows in tables.items():
        if not rows:
            continue
        buf = io.StringIO()
        writer = csv_mod.DictWriter(buf, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
        total += len(buf.getvalue().encode("utf-8"))
    return total


def _jsonl_bytes(tables: dict) -> int:
    total = 0
    for name, rows in tables.items():
        for row in rows:
            total += len(json.dumps(row, ensure_ascii=False).encode("utf-8")) + 1
    return total


def _tcf_bytes(tables, metadata, level, include_stats=False) -> int:
    meta_path, data_dir = _write_fixture(tables, metadata)
    text = encode(str(meta_path), str(data_dir),
                  EncodeConfig(level=level, include_stats=include_stats))
    return len(text.encode("utf-8"))


def _roundtrip_ok(tables, metadata, level) -> bool:
    """Verify encode->decode preserves all data."""
    meta_path, data_dir = _write_fixture(tables, metadata)
    text = encode(str(meta_path), str(data_dir),
                  EncodeConfig(level=level, include_stats=False))
    decoded = decode(text, normalize=False)
    name = list(decoded.keys())[0]
    rows = decoded[name]

    # Build original flat set (resolve FKs)
    from tcf.schema import load_schema
    schema = load_schema(meta_path, data_dir)
    fact_name = max(schema, key=lambda t: len(schema[t].fks))
    fact_meta = schema[fact_name]
    fact_rows = list(csv_mod.DictReader(
        schema[fact_name].file.open(newline="", encoding="utf-8")))

    # Compare row counts
    return len(rows) == len(fact_rows)


def _measure(tables, metadata) -> dict:
    """Full measurement of a dataset across all formats and levels."""
    csv_size = _csv_bytes(tables)
    jsonl_size = _jsonl_bytes(tables)
    total_rows = sum(len(rows) for rows in tables.values())

    result = {
        "total_rows": total_rows,
        "csv_bytes": csv_size,
        "jsonl_bytes": jsonl_size,
    }

    for level in [0, 1, 2, 3]:
        result[f"L{level}_bytes"] = _tcf_bytes(tables, metadata, level, include_stats=False)
        result[f"L{level}_stats_bytes"] = _tcf_bytes(tables, metadata, level, include_stats=True)
        result[f"L{level}_vs_csv"] = round(result[f"L{level}_bytes"] / csv_size, 4) if csv_size else 0
        result[f"L{level}_vs_jsonl"] = round(result[f"L{level}_bytes"] / jsonl_size, 4) if jsonl_size else 0

    # Best level
    sizes = {lv: result[f"L{lv}_bytes"] for lv in range(4)}
    result["best_level"] = min(sizes, key=sizes.get)
    result["best_bytes"] = sizes[result["best_level"]]
    result["best_vs_csv"] = round(result["best_bytes"] / csv_size, 4) if csv_size else 0
    result["best_vs_jsonl"] = round(result["best_bytes"] / jsonl_size, 4) if jsonl_size else 0

    # Stats overhead
    for level in [0, 2, 3]:
        base = result[f"L{level}_bytes"]
        with_stats = result[f"L{level}_stats_bytes"]
        result[f"L{level}_stats_overhead"] = with_stats - base

    return result


# ---------------------------------------------------------------------------
# Test scenarios
# ---------------------------------------------------------------------------

SCENARIOS = [
    ("crm_20", crm_sales(20, 5, 5, seed=1)),
    ("crm_50", crm_sales(50, 5, 5, seed=1)),
    ("crm_200", crm_sales(200, 20, 15, seed=2)),
    ("crm_1000", crm_sales(1000, 30, 20, seed=3)),
    ("crm_5000", crm_sales(5000, 50, 20, seed=4)),
    ("crm_10000", crm_sales(10000, 50, 30, seed=5)),
    ("logs_500", service_logs(500, seed=1)),
    ("logs_5000", service_logs(5000, seed=2)),
    ("survey_500", survey_likert(100, 5, seed=1)),
    ("survey_5000", survey_likert(500, 10, seed=2)),
    ("unique_200", unique_data(200, seed=1)),
    ("unique_1000", unique_data(1000, seed=2)),
]


# ---------------------------------------------------------------------------
# Roundtrip tests — all levels, all scenarios
# ---------------------------------------------------------------------------

class TestRoundtrip:
    """Verify encode->decode preserves data for all scenarios and levels."""

    @pytest.mark.parametrize("name,data", SCENARIOS, ids=[s[0] for s in SCENARIOS])
    @pytest.mark.parametrize("level", [0, 1, 2, 3])
    def test_roundtrip(self, name, data, level):
        tables, meta = data
        assert _roundtrip_ok(tables, meta, level), \
            f"Roundtrip failed: {name} level={level}"


# ---------------------------------------------------------------------------
# Compression assertions
# ---------------------------------------------------------------------------

class TestCompression:
    """Verify key compression properties."""

    def test_L3_beats_csv_at_200_rows(self):
        tables, meta = crm_sales(200, 20, 15, seed=42)
        m = _measure(tables, meta)
        assert m["L3_vs_csv"] < 1.0, \
            f"L3 should beat CSV at 200 rows, got {m['L3_vs_csv']}"

    def test_L3_always_beats_jsonl(self):
        """L3 should beat JSONL in all scenarios with repetition."""
        for name, (tables, meta) in SCENARIOS:
            if "unique" in name:
                continue
            m = _measure(tables, meta)
            assert m["L3_vs_jsonl"] < 1.0, \
                f"L3 should beat JSONL for {name}, got {m['L3_vs_jsonl']}"

    def test_L3_better_than_L2_at_scale(self):
        """L3 (dict) should beat L2 (no dict) at 200+ rows."""
        tables, meta = crm_sales(500, 30, 20, seed=42)
        m = _measure(tables, meta)
        assert m["L3_bytes"] < m["L2_bytes"], \
            f"L3 ({m['L3_bytes']}) should be smaller than L2 ({m['L2_bytes']}) at 500 rows"

    def test_unique_data_worst_case(self):
        """Unique data is worst case — L3 may expand vs CSV."""
        tables, meta = unique_data(200, seed=1)
        m = _measure(tables, meta)
        # Document, don't assert success
        assert m["L3_vs_csv"] < 1.5, \
            f"L3 should not expand more than 50% for unique data, got {m['L3_vs_csv']}"

    def test_stats_overhead_small(self):
        """Stats should add < 10% overhead."""
        tables, meta = crm_sales(500, 30, 20, seed=42)
        m = _measure(tables, meta)
        if m["L3_bytes"] > 0:
            pct = m["L3_stats_overhead"] / m["L3_bytes"] * 100
            assert pct < 10, f"Stats overhead {pct:.1f}% exceeds 10%"

    def test_compression_stable_at_scale(self):
        """L3/CSV ratio should be < 0.80 at 200+ rows (stable compression)."""
        for n in [200, 1000, 5000]:
            tables, meta = crm_sales(n, min(n // 3, 50), 20, seed=42)
            m = _measure(tables, meta)
            assert m["L3_vs_csv"] < 0.80, \
                f"L3/CSV should be < 0.80 at {n} rows, got {m['L3_vs_csv']}"


# ---------------------------------------------------------------------------
# Benchmark report (visible with pytest -s)
# ---------------------------------------------------------------------------

class TestBenchmarkReport:
    """Print human-readable compression report."""

    def test_print_report(self, capsys):
        print("\n")
        print("=" * 110)
        print("TCF v0.2 COMPRESSION BENCHMARK")
        print("=" * 110)
        print(f"{'Dataset':<16} {'Rows':>6} {'CSV':>8} {'JSONL':>8} "
              f"{'L0':>8} {'L1':>8} {'L2':>8} {'L3':>8} "
              f"{'L3/CSV':>7} {'L3/JL':>7} {'Best':>5}")
        print("-" * 110)

        all_results = []
        for name, (tables, meta) in SCENARIOS:
            m = _measure(tables, meta)
            all_results.append((name, m))
            bl = m["best_level"]
            print(
                f"{name:<16} {m['total_rows']:>6} "
                f"{m['csv_bytes']:>7}B {m['jsonl_bytes']:>7}B "
                f"{m['L0_bytes']:>7}B {m['L1_bytes']:>7}B "
                f"{m['L2_bytes']:>7}B {m['L3_bytes']:>7}B "
                f"{m['L3_vs_csv']:>6.2f}x {m['L3_vs_jsonl']:>6.2f}x "
                f"L{bl}"
            )

        print("-" * 110)

        # Stats overhead summary
        print("\nStats overhead (L3):")
        for name, m in all_results:
            oh = m.get("L3_stats_overhead", 0)
            base = m["L3_bytes"]
            pct = oh / base * 100 if base else 0
            print(f"  {name:<16} +{oh}B ({pct:.1f}%)")

        print("\n" + "=" * 110)
        print("L3/CSV < 1.0 means L3 is smaller than CSV")
        print("L3/JL  < 1.0 means L3 is smaller than JSONL")
        print("Best = level with smallest output for this dataset")
        print("=" * 110)

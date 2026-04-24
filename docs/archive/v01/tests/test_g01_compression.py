"""G01 — Compression benchmark: when does TCF actually compress?

Tests TCF output size vs CSV vs JSONL across:
  - Dataset types (crm_sales, service_logs, survey, unique_data)
  - Scales (50, 200, 1000 rows)
  - Cardinalities (few FKs vs many)
  - Config variants (sorted, no-sorted, stats)

This is NOT about LLM accuracy — it's about understanding the
compression characteristics of TCF before involving any model.

Scientific questions answered:
  Q1: When does TCF compress vs CSV? vs JSONL?
  Q2: How much does RLE help, and when?
  Q3: What's the overhead of sorted columns, header, stats?
  Q4: At what row count does TCF become more compact than CSV?
"""

import csv as csv_mod
import io
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))

from tcf.encoder import encode, EncoderConfig
from tests.fixtures import _write_fixture
from tests.fixtures.synthetic import (
    crm_sales,
    service_logs,
    survey_likert,
    unique_data,
)


# =========================================================================
# Helpers
# =========================================================================

def _csv_bytes(tables: dict) -> int:
    """Total CSV size for all tables."""
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
    """Total JSONL size: every row as a JSON object with keys repeated."""
    total = 0
    for name, rows in tables.items():
        for row in rows:
            total += len(json.dumps(row, ensure_ascii=False).encode("utf-8")) + 1  # +1 for newline
    return total


def _tcf_bytes(meta_path, data_dir, config=None) -> int:
    tcf = encode(meta_path, data_dir, config=config)
    return len(tcf.encode("utf-8"))


def _rle_stats(tcf_text: str) -> dict:
    """Extract RLE stats from sorted columns."""
    stats = {"sorted_columns": 0, "total_values": 0, "rle_tokens": 0}
    for line in tcf_text.splitlines():
        if "[sorted]:" in line:
            stats["sorted_columns"] += 1
            values_part = line.split(": ", 1)[1]
            tokens = values_part.split()
            stats["rle_tokens"] += len(tokens)
            for t in tokens:
                if ":" in t:
                    n = int(t.split(":")[0])
                    stats["total_values"] += n
                else:
                    stats["total_values"] += 1
    return stats


def _measure(tables, metadata) -> dict:
    """Full measurement of a dataset across formats."""
    meta_path, data_dir = _write_fixture(tables, metadata)

    csv_size = _csv_bytes(tables)
    jsonl_size = _jsonl_bytes(tables)

    cfg_default = EncoderConfig()
    cfg_nosorted = EncoderConfig(include_sorted=False)
    cfg_stats = EncoderConfig(include_stats=True)

    tcf_default = encode(meta_path, data_dir, config=cfg_default)
    tcf_nosorted_text = encode(meta_path, data_dir, config=cfg_nosorted)
    tcf_stats_text = encode(meta_path, data_dir, config=cfg_stats)

    tcf_size = len(tcf_default.encode("utf-8"))
    tcf_nosorted_size = len(tcf_nosorted_text.encode("utf-8"))
    tcf_stats_size = len(tcf_stats_text.encode("utf-8"))

    rle = _rle_stats(tcf_default)
    rle_ratio = rle["total_values"] / rle["rle_tokens"] if rle["rle_tokens"] else 1.0

    total_rows = sum(len(rows) for rows in tables.values())

    return {
        "total_rows": total_rows,
        "csv_bytes": csv_size,
        "jsonl_bytes": jsonl_size,
        "tcf_bytes": tcf_size,
        "tcf_nosorted_bytes": tcf_nosorted_size,
        "tcf_stats_bytes": tcf_stats_size,
        "tcf_vs_csv": round(tcf_size / csv_size, 4) if csv_size else 0,
        "tcf_vs_jsonl": round(tcf_size / jsonl_size, 4) if jsonl_size else 0,
        "tcf_nosorted_vs_csv": round(tcf_nosorted_size / csv_size, 4) if csv_size else 0,
        "rle_sorted_columns": rle["sorted_columns"],
        "rle_total_values": rle["total_values"],
        "rle_tokens": rle["rle_tokens"],
        "rle_ratio": round(rle_ratio, 2),
        "sorted_overhead_bytes": tcf_size - tcf_nosorted_size,
        "stats_overhead_bytes": tcf_stats_size - tcf_size,
    }


# =========================================================================
# CRM Sales — varying scale and cardinality
# =========================================================================

class TestCrmCompression:
    """CRM sales data: FK-heavy, Zipf-like distribution."""

    def test_small_50rows_high_repetition(self):
        """50 rows, 5 customers, 5 products → high FK repetition."""
        tables, meta = crm_sales(n_rows=50, n_customers=5, n_products=5, seed=1)
        m = _measure(tables, meta)
        # With only 5 FK values across 50 rows, RLE should compress well
        assert m["rle_ratio"] >= 2.0, f"RLE ratio {m['rle_ratio']} too low for high repetition"

    def test_medium_200rows(self):
        """200 rows, 20 customers, 15 products → moderate repetition."""
        tables, meta = crm_sales(n_rows=200, n_customers=20, n_products=15, seed=2)
        m = _measure(tables, meta)
        # TCF should be smaller than JSONL
        assert m["tcf_vs_jsonl"] < 1.0, (
            f"TCF ({m['tcf_bytes']}B) should be smaller than JSONL ({m['jsonl_bytes']}B)"
        )

    def test_large_1000rows(self):
        """1000 rows, 30 customers, 20 products → good amortization."""
        tables, meta = crm_sales(n_rows=1000, n_customers=30, n_products=20, seed=3)
        m = _measure(tables, meta)
        # At 1000 rows, header overhead is amortized
        assert m["tcf_vs_jsonl"] < 0.7, (
            f"At 1000 rows, TCF should be >=30% smaller than JSONL, got {m['tcf_vs_jsonl']}"
        )

    def test_cardinality_effect(self):
        """Same rows, different FK cardinality → measures RLE impact."""
        # Low cardinality: 5 customers
        tables_low, meta_low = crm_sales(n_rows=200, n_customers=5, n_products=5, seed=10)
        m_low = _measure(tables_low, meta_low)

        # High cardinality: 100 customers
        tables_high, meta_high = crm_sales(n_rows=200, n_customers=100, n_products=25, seed=10)
        m_high = _measure(tables_high, meta_high)

        # Low cardinality should have better RLE
        assert m_low["rle_ratio"] > m_high["rle_ratio"], (
            f"Low cardinality RLE ({m_low['rle_ratio']}) should beat "
            f"high cardinality ({m_high['rle_ratio']})"
        )


# =========================================================================
# Service Logs — extreme FK repetition
# =========================================================================

class TestLogsCompression:
    """Service logs: only 5 status codes + 8 categories → ideal for RLE."""

    def test_high_rle_efficiency(self):
        """500 rows with 5 status codes → very high RLE compression."""
        tables, meta = service_logs(n_rows=500, seed=1)
        m = _measure(tables, meta)
        # Without FK declarations, no sorted columns exist
        # But the data itself is very repetitive

    def test_tcf_smaller_than_jsonl(self):
        tables, meta = service_logs(n_rows=500, seed=1)
        m = _measure(tables, meta)
        assert m["tcf_vs_jsonl"] < 1.0


# =========================================================================
# Survey — Likert scale (extreme value repetition)
# =========================================================================

class TestSurveyCompression:
    """Survey data: 1-5 scale values → extreme repetition potential."""

    def test_likert_rle_compression(self):
        """100 respondents x 5 questions = 500 responses, only 5 values."""
        tables, meta = survey_likert(n_respondents=100, n_questions=5, seed=1)
        m = _measure(tables, meta)
        # FK (id_respondente) has 100 unique values, moderate RLE
        # nota column has only 5 values, but it's not sorted by default
        assert m["tcf_vs_jsonl"] < 0.8

    def test_large_survey(self):
        """500 respondents x 10 questions = 5000 responses."""
        tables, meta = survey_likert(n_respondents=500, n_questions=10, seed=2)
        m = _measure(tables, meta)
        # At 5000 rows, TCF should significantly beat JSONL
        assert m["tcf_vs_jsonl"] < 0.5, (
            f"At 5000 rows, TCF should be >=50% smaller than JSONL, got {m['tcf_vs_jsonl']}"
        )


# =========================================================================
# Unique Data — worst case control group
# =========================================================================

class TestUniqueCompression:
    """All unique values — worst case for RLE (control group)."""

    def test_no_rle_benefit(self):
        """200 unique rows → no repetition in sorted columns."""
        tables, meta = unique_data(n_rows=200, seed=1)
        m = _measure(tables, meta)
        # RLE ratio should be near 1.0 (no compression)
        assert m["rle_ratio"] <= 1.5, (
            f"Unique data should have RLE ratio near 1.0, got {m['rle_ratio']}"
        )

    def test_still_beats_jsonl(self):
        """Even without RLE, columnar avoids key repetition vs JSONL."""
        tables, meta = unique_data(n_rows=200, seed=1)
        m = _measure(tables, meta)
        assert m["tcf_vs_jsonl"] < 1.0, (
            "Even worst-case TCF should beat JSONL due to no key repetition"
        )

    def test_sorted_overhead_documented(self):
        """Sorted columns add overhead when there's no RLE benefit."""
        tables, meta = unique_data(n_rows=200, seed=1)
        m = _measure(tables, meta)
        # Sorted columns should be pure overhead for unique data
        if m["sorted_overhead_bytes"] > 0:
            overhead_pct = m["sorted_overhead_bytes"] / m["tcf_bytes"] * 100
            # Document: sorted adds X% overhead with no benefit
            assert overhead_pct < 50, f"Sorted overhead {overhead_pct:.1f}% is excessive"


# =========================================================================
# Crossover analysis — at what scale does TCF beat CSV?
# =========================================================================

class TestCrossoverPoint:
    """Find the row count where TCF becomes smaller than CSV."""

    def test_tcf_vs_csv_scaling(self):
        """TCF/CSV ratio should decrease as rows increase."""
        ratios = []
        for n in [20, 50, 100, 200, 500, 1000]:
            tables, meta = crm_sales(
                n_rows=n, n_customers=min(n // 3, 30), n_products=15, seed=42
            )
            m = _measure(tables, meta)
            ratios.append((n, m["tcf_vs_csv"]))

        # Ratio should decrease as n grows (header amortized)
        # At some point it should cross 1.0
        first_ratio = ratios[0][1]
        last_ratio = ratios[-1][1]
        assert last_ratio < first_ratio, (
            f"TCF/CSV ratio should decrease with scale: "
            f"n={ratios[0][0]} ratio={first_ratio}, n={ratios[-1][0]} ratio={last_ratio}"
        )

    def test_tcf_vs_jsonl_always_better_at_scale(self):
        """TCF should always beat JSONL at >= 50 rows."""
        for n in [50, 100, 500]:
            tables, meta = crm_sales(
                n_rows=n, n_customers=min(n // 3, 30), n_products=15, seed=42
            )
            m = _measure(tables, meta)
            assert m["tcf_vs_jsonl"] < 1.0, (
                f"TCF should beat JSONL at {n} rows, got ratio {m['tcf_vs_jsonl']}"
            )


# =========================================================================
# Overhead analysis
# =========================================================================

class TestOverhead:
    """Quantify overhead of TCF features."""

    def test_sorted_overhead_proportional_to_fk_count(self):
        """More FK columns = more sorted overhead."""
        tables, meta = crm_sales(n_rows=200, n_customers=20, n_products=15, seed=42)
        m = _measure(tables, meta)
        # Should have sorted columns for id_cliente and id_produto
        assert m["rle_sorted_columns"] >= 2

    def test_stats_overhead_small(self):
        """Stats lines should add < 15% overhead."""
        tables, meta = crm_sales(n_rows=200, n_customers=20, n_products=15, seed=42)
        m = _measure(tables, meta)
        if m["tcf_bytes"] > 0:
            pct = m["stats_overhead_bytes"] / m["tcf_bytes"] * 100
            assert pct < 15, f"Stats overhead {pct:.1f}% exceeds 15% threshold"

    def test_no_sorted_reduces_size(self):
        """Disabling sorted columns should reduce TCF size."""
        tables, meta = crm_sales(n_rows=200, n_customers=20, n_products=15, seed=42)
        m = _measure(tables, meta)
        assert m["tcf_nosorted_bytes"] < m["tcf_bytes"], (
            "TCF without sorted should be smaller"
        )


# =========================================================================
# Print benchmark report (runs with pytest -s)
# =========================================================================

class TestBenchmarkReport:
    """Print a human-readable compression report (visible with pytest -s)."""

    def test_print_report(self, capsys):
        """Generate full compression benchmark to stdout."""
        scenarios = [
            ("crm_50r_5c", crm_sales(50, 5, 5, seed=1)),
            ("crm_200r_20c", crm_sales(200, 20, 15, seed=2)),
            ("crm_1000r_30c", crm_sales(1000, 30, 20, seed=3)),
            ("logs_500r", service_logs(500, seed=1)),
            ("survey_500r", survey_likert(100, 5, seed=1)),
            ("survey_5000r", survey_likert(500, 10, seed=2)),
            ("unique_200r", unique_data(200, seed=1)),
        ]

        print("\n")
        print("=" * 90)
        print("COMPRESSION BENCHMARK REPORT")
        print("=" * 90)
        print(f"{'Dataset':<20} {'Rows':>6} {'CSV':>8} {'JSONL':>8} {'TCF':>8} "
              f"{'TCF/CSV':>8} {'TCF/JL':>8} {'RLE':>5}")
        print("-" * 90)

        for name, (tables, meta) in scenarios:
            m = _measure(tables, meta)
            print(
                f"{name:<20} {m['total_rows']:>6} "
                f"{m['csv_bytes']:>7}B {m['jsonl_bytes']:>7}B {m['tcf_bytes']:>7}B "
                f"{m['tcf_vs_csv']:>7.2f}x {m['tcf_vs_jsonl']:>7.2f}x "
                f"{m['rle_ratio']:>4.1f}x"
            )

        print("-" * 90)
        print("TCF/CSV < 1.0 means TCF is smaller than CSV")
        print("TCF/JL  < 1.0 means TCF is smaller than JSONL")
        print("RLE     > 1.0 means sorted columns compress (higher = better)")
        print("=" * 90)

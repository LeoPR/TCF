"""Tests for the Dataset Shaper (scripts/shaper/).

These tests require the SQLite databases to exist in the configured
data_root. Run `python scripts/csv_to_sqlite.py` first if needed.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Make scripts importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from shaper import ShapeRequest, ShapeResult, Shaper  # noqa: E402


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def shaper():
    return Shaper()


def _needs_db(name: str):
    """Skip test if SQLite DB doesn't exist."""
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
    from _paths import interim_db
    db = interim_db(name)
    if not db.exists():
        pytest.skip(f"SQLite DB not found: {db}. Run csv_to_sqlite.py first.")


# ---------------------------------------------------------------------------
# ShapeRequest validation
# ---------------------------------------------------------------------------

class TestShapeRequestValidation:
    def test_valid_minimal(self):
        r = ShapeRequest(dataset="adult-census")
        assert r.is_valid

    def test_valid_full(self):
        r = ShapeRequest(
            dataset="tpch-sf001", volume=100, seed=7,
            schema="core", order="random", join_level="flat",
        )
        assert r.is_valid

    def test_invalid_empty_dataset(self):
        r = ShapeRequest(dataset="")
        assert not r.is_valid

    def test_invalid_volume_negative(self):
        r = ShapeRequest(dataset="x", volume=-1)
        assert not r.is_valid

    def test_invalid_volume_fraction_out_of_range(self):
        r = ShapeRequest(dataset="x", volume=1.5)
        assert not r.is_valid

    def test_invalid_schema_name(self):
        r = ShapeRequest(dataset="x", schema="nope")
        assert not r.is_valid

    def test_valid_schema_list(self):
        r = ShapeRequest(dataset="x", schema=["table1"])
        assert r.is_valid

    def test_invalid_schema_empty_list(self):
        r = ShapeRequest(dataset="x", schema=[])
        assert not r.is_valid

    def test_invalid_join_level(self):
        r = ShapeRequest(dataset="x", join_level="semi")
        assert not r.is_valid

    def test_invalid_order(self):
        r = ShapeRequest(dataset="x", order="upside_down")
        assert not r.is_valid

    def test_valid_order_sorted(self):
        r = ShapeRequest(dataset="x", order="sorted:age")
        assert r.is_valid

    def test_invalid_compressibility(self):
        r = ShapeRequest(dataset="x", compressibility_range=(0.8, 0.2))
        assert not r.is_valid

    def test_assert_valid_raises(self):
        r = ShapeRequest(dataset="", volume=-5)
        with pytest.raises(ValueError):
            r.assert_valid()


# ---------------------------------------------------------------------------
# Pipeline — Adult (flat, 1 table)
# ---------------------------------------------------------------------------

class TestShaperAdult:
    @pytest.fixture(autouse=True)
    def _check_db(self):
        _needs_db("adult-census")

    def test_full_dataset(self, shaper):
        r = shaper.apply(ShapeRequest(dataset="adult-census"))
        assert r.total_rows == 48842
        assert "adult" in r.table_names

    def test_volume_fraction(self, shaper):
        r = shaper.apply(ShapeRequest(dataset="adult-census", volume=0.1))
        assert 4800 <= r.total_rows <= 4900

    def test_volume_absolute(self, shaper):
        r = shaper.apply(ShapeRequest(dataset="adult-census", volume=50))
        assert r.total_rows == 50

    def test_volume_zero(self, shaper):
        r = shaper.apply(ShapeRequest(dataset="adult-census", volume=0))
        assert r.total_rows == 0

    def test_determinism(self, shaper):
        req = ShapeRequest(dataset="adult-census", volume=20, order="random", seed=42)
        r1 = shaper.apply(req)
        r2 = shaper.apply(req)
        assert r1.tables["adult"] == r2.tables["adult"]

    def test_different_seeds_differ(self, shaper):
        r1 = shaper.apply(ShapeRequest(dataset="adult-census", volume=20, order="random", seed=42))
        r2 = shaper.apply(ShapeRequest(dataset="adult-census", volume=20, order="random", seed=99))
        assert r1.tables["adult"] != r2.tables["adult"]

    def test_sorted_order(self, shaper):
        r = shaper.apply(ShapeRequest(dataset="adult-census", volume=10, order="sorted:age"))
        ages = [row["age"] for row in r.tables["adult"]]
        assert ages == sorted(ages)

    def test_reverse_order(self, shaper):
        r = shaper.apply(ShapeRequest(dataset="adult-census", volume=10, order="reverse:age"))
        ages = [row["age"] for row in r.tables["adult"]]
        assert ages == sorted(ages, reverse=True)

    def test_trace_not_empty(self, shaper):
        r = shaper.apply(ShapeRequest(dataset="adult-census", volume=5))
        assert len(r.trace) >= 3  # request + opened + loaded + strategies

    def test_stats_present(self, shaper):
        r = shaper.apply(ShapeRequest(dataset="adult-census", volume=100))
        assert "rows_before" in r.stats
        assert "rows_after" in r.stats
        assert r.stats["rows_after"] == 100

    def test_never_more_than_requested(self, shaper):
        r = shaper.apply(ShapeRequest(dataset="adult-census", volume=50))
        assert r.total_rows <= 50


# ---------------------------------------------------------------------------
# Pipeline — TPC-H (relational, 8 tables)
# ---------------------------------------------------------------------------

class TestShaperTPCH:
    @pytest.fixture(autouse=True)
    def _check_db(self):
        _needs_db("tpch-sf001")

    def test_full_dataset(self, shaper):
        r = shaper.apply(ShapeRequest(dataset="tpch-sf001"))
        assert len(r.table_names) == 8
        assert r.total_rows > 80000

    def test_schema_minimal(self, shaper):
        r = shaper.apply(ShapeRequest(dataset="tpch-sf001", schema="minimal"))
        assert r.table_names == ["customer"]
        assert r.total_rows == 1500

    def test_schema_core(self, shaper):
        r = shaper.apply(ShapeRequest(dataset="tpch-sf001", schema="core"))
        assert set(r.table_names) == {"customer", "orders"}

    def test_schema_chain(self, shaper):
        r = shaper.apply(ShapeRequest(dataset="tpch-sf001", schema="chain"))
        assert set(r.table_names) == {"customer", "orders", "lineitem"}

    def test_schema_custom(self, shaper):
        r = shaper.apply(ShapeRequest(dataset="tpch-sf001", schema=["nation", "region"]))
        assert set(r.table_names) == {"nation", "region"}
        assert r.total_rows == 30  # 25 nations + 5 regions

    def test_schema_chain_with_volume(self, shaper):
        r = shaper.apply(ShapeRequest(dataset="tpch-sf001", schema="chain", volume=0.01))
        for name in r.table_names:
            assert len(r.tables[name]) > 0  # not empty

    def test_volume_applies_per_table(self, shaper):
        r = shaper.apply(ShapeRequest(dataset="tpch-sf001", schema="core", volume=10))
        # Each table gets 10 rows independently
        assert r.tables["customer"] == r.tables["customer"][:10] or len(r.tables["customer"]) == 10
        assert len(r.tables["orders"]) == 10

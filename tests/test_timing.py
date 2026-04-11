"""Tests for src/tcf/timing.py."""

import time

import pytest

from tcf.timing import Timings, repeat_with_stats


# ---------------------------------------------------------------------------
# Timings basics
# ---------------------------------------------------------------------------

def test_measure_records_phase():
    t = Timings()
    with t.measure("phase_a"):
        time.sleep(0.005)
    assert "phase_a" in t
    # at least 4ms in nanoseconds (allow slack for timer resolution)
    assert t.events["phase_a"] >= 4_000_000


def test_multiple_phases_preserved():
    t = Timings()
    with t.measure("a"):
        time.sleep(0.002)
    with t.measure("b"):
        time.sleep(0.004)
    d = t.to_dict(unit="ms")
    assert set(d.keys()) == {"a", "b"}
    assert d["b"] > d["a"]


def test_to_dict_units():
    t = Timings()
    t.record("x", 5_000_000)  # 5 ms exactly
    assert t.to_dict(unit="ns")["x"] == 5_000_000
    assert t.to_dict(unit="us")["x"] == 5_000
    assert t.to_dict(unit="ms")["x"] == 5
    assert t.to_dict(unit="s")["x"] == 0.005


def test_to_dict_invalid_unit_raises():
    t = Timings()
    t.record("x", 100)
    with pytest.raises(ValueError):
        t.to_dict(unit="minutes")


def test_total_sums_all_events():
    t = Timings()
    t.record("a", 1_000_000)
    t.record("b", 2_000_000)
    t.record("c", 3_000_000)
    assert t.total(unit="ms") == 6.0
    assert t.total(unit="ns") == 6_000_000


def test_record_overrides_previous():
    t = Timings()
    t.record("x", 1_000)
    t.record("x", 5_000)
    assert t.events["x"] == 5_000


def test_contains_and_len():
    t = Timings()
    assert len(t) == 0
    assert "nothing" not in t
    t.record("a", 100)
    t.record("b", 200)
    assert len(t) == 2
    assert "a" in t
    assert "b" in t


# ---------------------------------------------------------------------------
# repeat_with_stats
# ---------------------------------------------------------------------------

def test_repeat_with_stats_basic():
    def run(t):
        with t.measure("step"):
            time.sleep(0.002)

    stats = repeat_with_stats(run, n=3, warmup=1)
    assert "step" in stats
    s = stats["step"]
    for key in ("median_ms", "mean_ms", "p95_ms", "min_ms", "max_ms", "stdev_ms", "n"):
        assert key in s
    assert s["n"] == 3
    assert s["median_ms"] >= 1.0  # ~2ms but allow slack


def test_repeat_with_stats_multiple_phases():
    def run(t):
        with t.measure("fast"):
            time.sleep(0.001)
        with t.measure("slow"):
            time.sleep(0.003)

    stats = repeat_with_stats(run, n=2, warmup=0)
    assert set(stats.keys()) == {"fast", "slow"}
    assert stats["slow"]["median_ms"] > stats["fast"]["median_ms"]


def test_repeat_with_stats_zero_warmup():
    def run(t):
        t.record("fake", 1_000_000)

    stats = repeat_with_stats(run, n=1, warmup=0)
    assert stats["fake"]["n"] == 1
    assert stats["fake"]["stdev_ms"] == 0.0


def test_repeat_with_stats_invalid_n():
    def run(t):
        pass
    with pytest.raises(ValueError):
        repeat_with_stats(run, n=0)


def test_repeat_with_stats_deterministic_values():
    # Use record() to avoid timer noise — verify stats math
    counter = {"i": 0}

    def run(t):
        vals_ns = [1_000_000, 2_000_000, 3_000_000, 4_000_000, 5_000_000]
        t.record("x", vals_ns[counter["i"]])
        counter["i"] += 1

    stats = repeat_with_stats(run, n=5, warmup=0)
    s = stats["x"]
    assert s["n"] == 5
    assert s["min_ms"] == 1.0
    assert s["max_ms"] == 5.0
    assert s["median_ms"] == 3.0
    assert s["mean_ms"] == 3.0

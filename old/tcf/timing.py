"""Honest phase timing for benchmarks.

Provides `Timings` for measuring distinct phases of a pipeline and
`repeat_with_stats` for running a function multiple times and reporting
median/mean/p95/stdev across runs.

Why this exists:
    Reporting "encoding took 500ms" is meaningless if 450ms of that was
    reading from disk or parsing CSV. In benchmarks comparing formats
    (TCF vs CSV vs JSONL vs TOON) we need to isolate each phase so we
    can answer "how much time does the *format's encoder* actually take".

Design goals:
    - Pure stdlib (`time`, `contextlib`, `statistics`) — zero deps
    - Nanosecond resolution via `time.perf_counter_ns()`
    - No I/O or printing side effects inside measurements
    - Tiny surface area: `with t.measure("name"): ...`
    - Exports dict ready for JSONL manifests

Usage:
    from tcf.timing import Timings, repeat_with_stats

    t = Timings()
    with t.measure("io_read"):
        raw = path.read_bytes()
    with t.measure("parse_csv"):
        rows = parse_csv(raw)
    with t.measure("tcf_encode"):
        tcf_text = tcf.encode(rows)

    print(t.to_dict(unit="ms"))
    # {"io_read": 2.1, "parse_csv": 45.3, "tcf_encode": 12.7}

    # Multi-run statistics
    def run(t):
        with t.measure("phase1"):
            work()
    stats = repeat_with_stats(run, n=5, warmup=1)
    # {"phase1": {"median_ms": ..., "p95_ms": ..., ...}}
"""

from __future__ import annotations

import statistics
import time
from contextlib import contextmanager
from typing import Callable, Iterator


_UNIT_DIVISORS = {
    "ns": 1,
    "us": 1_000,
    "ms": 1_000_000,
    "s":  1_000_000_000,
}


class Timings:
    """Collects per-phase durations in nanoseconds using perf_counter_ns.

    Each call to `measure(name)` overrides any prior measurement of the
    same name. Use distinct names when phases must not collide.
    """

    __slots__ = ("events",)

    def __init__(self) -> None:
        self.events: dict[str, int] = {}

    @contextmanager
    def measure(self, name: str) -> Iterator[None]:
        """Measure the enclosed block and store duration under `name`."""
        t0 = time.perf_counter_ns()
        try:
            yield
        finally:
            self.events[name] = time.perf_counter_ns() - t0

    def record(self, name: str, duration_ns: int) -> None:
        """Record a pre-computed duration (e.g. from an external timer)."""
        self.events[name] = int(duration_ns)

    def to_dict(self, unit: str = "ms") -> dict[str, float]:
        """Return measurements as a dict, converted to the chosen unit.

        Args:
            unit: one of "ns", "us", "ms", "s". Default "ms".
        """
        if unit not in _UNIT_DIVISORS:
            raise ValueError(f"unit must be one of {list(_UNIT_DIVISORS)}; got {unit!r}")
        div = _UNIT_DIVISORS[unit]
        return {k: round(v / div, 3) for k, v in self.events.items()}

    def total(self, unit: str = "ms") -> float:
        """Sum of all recorded events in the chosen unit."""
        if unit not in _UNIT_DIVISORS:
            raise ValueError(f"unit must be one of {list(_UNIT_DIVISORS)}; got {unit!r}")
        div = _UNIT_DIVISORS[unit]
        return round(sum(self.events.values()) / div, 3)

    def keys(self):
        return self.events.keys()

    def __contains__(self, name: str) -> bool:
        return name in self.events

    def __len__(self) -> int:
        return len(self.events)


def repeat_with_stats(
    fn: Callable[["Timings"], None],
    n: int = 5,
    warmup: int = 1,
) -> dict[str, dict[str, float]]:
    """Run `fn` (n + warmup) times and return per-phase statistics.

    `fn` must accept a single argument — a fresh `Timings` instance — and
    record its measurements into it.

    Args:
        fn: callable taking a Timings and performing timed work
        n: number of measurement runs (minimum 1)
        warmup: number of discarded warmup runs (to avoid cold-start noise)

    Returns:
        dict keyed by phase name, each value is:
            {
              "median_ms": ..., "mean_ms": ...,
              "p95_ms": ..., "min_ms": ..., "max_ms": ...,
              "stdev_ms": ..., "n": n
            }

    Raises:
        ValueError: if n < 1
    """
    if n < 1:
        raise ValueError(f"n must be >= 1; got {n}")

    for _ in range(max(0, warmup)):
        t_warm = Timings()
        fn(t_warm)

    runs: list[dict[str, float]] = []
    for _ in range(n):
        t = Timings()
        fn(t)
        runs.append(t.to_dict(unit="ms"))

    if not runs:
        return {}

    all_keys: set[str] = set()
    for run in runs:
        all_keys.update(run.keys())

    result: dict[str, dict[str, float]] = {}
    for key in sorted(all_keys):
        values = [run[key] for run in runs if key in run]
        if not values:
            continue
        sorted_vals = sorted(values)
        # p95 via nearest-rank method; for tiny n this is approximate
        p95_idx = max(0, min(len(sorted_vals) - 1, int(round(len(sorted_vals) * 0.95 - 1))))
        result[key] = {
            "median_ms": round(statistics.median(values), 3),
            "mean_ms":   round(statistics.fmean(values), 3),
            "p95_ms":    round(sorted_vals[p95_idx], 3),
            "min_ms":    round(min(values), 3),
            "max_ms":    round(max(values), 3),
            "stdev_ms":  round(statistics.stdev(values), 3) if len(values) > 1 else 0.0,
            "n":         len(values),
        }
    return result


__all__ = ["Timings", "repeat_with_stats"]

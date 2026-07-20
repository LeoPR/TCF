"""Statistical confidence engine for LLM evaluation experiments.

Provides:
  wilson_ci        — Wilson score interval for proportions
  bootstrap_ci     — Bootstrap CI for any statistic
  segment_report   — Per-segment accuracy + CI table
  chi2_independence — Chi-square test between two categorical dimensions
  adequacy_check   — Minimum N to detect a given effect size at target power
"""
from __future__ import annotations
import math
import random
from collections import defaultdict
from typing import Any


# ---------------------------------------------------------------------------
# Wilson score confidence interval
# ---------------------------------------------------------------------------

def wilson_ci(ok: int, n: int, alpha: float = 0.05) -> tuple[float, float]:
    """Wilson score CI for a proportion.

    Handles n=0 and edge proportions (0 and 1) correctly.
    Returns (lower, upper) as fractions in [0, 1].
    """
    if n == 0:
        return (0.0, 1.0)
    z = _z_score(1 - alpha / 2)
    p = ok / n
    z2 = z * z
    center = (p + z2 / (2 * n)) / (1 + z2 / n)
    margin = (z / (1 + z2 / n)) * math.sqrt(p * (1 - p) / n + z2 / (4 * n * n))
    return (max(0.0, center - margin), min(1.0, center + margin))


def _z_score(p: float) -> float:
    """Inverse normal CDF (Abramowitz & Stegun approximation)."""
    # Rational approximation for |z| up to ~3.5
    if p <= 0.5:
        return -_z_score(1 - p)
    t = math.sqrt(-2 * math.log(1 - p))
    c = (2.515517, 0.802853, 0.010328)
    d = (1.432788, 0.189269, 0.001308)
    return t - (c[0] + c[1] * t + c[2] * t * t) / (1 + d[0] * t + d[1] * t * t + d[2] * t ** 3)


# ---------------------------------------------------------------------------
# Bootstrap CI
# ---------------------------------------------------------------------------

def bootstrap_ci(
    values: list[float | int | bool],
    stat_fn=None,
    n_boot: int = 5000,
    alpha: float = 0.05,
    seed: int = 0,
) -> tuple[float, float]:
    """Bootstrap CI for any statistic (default: mean/proportion).

    Returns (lower, upper) percentile interval.
    """
    if not values:
        return (0.0, 1.0)
    if stat_fn is None:
        stat_fn = lambda xs: sum(xs) / len(xs)

    rng = random.Random(seed)
    n = len(values)
    boots = []
    for _ in range(n_boot):
        sample = [values[rng.randint(0, n - 1)] for _ in range(n)]
        boots.append(stat_fn(sample))
    boots.sort()
    lo = boots[int(alpha / 2 * n_boot)]
    hi = boots[int((1 - alpha / 2) * n_boot)]
    return (lo, hi)


# ---------------------------------------------------------------------------
# Segment report
# ---------------------------------------------------------------------------

def segment_report(
    records: list[dict],
    group_dims: list[str],
    ok_field: str = "ok",
    alpha: float = 0.05,
) -> list[dict]:
    """Compute accuracy + Wilson CI for each unique combination of group_dims.

    Returns list of dicts sorted by segment key:
      {dim1: v1, dim2: v2, ..., n: int, ok: int, acc: float, ci_lo: float, ci_hi: float}
    """
    buckets: dict[tuple, list[bool]] = defaultdict(list)
    for r in records:
        key = tuple(r.get(d, "?") for d in group_dims)
        buckets[key].append(bool(r[ok_field]))

    rows = []
    for key, oks in sorted(buckets.items()):
        n = len(oks)
        ok = sum(oks)
        lo, hi = wilson_ci(ok, n, alpha=alpha)
        row = {d: v for d, v in zip(group_dims, key)}
        row.update({"n": n, "ok": ok, "acc": ok / n if n else 0.0,
                    "ci_lo": lo, "ci_hi": hi, "ci_width": hi - lo})
        rows.append(row)
    return rows


# ---------------------------------------------------------------------------
# Chi-square test for independence
# ---------------------------------------------------------------------------

def chi2_independence(
    records: list[dict],
    dim_a: str,
    dim_b: str,
    ok_field: str = "ok",
) -> dict:
    """Test whether accuracy differs significantly across values of dim_a
    when controlling for dim_b (or vice versa).

    Returns: {stat, p_value, dof, significant (p<0.05), contingency_table}
    """
    # Build contingency table: rows=dim_a values, cols=(ok, fail)
    from collections import Counter
    a_vals = sorted(set(r[dim_a] for r in records))
    counts: dict[Any, list[int]] = {a: [0, 0] for a in a_vals}
    for r in records:
        idx = 0 if r[ok_field] else 1
        counts[r[dim_a]][idx] += 1

    table = [counts[a] for a in a_vals]
    stat, p, dof = _chi2(table)
    return {
        "stat": round(stat, 4),
        "p_value": round(p, 6),
        "dof": dof,
        "significant": p < 0.05,
        "contingency_table": {a: dict(zip(["ok", "fail"], counts[a])) for a in a_vals},
    }


def _chi2(table: list[list[int]]) -> tuple[float, float, int]:
    """Compute chi-square statistic and p-value from a contingency table."""
    nrows = len(table)
    ncols = len(table[0])
    row_sums = [sum(row) for row in table]
    col_sums = [sum(table[r][c] for r in range(nrows)) for c in range(ncols)]
    total = sum(row_sums)

    stat = 0.0
    for r in range(nrows):
        for c in range(ncols):
            expected = row_sums[r] * col_sums[c] / total if total else 0
            if expected > 0:
                stat += (table[r][c] - expected) ** 2 / expected

    dof = (nrows - 1) * (ncols - 1)
    p = 1.0 - _chi2_cdf(stat, dof)
    return stat, p, dof


def _chi2_cdf(x: float, k: int) -> float:
    """Chi-square CDF via regularized incomplete gamma (series expansion)."""
    if x <= 0:
        return 0.0
    return _regularized_gamma(k / 2, x / 2)


def _regularized_gamma(a: float, x: float, tol: float = 1e-10, max_iter: int = 300) -> float:
    """Lower regularized incomplete gamma P(a, x) via series."""
    if x < 0:
        return 0.0
    if x == 0:
        return 0.0
    # Use series expansion for x <= a+1, continued fraction otherwise
    if x <= a + 1:
        ap = a
        delta = 1.0 / a
        total = delta
        for _ in range(max_iter):
            ap += 1
            delta *= x / ap
            total += delta
            if abs(delta) < abs(total) * tol:
                break
        return total * math.exp(-x + a * math.log(x) - math.lgamma(a))
    else:
        # Continued fraction (Lentz)
        fpmin = 1e-300
        b = x + 1 - a
        c = 1 / fpmin
        d = 1 / b
        h = d
        for i in range(1, max_iter + 1):
            an = -i * (i - a)
            b += 2
            d = an * d + b
            if abs(d) < fpmin:
                d = fpmin
            c = b + an / c
            if abs(c) < fpmin:
                c = fpmin
            d = 1 / d
            delta = d * c
            h *= delta
            if abs(delta - 1) < tol:
                break
        return 1.0 - math.exp(-x + a * math.log(x) - math.lgamma(a)) * h


# ---------------------------------------------------------------------------
# Sample adequacy check
# ---------------------------------------------------------------------------

def adequacy_check(
    n_per_cell: int,
    baseline_acc: float,
    target_delta: float = 0.05,
    power: float = 0.80,
    alpha: float = 0.05,
) -> dict:
    """How many samples are needed to reliably detect a `target_delta` improvement?

    Returns:
      required_n   — minimum N per group
      current_n    — N you have
      adequate     — bool (current_n >= required_n)
      detectable_delta — smallest effect detectable at given power with current_n
    """
    p1 = baseline_acc
    p2 = baseline_acc + target_delta
    p_bar = (p1 + p2) / 2
    z_alpha = _z_score(1 - alpha / 2)
    z_beta = _z_score(power)
    required_n = (
        (z_alpha * math.sqrt(2 * p_bar * (1 - p_bar)) +
         z_beta * math.sqrt(p1 * (1 - p1) + p2 * (1 - p2))) ** 2
        / (p1 - p2) ** 2
    )
    required_n = math.ceil(required_n)

    # Detectable delta at current N
    det_delta = _min_detectable_delta(n_per_cell, baseline_acc, alpha, power)

    return {
        "required_n": required_n,
        "current_n": n_per_cell,
        "adequate": n_per_cell >= required_n,
        "detectable_delta_pct": round(det_delta * 100, 1),
    }


def _min_detectable_delta(n: int, p1: float, alpha: float, power: float) -> float:
    """Binary search for minimum detectable delta given n (no recursion)."""
    def required_n_for(delta: float) -> int:
        p2 = p1 + delta
        p_bar = (p1 + p2) / 2
        z_a = _z_score(1 - alpha / 2)
        z_b = _z_score(power)
        req = (
            (z_a * math.sqrt(2 * p_bar * (1 - p_bar)) +
             z_b * math.sqrt(p1 * (1 - p1) + p2 * (1 - p2))) ** 2
            / (p1 - p2) ** 2
        )
        return math.ceil(req)

    lo, hi = 0.0, min(1.0 - p1, p1)
    for _ in range(60):
        mid = (lo + hi) / 2
        if mid < 1e-8:
            break
        if required_n_for(mid) <= n:
            hi = mid
        else:
            lo = mid
    return hi


# ---------------------------------------------------------------------------
# Summary printer
# ---------------------------------------------------------------------------

def print_confidence_report(
    records: list[dict],
    primary_dim: str,
    secondary_dims: list[str] | None = None,
    ok_field: str = "ok",
    alpha: float = 0.05,
) -> None:
    """Print a segmented confidence report to stdout."""
    secondary_dims = secondary_dims or []
    all_dims = [primary_dim] + secondary_dims

    # Overall
    total_n = len(records)
    total_ok = sum(1 for r in records if r[ok_field])
    lo, hi = wilson_ci(total_ok, total_n, alpha)
    print(f"\n=== Confidence Report (alpha={alpha}) ===")
    print(f"  Overall: {total_ok}/{total_n} = {total_ok/total_n*100:.1f}%  "
          f"95% CI [{lo*100:.1f}%, {hi*100:.1f}%]\n")

    # Per primary dim
    rows = segment_report(records, [primary_dim], ok_field=ok_field, alpha=alpha)
    print(f"  Per {primary_dim}:")
    print(f"  {'Value':<24} {'n':>5} {'Acc':>7}  {'95% CI':>20}  {'Width':>7}")
    print(f"  {'-'*24} {'-'*5} {'-'*7}  {'-'*20}  {'-'*7}")
    for row in rows:
        val = str(row[primary_dim])[:24]
        print(f"  {val:<24} {row['n']:>5} {row['acc']*100:>6.1f}%  "
              f"[{row['ci_lo']*100:>5.1f}%, {row['ci_hi']*100:>5.1f}%]  "
              f"{row['ci_width']*100:>6.1f}pp")

    # Chi-square: does primary_dim matter?
    # (Chi-square tests if an outcome depends on a dimension, not univariate)

    # Per secondary dims
    for dim in secondary_dims:
        rows2 = segment_report(records, [primary_dim, dim], ok_field=ok_field, alpha=alpha)
        print(f"\n  Per ({primary_dim} × {dim}):")
        # Pivot display
        dim_vals = sorted(set(r[primary_dim] for r in records))
        sec_vals = sorted(set(r[dim] for r in records))
        # header
        print(f"  {'':24} " + " ".join(f"{str(v)[:10]:>12}" for v in sec_vals))
        by_key = {(r[primary_dim], r[dim]): r for r in rows2}
        for pv in dim_vals:
            row_str = f"  {str(pv)[:24]:<24}"
            for sv in sec_vals:
                cell = by_key.get((pv, sv))
                if cell:
                    row_str += f"  {cell['acc']*100:>4.0f}% ±{cell['ci_width']*100:>3.0f}pp"
                else:
                    row_str += f"  {'—':>10}"
            print(row_str)

    # Adequacy check
    n_per_cell = total_n // max(1, len(set(r[primary_dim] for r in records)))
    adq = adequacy_check(n_per_cell, total_ok / total_n if total_n else 0)
    print(f"\n  Adequacy (detect 5pp delta, 80% power):")
    print(f"    Required N/cell: {adq['required_n']}, current: {adq['current_n']}  "
          f"{'OK' if adq['adequate'] else 'INSUFFICIENT'}")
    print(f"    Detectable delta at current N: {adq['detectable_delta_pct']}pp")

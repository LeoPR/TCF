"""Stratification representativeness metrics — classic + modern.

Quantifies how well a stratified sample preserves the population's
distribution. Used by `fk_preserving` and `stratify` strategies.

Metrics implemented:

  Classic
  -------
  - **Wilson score CI** per group proportion (95% by default)
    Standard binomial confidence interval, robust at small N.

  - **Chi-square goodness-of-fit** (p-value)
    Tests H0: sample distribution matches population.
    p > 0.05 means we cannot reject H0 → sample is consistent with population.
    Note: low N (<5 expected per cell) makes the test unreliable.

  Modern
  ------
  - **Total Variation Distance (TVD)** ∈ [0, 1]
    TVD = (1/2) Σ |p_i − q_i|
    "Worst-case probability difference" between distributions.
    Intuitive: TVD=0.05 means "samples differ from population by ≤5pp in TV norm".

  - **Jensen-Shannon Divergence (JSD)** ∈ [0, 1] (base-2 log)
    Symmetric, smooth, bounded version of KL divergence.
    Modern default for distribution comparison in ML.

  - **Hellinger distance** ∈ [0, 1]
    H(P,Q) = (1/√2) √(Σ (√p_i − √q_i)²)
    Symmetric, bounded, more sensitive to tail differences than TVD.

  References
  ----------
  - Wilson 1927 — score interval for proportion
  - Endres & Schindelin 2003 — JSD as metric (sqrt of JSD is metric)
  - Sui et al. 2024 — informally cite TVD for sample assessment

Returned dict shape:
    {
      "tvd": float,
      "jsd": float,
      "hellinger": float,
      "chi2_pvalue": float,
      "chi2_warn_low_n": bool,
      "groups": {
          group_key: {
              "pop_prop": float,
              "sample_prop": float,
              "wilson_ci": [lo, hi],
              "diff_pp": float,
          },
          ...
      },
      "n_pop": int,
      "n_sample": int,
      "n_groups": int,
    }
"""
from __future__ import annotations

import math
from typing import Any


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _z_score(p: float) -> float:
    """Inverse normal CDF (Abramowitz & Stegun approximation), 0 < p < 1."""
    if p <= 0.5:
        return -_z_score(1 - p)
    t = math.sqrt(-2 * math.log(1 - p))
    c = (2.515517, 0.802853, 0.010328)
    d = (1.432788, 0.189269, 0.001308)
    return t - (c[0] + c[1] * t + c[2] * t * t) / (1 + d[0] * t + d[1] * t * t + d[2] * t ** 3)


def _wilson_ci(ok: int, n: int, alpha: float = 0.05) -> tuple[float, float]:
    """Wilson score CI for a proportion (returns (lo, hi))."""
    if n == 0:
        return (0.0, 1.0)
    z = _z_score(1 - alpha / 2)
    p = ok / n
    z2 = z * z
    center = (p + z2 / (2 * n)) / (1 + z2 / n)
    margin = (z / (1 + z2 / n)) * math.sqrt(p * (1 - p) / n + z2 / (4 * n * n))
    return (max(0.0, center - margin), min(1.0, center + margin))


def _chi2_pvalue(observed: list[int], expected: list[float]) -> float:
    """Chi-square goodness-of-fit p-value via regularized incomplete gamma."""
    stat = 0.0
    for o, e in zip(observed, expected):
        if e > 0:
            stat += (o - e) ** 2 / e
    dof = len(observed) - 1
    if dof <= 0 or stat <= 0:
        return 1.0
    return 1.0 - _regularized_gamma(dof / 2, stat / 2)


def _regularized_gamma(a: float, x: float, tol: float = 1e-10, max_iter: int = 300) -> float:
    """Lower regularized incomplete gamma P(a, x) via series + continued fraction."""
    if x <= 0:
        return 0.0
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
# Distribution distances
# ---------------------------------------------------------------------------

def _tvd(p: dict, q: dict) -> float:
    """Total Variation Distance between two prob distributions over the same keys."""
    keys = set(p.keys()) | set(q.keys())
    return 0.5 * sum(abs(p.get(k, 0.0) - q.get(k, 0.0)) for k in keys)


def _jsd(p: dict, q: dict) -> float:
    """Jensen-Shannon divergence (base-2), bounded [0, 1]."""
    keys = set(p.keys()) | set(q.keys())
    m = {k: 0.5 * (p.get(k, 0.0) + q.get(k, 0.0)) for k in keys}

    def _kl(a, b):
        s = 0.0
        for k in keys:
            ak = a.get(k, 0.0)
            bk = b.get(k, 0.0)
            if ak > 0 and bk > 0:
                s += ak * math.log2(ak / bk)
        return s

    return 0.5 * _kl(p, m) + 0.5 * _kl(q, m)


def _hellinger(p: dict, q: dict) -> float:
    """Hellinger distance, bounded [0, 1]."""
    keys = set(p.keys()) | set(q.keys())
    s = sum((math.sqrt(p.get(k, 0.0)) - math.sqrt(q.get(k, 0.0))) ** 2 for k in keys)
    return math.sqrt(s) / math.sqrt(2)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_stratification_metrics(
    pop_counts: dict[Any, int],
    sample_counts: dict[Any, int],
    alpha: float = 0.05,
) -> dict[str, Any]:
    """Compute representativeness metrics for a stratified sample.

    Args:
        pop_counts:    {group_key: count_in_population}
        sample_counts: {group_key: count_in_sample}
        alpha:         CI level (default 0.05 → 95% CI)

    Returns:
        dict with TVD, JSD, Hellinger, chi-square p-value, and
        per-group Wilson CIs, all keyed for easy logging/comparison.
    """
    n_pop = sum(pop_counts.values())
    n_sample = sum(sample_counts.values())
    n_groups = len(set(pop_counts) | set(sample_counts))

    if n_pop == 0 or n_sample == 0:
        return {
            "tvd": float("nan"), "jsd": float("nan"), "hellinger": float("nan"),
            "chi2_pvalue": float("nan"), "chi2_warn_low_n": True,
            "groups": {}, "n_pop": n_pop, "n_sample": n_sample,
            "n_groups": n_groups,
        }

    pop_props = {k: v / n_pop for k, v in pop_counts.items()}
    sample_props = {k: sample_counts.get(k, 0) / n_sample for k in pop_counts}

    # Distribution distances
    tvd = _tvd(pop_props, sample_props)
    jsd = _jsd(pop_props, sample_props)
    hellinger = _hellinger(pop_props, sample_props)

    # Chi-square goodness-of-fit
    keys = sorted(pop_counts.keys(), key=lambda k: (k is None, str(k)))
    observed = [sample_counts.get(k, 0) for k in keys]
    expected = [pop_props[k] * n_sample for k in keys]
    chi2_warn = any(e < 5 for e in expected)
    chi2_p = _chi2_pvalue(observed, expected)

    # Per-group Wilson CIs
    groups: dict[Any, dict] = {}
    for k in keys:
        s_count = sample_counts.get(k, 0)
        ci_lo, ci_hi = _wilson_ci(s_count, n_sample, alpha)
        groups[k] = {
            "pop_count": pop_counts[k],
            "pop_prop": pop_props[k],
            "sample_count": s_count,
            "sample_prop": sample_props.get(k, 0.0),
            "wilson_ci": [round(ci_lo, 4), round(ci_hi, 4)],
            "diff_pp": round((sample_props.get(k, 0.0) - pop_props[k]) * 100, 2),
        }

    return {
        "tvd": round(tvd, 4),
        "jsd": round(jsd, 4),
        "hellinger": round(hellinger, 4),
        "chi2_pvalue": round(chi2_p, 4),
        "chi2_warn_low_n": chi2_warn,
        "n_pop": n_pop,
        "n_sample": n_sample,
        "n_groups": n_groups,
        "groups": {str(k): v for k, v in groups.items()},
    }


def format_metrics_summary(metrics: dict[str, Any]) -> str:
    """One-line human-readable summary of metrics for trace logging."""
    if metrics.get("chi2_warn_low_n"):
        chi2_str = f"chi2_p={metrics['chi2_pvalue']:.3f}* (low N warning)"
    else:
        chi2_str = f"chi2_p={metrics['chi2_pvalue']:.3f}"
    return (
        f"TVD={metrics['tvd']:.4f}, JSD={metrics['jsd']:.4f}, "
        f"Hellinger={metrics['hellinger']:.4f}, {chi2_str}, "
        f"n_pop={metrics['n_pop']}, n_sample={metrics['n_sample']}, "
        f"n_groups={metrics['n_groups']}"
    )


__all__ = ["compute_stratification_metrics", "format_metrics_summary"]

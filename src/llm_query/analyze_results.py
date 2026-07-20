"""Unified results analyzer — works on any experiment manifest (M1-M5+).

Usage:
  python analyze_results.py --manifest experiments/results/m5_intermediate/manifest.jsonl
  python analyze_results.py --manifest .../manifest.jsonl --primary variant --secondary model domain
  python analyze_results.py --manifest .../manifest.jsonl --compare variant --chi2 model
  python analyze_results.py --manifest .../manifest.jsonl --adequacy --target-delta 5
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from llm_eval.stats import (
    wilson_ci, bootstrap_ci, segment_report,
    chi2_independence, adequacy_check,
    print_confidence_report,
)


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------

def load_manifest(path: Path) -> list[dict]:
    seen: set[str] = set()
    records = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            r = json.loads(line)
        except Exception:
            continue
        if r.get("key") and r["key"] not in seen:
            seen.add(r["key"])
            records.append(r)
    return records


# ---------------------------------------------------------------------------
# Comparison table: one dim as rows, another as columns
# ---------------------------------------------------------------------------

def comparison_table(
    records: list[dict],
    row_dim: str,
    col_dim: str,
    ok_field: str = "ok",
    alpha: float = 0.05,
) -> None:
    """Print a comparison table: rows = row_dim values, cols = col_dim values.

    Each cell: acc% ±CI_half_width_pp
    """
    from collections import defaultdict
    by_rc = defaultdict(list)
    for r in records:
        by_rc[(r.get(row_dim, "?"), r.get(col_dim, "?"))].append(bool(r[ok_field]))

    row_vals = sorted(set(r.get(row_dim, "?") for r in records))
    col_vals = sorted(set(r.get(col_dim, "?") for r in records))

    header = f"  {'':22} " + " ".join(f"{str(v)[:14]:>16}" for v in col_vals)
    print(header)
    print(f"  {'-'*22} " + " ".join(f"{'':->16}" for _ in col_vals))

    for rv in row_vals:
        row_str = f"  {str(rv)[:22]:<22}"
        for cv in col_vals:
            oks = by_rc[(rv, cv)]
            if not oks:
                row_str += f"  {'—':>14}"
            else:
                n = len(oks)
                ok = sum(oks)
                lo, hi = wilson_ci(ok, n, alpha=alpha)
                half = (hi - lo) / 2 * 100
                row_str += f"  {ok/n*100:>5.1f}% ±{half:>4.1f}pp"
        print(row_str)


# ---------------------------------------------------------------------------
# Quality report
# ---------------------------------------------------------------------------

def quality_report(records: list[dict], group_dim: str = "variant") -> None:
    """Report SQL quality scores by group_dim."""
    from collections import defaultdict
    sql_records = [r for r in records
                   if r.get("quality") and isinstance(r["quality"], dict)
                   and r["quality"].get("quality_score") is not None]
    if not sql_records:
        print("  No quality scores found in manifest.")
        return

    by_group: dict[str, list] = defaultdict(list)
    fields = ["quality_score", "has_explicit_join", "join_uses_on",
              "no_select_star", "single_result_col", "tables_exist",
              "token_count", "has_subquery"]

    for r in sql_records:
        q = r["quality"]
        by_group[r.get(group_dim, "?")].append(q)

    print(f"  SQL quality by {group_dim}:")
    print(f"  {'':18} {'score':>7} {'expl_join':>10} {'on_clause':>10} "
          f"{'no_star':>8} {'1_col':>7} {'tbl_ok':>7} {'tokens':>7} {'sub':>5}")
    print(f"  {'-'*18} {'-'*7} {'-'*10} {'-'*10} {'-'*8} {'-'*7} {'-'*7} {'-'*7} {'-'*5}")

    for group_val in sorted(by_group.keys()):
        qs = by_group[group_val]
        n = len(qs)

        def avg(field):
            vals = [q[field] for q in qs if field in q]
            if not vals:
                return float("nan")
            if isinstance(vals[0], bool):
                return sum(vals) / len(vals) * 100
            return sum(vals) / len(vals)

        print(f"  {str(group_val)[:18]:<18} {avg('quality_score'):>6.3f} "
              f"{avg('has_explicit_join'):>9.0f}% {avg('join_uses_on'):>9.0f}% "
              f"{avg('no_select_star'):>7.0f}% {avg('single_result_col'):>6.0f}% "
              f"{avg('tables_exist'):>6.0f}% {avg('token_count'):>7.1f} "
              f"{avg('has_subquery'):>4.0f}%")


# ---------------------------------------------------------------------------
# Latency / efficiency report
# ---------------------------------------------------------------------------

def performance_report(records: list[dict], group_dim: str = "variant") -> None:
    """Latency and prompt efficiency by group."""
    from collections import defaultdict
    by_group: dict[str, list] = defaultdict(list)
    for r in records:
        by_group[r.get(group_dim, "?")].append(r)

    print(f"\n  Performance by {group_dim}:")
    print(f"  {'':18} {'N':>5} {'med_llm_ms':>12} {'med_prompt_c':>13} {'c_per_ok':>10}")
    print(f"  {'-'*18} {'-'*5} {'-'*12} {'-'*13} {'-'*10}")

    for gv in sorted(by_group.keys()):
        rs = by_group[gv]
        n = len(rs)
        llm_ms = sorted([r["total_ms"] for r in rs if r.get("total_ms")])
        prompt_c = sorted([r["prompt_chars"] for r in rs if r.get("prompt_chars")])
        ok_count = sum(1 for r in rs if r.get("ok"))
        med_ms = llm_ms[len(llm_ms) // 2] if llm_ms else 0
        med_pc = prompt_c[len(prompt_c) // 2] if prompt_c else 0
        total_chars = sum(r.get("prompt_chars", 0) for r in rs)
        cpo = total_chars / ok_count if ok_count else float("inf")
        print(f"  {str(gv)[:18]:<18} {n:>5} {med_ms:>11}ms {med_pc:>12}c {cpo:>10.0f}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Unified results analyzer with confidence intervals")
    parser.add_argument("--manifest", required=True, help="Path to manifest.jsonl")
    parser.add_argument("--primary", default="variant",
                        help="Primary dimension for segmentation")
    parser.add_argument("--secondary", nargs="*", default=["model", "domain"],
                        help="Secondary dimensions for cross-tab")
    parser.add_argument("--compare", nargs=2, metavar=("ROW_DIM", "COL_DIM"),
                        help="Show comparison table between two dimensions")
    parser.add_argument("--chi2", nargs="*", default=[],
                        help="Dimensions to chi-square test against accuracy")
    parser.add_argument("--adequacy", action="store_true",
                        help="Show sample adequacy check")
    parser.add_argument("--target-delta", type=float, default=5.0,
                        help="Target detectable delta in pp for adequacy check")
    parser.add_argument("--quality", action="store_true",
                        help="Show SQL quality report")
    parser.add_argument("--perf", action="store_true",
                        help="Show performance/latency report")
    parser.add_argument("--filter", nargs=2, action="append", metavar=("FIELD", "VALUE"),
                        help="Filter records: --filter model qwen3:14b")
    args = parser.parse_args()

    manifest_path = Path(args.manifest)
    if not manifest_path.exists():
        print(f"Not found: {manifest_path}")
        sys.exit(1)

    records = load_manifest(manifest_path)
    print(f"Loaded {len(records)} unique records from {manifest_path.name}")

    # Apply filters
    if args.filter:
        for field, value in args.filter:
            records = [r for r in records if str(r.get(field, "")) == value]
        print(f"After filters: {len(records)} records")

    if not records:
        print("No records after filtering.")
        sys.exit(0)

    # Confidence report
    print_confidence_report(
        records,
        primary_dim=args.primary,
        secondary_dims=args.secondary,
        alpha=0.05,
    )

    # Comparison table
    if args.compare:
        print(f"\n  Comparison table ({args.compare[0]} x {args.compare[1]}):")
        comparison_table(records, args.compare[0], args.compare[1])

    # Chi-square tests
    for dim in args.chi2:
        if len(set(r.get(dim, "?") for r in records)) > 1:
            result = chi2_independence(records, dim)
            sig = "SIGNIFICANT" if result["significant"] else "not significant"
            print(f"\n  Chi-square ({dim}): χ²={result['stat']} p={result['p_value']} ({sig})")

    # Adequacy check
    if args.adequacy:
        total_n = len(records)
        total_ok = sum(1 for r in records if r.get("ok"))
        base_acc = total_ok / total_n if total_n else 0
        dims_checked = [args.primary] + (args.secondary or [])
        print(f"\n  Sample adequacy (target delta={args.target_delta}pp):")
        for dim in dims_checked:
            vals = set(r.get(dim, "?") for r in records)
            n_per_cell = total_n // max(len(vals), 1)
            adq = adequacy_check(n_per_cell, base_acc,
                                 target_delta=args.target_delta / 100)
            status = "OK" if adq["adequate"] else "INSUFFICIENT"
            print(f"  {dim:<18} n/cell={n_per_cell:>4}  "
                  f"req={adq['required_n']:>4}  "
                  f"detectable={adq['detectable_delta_pct']:>5.1f}pp  {status}")

    # Quality
    if args.quality:
        print(f"\n")
        quality_report(records, group_dim=args.primary)

    # Performance
    if args.perf:
        performance_report(records, group_dim=args.primary)


if __name__ == "__main__":
    main()

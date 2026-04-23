"""M_inv — Post-hoc invariant analysis on M6/M7 SQL failures.

For each failed SQL execution, compute a mathematical invariant from the
original data tables and classify the failure as:

  Type A — invariant violated: detectable without GT
             (e.g., result > COUNT(DISTINCT fk1) is mathematically impossible)
  Type B — invariant OK, result just wrong: silent failure
             (model generated plausible-but-incorrect SQL)

No new LLM calls. Reads existing manifests and regenerates data tables
from the same fixture generators used in M6/M7.

Invariants per question type:
  q_having        count <= COUNT(DISTINCT fk1)
  q_above_avg     count <= COUNT(DISTINCT fk1)
  q_filter_entity count <= COUNT(*) in fact
  q_filter_month  numeric <= SUM(metric) total
  q_group_sum     result IS valid entity2 name
  q_e2_most_e1    result IS valid entity2 name
  q_top_e1_best_e2 result IS valid entity2 name
  q_top_e1_best_e2 (extra) result IS valid entity2 name of entity2s linked to top-entity1
"""
from __future__ import annotations
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from run_m6_filter_questions import DOMAIN_CONFIGS


# ---------------------------------------------------------------------------
# Invariant functions
# ---------------------------------------------------------------------------

def _valid_entity_names(tables: dict, cfg: dict, dim_key: str) -> set[str]:
    dim_table = cfg[dim_key]          # e.g. "dim2" -> "produtos"
    name_col = cfg[dim_key.replace("dim", "dim") + "_name_col"]
    return {str(r[name_col]).lower() for r in tables[dim_table]}


def compute_invariant(q_name: str, tables: dict, cfg: dict, executed_result: str) -> dict:
    """Return {type: 'A'|'B'|'unknown', bound: ..., result: ..., reason: ...}"""
    fact = tables[cfg["fact"]]
    fk1 = cfg["fact_fk1"]
    fk2 = cfg["fact_fk2"]
    metric = cfg["numeric_col"]

    try:
        result_val = executed_result.strip() if executed_result else ""

        if q_name in ("q_having", "q_above_avg"):
            bound = len(set(r[fk1] for r in fact))
            try:
                v = int(float(result_val)) if result_val else -1
            except (ValueError, TypeError):
                return {"type": "B", "bound": bound, "result": result_val,
                        "reason": "result_not_parseable"}
            if v > bound:
                return {"type": "A", "bound": bound, "result": v,
                        "reason": f"result {v} > max_possible {bound}"}
            return {"type": "B", "bound": bound, "result": v,
                    "reason": f"result {v} <= bound {bound} but wrong"}

        if q_name == "q_filter_entity":
            bound = len(fact)
            try:
                v = int(float(result_val)) if result_val else -1
            except (ValueError, TypeError):
                return {"type": "B", "bound": bound, "result": result_val,
                        "reason": "result_not_parseable"}
            if v > bound:
                return {"type": "A", "bound": bound, "result": v,
                        "reason": f"result {v} > COUNT(*) {bound}"}
            return {"type": "B", "bound": bound, "result": v,
                    "reason": f"result {v} <= COUNT(*) {bound} but wrong"}

        if q_name == "q_filter_month":
            bound = sum(float(r.get(metric) or 0) for r in fact)
            try:
                v = float(result_val) if result_val else -1
            except (ValueError, TypeError):
                return {"type": "B", "bound": round(bound, 2), "result": result_val,
                        "reason": "result_not_parseable"}
            if v > bound * 1.01:  # 1% tolerance for float rounding
                return {"type": "A", "bound": round(bound, 2), "result": round(v, 2),
                        "reason": f"result {v:.2f} > total_sum {bound:.2f}"}
            return {"type": "B", "bound": round(bound, 2), "result": round(v, 2),
                    "reason": f"result {v:.2f} <= total_sum {bound:.2f} but wrong"}

        if q_name in ("q_group_sum", "q_e2_most_e1"):
            dim2_table = cfg["dim2"]
            name_col = cfg["dim2_name_col"]
            valid = {str(r[name_col]).lower() for r in tables[dim2_table]}
            rv = result_val.lower().strip()
            if rv and rv not in valid:
                return {"type": "A", "bound": f"must be in {list(valid)[:3]}...",
                        "result": result_val,
                        "reason": "hallucinated_entity_name"}
            return {"type": "B", "bound": "valid name", "result": result_val,
                    "reason": "valid name but wrong entity"}

        if q_name == "q_top_e1_best_e2":
            # Tighter invariant: result must be entity2 associated to the busiest entity1
            fk1_counter = Counter(r[fk1] for r in fact)
            top_fk1 = fk1_counter.most_common(1)[0][0]
            valid_fk2s = {r[fk2] for r in fact if r[fk1] == top_fk1}
            dim2_table = cfg["dim2"]
            name_col = cfg["dim2_name_col"]
            valid_names = {str(r[name_col]).lower() for r in tables[dim2_table]
                          if r["id"] in valid_fk2s}
            all_names = {str(r[name_col]).lower() for r in tables[dim2_table]}
            rv = result_val.lower().strip()
            if rv and rv not in all_names:
                return {"type": "A", "bound": "must be valid entity2 name",
                        "result": result_val, "reason": "hallucinated_entity_name"}
            if rv and rv in all_names and rv not in valid_names:
                return {"type": "A", "bound": f"must be entity2 of top entity1",
                        "result": result_val,
                        "reason": "wrong_entity1_scope"}
            return {"type": "B", "bound": "valid entity2 of top entity1",
                    "result": result_val, "reason": "plausible but incorrect"}

    except Exception as e:
        return {"type": "unknown", "bound": "?", "result": executed_result,
                "reason": f"invariant_error:{e}"}

    return {"type": "unknown", "bound": "?", "result": executed_result, "reason": "no_invariant"}


# ---------------------------------------------------------------------------
# Main analysis
# ---------------------------------------------------------------------------

def run_minv() -> None:
    manifests = [
        ("m6",  ROOT / "experiments/results/m6_filter/manifest.jsonl"),
        ("m6b", ROOT / "experiments/results/m6b_having_fix/manifest.jsonl"),
        ("m7",  ROOT / "experiments/results/m7_complex/manifest.jsonl"),
    ]

    all_results = []

    for phase, mpath in manifests:
        if not mpath.exists():
            print(f"[M_inv] {phase} manifest not found, skipping")
            continue

        seen = {}
        for line in mpath.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                r = json.loads(line)
            except Exception:
                continue
            if r["key"] not in seen:
                seen[r["key"]] = r

        records = list(seen.values())
        failures = [r for r in records if not r["ok"]]
        print(f"\n[{phase.upper()}] {len(failures)} failures out of {len(records)}")

        # Preload data tables per (domain, seed)
        tables_cache: dict[tuple, dict] = {}
        for r in failures:
            domain = r.get("domain", "retail")
            seed = r.get("seed", 42)
            n_orders = r.get("n_orders", 100)
            key = (domain, seed, n_orders)
            if key not in tables_cache:
                cfg = DOMAIN_CONFIGS[domain]
                tbls, _ = cfg["fixture"](n_orders=n_orders, seed=seed)
                tables_cache[key] = tbls

        for r in failures:
            domain = r.get("domain", "retail")
            seed = r.get("seed", 42)
            n_orders = r.get("n_orders", 100)
            cfg = DOMAIN_CONFIGS[domain]
            tables = tables_cache[(domain, seed, n_orders)]
            q_name = r.get("question", "?")
            executed = str(r.get("executed_result", ""))

            inv = compute_invariant(q_name, tables, cfg, executed)
            inv_type = inv["type"]

            result_row = {
                "phase": phase, "model": r["model"], "domain": domain,
                "question": q_name, "seed": seed,
                "expected": r.get("expected", "?"),
                "executed": executed,
                "reason_exec": r.get("reason", "?"),
                "inv_type": inv_type,
                "inv_reason": inv["reason"],
                "inv_bound": str(inv["bound"]),
            }
            all_results.append(result_row)

    # -----------------------------------------------------------------------
    # Summary
    # -----------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("=== M_inv Summary — Invariant Classification of Failures ===")
    print("=" * 60)

    total = len(all_results)
    by_type = Counter(r["inv_type"] for r in all_results)
    print(f"\nTotal failures analyzed: {total}")
    print(f"  Type A (invariant violated, detectable without GT): {by_type['A']}  ({by_type['A']/total*100:.0f}%)")
    print(f"  Type B (silent failure — plausible but wrong):      {by_type['B']}  ({by_type['B']/total*100:.0f}%)")
    print(f"  Unknown:                                             {by_type['unknown']}")

    print("\n--- Per question type ---")
    by_q = defaultdict(lambda: Counter())
    for r in all_results:
        by_q[r["question"]][r["inv_type"]] += 1
    for q in sorted(by_q):
        c = by_q[q]
        tot = sum(c.values())
        print(f"  {q:<25}  A={c['A']:>2}  B={c['B']:>2}  ({c['A']/tot*100:.0f}% detectable)")

    print("\n--- Per phase ---")
    by_phase = defaultdict(lambda: Counter())
    for r in all_results:
        by_phase[r["phase"]][r["inv_type"]] += 1
    for ph in sorted(by_phase):
        c = by_phase[ph]
        tot = sum(c.values())
        print(f"  {ph:<8}  A={c['A']:>2}  B={c['B']:>2}  ({c['A']/tot*100:.0f}% detectable)")

    print("\n--- Type A failure details (detectable) ---")
    for r in all_results:
        if r["inv_type"] == "A":
            print(f"  [{r['phase']}/{r['question']}/{r['model'].split(':')[0]}/{r['domain']}]"
                  f"  reason={r['inv_reason']}  result={r['executed']}  bound={r['inv_bound']}")

    print("\n--- Type B failure details (silent) ---")
    by_q_b = defaultdict(list)
    for r in all_results:
        if r["inv_type"] == "B":
            by_q_b[r["question"]].append(r)
    for q, rows in sorted(by_q_b.items()):
        reasons = Counter(r["inv_reason"] for r in rows)
        print(f"  {q}: {len(rows)} silent failures  {dict(reasons)}")

    print()


if __name__ == "__main__":
    run_minv()

"""M8b — Safe-SQL flag combinations: do gains sum or interfere?

M8 tested each flag in isolation (F-Q22). Results:
  safe_having        +70.4pp q_having      +11.1pp top_e1   +0pp  e2_most
  safe_subquery_col  +29.6pp q_having      +14.8pp top_e1   +3.7  e2_most
  safe_name_join     -3.7pp  q_having      +18.5pp top_e1   +11.1 e2_most
  safe_explicit_fk   +0pp    q_having      -11.1pp top_e1   +14.8 e2_most

M8b asks: when we combine flags, do the gains add? Does a negative flag
(safe_explicit_fk) cancel the gains of a positive one when combined?

Variants tested:
  baseline             no flags (reference)
  having_plus_subq     safe_having + safe_subquery_col     (2 positives)
  having_plus_name     safe_having + safe_name_join        (positive + mixed)
  triple_positive      having + subquery_col + name_join   (3 positives, no FK)
  all_flags            all 4 flags                         (kitchen sink)

Design: 3 models × 3 domains × 3 questions × 5 variants × 3 seeds = 405 combos.
"""
from __future__ import annotations
import argparse
import json
import sys
import time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from data_sources import load_dataset
from llm_eval.ollama_client import OllamaClient
from run_m1_codegen import LLM_OPTIONS, PROMPT_TEMPLATE, build_sqlite_from_tables, extract_sql, score_sql
from run_m2_codegen import FEWSHOT_BLOCK, build_payload_stats
from run_m6_filter_questions import DOMAIN_CONFIGS
from run_m8_safe_sql import (
    STYLE_HAVING, STYLE_SUBQUERY_COL, STYLE_NAME_JOIN, STYLE_EXPLICIT_FK,
    build_m8_questions,
)


RESULTS_DIR = ROOT / "experiments" / "results" / "m8b_safe_sql_combos"


# ---------------------------------------------------------------------------
# Combination variants
# ---------------------------------------------------------------------------

COMBO_BLOCKS = {
    "baseline":         "",
    "having_plus_subq": STYLE_HAVING + STYLE_SUBQUERY_COL,
    "having_plus_name": STYLE_HAVING + STYLE_NAME_JOIN,
    "triple_positive":  STYLE_HAVING + STYLE_SUBQUERY_COL + STYLE_NAME_JOIN,
    "all_flags":        STYLE_HAVING + STYLE_SUBQUERY_COL + STYLE_NAME_JOIN + STYLE_EXPLICIT_FK,
}


def build_payload(tables: dict, meta: dict, variant: str) -> str:
    base = build_payload_stats(tables, meta) + "\n" + FEWSHOT_BLOCK
    return base + COMBO_BLOCKS[variant]


# ---------------------------------------------------------------------------
# Manifest I/O
# ---------------------------------------------------------------------------

def _load_completed(manifest_path: Path) -> set[str]:
    if not manifest_path.exists():
        return set()
    out: set[str] = set()
    for line in manifest_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            r = json.loads(line)
        except Exception:
            continue
        if r.get("reason") != "exception":
            out.add(r["key"])
    return out


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run_m8b(
    models: list[str], n_orders: int, domains: list[str],
    seeds: list[int], variants: list[str], endpoint: str,
) -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    manifest_path = RESULTS_DIR / "manifest.jsonl"
    client = OllamaClient(endpoint)
    completed = _load_completed(manifest_path)

    per_state: dict[tuple[str, int], dict] = {}
    for domain in domains:
        cfg = DOMAIN_CONFIGS[domain]
        for seed in seeds:
            tables, meta = load_dataset(cfg["source"], n_orders=n_orders, seed=seed)
            questions, gt = build_m8_questions(cfg, tables)
            conn = build_sqlite_from_tables(tables)
            per_state[(domain, seed)] = {
                "gt": gt, "conn": conn, "questions": questions,
                "tables": tables, "meta": meta, "cfg": cfg,
            }

    combos = []
    for domain in domains:
        for seed in seeds:
            state = per_state[(domain, seed)]
            for model in models:
                for variant in variants:
                    for q_name, q in state["questions"].items():
                        key = f"m8b|{model}|{domain}|{variant}|n{n_orders}|s{seed}|{q_name}"
                        if key not in completed:
                            combos.append({
                                "key": key, "model": model, "domain": domain,
                                "seed": seed, "variant": variant,
                                "q_name": q_name, "q": q,
                            })

    total = len(domains) * len(models) * len(seeds) * len(variants) * 3
    print(f"[M8b] {len(domains)}d x {len(models)}m x {len(variants)}v x 3q x {len(seeds)}s = {total} combos")
    print(f"      {len(combos)} to run, {len(completed)} cached\n")

    t_start = time.time()
    warmed: set[str] = set()
    payload_cache: dict[tuple, str] = {}

    for i, c in enumerate(combos, 1):
        model = c["model"]
        state = per_state[(c["domain"], c["seed"])]
        variant = c["variant"]

        pkey = (c["domain"], c["seed"], variant)
        if pkey not in payload_cache:
            payload_cache[pkey] = build_payload(state["tables"], state["meta"], variant)
        payload = payload_cache[pkey]

        if model not in warmed:
            print(f"  warming {model} ...")
            try:
                client.generate(model, "ok",
                                options={**LLM_OPTIONS, "num_predict": 2, "think": False},
                                timeout=300)
            except Exception as e:
                print(f"  warm failed: {e}", file=sys.stderr)
            warmed.add(model)

        prompt = PROMPT_TEMPLATE.format(payload=payload, question=c["q"]["text"])
        elapsed = time.time() - t_start
        print(f"  [{i}/{len(combos)} el={elapsed:.0f}s] {c['key']}", end=" ", flush=True)

        call_options = {**LLM_OPTIONS, "think": False}
        response, ok, reason, executed, sql, total_ms = "", False, "exception", "", "", 0

        for attempt in (1, 2):
            try:
                result = client.generate(model, prompt, options=call_options)
                response = result["text"]
                total_ms = result.get("total_duration_ns", 0) // 1_000_000
                sql = extract_sql(response)
                ok, reason, executed = score_sql(c["q"], sql, state["conn"], state["gt"])
                print(f"{'OK' if ok else 'NO'} ({reason})")
                break
            except Exception as e:
                es = str(e)
                transient = any(x in es for x in ("RemoteDisconnected", "ConnectionError",
                                                   "ConnectionAborted", "ReadTimeout"))
                if transient and attempt == 1:
                    print(f"TRANSIENT; retry 15s...", flush=True)
                    time.sleep(15)
                    continue
                print(f"ERROR: {e}")
                response = f"ERROR:{e}"
                break

        record = {
            "key": c["key"], "phase": "m8b", "model": model,
            "domain": c["domain"], "variant": variant,
            "question": c["q_name"], "question_key": c["q"]["key"],
            "question_type": c["q"]["type"],
            "seed": c["seed"], "n_orders": n_orders,
            "response": response, "sql": sql, "executed_result": executed,
            "ok": ok, "reason": reason,
            "expected": str(state["gt"][c["q"]["key"]]),
            "prompt_chars": len(prompt), "total_ms": total_ms,
        }
        with open(manifest_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")

    for state in per_state.values():
        state["conn"].close()

    print_summary(manifest_path)


# ---------------------------------------------------------------------------
# Summary: compare combinations to M8 single-flag effects
# ---------------------------------------------------------------------------

# M8 single-flag results (from manifest analysis) — reference for delta
M8_BASELINE = {"q_having": 14.8, "q_top_e1_best_e2": 51.9, "q_e2_most_e1": 74.1}
M8_SINGLE = {
    "safe_having":       {"q_having": 85.2, "q_top_e1_best_e2": 63.0, "q_e2_most_e1": 74.1},
    "safe_subquery_col": {"q_having": 44.4, "q_top_e1_best_e2": 66.7, "q_e2_most_e1": 77.8},
    "safe_name_join":    {"q_having": 11.1, "q_top_e1_best_e2": 70.4, "q_e2_most_e1": 85.2},
    "safe_explicit_fk":  {"q_having": 14.8, "q_top_e1_best_e2": 40.7, "q_e2_most_e1": 88.9},
}


def expected_combo(flags: list[str], q: str) -> float:
    """Expected accuracy if flag effects were independent and additive.
    Uses max of each flag's gain (probabilistic OR, same as binary outcome)."""
    # Additive model: baseline + sum of deltas (capped at 100)
    delta = sum(M8_SINGLE[f][q] - M8_BASELINE[q] for f in flags)
    return max(0.0, min(100.0, M8_BASELINE[q] + delta))


COMBO_FLAGS = {
    "having_plus_subq": ["safe_having", "safe_subquery_col"],
    "having_plus_name": ["safe_having", "safe_name_join"],
    "triple_positive":  ["safe_having", "safe_subquery_col", "safe_name_join"],
    "all_flags":        ["safe_having", "safe_subquery_col", "safe_name_join", "safe_explicit_fk"],
}


def print_summary(manifest_path: Path) -> None:
    if not manifest_path.exists():
        print("[M8b] No records.")
        return
    by_key: dict[str, dict] = {}
    for line in manifest_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        by_key[r["key"]] = r  # last occurrence wins (handles re-runs)
    records = list(by_key.values())

    total = len(records)
    ok_count = sum(r["ok"] for r in records)
    print(f"\n=== M8b Summary ({total} records) ===")
    print(f"  Overall: {ok_count}/{total} = {ok_count/total*100:.1f}%\n")

    by_vq = defaultdict(list)
    for r in records:
        by_vq[(r["variant"], r["question"])].append(r["ok"])

    variants = ["baseline", "having_plus_subq", "having_plus_name", "triple_positive", "all_flags"]
    questions = ["q_having", "q_top_e1_best_e2", "q_e2_most_e1"]

    print("  Observed accuracy vs independent-additive prediction:\n")
    print(f"  {'Variant':<22}  " + "  ".join(f"{q:<24}" for q in questions))
    print(f"  {'-'*22}  " + "  ".join("-" * 24 for _ in questions))

    for v in variants:
        row = f"  {v:<22}"
        for q in questions:
            oks = by_vq.get((v, q), [])
            if not oks:
                row += f"  {'—':<24}"
                continue
            observed = sum(oks) / len(oks) * 100
            if v == "baseline":
                row += f"  {observed:>5.1f}% (baseline)     "
            else:
                flags = COMBO_FLAGS.get(v, [])
                predicted = expected_combo(flags, q)
                diff = observed - predicted
                sign = "+" if diff >= 0 else ""
                row += f"  {observed:>5.1f}% (pred {predicted:>5.1f}, {sign}{diff:+5.1f})  "
        print(row)

    # Also show per-model for q_having
    print("\n  Per-model on q_having:")
    models = sorted(set(r["model"] for r in records))
    print(f"  {'Variant':<22}  " + "  ".join(f"{m[:22]:<22}" for m in models))
    for v in variants:
        row = f"  {v:<22}"
        for m in models:
            oks = [r["ok"] for r in records if r["model"] == m and r["variant"] == v and r["question"] == "q_having"]
            if oks:
                row += f"  {sum(oks)}/{len(oks)} ({sum(oks)/len(oks)*100:.0f}%)          "
            else:
                row += f"  {'—':<22}"
        print(row)

    # Reading guide
    print("\n  Reading the numbers:")
    print("    pred = predicted accuracy if flag effects were independent+additive")
    print("    +X   = combination outperforms additive model (synergy)")
    print("    -X   = combination underperforms additive model (interference)")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="M8b - Safe-SQL combination ablation")
    parser.add_argument("--models", nargs="+",
                        default=["qwen3:14b", "phi4:latest", "qwen2.5-coder:7b"])
    parser.add_argument("--domains", nargs="+", default=["retail", "medical", "financial"])
    parser.add_argument("--seeds", nargs="+", type=int, default=[42, 123, 7])
    parser.add_argument("--variants", nargs="+", default=list(COMBO_BLOCKS.keys()))
    parser.add_argument("--n-orders", type=int, default=100)
    parser.add_argument("--endpoint", default="http://localhost:11434")
    parser.add_argument("--summary", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.summary:
        print_summary(RESULTS_DIR / "manifest.jsonl")
        return

    if args.dry_run:
        for v in args.variants:
            print(f"\n=== {v} ===")
            print(f"  Flags combined: {len(COMBO_BLOCKS[v])} chars of style hints")
            if v in COMBO_FLAGS:
                print(f"  Flags: {COMBO_FLAGS[v]}")
        return

    run_m8b(args.models, args.n_orders, args.domains,
            args.seeds, args.variants, args.endpoint)


if __name__ == "__main__":
    main()

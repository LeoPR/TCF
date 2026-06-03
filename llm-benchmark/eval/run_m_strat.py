"""M-strat — random vs stratified sampling: efeito em accuracy + variância.

Reusa infra de run_m9_adult.py (questions, GT, payload). A diferença é
varrer 2 modos × 5 seeds para medir:

  H1: mean_acc(stratified) ≈ mean_acc(random)
      Esperado: não há diferença significativa em accuracy média
      (stratification não inflate accuracy; só estabiliza)

  H2: std_acc(stratified) < std_acc(random)
      Esperado: stratification reduz variância inter-seed
      (com proporcionalidade preservada, accuracy fica mais consistente)

  H3: Questões sensíveis a class balance (q_count_high_class) têm
      comportamento diferente entre modos.

Design: Adult Census × 3 modelos × 7 questions × 2 modos × 5 seeds = 210 combos.
"""
from __future__ import annotations
import argparse
import json
import statistics
import sys
import time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(ROOT / "scripts"))

from llm_eval.ollama_client import OllamaClient
from run_m1_codegen import (
    LLM_OPTIONS, PROMPT_TEMPLATE, build_sqlite_from_tables,
    extract_sql, score_sql,
)
from run_m9_adult import (
    ADULT_CONFIG, compute_gt_adult, build_questions_adult, build_payload_adult,
)
from data_sources import load_dataset


RESULTS_DIR = ROOT / "experiments" / "results" / "m_strat"


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


def run_m_strat(
    models: list[str], volume: int, seeds: list[int], modes: list[str], endpoint: str,
) -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    manifest_path = RESULTS_DIR / "manifest.jsonl"
    client = OllamaClient(endpoint)
    completed = _load_completed(manifest_path)

    # Pre-load (mode, seed) state
    per_state: dict[tuple, dict] = {}
    for mode in modes:
        stratify_by = "class" if mode == "stratify" else None
        for seed in seeds:
            tables, meta = load_dataset(
                "canonical:adult-census",
                volume=volume, seed=seed,
                stratify_by=stratify_by,
            )
            gt = compute_gt_adult(tables["adult"])
            conn = build_sqlite_from_tables(tables)
            questions = build_questions_adult()
            payload = build_payload_adult(tables, meta)
            per_state[(mode, seed)] = {
                "gt": gt, "conn": conn, "questions": questions,
                "payload": payload, "tables": tables, "meta": meta,
                "stratify_by": stratify_by,
            }

    combos = []
    for mode in modes:
        for seed in seeds:
            state = per_state[(mode, seed)]
            for model in models:
                for q_name, q in state["questions"].items():
                    key = f"mstrat|{model}|{mode}|vol{volume}|s{seed}|{q_name}"
                    if key in completed:
                        continue
                    combos.append({
                        "key": key, "model": model, "mode": mode,
                        "seed": seed, "q_name": q_name, "q": q,
                    })

    total = len(modes) * len(seeds) * len(models) * 7
    print(f"[M-strat] {len(modes)}m x {len(models)}models x 7q x {len(seeds)}s = {total} combos")
    print(f"          {len(combos)} to run, {len(completed)} cached\n")

    # Preview: stratification metrics for first stratified seed
    for mode in modes:
        for seed in seeds[:1]:
            state = per_state[(mode, seed)]
            gt = state["gt"]
            sm = state["meta"].get("_stratification_metrics", [])
            print(f"  mode={mode} seed={seed}: GT count={gt['count']}, count_high_class={gt['count_high_class']}")
            if sm:
                m = sm[0]
                print(f"    stratification: TVD={m['tvd']}, chi2_p={m['chi2_pvalue']}")
            else:
                print(f"    stratification: random (no metrics)")

    print()
    t_start = time.time()
    warmed: set[str] = set()

    for i, c in enumerate(combos, 1):
        model = c["model"]
        state = per_state[(c["mode"], c["seed"])]

        if model not in warmed:
            print(f"  warming {model} ...")
            try:
                client.generate(model, "ok",
                                options={**LLM_OPTIONS, "num_predict": 2, "think": False},
                                timeout=300)
            except Exception as e:
                print(f"  warm failed: {e}", file=sys.stderr)
            warmed.add(model)

        prompt = PROMPT_TEMPLATE.format(payload=state["payload"], question=c["q"]["text"])
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

        strat_metrics = state["meta"].get("_stratification_metrics", [])
        record = {
            "key": c["key"], "phase": "m_strat", "model": model,
            "dataset": "adult-census", "variant": "sql_stats_fs",
            "mode": c["mode"],
            "stratify_by": state["stratify_by"],
            "stratification_metrics": strat_metrics[0] if strat_metrics else None,
            "question": c["q_name"], "question_key": c["q"]["key"],
            "question_type": c["q"]["type"],
            "seed": c["seed"], "volume": volume,
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


def print_summary(manifest_path: Path) -> None:
    if not manifest_path.exists():
        print("[M-strat] No records.")
        return
    by_key: dict[str, dict] = {}
    for line in manifest_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        by_key[r["key"]] = r  # last occurrence wins (handles re-runs)
    records = list(by_key.values())

    total = len(records)
    ok = sum(r["ok"] for r in records)
    print(f"\n=== M-strat Summary ({total} records) ===")
    print(f"  Overall: {ok}/{total} = {ok/total*100:.1f}%\n")

    # Per-mode accuracy + inter-seed variance
    by_mode_seed: dict = defaultdict(lambda: defaultdict(list))
    for r in records:
        by_mode_seed[r["mode"]][r["seed"]].append(r["ok"])

    print("  H1+H2: Accuracy mean and inter-seed std per mode")
    print(f"  {'Mode':<12}  {'mean acc':>10}  {'std (seed)':>12}  {'range':>12}  {'CI 95%':>20}")
    print(f"  {'-'*12}  {'-'*10}  {'-'*12}  {'-'*12}  {'-'*20}")

    mode_results = {}
    for mode, by_seed in by_mode_seed.items():
        per_seed_acc = []
        for seed, oks in sorted(by_seed.items()):
            per_seed_acc.append(sum(oks) / len(oks) * 100)
        mean = statistics.mean(per_seed_acc)
        sd = statistics.stdev(per_seed_acc) if len(per_seed_acc) > 1 else 0.0
        # Wilson CI on overall accuracy across all seeds
        all_oks = [o for oks in by_seed.values() for o in oks]
        from llm_eval.stats import wilson_ci
        lo, hi = wilson_ci(sum(all_oks), len(all_oks))
        mode_results[mode] = {"mean": mean, "std": sd, "per_seed": per_seed_acc, "ci": (lo*100, hi*100)}
        print(f"  {mode:<12}  {mean:>9.1f}%  {sd:>11.2f}  {min(per_seed_acc):>4.0f}-{max(per_seed_acc):<5.0f}%  [{lo*100:>5.1f}%, {hi*100:>5.1f}%]")

    if "random" in mode_results and "stratify" in mode_results:
        d_mean = mode_results["stratify"]["mean"] - mode_results["random"]["mean"]
        d_std = mode_results["stratify"]["std"] - mode_results["random"]["std"]
        print(f"\n  Diff (stratify - random): mean={d_mean:+.2f}pp, std={d_std:+.2f}")
        print(f"  Interpretation:")
        print(f"    H1 (mean random ~ stratify): {'CONFIRM' if abs(d_mean) < 2 else 'REJECT'} (|diff|={abs(d_mean):.2f}pp, threshold=2pp)")
        print(f"    H2 (stratify std < random std): {'CONFIRM' if d_std < 0 else 'REJECT'} (diff={d_std:+.2f})")

    # Per-question per-mode (H3: class-sensitive)
    print(f"\n  H3: Per-question accuracy per mode")
    questions = ["q_count", "q_avg_age", "q_max_age", "q_distinct_workclass",
                 "q_top_education", "q_count_high_class", "q_avg_hours_male"]
    by_qm: dict = defaultdict(lambda: defaultdict(list))
    for r in records:
        by_qm[r["question"]][r["mode"]].append(r["ok"])
    print(f"  {'Question':<25} {'random':>15} {'stratify':>15}")
    for q in questions:
        if q not in by_qm:
            continue
        rand_oks = by_qm[q].get("random", [])
        strat_oks = by_qm[q].get("stratify", [])
        rand_acc = sum(rand_oks)/len(rand_oks)*100 if rand_oks else 0
        strat_acc = sum(strat_oks)/len(strat_oks)*100 if strat_oks else 0
        print(f"  {q:<25} {sum(rand_oks)}/{len(rand_oks)} ({rand_acc:.0f}%)   {sum(strat_oks)}/{len(strat_oks)} ({strat_acc:.0f}%)")

    # Stratification metrics summary (per stratified seed)
    print(f"\n  Stratification quality (per seed):")
    seeds_seen = sorted(set(r["seed"] for r in records if r["mode"] == "stratify"))
    for seed in seeds_seen:
        sm_records = [r for r in records if r["mode"]=="stratify" and r["seed"]==seed and r.get("stratification_metrics")]
        if sm_records:
            m = sm_records[0]["stratification_metrics"]
            print(f"    seed={seed}: TVD={m['tvd']}, JSD={m['jsd']}, chi2_p={m['chi2_pvalue']}")


def main() -> None:
    parser = argparse.ArgumentParser(description="M-strat - random vs stratified")
    parser.add_argument("--models", nargs="+",
                        default=["qwen3:14b", "phi4:latest", "qwen2.5-coder:7b"])
    parser.add_argument("--seeds", nargs="+", type=int, default=[42, 123, 7, 17, 99])
    parser.add_argument("--volume", type=int, default=100)
    parser.add_argument("--modes", nargs="+", default=["random", "stratify"],
                        choices=["random", "stratify"])
    parser.add_argument("--endpoint", default="http://localhost:11434")
    parser.add_argument("--summary", action="store_true")
    args = parser.parse_args()

    if args.summary:
        print_summary(RESULTS_DIR / "manifest.jsonl")
        return

    run_m_strat(args.models, args.volume, args.seeds, args.modes, args.endpoint)


if __name__ == "__main__":
    main()

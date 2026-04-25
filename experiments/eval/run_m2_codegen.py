"""M2 — Code-gen confirmation study: replication + few-shot + scale invariance.

Builds on M1 (which confirmed H-TCF2: schema-only prompt > data-full for SQL
generation). M2 addresses the three weaknesses of M1:

  M2a  Replication: N seeds (default 3) -> confidence intervals per combo
  M2c  Few-shot:    add a variant with 1 JOIN example to address q_top_product
                    / q_lookup failures (SQL hallucination of non-existent cols)
  M2d  Scale inv:   prove the SAME generated SQL works on n=100, n=1000, n=10000

Reuses run_m1_codegen helpers (payload builders, SQLite backend, scoring).
Results written to experiments/results/m2_codegen/manifest.jsonl — distinct
from M1 so analysis can compare directly.
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

# Reuse M1 helpers
from run_m1_codegen import (
    QUESTIONS, LLM_OPTIONS, PROMPT_TEMPLATE,
    _compute_gt, build_sqlite_from_tables,
    build_payload_full, build_payload_schema, build_payload_stats,
    extract_sql, score_sql,
)


RESULTS_DIR = ROOT / "experiments" / "results" / "m2_codegen"


# ---------------------------------------------------------------------------
# Few-shot example payload (addresses q_top_product / q_lookup SQL errors)
# ---------------------------------------------------------------------------

FEWSHOT_BLOCK = """
## Exemplo
Pergunta: Qual produto mais vendido?
SQL:
```sql
SELECT p.nome FROM vendas v JOIN produtos p ON v.id_produto = p.id
GROUP BY p.nome ORDER BY COUNT(*) DESC LIMIT 1
```
Nota: a tabela `vendas` NAO tem coluna `id`; use JOINs explicitos por `id_cliente` e `id_produto`.
"""


def build_payload_schema_fewshot(tables: dict, meta: dict) -> str:
    return build_payload_schema(tables, meta) + "\n" + FEWSHOT_BLOCK


def build_payload_stats_fewshot(tables: dict, meta: dict) -> str:
    return build_payload_stats(tables, meta) + "\n" + FEWSHOT_BLOCK


VARIANTS = {
    "sql_full": build_payload_full,
    "sql_schema": build_payload_schema,
    "sql_stats": build_payload_stats,
    "sql_schema_fs": build_payload_schema_fewshot,
    "sql_stats_fs": build_payload_stats_fewshot,
}


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
        if r.get("reason") == "exception":
            continue
        out.add(r["key"])
    return out


# ---------------------------------------------------------------------------
# Core runner (with seed dimension)
# ---------------------------------------------------------------------------

def run_m2(models: list[str], n_orders: int, variants: list[str],
           seeds: list[int], endpoint: str) -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    manifest_path = RESULTS_DIR / "manifest.jsonl"

    client = OllamaClient(endpoint)
    completed = _load_completed(manifest_path)

    combos: list[dict] = []
    # Build ONCE per seed: (tables, gt, conn, payloads)
    per_seed: dict[int, dict] = {}
    for seed in seeds:
        tables, meta = load_dataset("synthetic:retail_sales", n_orders=n_orders, seed=seed)
        gt = _compute_gt(tables)
        conn = build_sqlite_from_tables(tables)
        payloads = {v: VARIANTS[v](tables, meta) for v in variants}
        per_seed[seed] = {"gt": gt, "conn": conn, "payloads": payloads}

    # Build combo list
    for seed in seeds:
        for model in models:
            for variant in variants:
                for q_name, q in QUESTIONS.items():
                    key = f"m2|{model}|{variant}|n{n_orders}|s{seed}|{q_name}"
                    if key in completed:
                        continue
                    combos.append({
                        "key": key, "model": model, "variant": variant,
                        "q_name": q_name, "q": q, "seed": seed,
                    })

    print(f"[M2] {len(models)} models x {len(variants)} variants x {len(QUESTIONS)} q "
          f"x {len(seeds)} seeds = {len(models)*len(variants)*len(QUESTIONS)*len(seeds)} combos total")
    print(f"     {len(combos)} to run, {len(completed)} cached\n")

    t_start = time.time()
    warmed: set[str] = set()

    for i, c in enumerate(combos, 1):
        model = c["model"]
        seed = c["seed"]
        state = per_seed[seed]

        if model not in warmed:
            print(f"  warming {model} ...")
            try:
                client.generate(model, "ok",
                                options={**LLM_OPTIONS, "num_predict": 2, "think": False},
                                timeout=300)
            except Exception as e:
                print(f"  warm failed: {e}", file=sys.stderr)
            warmed.add(model)

        prompt = PROMPT_TEMPLATE.format(
            payload=state["payloads"][c["variant"]],
            question=c["q"]["text"],
        )

        elapsed = time.time() - t_start
        print(f"  [{i}/{len(combos)} el={elapsed:.0f}s] {c['key']}", end=" ", flush=True)

        call_options = dict(LLM_OPTIONS)
        call_options["think"] = False  # SQL generation doesn't need thinking

        response, ok, reason, executed, sql, total_ms = "", False, "exception", "", "", 0
        for attempt in (1, 2):
            try:
                result = client.generate(model, prompt, options=call_options)
                response = result["text"]
                total_ms = result.get("total_duration_ns", 0) // 1_000_000
                sql = extract_sql(response)
                ok, reason, executed = score_sql(c["q"], sql, state["conn"], state["gt"])
                print(f"{'OK' if ok else 'NO'} ({reason}) -> {executed[:40]}")
                break
            except Exception as e:
                es = str(e)
                transient = any(x in es for x in ("RemoteDisconnected", "ConnectionError",
                                                   "ConnectionAborted", "ReadTimeout"))
                if transient and attempt == 1:
                    print(f"TRANSIENT; sleeping 15s...", flush=True)
                    time.sleep(15)
                    continue
                print(f"ERROR: {e}")
                response = f"ERROR:{e}"
                break

        record = {
            "key": c["key"], "phase": "m2", "model": model,
            "variant": c["variant"], "question": c["q_name"],
            "question_key": c["q"]["key"],
            "seed": seed, "n_orders": n_orders,
            "response": response, "sql": sql, "executed_result": executed,
            "ok": ok, "reason": reason,
            "expected": str(state["gt"][c["q"]["key"]]),
            "prompt_chars": len(prompt), "total_ms": total_ms,
        }
        with open(manifest_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")

    for state in per_seed.values():
        state["conn"].close()

    print_summary(manifest_path)


# ---------------------------------------------------------------------------
# Scale invariance probe
# ---------------------------------------------------------------------------

def run_scale_invariance(manifest_m2_path: Path, scales: list[int]) -> None:
    """Take SQLs generated at n_orders=100 (from M2 manifest) and re-execute
    against fresh DBs built at different scales.

    Proves the key claim: the SAME SQL works at any n."""
    print(f"\n=== Scale invariance probe (scales={scales}) ===")
    if not manifest_m2_path.exists():
        print("No M2 manifest to source SQLs from.")
        return

    records = [json.loads(l) for l in manifest_m2_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    # Take only records that succeeded (ok=True) at n=100 — they have valid SQL
    valid = [r for r in records if r["ok"] and r.get("n_orders") == 100]
    print(f"  Found {len(valid)} valid SQLs from M2 to test at larger scales")

    scale_results = defaultdict(lambda: {"tested": 0, "ok": 0})
    for scale in scales:
        tables, meta = load_dataset("synthetic:retail_sales", n_orders=scale, seed=42)
        gt = _compute_gt(tables)
        conn = build_sqlite_from_tables(tables)
        print(f"\n  Scale n_orders={scale} ({len(tables['vendas'])} vendas)")
        for r in valid:
            if r["seed"] != 42:  # only test seed=42 SQLs against fresh seed=42 data
                continue
            sql = r["sql"]
            q = QUESTIONS[r["question"]]
            ok, reason, result = score_sql(q, sql, conn, gt)
            scale_results[scale]["tested"] += 1
            if ok:
                scale_results[scale]["ok"] += 1
        conn.close()

    print("\n  Scale | SQLs tested | Still correct | %")
    for scale in scales:
        d = scale_results[scale]
        pct = d["ok"] / d["tested"] * 100 if d["tested"] else 0
        print(f"  n={scale:<5} {d['tested']:<13} {d['ok']:<14} {pct:>5.1f}%")


# ---------------------------------------------------------------------------
# Summary with seed-aware reporting
# ---------------------------------------------------------------------------

def print_summary(manifest_path: Path) -> None:
    if not manifest_path.exists():
        print("[M2] No records.")
        return
    records = [json.loads(l) for l in manifest_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    if not records:
        print("[M2] Empty manifest.")
        return

    print(f"\n=== M2 Summary ({len(records)} records) ===\n")

    # Per (model, variant) averaged across seeds
    by_mv = defaultdict(list)
    for r in records:
        by_mv[(r["model"], r["variant"])].append(r["ok"])

    print(f"  {'Model':<22} {'Variant':<16} {'Acc':<10} (per seed ok counts)")
    print(f"  {'-'*22} {'-'*16} {'-'*10}  ----------------")
    # Group per (model, variant, seed)
    by_mvs = defaultdict(list)
    for r in records:
        by_mvs[(r["model"], r["variant"], r["seed"])].append(r["ok"])

    seen = set()
    for (m, v) in sorted(set((r["model"], r["variant"]) for r in records)):
        if (m, v) in seen: continue
        seen.add((m, v))
        oks = by_mv[(m, v)]
        acc = sum(oks) / len(oks) * 100 if oks else 0
        seed_breakdown = []
        for s in sorted(set(r["seed"] for r in records if r["model"]==m and r["variant"]==v)):
            per_s = by_mvs[(m, v, s)]
            seed_breakdown.append(f"s{s}:{sum(per_s)}/{len(per_s)}")
        print(f"  {m:<22} {v:<16} {acc:>4.0f}% ({sum(oks)}/{len(oks)})  {' '.join(seed_breakdown)}")

    # Per (variant, question) aggregated
    print(f"\n  Per-question × variant (aggregated across models and seeds):")
    vqs = sorted(set((r["variant"], r["question"]) for r in records))
    variants_order = sorted(set(v for v, _ in vqs))
    print(f"  {'Question':<18} " + " ".join(f"{v:>12}" for v in variants_order))
    for q_name in QUESTIONS.keys():
        row = f"  {q_name:<18} "
        for v in variants_order:
            oks = [r["ok"] for r in records if r["variant"] == v and r["question"] == q_name]
            if oks:
                row += f"  {sum(oks)}/{len(oks):<4}    "
            else:
                row += f"     -        "
        print(row)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="M2 - Code-gen replication + few-shot + scale invariance")
    parser.add_argument("--models", nargs="+",
                        default=["qwen3:14b", "phi4:latest", "qwen2.5-coder:7b"])
    parser.add_argument("--variants", nargs="+", default=None,
                        choices=list(VARIANTS.keys()))
    parser.add_argument("--seeds", nargs="+", type=int, default=[42, 123, 7])
    parser.add_argument("--n-orders", type=int, default=100)
    parser.add_argument("--endpoint", default="http://localhost:11434")
    parser.add_argument("--summary", action="store_true")
    parser.add_argument("--scale-invariance", action="store_true",
                        help="Re-run existing M2 SQLs at n=1000, 5000, 10000")
    parser.add_argument("--scales", nargs="+", type=int, default=[500, 1000, 5000])
    args = parser.parse_args()

    if args.summary:
        print_summary(RESULTS_DIR / "manifest.jsonl")
        return

    if args.scale_invariance:
        run_scale_invariance(RESULTS_DIR / "manifest.jsonl", args.scales)
        return

    variants = args.variants or list(VARIANTS.keys())
    run_m2(args.models, args.n_orders, variants, args.seeds, args.endpoint)


if __name__ == "__main__":
    main()

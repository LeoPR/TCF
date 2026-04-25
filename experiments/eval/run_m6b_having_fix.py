"""M6b — Targeted fix for q_having universal failure (F-Q19).

Root cause confirmed in M6: models generate one-level aggregation
(COUNT directly on fact table) instead of two-level subquery pattern.
  Wrong:  SELECT COUNT(DISTINCT fk1) FROM fact GROUP BY fk1 HAVING COUNT(*) > N
  Correct: SELECT COUNT(*) FROM (SELECT fk1 FROM fact GROUP BY fk1 HAVING COUNT(*) > N)

Fix: add a HAVING-with-subquery example to the fewshot block.

Design: 3 domains × 3 models × 1 question (q_having only) × 3 seeds = 27 combos.
Saves to experiments/results/m6b_having_fix/manifest.jsonl.
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
from run_m6_filter_questions import DOMAIN_CONFIGS, compute_gt_m6, build_questions_m6


RESULTS_DIR = ROOT / "experiments" / "results" / "m6b_having_fix"

# The fix: extends the base fewshot with a HAVING-subquery example.
HAVING_FEWSHOT_ADDENDUM = """
## Exemplo adicional — HAVING com subquery
Pergunta: Quantos clientes distintos aparecem mais de 5 vezes em vendas?
SQL:
```sql
SELECT COUNT(*) FROM (
  SELECT id_cliente FROM vendas GROUP BY id_cliente HAVING COUNT(*) > 5
)
```
Nota: NAO use COUNT(DISTINCT ...) com HAVING diretamente.
O padrao correto e: subquery que filtra com HAVING, depois COUNT(*) externo.
"""

FEWSHOT_BLOCK_HAVING = FEWSHOT_BLOCK + HAVING_FEWSHOT_ADDENDUM


def build_payload_having_fewshot(tables: dict, meta: dict) -> str:
    return build_payload_stats(tables, meta) + "\n" + FEWSHOT_BLOCK_HAVING


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


def run_m6b(models: list[str], n_orders: int, domains: list[str], seeds: list[int], endpoint: str) -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    manifest_path = RESULTS_DIR / "manifest.jsonl"
    client = OllamaClient(endpoint)
    completed = _load_completed(manifest_path)

    per_state: dict[tuple[str, int], dict] = {}
    for domain in domains:
        cfg = DOMAIN_CONFIGS[domain]
        for seed in seeds:
            tables, meta = load_dataset(cfg["source"], n_orders=n_orders, seed=seed)
            gt = compute_gt_m6(tables, cfg)
            conn = build_sqlite_from_tables(tables)
            questions = build_questions_m6(cfg, gt)
            payload = build_payload_having_fewshot(tables, meta)
            per_state[(domain, seed)] = {
                "gt": gt, "conn": conn,
                "q": questions["q_having"],
                "payload": payload,
            }

    combos = []
    for domain in domains:
        for seed in seeds:
            for model in models:
                key = f"m6b|{model}|{domain}|sql_having_fs|n{n_orders}|s{seed}|q_having"
                if key not in completed:
                    combos.append({"key": key, "model": model, "domain": domain, "seed": seed})

    total = len(domains) * len(models) * len(seeds)
    print(f"[M6b] {len(domains)}d x {len(models)}m x 1q x {len(seeds)}s = {total} combos")
    print(f"      {len(combos)} to run, {len(completed)} cached\n")

    # Dry-run preview
    for domain in domains[:1]:
        state = per_state[(domain, seeds[0])]
        print(f"  [{domain}] GT having_count={state['gt']['having_count']}, "
              f"threshold={state['gt']['having_threshold']}")
        print(f"  Q: {state['q']['text']}\n")

    t_start = time.time()
    warmed: set[str] = set()

    for i, c in enumerate(combos, 1):
        model = c["model"]
        state = per_state[(c["domain"], c["seed"])]

        if model not in warmed:
            print(f"  warming {model} ...")
            try:
                client.generate(model, "ok",
                                options={**LLM_OPTIONS, "num_predict": 2, "think": False},
                                timeout=300)
            except Exception as e:
                print(f"  warm failed: {e}", file=sys.stderr)
            warmed.add(model)

        prompt = PROMPT_TEMPLATE.format(payload=state["payload"], question=state["q"]["text"])
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
                ok, reason, executed = score_sql(state["q"], sql, state["conn"], state["gt"])
                print(f"{'OK' if ok else 'NO'} ({reason}) -> {str(executed)[:40]}")
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
            "key": c["key"], "phase": "m6b", "model": model,
            "domain": c["domain"], "variant": "sql_having_fs",
            "question": "q_having", "question_key": "having_count",
            "question_type": "count", "seed": c["seed"], "n_orders": n_orders,
            "response": response, "sql": sql, "executed_result": executed,
            "ok": ok, "reason": reason,
            "expected": str(state["gt"]["having_count"]),
            "prompt_chars": len(prompt), "total_ms": total_ms,
        }
        with open(manifest_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")

    for state in per_state.values():
        state["conn"].close()

    print_summary(manifest_path)


def print_summary(manifest_path: Path) -> None:
    if not manifest_path.exists():
        print("[M6b] No records.")
        return
    seen: set[str] = set()
    records = []
    for line in manifest_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        if r["key"] not in seen:
            seen.add(r["key"])
            records.append(r)

    total = len(records)
    ok_count = sum(r["ok"] for r in records)
    print(f"\n=== M6b Summary ({total} records) ===")
    print(f"  q_having with HAVING-subquery fewshot: {ok_count}/{total} = {ok_count/total*100:.1f}%")
    print(f"  M6 baseline (no subquery example):     7%")
    print()

    by_model = defaultdict(list)
    by_domain = defaultdict(list)
    for r in records:
        by_model[r["model"]].append(r["ok"])
        by_domain[r["domain"]].append(r["ok"])

    print("  Per model:")
    for m, oks in sorted(by_model.items()):
        print(f"    {m:<30} {sum(oks)}/{len(oks)} = {sum(oks)/len(oks)*100:.0f}%")
    print("  Per domain:")
    for d, oks in sorted(by_domain.items()):
        print(f"    {d:<20} {sum(oks)}/{len(oks)} = {sum(oks)/len(oks)*100:.0f}%")

    print("\n  Failure SQL samples:")
    shown = 0
    for r in records:
        if not r["ok"] and shown < 3:
            print(f"    [{r['model']}/{r['domain']}] expected={r['expected']}")
            print(f"    SQL: {r['sql'][:120]}")
            shown += 1


def main() -> None:
    parser = argparse.ArgumentParser(description="M6b - HAVING subquery fewshot fix")
    parser.add_argument("--models", nargs="+",
                        default=["qwen3:14b", "phi4:latest", "qwen2.5-coder:7b"])
    parser.add_argument("--domains", nargs="+", default=["retail", "medical", "financial"])
    parser.add_argument("--seeds", nargs="+", type=int, default=[42, 123, 7])
    parser.add_argument("--n-orders", type=int, default=100)
    parser.add_argument("--endpoint", default="http://localhost:11434")
    parser.add_argument("--summary", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.summary:
        print_summary(RESULTS_DIR / "manifest.jsonl")
        return

    if args.dry_run:
        from run_m6_filter_questions import compute_gt_m6, build_questions_m6
        for domain in args.domains:
            cfg = DOMAIN_CONFIGS[domain]
            tables, meta = load_dataset(cfg["source"], n_orders=args.n_orders, seed=42)
            gt = compute_gt_m6(tables, cfg)
            questions = build_questions_m6(cfg, gt)
            print(f"\n=== {domain} ===")
            q = questions["q_having"]
            print(f"  {q['text']}")
            print(f"  expected: having_count={gt['having_count']}, threshold={gt['having_threshold']}")
        return

    run_m6b(args.models, args.n_orders, args.domains, args.seeds, args.endpoint)


if __name__ == "__main__":
    main()

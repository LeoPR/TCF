"""M7 — Complex SQL patterns: subquery, nested aggregation, COUNT DISTINCT GROUP BY.

M6 tested L2 complexity (WHERE filter, HAVING). M7 tests L3 complexity:
  q_above_avg      — entity1s with SUM(metric) > global avg of per-entity1 sums (CTE+subquery)
  q_top_e1_best_e2 — for busiest entity1, which entity2 is most frequent? (nested subquery)
  q_e2_most_e1     — entity2 with most distinct entity1s (COUNT DISTINCT in GROUP BY)

These patterns require:
- Two-pass aggregation (aggregate then filter on aggregate)
- Correlated subquery in WHERE
- COUNT(DISTINCT ...) inside GROUP BY

Design: 3 domains × 3 models × 3 questions × 3 seeds = 81 combos.
Variant: sql_stats_fs_m7 (fewshot includes complex SQL examples).
"""
from __future__ import annotations
import argparse
import json
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from llm_eval.ollama_client import OllamaClient
from run_m1_codegen import (
    LLM_OPTIONS, PROMPT_TEMPLATE, build_sqlite_from_tables, extract_sql, score_sql,
)
from run_m2_codegen import FEWSHOT_BLOCK, build_payload_stats
from run_m6_filter_questions import DOMAIN_CONFIGS


RESULTS_DIR = ROOT / "experiments" / "results" / "m7_complex"

# Extended fewshot: adds CTE+subquery and COUNT DISTINCT GROUP BY patterns.
COMPLEX_FEWSHOT_ADDENDUM = """
## Exemplo — subquery com filtro em agregacao
Pergunta: Quantos clientes têm soma de total acima da media de todos os clientes?
SQL:
```sql
WITH por_cliente AS (
  SELECT id_cliente, SUM(total) AS soma FROM vendas GROUP BY id_cliente
)
SELECT COUNT(*) FROM por_cliente
WHERE soma > (SELECT AVG(soma) FROM por_cliente)
```
Nota: use CTE para calcular soma por entidade, depois filtre pelo AVG do CTE.

## Exemplo — subquery aninhada em WHERE
Pergunta: Para o cliente com mais compras, qual produto aparece mais vezes?
SQL:
```sql
SELECT p.nome FROM vendas v
JOIN produtos p ON v.id_produto = p.id
WHERE v.id_cliente = (
  SELECT id_cliente FROM vendas GROUP BY id_cliente ORDER BY COUNT(*) DESC LIMIT 1
)
GROUP BY p.nome ORDER BY COUNT(*) DESC LIMIT 1
```

## Exemplo — COUNT(DISTINCT) em GROUP BY
Pergunta: Qual produto foi comprado por mais clientes distintos?
SQL:
```sql
SELECT p.nome FROM vendas v
JOIN produtos p ON v.id_produto = p.id
GROUP BY p.nome ORDER BY COUNT(DISTINCT v.id_cliente) DESC LIMIT 1
```
"""

M7_FEWSHOT_BLOCK = FEWSHOT_BLOCK + COMPLEX_FEWSHOT_ADDENDUM


def build_payload_m7_fewshot(tables: dict, meta: dict) -> str:
    return build_payload_stats(tables, meta) + "\n" + M7_FEWSHOT_BLOCK


# ---------------------------------------------------------------------------
# Ground truth
# ---------------------------------------------------------------------------

def compute_gt_m7(tables: dict, cfg: dict) -> dict:
    """Compute M7 ground truth: above_avg, top_e1_best_e2, e2_most_e1."""
    dim1_rows = tables[cfg["dim1"]]
    dim2_rows = tables[cfg["dim2"]]
    fact_rows = tables[cfg["fact"]]

    dim1_id_to_name = {r["id"]: r[cfg["dim1_name_col"]] for r in dim1_rows}
    dim2_id_to_name = {r["id"]: r[cfg["dim2_name_col"]] for r in dim2_rows}
    fk1 = cfg["fact_fk1"]
    fk2 = cfg["fact_fk2"]
    metric = cfg["numeric_col"]

    # --- q_above_avg: count entity1s with sum(metric) > avg of per-entity1 sums ---
    per_e1_sum: dict = defaultdict(float)
    for r in fact_rows:
        per_e1_sum[r[fk1]] += float(r.get(metric) or 0)
    sums = list(per_e1_sum.values())
    avg_sum = sum(sums) / len(sums) if sums else 0.0
    above_avg_count = sum(1 for s in sums if s > avg_sum)

    # --- q_top_e1_best_e2: for entity1 with most rows, most frequent entity2 ---
    fk1_counter: Counter = Counter(r[fk1] for r in fact_rows)
    top_fk1 = fk1_counter.most_common(1)[0][0]
    fk2_counter_for_top: Counter = Counter(
        r[fk2] for r in fact_rows if r[fk1] == top_fk1
    )
    top_fk2_for_top = fk2_counter_for_top.most_common(1)[0][0]
    top_e1_best_e2_name = dim2_id_to_name[top_fk2_for_top]
    top_e1_name = dim1_id_to_name[top_fk1]

    # --- q_e2_most_e1: entity2 with most distinct entity1s ---
    e2_e1_sets: dict = defaultdict(set)
    for r in fact_rows:
        e2_e1_sets[r[fk2]].add(r[fk1])
    top_e2_by_e1 = max(e2_e1_sets, key=lambda k: len(e2_e1_sets[k]))
    e2_most_e1_name = dim2_id_to_name[top_e2_by_e1]

    return {
        "above_avg_count": above_avg_count,
        "top_e1_best_e2": top_e1_best_e2_name,
        "e2_most_e1": e2_most_e1_name,
        "top_e1_name": top_e1_name,  # metadata for question wording
        "avg_sum": round(avg_sum, 2),  # metadata for debugging
    }


# ---------------------------------------------------------------------------
# Question wording
# ---------------------------------------------------------------------------

def build_questions_m7(cfg: dict, gt: dict) -> dict:
    ent1 = cfg["label_entity1"]
    ent2 = cfg["label_entity2"]
    metric = cfg["label_metric"]
    fact = cfg["fact"]

    return {
        "q_above_avg": {
            "text": (
                f"Quantos {ent1} distintos têm soma de {metric} em {fact} "
                f"acima da média das somas por {ent1}?"
            ),
            "key": "above_avg_count",
            "type": "count",
        },
        "q_top_e1_best_e2": {
            "text": (
                f"Para o {ent1} com mais registros em {fact}, "
                f"qual é o {ent2} mais frequente?"
            ),
            "key": "top_e1_best_e2",
            "type": "string",
        },
        "q_e2_most_e1": {
            "text": (
                f"Qual {ent2} está associado ao maior número de {ent1} "
                f"distintos em {fact}?"
            ),
            "key": "e2_most_e1",
            "type": "string",
        },
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
        if r.get("reason") != "exception":
            out.add(r["key"])
    return out


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run_m7(models: list[str], n_orders: int, domains: list[str], seeds: list[int], endpoint: str) -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    manifest_path = RESULTS_DIR / "manifest.jsonl"
    client = OllamaClient(endpoint)
    completed = _load_completed(manifest_path)

    per_state: dict[tuple[str, int], dict] = {}
    for domain in domains:
        cfg = DOMAIN_CONFIGS[domain]
        for seed in seeds:
            tables, meta = cfg["fixture"](n_orders=n_orders, seed=seed)
            gt = compute_gt_m7(tables, cfg)
            conn = build_sqlite_from_tables(tables)
            questions = build_questions_m7(cfg, gt)
            payload = build_payload_m7_fewshot(tables, meta)
            per_state[(domain, seed)] = {
                "gt": gt, "conn": conn, "questions": questions,
                "payload": payload, "cfg": cfg,
            }

    combos = []
    for domain in domains:
        for seed in seeds:
            state = per_state[(domain, seed)]
            for model in models:
                for q_name, q in state["questions"].items():
                    key = f"m7|{model}|{domain}|sql_stats_fs_m7|n{n_orders}|s{seed}|{q_name}"
                    if key not in completed:
                        combos.append({
                            "key": key, "model": model, "domain": domain,
                            "seed": seed, "q_name": q_name, "q": q,
                        })

    total = len(domains) * len(models) * len(seeds) * 3
    print(f"[M7] {len(domains)}d x {len(models)}m x 3q x {len(seeds)}s = {total} combos")
    print(f"     {len(combos)} to run, {len(completed)} cached\n")

    for domain in domains[:1]:
        state = per_state[(domain, seeds[0])]
        print(f"  [{domain}] GT preview:")
        for q_name, q in state["questions"].items():
            print(f"    {q_name}: {q['text']}")
            print(f"      expected ({q['key']}): {state['gt'][q['key']]}")
        print()

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
            "key": c["key"], "phase": "m7", "model": model,
            "domain": c["domain"], "variant": "sql_stats_fs_m7",
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
# Summary
# ---------------------------------------------------------------------------

def print_summary(manifest_path: Path) -> None:
    if not manifest_path.exists():
        print("[M7] No records.")
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
    print(f"\n=== M7 Summary ({total} records) ===")
    print(f"  Overall: {ok_count}/{total} = {ok_count/total*100:.1f}%\n")

    questions = ["q_above_avg", "q_top_e1_best_e2", "q_e2_most_e1"]
    models = sorted(set(r["model"] for r in records))

    by_mq = defaultdict(list)
    by_q = defaultdict(list)
    by_model = defaultdict(list)
    by_domain = defaultdict(list)
    for r in records:
        by_mq[(r["model"], r["question"])].append(r["ok"])
        by_q[r["question"]].append(r["ok"])
        by_model[r["model"]].append(r["ok"])
        by_domain[r["domain"]].append(r["ok"])

    print(f"  {'Question':<20} {'M1-M6 baseline':>18} " + " ".join(f"{m[:18]:>20}" for m in models) + "  Agg")
    baselines = {"q_above_avg": "—(new)", "q_top_e1_best_e2": "—(new)", "q_e2_most_e1": "—(new)"}
    print(f"  {'-'*20} {'-'*18} " + " ".join(f"{'':->20}" for _ in models) + "  ---")
    for q in questions:
        row = f"  {q:<20} {baselines[q]:>18}"
        for m in models:
            oks = by_mq[(m, q)]
            row += f"  {sum(oks)}/{len(oks):<3}({sum(oks)/len(oks)*100:>4.0f}%)  " if oks else f"  {'—':>20}"
        agg = by_q[q]
        row += f"  {sum(agg)}/{len(agg)}({sum(agg)/len(agg)*100:.0f}%)" if agg else ""
        print(row)

    print("\n  Per model (all questions):")
    for m, oks in sorted(by_model.items()):
        print(f"    {m:<30} {sum(oks)}/{len(oks)} = {sum(oks)/len(oks)*100:.0f}%")

    print("\n  Per domain (all questions):")
    for d, oks in sorted(by_domain.items()):
        print(f"    {d:<20} {sum(oks)}/{len(oks)} = {sum(oks)/len(oks)*100:.0f}%")

    print("\n  Failure SQL samples (first 3):")
    shown = 0
    for r in records:
        if not r["ok"] and shown < 3:
            print(f"    [{r['model']}/{r['domain']}/{r['question']}] expected={r['expected']}")
            print(f"    SQL: {r['sql'][:150]}")
            shown += 1


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="M7 - Complex SQL: subquery/CTE/COUNT DISTINCT")
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
        for domain in args.domains:
            cfg = DOMAIN_CONFIGS[domain]
            tables, meta = cfg["fixture"](n_orders=args.n_orders, seed=42)
            gt = compute_gt_m7(tables, cfg)
            questions = build_questions_m7(cfg, gt)
            print(f"\n=== {domain} ===")
            for q_name, q in questions.items():
                print(f"  {q_name}: {q['text']}")
                print(f"    expected ({q['key']}): {gt[q['key']]}")
        return

    run_m7(args.models, args.n_orders, args.domains, args.seeds, args.endpoint)


if __name__ == "__main__":
    main()

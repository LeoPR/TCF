"""M6 — Filter/aggregation question types beyond simple analytics.

M1-M5 tested only 7 question types: COUNT(*), TOP by count, DISTINCT,
SUM, MAX-entity, MAX-value, AVG. All are "full-table" queries with no WHERE.

M6 tests whether sql_stats_fs (the M3/M4 winner) generalises to queries
that require:
  q_filter_month   — WHERE month filter (STRFTIME) + SUM
  q_filter_entity  — WHERE on joined entity name + COUNT
  q_having         — GROUP BY + HAVING COUNT(*) > threshold
  q_group_sum      — GROUP BY dim2 + SUM (vs q_top_entity2 which uses COUNT)

Design: 3 domains × 3 models × 4 new questions × 3 seeds = 108 combos.
Variant: sql_stats_fs only (established winner).
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

from tests.fixtures.synthetic_v2 import retail_sales
from tests.fixtures.synthetic_domains import medical_consultations, financial_transactions
from llm_eval.ollama_client import OllamaClient

from run_m1_codegen import (
    LLM_OPTIONS, PROMPT_TEMPLATE,
    build_sqlite_from_tables, extract_sql, score_sql,
)
from run_m2_codegen import build_payload_stats_fewshot


RESULTS_DIR = ROOT / "experiments" / "results" / "m6_filter"

_MONTH_NAMES = {
    "01": "janeiro", "02": "fevereiro", "03": "marco", "04": "abril",
    "05": "maio", "06": "junho", "07": "julho", "08": "agosto",
    "09": "setembro", "10": "outubro", "11": "novembro", "12": "dezembro",
}

DOMAIN_CONFIGS: dict[str, dict] = {
    "retail": {
        "fixture": retail_sales,
        "dim1": "clientes", "dim1_name_col": "nome",
        "dim2": "produtos",  "dim2_name_col": "nome",
        "fact": "vendas",    "fact_fk1": "id_cliente", "fact_fk2": "id_produto",
        "numeric_col": "total",  "date_col": "dt",
        "label_entity1": "cliente", "label_entity2": "produto",
        "label_metric": "total",
    },
    "medical": {
        "fixture": medical_consultations,
        "dim1": "pacientes", "dim1_name_col": "nome",
        "dim2": "medicos",   "dim2_name_col": "nome",
        "fact": "consultas", "fact_fk1": "id_paciente", "fact_fk2": "id_medico",
        "numeric_col": "custo", "date_col": "dt",
        "label_entity1": "paciente", "label_entity2": "medico",
        "label_metric": "custo",
    },
    "financial": {
        "fixture": financial_transactions,
        "dim1": "contas",     "dim1_name_col": "titular",
        "dim2": "categorias", "dim2_name_col": "nome",
        "fact": "transacoes", "fact_fk1": "id_conta", "fact_fk2": "id_categoria",
        "numeric_col": "valor", "date_col": "dt",
        "label_entity1": "titular", "label_entity2": "categoria",
        "label_metric": "valor",
    },
}


# ---------------------------------------------------------------------------
# Extended ground truth
# ---------------------------------------------------------------------------

def compute_gt_m6(tables: dict, cfg: dict) -> dict:
    """Compute M6 ground truth: filter month, filter entity, having, group sum."""
    dim1_rows = tables[cfg["dim1"]]
    dim2_rows = tables[cfg["dim2"]]
    fact_rows = tables[cfg["fact"]]

    dim1_id_to_name = {r["id"]: r[cfg["dim1_name_col"]] for r in dim1_rows}
    dim2_id_to_name = {r["id"]: r[cfg["dim2_name_col"]] for r in dim2_rows}

    date_col = cfg["date_col"]
    metric_col = cfg["numeric_col"]
    fk1 = cfg["fact_fk1"]
    fk2 = cfg["fact_fk2"]

    # --- q_filter_month: month with most rows, sum metric for that month ---
    month_counter: Counter = Counter()
    for r in fact_rows:
        m = r.get(date_col, "")[:7]  # "YYYY-MM"
        if m:
            month_counter[m[:7]] += 1
    top_month_ym = month_counter.most_common(1)[0][0]  # "YYYY-MM"
    top_month_num = top_month_ym.split("-")[1]           # "MM"
    top_month_name = _MONTH_NAMES.get(top_month_num, top_month_num)
    filter_sum = round(sum(
        float(r[metric_col])
        for r in fact_rows
        if r.get(date_col, "")[:7] == top_month_ym and r.get(metric_col)
    ), 2)
    filter_count = sum(1 for r in fact_rows if r.get(date_col, "")[:7] == top_month_ym)

    # --- q_filter_entity: most frequent entity1, count their fact rows ---
    fk1_counter: Counter = Counter(r[fk1] for r in fact_rows)
    top_entity1_id = fk1_counter.most_common(1)[0][0]
    top_entity1_name = dim1_id_to_name.get(top_entity1_id, top_entity1_id)
    filter_entity_count = fk1_counter[top_entity1_id]

    # --- q_having: how many entity1s with count > floor(avg_count) ---
    avg_count = len(fact_rows) / max(len(fk1_counter), 1)
    threshold = max(1, int(avg_count))  # floor of avg, at least 1
    having_count = sum(1 for cnt in fk1_counter.values() if cnt > threshold)

    # --- q_group_sum: entity2 with maximum SUM of metric ---
    dim2_sums: dict[str, float] = defaultdict(float)
    for r in fact_rows:
        if r.get(metric_col):
            dim2_sums[r[fk2]] += float(r[metric_col])
    top_dim2_by_sum_id = max(dim2_sums, key=lambda k: dim2_sums[k])
    top_dim2_by_sum_name = dim2_id_to_name.get(top_dim2_by_sum_id, top_dim2_by_sum_id)

    return {
        "filter_month_num": top_month_num,
        "filter_month_name": top_month_name,
        "filter_month_sum": filter_sum,
        "filter_month_count": filter_count,
        "filter_entity1_name": top_entity1_name,
        "filter_entity1_count": filter_entity_count,
        "having_threshold": threshold,
        "having_count": having_count,
        "group_sum_entity2": top_dim2_by_sum_name,
    }


def build_questions_m6(cfg: dict, gt: dict) -> dict[str, dict]:
    """Build 4 filter/aggregation questions with domain-specific wording."""
    fact = cfg["fact"]
    metric = cfg["label_metric"]
    ent1 = cfg["label_entity1"]
    ent2 = cfg["label_entity2"]
    dim1 = cfg["dim1"]

    month_name = gt["filter_month_name"]
    entity1_name = gt["filter_entity1_name"]
    threshold = gt["having_threshold"]

    return {
        "q_filter_month": {
            "text": (f"Qual e a soma de {metric} em {fact} no mes de {month_name}? "
                     f"Considere apenas registros cujo campo dt comece com o mes correto."),
            "key": "filter_month_sum",
            "type": "numeric",
        },
        "q_filter_entity": {
            "text": (f"Quantas vezes '{entity1_name}' aparece como {ent1} na tabela {fact}? "
                     f"Use a tabela {dim1} para resolver o nome."),
            "key": "filter_entity1_count",
            "type": "count",
        },
        "q_having": {
            "text": (f"Quantos {ent1} distintos aparecem mais de {threshold} "
                     f"vezes na tabela {fact}?"),
            "key": "having_count",
            "type": "count",
        },
        "q_group_sum": {
            "text": (f"Qual {ent2} tem a maior SOMA de {metric} em {fact}? "
                     f"Responda com o nome do {ent2}."),
            "key": "group_sum_entity2",
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
        if r.get("reason") == "exception":
            continue
        out.add(r["key"])
    return out


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run_m6(
    models: list[str],
    n_orders: int,
    domains: list[str],
    seeds: list[int],
    endpoint: str,
) -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    manifest_path = RESULTS_DIR / "manifest.jsonl"

    client = OllamaClient(endpoint)
    completed = _load_completed(manifest_path)

    per_state: dict[tuple[str, int], dict] = {}
    for domain in domains:
        cfg = DOMAIN_CONFIGS[domain]
        for seed in seeds:
            tables, meta = cfg["fixture"](n_orders=n_orders, seed=seed)
            gt = compute_gt_m6(tables, cfg)
            conn = build_sqlite_from_tables(tables)
            questions = build_questions_m6(cfg, gt)
            payload = build_payload_stats_fewshot(tables, meta)
            per_state[(domain, seed)] = {
                "gt": gt, "conn": conn, "questions": questions,
                "payload": payload, "cfg": cfg,
            }

    combos: list[dict] = []
    for domain in domains:
        for seed in seeds:
            state = per_state[(domain, seed)]
            for model in models:
                for q_name, q in state["questions"].items():
                    key = f"m6|{model}|{domain}|sql_stats_fs|n{n_orders}|s{seed}|{q_name}"
                    if key in completed:
                        continue
                    combos.append({
                        "key": key, "model": model, "domain": domain,
                        "seed": seed, "q_name": q_name, "q": q,
                    })

    total = len(domains) * len(seeds) * len(models) * 4
    print(f"[M6] {len(domains)}d x {len(models)}m x 4q x {len(seeds)}s = {total} combos")
    print(f"     {len(combos)} to run, {len(completed)} cached\n")

    # Dry-run: show GT sample
    for domain in domains[:1]:
        cfg = DOMAIN_CONFIGS[domain]
        state = per_state[(domain, seeds[0])]
        print(f"  [{domain}] GT preview: {state['gt']}")
        for q_name, q in state["questions"].items():
            print(f"    {q_name}: {q['text']}")
            print(f"      expected: {state['gt'][q['key']]}")
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

        prompt = PROMPT_TEMPLATE.format(
            payload=state["payload"],
            question=c["q"]["text"],
        )

        elapsed = time.time() - t_start
        print(f"  [{i}/{len(combos)} el={elapsed:.0f}s] {c['key']}", end=" ", flush=True)

        call_options = dict(LLM_OPTIONS)
        call_options["think"] = False

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
                    print(f"TRANSIENT; retry in 15s...", flush=True)
                    time.sleep(15)
                    continue
                print(f"ERROR: {e}")
                response = f"ERROR:{e}"
                break

        record = {
            "key": c["key"], "phase": "m6", "model": model,
            "domain": c["domain"], "variant": "sql_stats_fs",
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
        print("[M6] No records.")
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
    if not records:
        print("[M6] Empty.")
        return

    print(f"\n=== M6 Summary ({len(records)} records) ===\n")

    # Per (model, question)
    by_mq = defaultdict(list)
    for r in records:
        by_mq[(r["model"], r["question"])].append(r["ok"])

    questions = ["q_filter_month", "q_filter_entity", "q_having", "q_group_sum"]
    models = sorted(set(r["model"] for r in records))

    print(f"  {'Question':<18} " + " ".join(f"{m[:20]:>22}" for m in models) + "  Agg")
    print(f"  {'-'*18} " + " ".join(f"{'':->22}" for _ in models) + "  ---")
    by_q = defaultdict(list)
    for r in records:
        by_q[r["question"]].append(r["ok"])
    for q in questions:
        row = f"  {q:<18}"
        for m in models:
            oks = by_mq[(m, q)]
            row += f"  {sum(oks)}/{len(oks):<3} ({sum(oks)/len(oks)*100:>4.0f}%)   " if oks else f"  {'—':>22}"
        agg = by_q[q]
        row += f"  {sum(agg)}/{len(agg)} ({sum(agg)/len(agg)*100:.0f}%)" if agg else ""
        print(row)

    # Compare with M1-M5 baseline (full-table) accuracy
    print(f"\n  M6 vs M3 baseline (sql_stats_fs, same domains+models+seeds):")
    print(f"  M3 (full-table 7 questions):  90%+ across all domains")
    agg_all = [r["ok"] for r in records]
    print(f"  M6 (filter/having 4 questions): {sum(agg_all)/len(agg_all)*100:.1f}% ({sum(agg_all)}/{len(agg_all)})")

    # Per (domain, question)
    print(f"\n  Per domain:")
    domains = sorted(set(r["domain"] for r in records))
    print(f"  {'Question':<18} " + " ".join(f"{d:>12}" for d in domains))
    by_dq = defaultdict(list)
    for r in records:
        by_dq[(r["domain"], r["question"])].append(r["ok"])
    for q in questions:
        row = f"  {q:<18}"
        for d in domains:
            oks = by_dq[(d, q)]
            row += f"  {sum(oks)}/{len(oks):<4}    " if oks else f"  {'—':>12}"
        print(row)

    # Failure mode breakdown
    print(f"\n  Failure modes:")
    by_reason = defaultdict(int)
    for r in records:
        if not r["ok"]:
            by_reason[r["reason"]] += 1
    for reason, n in sorted(by_reason.items(), key=lambda x: -x[1]):
        print(f"    {reason}: {n}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="M6 - Filter/HAVING/GROUP BY question types")
    parser.add_argument("--models", nargs="+",
                        default=["qwen3:14b", "phi4:latest", "qwen2.5-coder:7b"])
    parser.add_argument("--domains", nargs="+", default=["retail", "medical", "financial"],
                        choices=list(DOMAIN_CONFIGS.keys()))
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
            gt = compute_gt_m6(tables, cfg)
            questions = build_questions_m6(cfg, gt)
            print(f"\n=== {domain} ===")
            for q_name, q in questions.items():
                print(f"  {q_name}: {q['text']}")
                print(f"    expected ({q['key']}): {gt[q['key']]}")
        return

    run_m6(args.models, args.n_orders, args.domains, args.seeds, args.endpoint)


if __name__ == "__main__":
    main()

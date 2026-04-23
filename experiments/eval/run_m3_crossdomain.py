"""M3 — Cross-domain validation of H-TCF2.

M2 confirmed that schema+stats+few-shot achieves 100% on retail sales.
M3 verifies the finding transfers to other domains (medical, financial)
using the same best-variant (sql_stats_fs) and same models.

Design:
  3 domains (retail, medical, financial) x 3 models x 3 seeds x 7 questions
  = 189 combos with only the winning variant.

Domains are parametrized via DOMAIN_CONFIGS — same canonical question
structure, with dim/fact table names and numeric column derived per domain.
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

# Reuse helpers from m1/m2
from run_m1_codegen import (
    LLM_OPTIONS, PROMPT_TEMPLATE,
    build_sqlite_from_tables,
    build_payload_stats,
    extract_sql, score_sql,
)
from run_m2_codegen import build_payload_stats_fewshot


RESULTS_DIR = ROOT / "experiments" / "results" / "m3_crossdomain"


# ---------------------------------------------------------------------------
# Domain configs
# ---------------------------------------------------------------------------

DOMAIN_CONFIGS: dict[str, dict] = {
    "retail": {
        "fixture": retail_sales,
        "dim1": "clientes",
        "dim1_name_col": "nome",
        "dim2": "produtos",
        "dim2_name_col": "nome",
        "fact": "vendas",
        "fact_fk1": "id_cliente",  # -> dim1.id
        "fact_fk2": "id_produto",  # -> dim2.id
        "numeric_col": "total",
        "label_entity1": "cliente",    # for q_lookup wording
        "label_entity2": "produto",    # for q_top wording
        "label_metric": "total",       # for q_sum/avg wording
    },
    "medical": {
        "fixture": medical_consultations,
        "dim1": "pacientes",
        "dim1_name_col": "nome",
        "dim2": "medicos",
        "dim2_name_col": "nome",
        "fact": "consultas",
        "fact_fk1": "id_paciente",
        "fact_fk2": "id_medico",
        "numeric_col": "custo",
        "label_entity1": "paciente",
        "label_entity2": "medico",
        "label_metric": "custo",
    },
    "financial": {
        "fixture": financial_transactions,
        "dim1": "contas",
        "dim1_name_col": "titular",     # <- titular, not nome
        "dim2": "categorias",
        "dim2_name_col": "nome",
        "fact": "transacoes",
        "fact_fk1": "id_conta",
        "fact_fk2": "id_categoria",
        "numeric_col": "valor",
        "label_entity1": "titular",
        "label_entity2": "categoria",
        "label_metric": "valor",
    },
}


# ---------------------------------------------------------------------------
# Domain-aware ground truth + question templates
# ---------------------------------------------------------------------------

def compute_gt(tables: dict, cfg: dict) -> dict:
    """Compute ground truth agnostic of domain, using cfg."""
    dim1_rows = tables[cfg["dim1"]]
    dim2_rows = tables[cfg["dim2"]]
    fact_rows = tables[cfg["fact"]]

    dim1_name_of = {r["id"]: r[cfg["dim1_name_col"]] for r in dim1_rows}
    dim2_name_of = {r["id"]: r[cfg["dim2_name_col"]] for r in dim2_rows}

    nums = [float(r[cfg["numeric_col"]]) for r in fact_rows if r.get(cfg["numeric_col"])]
    n = len(fact_rows)

    dim2_counter = Counter(r[cfg["fact_fk2"]] for r in fact_rows)
    top_dim2_id = dim2_counter.most_common(1)[0][0]

    dim1_counter = Counter(r[cfg["fact_fk1"]] for r in fact_rows)
    _ = dim1_counter  # unused except as confound diagnostic

    max_row = max(fact_rows, key=lambda r: float(r[cfg["numeric_col"]]) if r.get(cfg["numeric_col"]) else 0)

    return {
        "count": n,
        "sum_metric": round(sum(nums), 2),
        "avg_metric": round(sum(nums) / n, 2) if n else 0,
        "top_entity2": dim2_name_of.get(top_dim2_id, top_dim2_id),
        "distinct_entity1": len(set(r[cfg["fact_fk1"]] for r in fact_rows)),
        "max_buyer": dim1_name_of.get(max_row[cfg["fact_fk1"]], max_row[cfg["fact_fk1"]]),
        "max_metric_row": float(max_row[cfg["numeric_col"]]) if max_row.get(cfg["numeric_col"]) else 0.0,
    }


def build_questions(cfg: dict) -> dict[str, dict]:
    """Render domain-specific question text + keys."""
    fact = cfg["fact"]
    metric = cfg["label_metric"]
    ent1 = cfg["label_entity1"]
    ent2 = cfg["label_entity2"]
    return {
        "q_count": {
            "text": f"Quantas linhas existem na tabela {fact}?",
            "key": "count", "type": "count",
        },
        "q_top_entity2": {
            "text": f"Qual {ent2} aparece mais vezes em {fact}? Responda com o nome do {ent2}.",
            "key": "top_entity2", "type": "string",
        },
        "q_distinct": {
            "text": f"Quantos {ent1}s distintos aparecem na tabela {fact}?",
            "key": "distinct_entity1", "type": "count",
        },
        "q_sum": {
            "text": f"Qual e a soma de todos os valores da coluna {metric} em {fact}?",
            "key": "sum_metric", "type": "numeric",
        },
        "q_lookup": {
            "text": f"Qual {ent1} realizou o registro individual de maior {metric}? Responda com o nome do {ent1}.",
            "key": "max_buyer", "type": "string",
        },
        "q_lookup_value": {
            "text": f"Qual e o maior valor individual da coluna {metric} em {fact}?",
            "key": "max_metric_row", "type": "numeric",
        },
        "q_avg": {
            "text": f"Qual e a media da coluna {metric} em {fact}?",
            "key": "avg_metric", "type": "numeric",
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

def run_m3(models: list[str], n_orders: int, domains: list[str],
           seeds: list[int], variant: str, endpoint: str) -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    manifest_path = RESULTS_DIR / "manifest.jsonl"

    client = OllamaClient(endpoint)
    completed = _load_completed(manifest_path)

    # Pre-build per (domain, seed): state
    per_state: dict[tuple[str, int], dict] = {}
    for domain in domains:
        cfg = DOMAIN_CONFIGS[domain]
        for seed in seeds:
            tables, meta = cfg["fixture"](n_orders=n_orders, seed=seed)
            gt = compute_gt(tables, cfg)
            conn = build_sqlite_from_tables(tables)
            questions = build_questions(cfg)
            payload_fn = {
                "sql_stats": build_payload_stats,
                "sql_stats_fs": build_payload_stats_fewshot,
            }[variant]
            payload = payload_fn(tables, meta)
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
                    key = f"m3|{model}|{domain}|{variant}|n{n_orders}|s{seed}|{q_name}"
                    if key in completed:
                        continue
                    combos.append({
                        "key": key, "model": model, "domain": domain,
                        "seed": seed, "q_name": q_name, "q": q,
                    })

    total = len(domains) * len(seeds) * len(models) * 7
    print(f"[M3] {len(domains)} domains x {len(models)} models x 7 q x {len(seeds)} seeds "
          f"(variant={variant}) = {total} combos")
    print(f"     {len(combos)} to run, {len(completed)} cached\n")

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
            "key": c["key"], "phase": "m3", "model": model,
            "domain": c["domain"], "variant": variant,
            "question": c["q_name"],
            "question_key": c["q"]["key"],
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


def print_summary(manifest_path: Path) -> None:
    if not manifest_path.exists():
        print("[M3] No records.")
        return
    records = [json.loads(l) for l in manifest_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    if not records:
        print("[M3] Empty manifest.")
        return

    print(f"\n=== M3 Summary ({len(records)} records) ===\n")

    # (model, domain) grid
    print(f"  {'Model':<22} {'Domain':<12} {'Acc':<10}")
    print(f"  {'-'*22} {'-'*12} {'-'*10}")
    by_md = defaultdict(list)
    for r in records:
        by_md[(r["model"], r["domain"])].append(r["ok"])
    for (m, d), oks in sorted(by_md.items()):
        acc = sum(oks) / len(oks) * 100 if oks else 0
        print(f"  {m:<22} {d:<12} {acc:>4.0f}% ({sum(oks)}/{len(oks)})")

    # Per (domain, question)
    print(f"\n  Per-question accuracy by domain (aggregated over models+seeds):")
    domains = sorted(set(r["domain"] for r in records))
    print(f"  {'Question':<18} " + " ".join(f"{d:>12}" for d in domains))
    questions = sorted(set(r["question"] for r in records))
    for q in questions:
        row = f"  {q:<18} "
        for d in domains:
            oks = [r["ok"] for r in records if r["question"] == q and r["domain"] == d]
            if oks:
                row += f"  {sum(oks)}/{len(oks):<4}    "
            else:
                row += f"     -        "
        print(row)


def main() -> None:
    parser = argparse.ArgumentParser(description="M3 - Cross-domain H-TCF2 validation")
    parser.add_argument("--models", nargs="+",
                        default=["qwen3:14b", "phi4:latest", "qwen2.5-coder:7b"])
    parser.add_argument("--domains", nargs="+",
                        default=["retail", "medical", "financial"],
                        choices=list(DOMAIN_CONFIGS.keys()))
    parser.add_argument("--seeds", nargs="+", type=int, default=[42, 123, 7])
    parser.add_argument("--n-orders", type=int, default=100)
    parser.add_argument("--variant", default="sql_stats_fs",
                        choices=["sql_stats", "sql_stats_fs"])
    parser.add_argument("--endpoint", default="http://localhost:11434")
    parser.add_argument("--summary", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.summary:
        print_summary(RESULTS_DIR / "manifest.jsonl")
        return

    if args.dry_run:
        for d in args.domains:
            cfg = DOMAIN_CONFIGS[d]
            tables, meta = cfg["fixture"](n_orders=args.n_orders, seed=42)
            payload = build_payload_stats_fewshot(tables, meta) if args.variant == "sql_stats_fs" else build_payload_stats(tables, meta)
            questions = build_questions(cfg)
            print(f"\n=== {d} payload ({len(payload)} chars) ===")
            print(payload[:900])
            print(f"\n  Sample question (q_top_entity2): {questions['q_top_entity2']['text']}")
            print(f"  GT preview: {compute_gt(tables, cfg)}")
        return

    run_m3(args.models, args.n_orders, args.domains, args.seeds, args.variant, args.endpoint)


if __name__ == "__main__":
    main()

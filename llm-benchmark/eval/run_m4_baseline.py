"""M4 — Baseline format comparison: CSV vs JSON vs TCF.

M3 proved H-TCF2 generalizes (schema+stats+few-shot = 90%+ across domains).
M4 tests whether advantage is TCF-specific or format-agnostic.

Design:
  3 domains x 3 formats (csv, json, tcf) x 3 models x 3 seeds x 7 questions
  = 189 combos per format = 567 total.

TCF payload is reused from M3 (sql_stats_fs). CSV and JSON payloads render
the same schema in their native formats.
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

from data_sources import load_dataset
from llm_eval.ollama_client import OllamaClient

# Reuse helpers from m1/m2/m3
from run_m1_codegen import (
    LLM_OPTIONS, PROMPT_TEMPLATE,
    build_sqlite_from_tables,
    build_payload_stats,
    extract_sql, score_sql,
)
from run_m2_codegen import build_payload_stats_fewshot


RESULTS_DIR = ROOT / "experiments" / "results" / "m4_baseline"


# ---------------------------------------------------------------------------
# Domain configs (reuse from M3)
# ---------------------------------------------------------------------------

DOMAIN_CONFIGS: dict[str, dict] = {
    "retail": {
        "source": "synthetic:retail_sales",
        "dim1": "clientes",
        "dim1_name_col": "nome",
        "dim2": "produtos",
        "dim2_name_col": "nome",
        "fact": "vendas",
        "fact_fk1": "id_cliente",
        "fact_fk2": "id_produto",
        "numeric_col": "total",
        "label_entity1": "cliente",
        "label_entity2": "produto",
        "label_metric": "total",
    },
    "medical": {
        "source": "synthetic:medical_consultations",
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
        "source": "synthetic:financial_transactions",
        "dim1": "contas",
        "dim1_name_col": "titular",
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
# Ground truth (reuse from M3)
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
# Payload builders for CSV, JSON, TCF
# ---------------------------------------------------------------------------

def build_payload_csv(tables: dict, cfg: dict) -> str:
    """CSV format: raw CSV-like representation of schema with sample rows."""
    lines = []

    for table_name in [cfg["dim1"], cfg["dim2"], cfg["fact"]]:
        rows = tables[table_name]
        if not rows:
            continue

        # Header row
        cols = sorted(rows[0].keys())
        lines.append(f"\n## {table_name}.csv")
        lines.append(",".join(cols))

        # Sample rows (first 3)
        for r in rows[:3]:
            values = [str(r.get(c, "")) for c in cols]
            lines.append(",".join(values))

        if len(rows) > 3:
            lines.append(f"... ({len(rows) - 3} more rows)")

    return "\n".join(lines)


def build_payload_json(tables: dict, cfg: dict) -> str:
    """JSON format: JSON schema with sample structure and type hints."""
    schema = {}

    for table_name in [cfg["dim1"], cfg["dim2"], cfg["fact"]]:
        rows = tables[table_name]
        if not rows:
            continue

        # Infer types from first row
        sample = rows[0]
        cols = {}
        for k, v in sample.items():
            if k.startswith("id") or "id" in k:
                cols[k] = "integer"
            elif k in [cfg["numeric_col"], "valor", "custo", "total"]:
                cols[k] = "float"
            else:
                cols[k] = "string"

        schema[table_name] = {
            "columns": cols,
            "sample_row": sample,
            "row_count": len(rows)
        }

    return json.dumps(schema, indent=2, ensure_ascii=False)


def build_payload_tcf(tables: dict, meta: dict) -> str:
    """TCF format: schema + stats + few-shot (M3 winner)."""
    return build_payload_stats_fewshot(tables, meta)


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

def run_m4(models: list[str], n_orders: int, domains: list[str],
           seeds: list[int], formats: list[str], endpoint: str) -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    manifest_path = RESULTS_DIR / "manifest.jsonl"

    client = OllamaClient(endpoint)
    completed = _load_completed(manifest_path)

    # Pre-build per (domain, seed): state
    per_state: dict[tuple[str, int], dict] = {}
    for domain in domains:
        cfg = DOMAIN_CONFIGS[domain]
        for seed in seeds:
            tables, meta = load_dataset(cfg["source"], n_orders=n_orders, seed=seed)
            gt = compute_gt(tables, cfg)
            conn = build_sqlite_from_tables(tables)
            questions = build_questions(cfg)
            payloads = {
                "csv": build_payload_csv(tables, cfg),
                "json": build_payload_json(tables, cfg),
                "tcf": build_payload_tcf(tables, meta),
            }
            per_state[(domain, seed)] = {
                "gt": gt, "conn": conn, "questions": questions,
                "payloads": payloads, "cfg": cfg,
            }

    combos: list[dict] = []
    for domain in domains:
        for seed in seeds:
            state = per_state[(domain, seed)]
            for model in models:
                for fmt in formats:
                    for q_name, q in state["questions"].items():
                        key = f"m4|{model}|{domain}|{fmt}|n{n_orders}|s{seed}|{q_name}"
                        if key in completed:
                            continue
                        combos.append({
                            "key": key, "model": model, "domain": domain,
                            "format": fmt, "seed": seed, "q_name": q_name, "q": q,
                        })

    total = len(domains) * len(seeds) * len(models) * len(formats) * 7
    print(f"[M4] {len(domains)} domains x {len(models)} models x {len(formats)} formats x 7 q x {len(seeds)} seeds "
          f"= {total} combos total")
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
            payload=state["payloads"][c["format"]],
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
            "key": c["key"], "phase": "m4", "model": model,
            "domain": c["domain"], "format": c["format"],
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
        print("[M4] No records.")
        return
    records = [json.loads(l) for l in manifest_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    if not records:
        print("[M4] Empty manifest.")
        return

    print(f"\n=== M4 Summary ({len(records)} records) ===\n")

    # (model, format, domain) grid
    print(f"  {'Model':<22} {'Format':<8} {'Domain':<12} {'Acc':<10}")
    print(f"  {'-'*22} {'-'*8} {'-'*12} {'-'*10}")
    by_mfd = defaultdict(list)
    for r in records:
        by_mfd[(r["model"], r["format"], r["domain"])].append(r["ok"])
    for (m, f, d), oks in sorted(by_mfd.items()):
        acc = sum(oks) / len(oks) * 100 if oks else 0
        print(f"  {m:<22} {f:<8} {d:<12} {acc:>4.0f}% ({sum(oks)}/{len(oks)})")

    # Per format aggregated
    print(f"\n  Per-format accuracy (aggregated over models, domains, seeds):")
    by_format = defaultdict(list)
    for r in records:
        by_format[r["format"]].append(r["ok"])
    for fmt in sorted(by_format.keys()):
        oks = by_format[fmt]
        acc = sum(oks) / len(oks) * 100 if oks else 0
        print(f"  {fmt:<8} {acc:>4.0f}% ({sum(oks)}/{len(oks)})")


def main() -> None:
    parser = argparse.ArgumentParser(description="M4 - Baseline format comparison (CSV vs JSON vs TCF)")
    parser.add_argument("--models", nargs="+",
                        default=["qwen3:14b", "phi4:latest", "qwen2.5-coder:7b"])
    parser.add_argument("--domains", nargs="+",
                        default=["retail", "medical", "financial"],
                        choices=list(DOMAIN_CONFIGS.keys()))
    parser.add_argument("--formats", nargs="+", default=["csv", "json", "tcf"],
                        choices=["csv", "json", "tcf"])
    parser.add_argument("--seeds", nargs="+", type=int, default=[42, 123, 7])
    parser.add_argument("--n-orders", type=int, default=100)
    parser.add_argument("--endpoint", default="http://localhost:11434")
    parser.add_argument("--summary", action="store_true")
    args = parser.parse_args()

    if args.summary:
        print_summary(RESULTS_DIR / "manifest.jsonl")
        return

    run_m4(args.models, args.n_orders, args.domains, args.seeds, args.formats, args.endpoint)


if __name__ == "__main__":
    main()

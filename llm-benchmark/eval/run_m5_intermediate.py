"""M5 — Intermediate execution forms: SQL vs Pandas vs Polars vs CoT-SQL.

M4 showed TCF≈JSON≈96% and CSV≈94% for schema-based SQL generation.
M5 tests whether changing the *execution form* (not just schema format) changes
accuracy, especially for weaker models and join-heavy questions.

Variants tested (all use TCF schema+stats payload as input):
  sql_stats_fs   — LLM → SQL → SQLite            (M3/M4 baseline)
  pandas_fs      — LLM → Pandas Python → exec()
  polars_fs      — LLM → Polars Python → exec()
  cot_sql_fs     — LLM → Chain-of-thought + SQL → SQLite

Design: 5 seeds (vs 3 in M1-M4) → tighter confidence intervals.
  3 domains x 3 models x 4 variants x 7 questions x 5 seeds = 1260 combos.

Records include:
  - Binary correctness (ok)
  - SQL/Python quality scores
  - Execution latency (llm_ms + exec_ms)
  - Prompt token efficiency
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
from llm_eval.python_executor import extract_python, execute_python, score_python_result
from llm_eval.sql_quality import score_sql_quality

from run_m1_codegen import (
    LLM_OPTIONS, PROMPT_TEMPLATE,
    build_sqlite_from_tables,
    extract_sql, score_sql,
)
from run_m2_codegen import build_payload_stats_fewshot


RESULTS_DIR = ROOT / "experiments" / "results" / "m5_intermediate"

DOMAIN_CONFIGS: dict[str, dict] = {
    "retail": {
        "source": "synthetic:retail_sales",
        "dim1": "clientes", "dim1_name_col": "nome",
        "dim2": "produtos", "dim2_name_col": "nome",
        "fact": "vendas", "fact_fk1": "id_cliente", "fact_fk2": "id_produto",
        "numeric_col": "total", "label_entity1": "cliente",
        "label_entity2": "produto", "label_metric": "total",
    },
    "medical": {
        "source": "synthetic:medical_consultations",
        "dim1": "pacientes", "dim1_name_col": "nome",
        "dim2": "medicos", "dim2_name_col": "nome",
        "fact": "consultas", "fact_fk1": "id_paciente", "fact_fk2": "id_medico",
        "numeric_col": "custo", "label_entity1": "paciente",
        "label_entity2": "medico", "label_metric": "custo",
    },
    "financial": {
        "source": "synthetic:financial_transactions",
        "dim1": "contas", "dim1_name_col": "titular",
        "dim2": "categorias", "dim2_name_col": "nome",
        "fact": "transacoes", "fact_fk1": "id_conta", "fact_fk2": "id_categoria",
        "numeric_col": "valor", "label_entity1": "titular",
        "label_entity2": "categoria", "label_metric": "valor",
    },
}


# ---------------------------------------------------------------------------
# Prompt templates (one per execution form)
# ---------------------------------------------------------------------------

PANDAS_PROMPT_TEMPLATE = """\
{payload}

## Forma de resposta: Python / Pandas
Você tem acesso a um dict `tables` onde cada valor é um pandas.DataFrame.
Nomes das tabelas: conforme o schema acima.
Colunas numéricas já foram convertidas para float/int.

## Exemplo
```python
# Qual produto tem mais vendas?
tables["vendas"].merge(tables["produtos"], left_on="id_produto", right_on="id") \\
    .groupby("nome")["id_produto"].count().idxmax()
```
Nota: use merge com left_on/right_on para FK explícito. Última linha = resultado.

## Pergunta
{question}

## Resposta (apenas código Python, sem explicações):
```python
"""

POLARS_PROMPT_TEMPLATE = """\
{payload}

## Forma de resposta: Python / Polars
Você tem acesso a um dict `tables` onde cada valor é um polars.DataFrame.
Colunas numéricas foram convertidas para Float64 quando possível.

## Exemplo
```python
# Qual produto tem mais vendas?
(tables["vendas"]
 .join(tables["produtos"], left_on="id_produto", right_on="id")
 .group_by("nome").agg(pl.count().alias("n"))
 .sort("n", descending=True)
 .head(1)["nome"][0])
```
Nota: use join(left_on=, right_on=) para FK. Última expressão = resultado.

## Pergunta
{question}

## Resposta (apenas código Python/Polars, sem explicações):
```python
"""

COT_SQL_PROMPT_TEMPLATE = """\
{payload}

## Instrução
Antes de escrever o SQL, descreva em 2-3 linhas:
1. Quais tabelas são necessárias e como se relacionam (FK)
2. Qual agregação ou filtro é preciso
Depois emita o SQL final em bloco ```sql```.

## Pergunta
{question}

## Resposta:
"""


# ---------------------------------------------------------------------------
# Ground truth + questions (same as M3)
# ---------------------------------------------------------------------------

def compute_gt(tables: dict, cfg: dict) -> dict:
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
    fact = cfg["fact"]
    metric = cfg["label_metric"]
    ent1 = cfg["label_entity1"]
    ent2 = cfg["label_entity2"]
    return {
        "q_count":       {"text": f"Quantas linhas existem na tabela {fact}?", "key": "count", "type": "count"},
        "q_top_entity2": {"text": f"Qual {ent2} aparece mais vezes em {fact}? Responda com o nome.", "key": "top_entity2", "type": "string"},
        "q_distinct":    {"text": f"Quantos {ent1}s distintos aparecem na tabela {fact}?", "key": "distinct_entity1", "type": "count"},
        "q_sum":         {"text": f"Qual e a soma de todos os valores da coluna {metric} em {fact}?", "key": "sum_metric", "type": "numeric"},
        "q_lookup":      {"text": f"Qual {ent1} realizou o registro individual de maior {metric}? Responda com o nome.", "key": "max_buyer", "type": "string"},
        "q_lookup_value":{"text": f"Qual e o maior valor individual da coluna {metric} em {fact}?", "key": "max_metric_row", "type": "numeric"},
        "q_avg":         {"text": f"Qual e a media da coluna {metric} em {fact}?", "key": "avg_metric", "type": "numeric"},
    }


# ---------------------------------------------------------------------------
# Variant dispatch
# ---------------------------------------------------------------------------

def _prompt_for_variant(variant: str, payload: str, question: str) -> str:
    if variant == "pandas_fs":
        return PANDAS_PROMPT_TEMPLATE.format(payload=payload, question=question)
    elif variant == "polars_fs":
        return POLARS_PROMPT_TEMPLATE.format(payload=payload, question=question)
    elif variant == "cot_sql_fs":
        return COT_SQL_PROMPT_TEMPLATE.format(payload=payload, question=question)
    else:
        return PROMPT_TEMPLATE.format(payload=payload, question=question)


def _execute_variant(
    variant: str,
    response: str,
    q: dict,
    state: dict,
) -> tuple[bool, str, str, str, dict]:
    """Execute the response for the given variant.

    Returns: (ok, reason, executed, code_or_sql, quality_dict)
    """
    tables = state["tables"]
    gt = state["gt"]
    conn = state["conn"]

    if variant in ("sql_stats_fs", "cot_sql_fs"):
        sql = extract_sql(response)
        ok, reason, executed = score_sql(q, sql, conn, gt)
        quality = score_sql_quality(sql, tables, conn).to_dict()
        return ok, reason, executed, sql, quality

    else:  # pandas_fs / polars_fs
        lib = "polars" if variant == "polars_fs" else "pandas"
        code = extract_python(response)
        result_str, error, exec_ms = execute_python(code, tables, library=lib)
        if error:
            return False, f"exec_error:{error[:60]}", "", code, {"exec_ms": exec_ms}
        ok, reason, executed = score_python_result(q, result_str, gt)
        return ok, reason, executed, code, {"exec_ms": exec_ms}


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

def run_m5(
    models: list[str],
    n_orders: int,
    domains: list[str],
    seeds: list[int],
    variants: list[str],
    endpoint: str,
) -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    manifest_path = RESULTS_DIR / "manifest.jsonl"

    client = OllamaClient(endpoint)
    completed = _load_completed(manifest_path)

    # Pre-build state per (domain, seed)
    per_state: dict[tuple[str, int], dict] = {}
    for domain in domains:
        cfg = DOMAIN_CONFIGS[domain]
        for seed in seeds:
            tables, meta = load_dataset(cfg["source"], n_orders=n_orders, seed=seed)
            gt = compute_gt(tables, cfg)
            conn = build_sqlite_from_tables(tables)
            questions = build_questions(cfg)
            payload = build_payload_stats_fewshot(tables, meta)
            per_state[(domain, seed)] = {
                "gt": gt, "conn": conn, "questions": questions,
                "payload": payload, "cfg": cfg, "tables": tables,
            }

    combos: list[dict] = []
    for domain in domains:
        for seed in seeds:
            state = per_state[(domain, seed)]
            for model in models:
                for variant in variants:
                    for q_name, q in state["questions"].items():
                        key = f"m5|{model}|{domain}|{variant}|n{n_orders}|s{seed}|{q_name}"
                        if key in completed:
                            continue
                        combos.append({
                            "key": key, "model": model, "domain": domain,
                            "variant": variant, "seed": seed,
                            "q_name": q_name, "q": q,
                        })

    total = len(domains) * len(seeds) * len(models) * len(variants) * 7
    print(f"[M5] {len(domains)}d x {len(models)}m x {len(variants)}v x 7q x {len(seeds)}s = {total} combos")
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

        prompt = _prompt_for_variant(c["variant"], state["payload"], c["q"]["text"])
        elapsed = time.time() - t_start
        print(f"  [{i}/{len(combos)} el={elapsed:.0f}s] {c['key']}", end=" ", flush=True)

        call_options = dict(LLM_OPTIONS)
        call_options["think"] = False

        response, ok, reason, executed, code_or_sql, quality = "", False, "exception", "", "", {}
        total_ms = 0

        for attempt in (1, 2):
            try:
                result = client.generate(model, prompt, options=call_options)
                response = result["text"]
                total_ms = result.get("total_duration_ns", 0) // 1_000_000
                ok, reason, executed, code_or_sql, quality = _execute_variant(
                    c["variant"], response, c["q"], state
                )
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
            "key": c["key"], "phase": "m5", "model": model,
            "domain": c["domain"], "variant": c["variant"],
            "question": c["q_name"], "question_key": c["q"]["key"],
            "question_type": c["q"]["type"],
            "seed": c["seed"], "n_orders": n_orders,
            "response": response, "code": code_or_sql,
            "executed_result": executed,
            "ok": ok, "reason": reason,
            "expected": str(state["gt"][c["q"]["key"]]),
            "prompt_chars": len(prompt),
            "total_ms": total_ms,
            "quality": quality,
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
        print("[M5] No records.")
        return
    records = [json.loads(l) for l in manifest_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    if not records:
        print("[M5] Empty.")
        return

    # Deduplicate by key (last occurrence wins — handles re-runs after Ollama crashes)
    by_key: dict[str, dict] = {}
    for r in records:
        by_key[r["key"]] = r
    records = list(by_key.values())

    print(f"\n=== M5 Summary ({len(records)} records) ===\n")

    # Per (variant, model)
    by_vm = defaultdict(list)
    for r in records:
        by_vm[(r["variant"], r["model"])].append(r["ok"])
    variants = sorted(set(r["variant"] for r in records))
    models = sorted(set(r["model"] for r in records))

    print(f"  {'Variant':<16} " + " ".join(f"{m[:18]:>20}" for m in models))
    print(f"  {'-'*16} " + " ".join(f"{'':->20}" for _ in models))
    for v in variants:
        row = f"  {v:<16}"
        for m in models:
            oks = by_vm[(v, m)]
            if oks:
                acc = sum(oks) / len(oks) * 100
                row += f"  {acc:>5.1f}% ({sum(oks)}/{len(oks)})"
            else:
                row += f"  {'—':>16}"
        print(row)

    # Per question type
    print(f"\n  Per question type x variant (agg over models+domains+seeds):")
    q_types = sorted(set(r["question"] for r in records))
    print(f"  {'Question':<18} " + " ".join(f"{v:>14}" for v in variants))
    by_qv = defaultdict(list)
    for r in records:
        by_qv[(r["question"], r["variant"])].append(r["ok"])
    for q in q_types:
        row = f"  {q:<18}"
        for v in variants:
            oks = by_qv[(q, v)]
            row += f"  {sum(oks)}/{len(oks):<4}      " if oks else f"  {'—':>14}"
        print(row)

    # Quality scores (SQL variants)
    sql_records = [r for r in records if r["variant"] in ("sql_stats_fs", "cot_sql_fs")
                   and r.get("quality") and r["quality"].get("quality_score") is not None]
    if sql_records:
        print(f"\n  SQL quality scores (structural, where available):")
        by_v = defaultdict(list)
        for r in sql_records:
            by_v[r["variant"]].append(r["quality"]["quality_score"])
        for v, scores in sorted(by_v.items()):
            avg_q = sum(scores) / len(scores)
            print(f"  {v:<18} avg quality_score={avg_q:.3f} (n={len(scores)})")

    # Latency
    print(f"\n  Median LLM latency (ms) per variant:")
    by_v_ms = defaultdict(list)
    for r in records:
        if r.get("total_ms"):
            by_v_ms[r["variant"]].append(r["total_ms"])
    for v in variants:
        ms = sorted(by_v_ms[v])
        if ms:
            med = ms[len(ms) // 2]
            print(f"  {v:<18} {med:>8} ms  (n={len(ms)})")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="M5 - Intermediate execution forms")
    parser.add_argument("--models", nargs="+",
                        default=["qwen3:14b", "phi4:latest", "qwen2.5-coder:7b"])
    parser.add_argument("--domains", nargs="+", default=["retail", "medical", "financial"],
                        choices=list(DOMAIN_CONFIGS.keys()))
    parser.add_argument("--variants", nargs="+",
                        default=["sql_stats_fs", "pandas_fs", "polars_fs", "cot_sql_fs"],
                        choices=["sql_stats_fs", "pandas_fs", "polars_fs", "cot_sql_fs"])
    parser.add_argument("--seeds", nargs="+", type=int, default=[42, 123, 7, 17, 99])
    parser.add_argument("--n-orders", type=int, default=100)
    parser.add_argument("--endpoint", default="http://localhost:11434")
    parser.add_argument("--summary", action="store_true")
    args = parser.parse_args()

    if args.summary:
        print_summary(RESULTS_DIR / "manifest.jsonl")
        return

    run_m5(args.models, args.n_orders, args.domains, args.seeds, args.variants, args.endpoint)


if __name__ == "__main__":
    main()

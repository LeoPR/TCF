"""M9 — Pipeline B integration: replicate M3 protocol on canonical TPC-H.

All M1-M8 ran on synthetic fixtures (tests/fixtures/synthetic_v2.py +
synthetic_domains.py). Pipeline B (datasets/canonical/ + DatasetReader +
Shaper) exists and has Z:/tcf-data/ with real TPC-H and Adult Census data,
but was never integrated into M-series.

This experiment tests whether the M3 protocol (sql_stats_fs, 7 question
types, 3 models) produces comparable accuracy when fed real TPC-H data
via DatasetReader, using the partsupp/part/supplier star topology as a
direct analog to synthetic retail's vendas/produtos/clientes.

Topology analog:
  M3 synthetic retail     M9 canonical TPC-H
  ─────────────────────   ──────────────────────
  vendas    (fact)        partsupp    (fact, 8000 rows)
  produtos  (dim2)        part        (dim2, 2000 rows)
  clientes  (dim1)        supplier    (dim1, 100 rows)
  id_produto + id_cliente ps_partkey + ps_suppkey

Design: 1 dataset × 3 models × 7 questions × 3 seeds = 63 combos.
Uses FK-preserving sampling (volume=100 on fact, then filter dims).
Same FEWSHOT_BLOCK as M3 — tests pattern transfer across domains and
column naming conventions.
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
sys.path.insert(0, str(ROOT / "scripts"))

from llm_eval.ollama_client import OllamaClient
from run_m1_codegen import (
    LLM_OPTIONS, PROMPT_TEMPLATE, build_sqlite_from_tables,
    extract_sql, score_sql, _coerce_value, _detect_column_type,
)
from run_m2_codegen import FEWSHOT_BLOCK

from data_sources import load_dataset


RESULTS_DIR = ROOT / "experiments" / "results" / "m9_canonical"


# ---------------------------------------------------------------------------
# Canonical dataset configs — star-topology mapping for M3 protocol
# ---------------------------------------------------------------------------

CANONICAL_CONFIGS: dict[str, dict] = {
    "tpch-sf001": {
        "tables": ["partsupp", "part", "supplier"],
        "dim1": "supplier", "dim1_id_col": "s_suppkey", "dim1_name_col": "s_name",
        "dim2": "part",     "dim2_id_col": "p_partkey", "dim2_name_col": "p_name",
        "fact": "partsupp", "fact_fk1": "ps_suppkey", "fact_fk2": "ps_partkey",
        "numeric_col": "ps_supplycost",
        "label_entity1": "supplier",
        "label_entity2": "part",
        "label_metric": "ps_supplycost",
    },
}


# ---------------------------------------------------------------------------
# FK-preserving subset loader
# ---------------------------------------------------------------------------

def load_canonical_subset(dataset_name: str, volume: int, seed: int) -> tuple[dict, dict]:
    """Load canonical dataset via data_sources.load_dataset (Shaper-backed).

    Delegates to the unified data manager. Shaper's fk_preserving strategy
    handles the same FK-preserving sampling that was previously inline.
    """
    cfg = CANONICAL_CONFIGS[dataset_name]
    return load_dataset(
        f"canonical:{dataset_name}",
        volume=volume,
        seed=seed,
        schema=cfg["tables"],
        fact_table=cfg["fact"],
    )


# ---------------------------------------------------------------------------
# Ground truth (M3-equivalent question set)
# ---------------------------------------------------------------------------

def compute_gt_m9(tables: dict, cfg: dict) -> dict:
    fact = tables[cfg["fact"]]
    dim1 = tables[cfg["dim1"]]
    dim2 = tables[cfg["dim2"]]

    dim1_id_to_name = {r[cfg["dim1_id_col"]]: r[cfg["dim1_name_col"]] for r in dim1}
    dim2_id_to_name = {r[cfg["dim2_id_col"]]: r[cfg["dim2_name_col"]] for r in dim2}

    fk1 = cfg["fact_fk1"]
    fk2 = cfg["fact_fk2"]
    metric = cfg["numeric_col"]

    metrics = [float(r[metric]) for r in fact if r[metric] is not None]
    n = len(fact)

    fk2_counter: Counter = Counter(r[fk2] for r in fact)
    top_fk2 = fk2_counter.most_common(1)[0][0]

    max_row = max(fact, key=lambda r: float(r[metric]) if r[metric] is not None else 0)
    max_fk1 = max_row[fk1]

    return {
        "count": n,
        "sum_metric": round(sum(metrics), 2),
        "avg_metric": round(sum(metrics) / n, 2) if n else 0,
        "top_entity2": dim2_id_to_name.get(top_fk2, top_fk2),
        "distinct_entity1": len({r[fk1] for r in fact}),
        "max_entity1": dim1_id_to_name.get(max_fk1, max_fk1),
        "max_metric_value": float(max_row[metric]) if max_row[metric] is not None else 0.0,
    }


def build_questions_m9(cfg: dict) -> dict:
    ent1 = cfg["label_entity1"]
    ent2 = cfg["label_entity2"]
    metric = cfg["label_metric"]
    fact = cfg["fact"]

    return {
        "q_count": {
            "text": f"Quantas linhas existem na tabela {fact}?",
            "key": "count", "type": "count",
        },
        "q_top_product": {
            "text": f"Qual {ent2} aparece mais vezes em {fact}? Responda com o nome do {ent2}.",
            "key": "top_entity2", "type": "string",
        },
        "q_distinct": {
            "text": f"Quantos {ent1} distintos aparecem na tabela {fact}?",
            "key": "distinct_entity1", "type": "count",
        },
        "q_sum": {
            "text": f"Qual e a soma de todos os valores da coluna {metric} em {fact}?",
            "key": "sum_metric", "type": "numeric",
        },
        "q_lookup": {
            "text": f"Qual {ent1} tem o maior valor individual de {metric} em {fact}? Responda com o nome.",
            "key": "max_entity1", "type": "string",
        },
        "q_lookup_value": {
            "text": f"Qual e o maior valor individual de {metric} em {fact}?",
            "key": "max_metric_value", "type": "numeric",
        },
        "q_avg": {
            "text": f"Qual e a media da coluna {metric} em {fact}?",
            "key": "avg_metric", "type": "numeric",
        },
    }


# ---------------------------------------------------------------------------
# Payload builder — uses canonical FK metadata (not the heuristic id_X pattern)
# ---------------------------------------------------------------------------

def compute_column_stats_canonical(tables: dict, tcf_metadata: dict) -> str:
    """Stats with PK/FK annotations from canonical metadata.json."""
    lines = []
    tables_meta = tcf_metadata.get("tables", {})

    for tname, rows in tables.items():
        if not rows:
            continue
        t_meta = tables_meta.get(tname, {})
        pk_cols = set(t_meta.get("pk", []))
        fk_map = t_meta.get("fk", {})

        lines.append(f"\n### {tname} ({len(rows)} rows)")
        for col in rows[0].keys():
            raw_values = [r.get(col) for r in rows]
            ctype = _detect_column_type(raw_values)
            coerced = [_coerce_value(v) for v in raw_values]
            pk_tag = " PK" if col in pk_cols else ""
            fk_tag = f" [FK -> {fk_map[col]}]" if col in fk_map else ""

            if ctype in ("INTEGER", "REAL"):
                nums = [float(v) for v in coerced
                        if isinstance(v, (int, float)) and not isinstance(v, bool)]
                if not nums:
                    lines.append(f"  {col} {ctype}{pk_tag}{fk_tag}")
                    continue
                mn, mx, avg = min(nums), max(nums), sum(nums) / len(nums)
                card = len(set(nums))
                fmt = "{:.0f}" if ctype == "INTEGER" else "{:.2f}"
                lines.append(
                    f"  {col} {ctype}{pk_tag}{fk_tag}, range=[{fmt.format(mn)}, {fmt.format(mx)}], "
                    f"mean={avg:.2f}, cardinality={card}"
                )
            else:
                uniq = list(dict.fromkeys(str(v) for v in coerced if v is not None))
                card = len(uniq)
                sample = ", ".join(uniq[:3])
                lines.append(f"  {col} TEXT{pk_tag}{fk_tag}, cardinality={card}, samples=[{sample}]")
        lines.append("")
    return "\n".join(lines)


def build_payload_canonical(tables: dict, meta: dict) -> str:
    return "## Schema + Stats\n" + compute_column_stats_canonical(tables, meta) + "\n" + FEWSHOT_BLOCK


# ---------------------------------------------------------------------------
# Manifest I/O + Runner (identical shape to M3)
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


def run_m9(
    models: list[str], volume: int, datasets: list[str],
    seeds: list[int], endpoint: str,
) -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    manifest_path = RESULTS_DIR / "manifest.jsonl"
    client = OllamaClient(endpoint)
    completed = _load_completed(manifest_path)

    per_state: dict[tuple[str, int], dict] = {}
    for dataset in datasets:
        cfg = CANONICAL_CONFIGS[dataset]
        for seed in seeds:
            tables, meta = load_canonical_subset(dataset, volume, seed)
            gt = compute_gt_m9(tables, cfg)
            conn = build_sqlite_from_tables(tables)
            questions = build_questions_m9(cfg)
            payload = build_payload_canonical(tables, meta)
            per_state[(dataset, seed)] = {
                "gt": gt, "conn": conn, "questions": questions,
                "payload": payload, "cfg": cfg,
            }

    combos = []
    for dataset in datasets:
        for seed in seeds:
            state = per_state[(dataset, seed)]
            for model in models:
                for q_name, q in state["questions"].items():
                    key = f"m9|{model}|{dataset}|sql_stats_fs|vol{volume}|s{seed}|{q_name}"
                    if key in completed:
                        continue
                    combos.append({
                        "key": key, "model": model, "dataset": dataset,
                        "seed": seed, "q_name": q_name, "q": q,
                    })

    total = len(datasets) * len(seeds) * len(models) * 7
    print(f"[M9] {len(datasets)}d x {len(models)}m x 7q x {len(seeds)}s = {total} combos")
    print(f"     {len(combos)} to run, {len(completed)} cached\n")

    for dataset in datasets[:1]:
        state = per_state[(dataset, seeds[0])]
        cfg = state["cfg"]
        tables = {cfg["fact"]: state["gt"]["count"]}
        print(f"  [{dataset}] seed={seeds[0]} volume={volume}")
        print(f"    GT preview: {state['gt']}")
        print()

    t_start = time.time()
    warmed: set[str] = set()

    for i, c in enumerate(combos, 1):
        model = c["model"]
        state = per_state[(c["dataset"], c["seed"])]

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
            "key": c["key"], "phase": "m9", "model": model,
            "dataset": c["dataset"], "variant": "sql_stats_fs",
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


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

def print_summary(manifest_path: Path) -> None:
    if not manifest_path.exists():
        print("[M9] No records.")
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
    ok = sum(r["ok"] for r in records)
    print(f"\n=== M9 Summary ({total} records) ===")
    print(f"  Overall canonical: {ok}/{total} = {ok/total*100:.1f}%")
    print(f"  M3 synthetic baseline (reference): 90-95% (sql_stats_fs, 3 domains)\n")

    questions = ["q_count", "q_sum", "q_avg", "q_distinct",
                 "q_top_product", "q_lookup", "q_lookup_value"]
    models = sorted(set(r["model"] for r in records))

    by_mq = defaultdict(list)
    by_q = defaultdict(list)
    for r in records:
        by_mq[(r["model"], r["question"])].append(r["ok"])
        by_q[r["question"]].append(r["ok"])

    print(f"  {'Question':<18} " + " ".join(f"{m[:20]:>22}" for m in models) + "  Agg")
    print(f"  {'-'*18} " + " ".join(f"{'':->22}" for _ in models) + "  ---")
    for q in questions:
        row = f"  {q:<18}"
        for m in models:
            oks = by_mq.get((m, q), [])
            if oks:
                row += f"  {sum(oks)}/{len(oks):<3} ({sum(oks)/len(oks)*100:>4.0f}%)   "
            else:
                row += f"  {'—':>22}"
        agg = by_q[q]
        row += f"  {sum(agg)}/{len(agg)} ({sum(agg)/len(agg)*100:.0f}%)" if agg else ""
        print(row)

    print("\n  Failure samples (first 3):")
    shown = 0
    for r in records:
        if not r["ok"] and shown < 3:
            print(f"    [{r['question']}/{r['model'].split(':')[0]}/{r['dataset']}]"
                  f" expected={r['expected']} got={r['executed_result'][:40]}")
            print(f"    SQL: {r['sql'][:160]}")
            shown += 1


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="M9 - Canonical dataset via Pipeline B")
    parser.add_argument("--models", nargs="+",
                        default=["qwen3:14b", "phi4:latest", "qwen2.5-coder:7b"])
    parser.add_argument("--datasets", nargs="+", default=["tpch-sf001"],
                        choices=list(CANONICAL_CONFIGS.keys()))
    parser.add_argument("--seeds", nargs="+", type=int, default=[42, 123, 7])
    parser.add_argument("--volume", type=int, default=100)
    parser.add_argument("--endpoint", default="http://localhost:11434")
    parser.add_argument("--summary", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.summary:
        print_summary(RESULTS_DIR / "manifest.jsonl")
        return

    if args.dry_run:
        for dataset in args.datasets:
            cfg = CANONICAL_CONFIGS[dataset]
            tables, meta = load_canonical_subset(dataset, args.volume, 42)
            gt = compute_gt_m9(tables, cfg)
            questions = build_questions_m9(cfg)
            print(f"\n=== {dataset} (volume={args.volume}, seed=42) ===")
            print(f"Tables loaded: {[(k, len(v)) for k, v in tables.items()]}")
            print(f"GT: {gt}")
            for q_name, q in questions.items():
                print(f"  {q_name}: {q['text']}")
            print()
            payload = build_payload_canonical(tables, meta)
            print(f"Payload length: {len(payload)} chars")
            print(f"--- Payload preview (first 800 chars) ---")
            print(payload[:800])
        return

    run_m9(args.models, args.volume, args.datasets, args.seeds, args.endpoint)


if __name__ == "__main__":
    main()

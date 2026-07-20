"""M9-Adult — H-TCF2 protocol on Adult Census (single-table canonical).

Complement to run_m9_canonical.py (TPC-H). Adult Census has only 1 table
(no JOINs), so question types differ from M9-TPCH but the protocol
(sql_stats_fs, 3 models, manifest format) is the same for direct
comparability with M9 and M3.

Hypothesis: schema-carrier + SQL accuracy is preserved on a real-world
single-table dataset with mixed types and naming conventions
(hyphen-cased columns: hours-per-week, education-num, etc.).

Uses stratified sampling on `class` column to maintain population
representativeness (76.1% <=50K vs 23.9% >50K). Records stratification
metrics in manifest.

Design: 1 dataset × 3 models × 7 questions × 3 seeds = 63 combos.
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
from llm_eval.question_naturalness import (
    NaturalnessLevel, get_questions as get_natural_questions, iter_levels,
)
from run_m1_codegen import (
    LLM_OPTIONS, PROMPT_TEMPLATE, build_sqlite_from_tables,
    extract_sql, score_sql, _coerce_value, _detect_column_type,
)
from run_m2_codegen import FEWSHOT_BLOCK
from data_sources import load_dataset


RESULTS_DIR = ROOT / "experiments" / "results" / "m9_adult"


# ---------------------------------------------------------------------------
# Adult-specific config — single table, mixed types, hyphenated columns
# ---------------------------------------------------------------------------

ADULT_CONFIG = {
    "table": "adult",
    "stratify_by": "class",       # for proportional class sampling
    "numeric_cols": ["age", "hours-per-week"],
    "categorical_cols": ["workclass", "education", "sex", "class"],
}


# ---------------------------------------------------------------------------
# Ground truth
# ---------------------------------------------------------------------------

def compute_gt_adult(rows: list[dict]) -> dict:
    """Compute ground truth for 7 Adult Census questions."""
    n = len(rows)
    ages = [int(r["age"]) for r in rows if r.get("age") is not None]
    hours = [int(r["hours-per-week"]) for r in rows if r.get("hours-per-week") is not None]

    # Top education
    edu_counter = Counter(r["education"] for r in rows if r.get("education"))
    top_edu = edu_counter.most_common(1)[0][0] if edu_counter else None

    # Distinct workclass (ignore None)
    distinct_workclass = len({r["workclass"] for r in rows if r.get("workclass")})

    # Class distribution
    n_high_class = sum(1 for r in rows if r.get("class") == ">50K")

    # Avg hours among males
    male_hours = [int(r["hours-per-week"]) for r in rows
                  if r.get("sex") == "Male" and r.get("hours-per-week") is not None]
    avg_hours_male = round(sum(male_hours) / len(male_hours), 2) if male_hours else 0.0

    return {
        "count": n,
        "avg_age": round(sum(ages) / len(ages), 2) if ages else 0.0,
        "max_age": max(ages) if ages else 0,
        "distinct_workclass": distinct_workclass,
        "top_education": top_edu,
        "count_high_class": n_high_class,
        "avg_hours_male": avg_hours_male,
    }


def build_questions_adult() -> dict:
    return {
        "q_count": {
            "text": "Quantas linhas existem na tabela adult?",
            "key": "count", "type": "count",
        },
        "q_avg_age": {
            "text": "Qual e a media da coluna age na tabela adult?",
            "key": "avg_age", "type": "numeric",
        },
        "q_max_age": {
            "text": "Qual e o maior valor da coluna age na tabela adult?",
            "key": "max_age", "type": "count",
        },
        "q_distinct_workclass": {
            "text": "Quantos valores distintos de workclass aparecem na tabela adult? Ignore valores nulos.",
            "key": "distinct_workclass", "type": "count",
        },
        "q_top_education": {
            "text": "Qual valor de education aparece mais vezes na tabela adult? Responda com o valor exato.",
            "key": "top_education", "type": "string",
        },
        "q_count_high_class": {
            "text": "Quantas linhas têm class igual a '>50K' na tabela adult?",
            "key": "count_high_class", "type": "count",
        },
        "q_avg_hours_male": {
            "text": "Qual e a media de hours-per-week para linhas com sex igual a 'Male'?",
            "key": "avg_hours_male", "type": "numeric",
        },
    }


# ---------------------------------------------------------------------------
# Payload builder — schema + stats with PK info from metadata
# ---------------------------------------------------------------------------

def compute_column_stats_adult(tables: dict, tcf_metadata: dict) -> str:
    """Stats for single-table Adult — include PK info; no FK to annotate."""
    lines = []
    tables_meta = tcf_metadata.get("tables", {})

    for tname, rows in tables.items():
        if not rows:
            continue
        t_meta = tables_meta.get(tname, {})
        pk_cols = set(t_meta.get("pk") or [])

        lines.append(f"\n### {tname} ({len(rows)} rows)")
        for col in rows[0].keys():
            raw_values = [r.get(col) for r in rows]
            ctype = _detect_column_type(raw_values)
            coerced = [_coerce_value(v) for v in raw_values]
            pk_tag = " PK" if col in pk_cols else ""

            if ctype in ("INTEGER", "REAL"):
                nums = [float(v) for v in coerced
                        if isinstance(v, (int, float)) and not isinstance(v, bool)]
                if not nums:
                    lines.append(f'  "{col}" {ctype}{pk_tag}')
                    continue
                mn, mx, avg = min(nums), max(nums), sum(nums) / len(nums)
                card = len(set(nums))
                fmt = "{:.0f}" if ctype == "INTEGER" else "{:.2f}"
                lines.append(
                    f'  "{col}" {ctype}{pk_tag}, range=[{fmt.format(mn)}, {fmt.format(mx)}], '
                    f"mean={avg:.2f}, cardinality={card}"
                )
            else:
                uniq = list(dict.fromkeys(str(v) for v in coerced if v is not None))
                card = len(uniq)
                sample = ", ".join(uniq[:3])
                lines.append(f'  "{col}" TEXT{pk_tag}, cardinality={card}, samples=[{sample}]')
        lines.append("")
    return "\n".join(lines)


def build_payload_adult(tables: dict, meta: dict) -> str:
    return "## Schema + Stats\n" + compute_column_stats_adult(tables, meta) + "\n" + FEWSHOT_BLOCK


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

def run_m9_adult(
    models: list[str], volume: int, seeds: list[int], stratify: bool, endpoint: str,
    naturalness: tuple[NaturalnessLevel, ...] = (NaturalnessLevel.N0,),
) -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    manifest_path = RESULTS_DIR / "manifest.jsonl"
    client = OllamaClient(endpoint)
    completed = _load_completed(manifest_path)

    stratify_by = ADULT_CONFIG["stratify_by"] if stratify else None

    per_state: dict[int, dict] = {}
    for seed in seeds:
        tables, meta = load_dataset(
            "canonical:adult-census",
            volume=volume, seed=seed,
            stratify_by=stratify_by,
        )
        gt = compute_gt_adult(tables["adult"])
        conn = build_sqlite_from_tables(tables)
        payload = build_payload_adult(tables, meta)
        per_state[seed] = {
            "gt": gt, "conn": conn,
            "payload": payload, "tables": tables, "meta": meta,
        }

    combos = []
    for seed in seeds:
        for model in models:
            for nl in naturalness:
                questions = get_natural_questions("adult-census", nl)
                for q_name, q in questions.items():
                    strat_tag = f"strat-{stratify_by}" if stratify_by else "random"
                    # Backwards-compat: omit nl segment for N0 so existing keys/manifests match
                    if nl == NaturalnessLevel.N0:
                        key = f"m9adult|{model}|sql_stats_fs|vol{volume}|s{seed}|{strat_tag}|{q_name}"
                    else:
                        key = f"m9adult|{model}|sql_stats_fs|vol{volume}|s{seed}|{strat_tag}|{nl.value}|{q_name}"
                    if key in completed:
                        continue
                    combos.append({
                        "key": key, "model": model, "seed": seed,
                        "naturalness": nl, "q_name": q_name, "q": q,
                    })

    total = len(seeds) * len(models) * len(naturalness) * 7
    levels_str = ",".join(nl.value for nl in naturalness)
    print(f"[M9-Adult] {len(models)}m x 7q x {len(seeds)}s x {len(naturalness)}lvl ({levels_str}) = {total} combos")
    print(f"           stratify_by={stratify_by!r}")
    print(f"           {len(combos)} to run, {len(completed)} cached\n")

    # Preview: first seed GT + stratification metrics
    state = per_state[seeds[0]]
    print(f"  GT preview (seed={seeds[0]}, vol={volume}): {state['gt']}")
    print(f"  payload chars: {len(state['payload']):,}")
    sm = state["meta"].get("_stratification_metrics", [])
    if sm:
        m = sm[0]
        print(f"  stratification: TVD={m['tvd']}, JSD={m['jsd']}, chi2_p={m['chi2_pvalue']}, low_N_warn={m['chi2_warn_low_n']}")
    print()

    t_start = time.time()
    warmed: set[str] = set()

    for i, c in enumerate(combos, 1):
        model = c["model"]
        state = per_state[c["seed"]]

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

        # Capture stratification metrics for this seed (constant across questions)
        strat_metrics = state["meta"].get("_stratification_metrics", [])

        record = {
            "key": c["key"], "phase": "m9_adult", "model": model,
            "dataset": "adult-census", "variant": "sql_stats_fs",
            "naturalness_level": c["naturalness"].value,
            "question": c["q_name"], "question_key": c["q"]["key"],
            "question_type": c["q"]["type"],
            "question_text": c["q"]["text"],
            "seed": c["seed"], "volume": volume,
            "stratify_by": stratify_by,
            "stratification_metrics": strat_metrics[0] if strat_metrics else None,
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
        print("[M9-Adult] No records.")
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
    print(f"\n=== M9-Adult Summary ({total} records) ===")
    print(f"  Overall: {ok}/{total} = {ok/total*100:.1f}%")
    print(f"  M9-TPCH baseline (reference): 95.2% strict / 100% tie-aware\n")

    questions = ["q_count", "q_avg_age", "q_max_age", "q_distinct_workclass",
                 "q_top_education", "q_count_high_class", "q_avg_hours_male"]
    models = sorted(set(r["model"] for r in records))

    levels = sorted({r.get("naturalness_level", "N0") for r in records})
    multi_level = len(levels) > 1

    by_mq = defaultdict(list)
    by_q = defaultdict(list)
    by_ml = defaultdict(list)
    by_lq = defaultdict(list)
    for r in records:
        nl = r.get("naturalness_level", "N0")
        by_mq[(r["model"], r["question"])].append(r["ok"])
        by_q[r["question"]].append(r["ok"])
        by_ml[(r["model"], nl)].append(r["ok"])
        by_lq[(nl, r["question"])].append(r["ok"])

    if multi_level:
        from llm_eval.stats import wilson_ci
        print("  Per (model x naturalness):")
        print(f"  {'Model':<25}" + "  ".join(f"{l:<14}" for l in levels))
        for m in models:
            row = f"  {m:<25}"
            for l in levels:
                oks = by_ml.get((m, l), [])
                if oks:
                    row += f"  {sum(oks)}/{len(oks)} ({sum(oks)/len(oks)*100:.0f}%)    "
                else:
                    row += f"  {'-':<14}"
            print(row)

        print(f"\n  Per (naturalness x question):")
        print(f"  {'Question':<25}" + "  ".join(f"{l:<14}" for l in levels))
        for q in questions:
            row = f"  {q:<25}"
            for l in levels:
                oks = by_lq.get((l, q), [])
                if oks:
                    row += f"  {sum(oks)}/{len(oks)} ({sum(oks)/len(oks)*100:.0f}%)    "
                else:
                    row += f"  {'-':<14}"
            print(row)
        print()

    print(f"  Per (model x question)" + (" [aggregate over levels]" if multi_level else "") + ":")
    print(f"  {'Question':<25} " + " ".join(f"{m[:18]:>20}" for m in models) + "  Agg")
    print(f"  {'-'*25} " + " ".join(f"{'':->20}" for _ in models) + "  ---")
    for q in questions:
        row = f"  {q:<25}"
        for m in models:
            oks = by_mq.get((m, q), [])
            if oks:
                row += f"  {sum(oks)}/{len(oks):<3} ({sum(oks)/len(oks)*100:>4.0f}%)   "
            else:
                row += f"  {'-':>20}"
        agg = by_q[q]
        row += f"  {sum(agg)}/{len(agg)} ({sum(agg)/len(agg)*100:.0f}%)" if agg else ""
        print(row)

    # Stratification metrics summary (any seed has them)
    strat = next((r["stratification_metrics"] for r in records if r.get("stratification_metrics")), None)
    if strat:
        print(f"\n  Stratification on '{strat.get('stratify_by','?')}':")
        print(f"    TVD={strat['tvd']}, JSD={strat['jsd']}, Hellinger={strat['hellinger']}, chi2_p={strat['chi2_pvalue']}")
        print(f"    n_pop={strat['n_pop']}, n_sample={strat['n_sample']}, n_groups={strat['n_groups']}")

    # Failure samples
    print("\n  Failure samples (first 3):")
    shown = 0
    for r in records:
        if not r["ok"] and shown < 3:
            print(f"    [{r['question']}/{r['model'].split(':')[0]}]"
                  f" expected={r['expected']} got={str(r['executed_result'])[:40]}")
            print(f"    SQL: {r['sql'][:160]}")
            shown += 1


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="M9-Adult - canonical Adult Census via Pipeline B")
    parser.add_argument("--models", nargs="+",
                        default=["qwen3:14b", "phi4:latest", "qwen2.5-coder:7b"])
    parser.add_argument("--seeds", nargs="+", type=int, default=[42, 123, 7])
    parser.add_argument("--volume", type=int, default=100)
    parser.add_argument("--no-stratify", action="store_true",
                        help="disable stratified sampling (use random)")
    parser.add_argument("--endpoint", default="http://localhost:11434")
    parser.add_argument(
        "--naturalness", default="N0",
        help="Naturalness level(s): N0|N1|N2|N3|all|comma-separated. Default: N0 (legacy).",
    )
    parser.add_argument("--summary", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.summary:
        print_summary(RESULTS_DIR / "manifest.jsonl")
        return

    if args.dry_run:
        for seed in args.seeds[:1]:
            tables, meta = load_dataset(
                "canonical:adult-census",
                volume=args.volume, seed=seed,
                stratify_by=None if args.no_stratify else ADULT_CONFIG["stratify_by"],
            )
            gt = compute_gt_adult(tables["adult"])
            questions = build_questions_adult()
            print(f"\n=== adult-census (volume={args.volume}, seed={seed}) ===")
            print(f"Tables loaded: {[(k, len(v)) for k, v in tables.items()]}")
            print(f"GT: {gt}")
            sm = meta.get("_stratification_metrics", [])
            if sm:
                m = sm[0]
                print(f"Stratification: TVD={m['tvd']}, JSD={m['jsd']}, chi2_p={m['chi2_pvalue']}")
            for q_name, q in questions.items():
                print(f"  {q_name}: {q['text']}")
            payload = build_payload_adult(tables, meta)
            print(f"\nPayload length: {len(payload)} chars")
            print(f"--- Payload preview (first 600 chars) ---")
            print(payload[:600])
        return

    levels = tuple(iter_levels(args.naturalness))
    run_m9_adult(args.models, args.volume, args.seeds,
                 stratify=not args.no_stratify, endpoint=args.endpoint,
                 naturalness=levels)


if __name__ == "__main__":
    main()

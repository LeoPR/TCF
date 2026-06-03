"""M-Acomm-B — Linha B (LLM gera SQL → SQLite executa) em modelos comerciais.

Companion to ``run_m_acomm.py`` (Linha A). Same dataset and question set,
but the model is asked to generate SQL — the runner executes against
SQLite and scores the result. This tests F-Q30 (naturalness degrades
Linha B in locals): does the same degradation occur in commercial models,
or are they robust?

Reuses ``run_m9_adult`` for: payload builder, SQL extraction/scoring,
SQLite construction. Reuses ``run_m_acomm`` infra: AnswerCell schema is
NOT applicable here (we want raw SQL text), and naturalness/iter logic.

Design (default): 4 commercial models × 7 questions × 3 seeds × 4 levels
= 336 calls. Payload ~470 tokens (schema only) vs Linha A's 3000+ tokens
— roughly 5× cheaper.
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
sys.path.insert(0, str(ROOT / "scripts"))

from pydantic import BaseModel

from llm_eval.commercial_client import CommercialClient, PRICING, estimate_cost
from llm_eval.question_naturalness import (
    NaturalnessLevel, get_questions as get_natural_questions, iter_levels,
)
from run_m9_adult import (
    compute_gt_adult, build_payload_adult, ADULT_CONFIG,
)
from run_m1_codegen import (
    PROMPT_TEMPLATE, build_sqlite_from_tables, extract_sql, score_sql,
)
from data_sources import load_dataset


RESULTS_DIR = ROOT / "experiments" / "results" / "m_acomm_b"

# Same default panel as M-Acomm (Linha A) for direct comparability.
DEFAULT_MODELS = [
    "gpt-5.4-nano",
    "gpt-5.4-mini",
    "gpt-5.4",
    "gpt-4o-mini",
]


class SqlAnswer(BaseModel):
    """Structured output for SQL generation.

    Forcing structured output ensures the model returns exactly one SQL
    statement, eliminating preamble/explanation/code-fence parse errors
    that plague raw text mode.
    """
    sql: str


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


def run_m_acomm_b(
    models: list[str], volume: int, seeds: list[int],
    max_cost_usd: float | None,
    naturalness: tuple[NaturalnessLevel, ...] = (NaturalnessLevel.N0,),
) -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    manifest_path = RESULTS_DIR / "manifest.jsonl"
    client = CommercialClient(max_cost_usd=max_cost_usd)
    completed = _load_completed(manifest_path)

    available_models = [m for m in models if client.is_available(m)]
    skipped = [m for m in models if not client.is_available(m)]
    if skipped:
        print(f"[M-Acomm-B] SKIPPING (no API key): {skipped}")
    if not available_models:
        print("[M-Acomm-B] ERROR: no models with API keys configured.")
        return

    stratify_by = ADULT_CONFIG["stratify_by"]
    per_seed: dict[int, dict] = {}
    for seed in seeds:
        tables, meta = load_dataset(
            "canonical:adult-census",
            volume=volume, seed=seed, stratify_by=stratify_by,
        )
        gt = compute_gt_adult(tables["adult"])
        conn = build_sqlite_from_tables(tables)
        payload = build_payload_adult(tables, meta)
        per_seed[seed] = {
            "gt": gt, "conn": conn, "payload": payload,
            "tables": tables, "meta": meta,
            "payload_chars": len(payload),
            "stratification_metrics": meta.get("_stratification_metrics", []),
        }

    combos = []
    for model in available_models:
        for seed in seeds:
            for nl in naturalness:
                questions = get_natural_questions("adult-census", nl)
                for q_name, q in questions.items():
                    key = f"macommB|{model}|sql|vol{volume}|s{seed}|{nl.value}|{q_name}"
                    if key in completed:
                        continue
                    combos.append({
                        "key": key, "model": model, "seed": seed,
                        "naturalness": nl, "q_name": q_name, "q": q,
                    })

    total = len(seeds) * len(available_models) * len(naturalness) * 7
    levels_str = ",".join(nl.value for nl in naturalness)
    print(f"[M-Acomm-B] {len(available_models)}m x 7q x {len(seeds)}s x {len(naturalness)}lvl ({levels_str}) = {total} combos")
    print(f"            {len(combos)} to run, {len(completed)} cached")

    sample = per_seed[seeds[0]]
    print(f"\n  Adult vol={volume} seed={seeds[0]}:")
    print(f"  GT: {sample['gt']}")
    print(f"  Payload size: {sample['payload_chars']:,} chars (schema-only — Linha B)\n")

    t_start = time.time()

    for i, c in enumerate(combos, 1):
        model = c["model"]
        state = per_seed[c["seed"]]
        provider = "openai"  # only OpenAI supported in this run

        cache_prefix = state["payload"]
        prompt = (
            f"Pergunta: {c['q']['text']}\n"
            f"Gere apenas o SQL para responder, sem explicacao."
        )
        cache_key = f"macommB|{model}|s{c['seed']}"

        elapsed = time.time() - t_start
        print(f"  [{i}/{len(combos)} el={elapsed:.0f}s ${client.total_cost_usd:.3f}] {c['key']}",
              end=" ", flush=True)

        response = ""
        text_parsed = None
        sql = ""
        ok = False
        reason = "exception"
        executed = ""
        cost_usd = 0.0
        prompt_tokens = 0
        response_tokens = 0
        cached_tokens = 0
        total_ms = 0

        try:
            num_predict = 2048 if (model.startswith("gpt-5") or model.startswith("o")) else 256
            result = client.generate(
                model, prompt,
                options={"temperature": 0, "num_predict": num_predict},
                timeout=180,
                cache_prefix=cache_prefix,
                text_format=SqlAnswer,
                cache_key=cache_key,
            )
            response = result["text"]
            text_parsed = result.get("text_parsed")
            total_ms = result["total_duration_ns"] // 1_000_000
            prompt_tokens = result["prompt_tokens"]
            response_tokens = result["response_tokens"]
            cached_tokens = result.get("cached_tokens", 0)
            cost_usd = result["cost_usd"]

            sql = text_parsed.sql if text_parsed is not None else extract_sql(response)
            ok, reason, executed = score_sql(c["q"], sql, state["conn"], state["gt"])
            cache_tag = f" cache={cached_tokens}" if cached_tokens > 0 else ""
            print(f"{'OK' if ok else 'NO'} ({reason}) -> {str(executed)[:40]} ${cost_usd:.4f}{cache_tag}")
        except Exception as e:
            es = str(e)
            print(f"ERROR: {es[:80]}")
            response = f"ERROR:{es}"
            if "Budget cap" in es:
                print(f"\n[M-Acomm-B] BUDGET CAP HIT — stopping. Cumulative: ${client.total_cost_usd:.4f}")
                break

        record = {
            "key": c["key"], "phase": "m_acomm_b", "model": model,
            "dataset": "adult-census", "variant": "linha_b_sql",
            "naturalness_level": c["naturalness"].value,
            "question": c["q_name"], "question_key": c["q"]["key"],
            "question_type": c["q"]["type"],
            "question_text": c["q"]["text"],
            "seed": c["seed"], "volume": volume,
            "stratify_by": stratify_by,
            "stratification_metrics": (state["stratification_metrics"][0]
                                        if state["stratification_metrics"] else None),
            "response": response,
            "response_parsed": text_parsed.sql if text_parsed is not None else None,
            "sql": sql, "executed_result": str(executed),
            "ok": ok, "reason": reason,
            "expected": str(state["gt"][c["q"]["key"]]),
            "prompt_chars": len(prompt), "total_ms": total_ms,
            "prompt_tokens": prompt_tokens, "response_tokens": response_tokens,
            "cached_tokens": cached_tokens,
            "cost_usd": cost_usd, "cumulative_cost_usd": client.total_cost_usd,
        }
        with open(manifest_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")

    for state in per_seed.values():
        state["conn"].close()

    print(f"\n[M-Acomm-B] DONE. Total cost: ${client.total_cost_usd:.4f} USD")
    print_summary(manifest_path)


def print_summary(manifest_path: Path) -> None:
    if not manifest_path.exists():
        print("[M-Acomm-B] No records.")
        return
    by_key: dict[str, dict] = {}
    for line in manifest_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        by_key[r["key"]] = r
    records = list(by_key.values())

    if not records:
        print("[M-Acomm-B] Empty manifest.")
        return

    total = len(records)
    ok = sum(r["ok"] for r in records)
    total_cost = max((r.get("cumulative_cost_usd", 0) for r in records), default=0)

    print(f"\n=== M-Acomm-B Summary ({total} records) ===")
    print(f"  Overall: {ok}/{total} = {ok/total*100:.1f}%")
    print(f"  Total cost: ${total_cost:.4f} USD\n")

    levels = sorted({r.get("naturalness_level", "N0") for r in records})
    multi_level = len(levels) > 1
    from llm_eval.stats import wilson_ci

    by_m = defaultdict(list)
    by_ml = defaultdict(list)
    by_lq = defaultdict(list)
    for r in records:
        nl = r.get("naturalness_level", "N0")
        by_m[r["model"]].append(r["ok"])
        by_ml[(r["model"], nl)].append(r["ok"])
        by_lq[(nl, r["question"])].append(r["ok"])

    questions = ["q_count", "q_avg_age", "q_max_age", "q_distinct_workclass",
                 "q_top_education", "q_count_high_class", "q_avg_hours_male"]

    print("  Per model:")
    for m in sorted(by_m):
        oks = by_m[m]
        lo, hi = wilson_ci(sum(oks), len(oks))
        pricing = PRICING.get(m, ("?", "?"))
        print(f"    {m:<22} {sum(oks)}/{len(oks)} = {sum(oks)/len(oks)*100:>5.1f}%  "
              f"CI [{lo*100:.1f}%, {hi*100:.1f}%]  (pricing: ${pricing[0]}/${pricing[1]} per 1M)")

    if multi_level:
        print(f"\n  Per (model x naturalness):")
        print(f"  {'Model':<22}" + "  ".join(f"{l:<14}" for l in levels))
        for m in sorted(by_m):
            row = f"  {m:<22}"
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

    print("\n  Cost breakdown:")
    cost_by_m = defaultdict(float)
    calls_by_m = defaultdict(int)
    for r in records:
        cost_by_m[r["model"]] += r.get("cost_usd", 0)
        calls_by_m[r["model"]] += 1
    for m in sorted(cost_by_m):
        print(f"    {m:<22} {calls_by_m[m]} calls, ${cost_by_m[m]:.4f} (avg ${cost_by_m[m]/max(calls_by_m[m],1):.5f}/call)")


def main() -> None:
    parser = argparse.ArgumentParser(description="M-Acomm-B — Linha B (SQL gen) on commercial models")
    parser.add_argument("--models", nargs="+", default=DEFAULT_MODELS)
    parser.add_argument("--seeds", nargs="+", type=int, default=[42, 123, 7])
    parser.add_argument("--volume", type=int, default=100)
    parser.add_argument("--max-cost-usd", type=float, default=2.0)
    parser.add_argument("--naturalness", default="N0",
                        help="N0|N1|N2|N3|all|comma-list. Default: N0.")
    parser.add_argument("--summary", action="store_true")
    args = parser.parse_args()

    if args.summary:
        print_summary(RESULTS_DIR / "manifest.jsonl")
        return

    levels = tuple(iter_levels(args.naturalness))
    run_m_acomm_b(args.models, args.volume, args.seeds, args.max_cost_usd,
                  naturalness=levels)


if __name__ == "__main__":
    main()

"""M-Acomm-B-TPCH — Linha B (LLM gera SQL → SQLite executa) em TPC-H comerciais.

Companion to ``run_m_acomm_b.py`` (Linha B Adult). Same paradigm but
applied to TPC-H multi-table (partsupp + supplier + part). Tests F-Q33:
does the schema ambiguity that crashed local SQL gen on TPC-H N2 (-30 to
-45pp) also affect commercial top models, or do they preserve high accuracy
like in Adult (F-Q32)?

Reuses ``run_m9_canonical`` infrastructure for: payload, GT computation,
SQL extraction/scoring, SQLite construction. Reuses ``run_m_acomm_b``
infra for: SqlAnswer schema, CommercialClient with caching.
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
from run_m9_canonical import (
    CANONICAL_CONFIGS, compute_gt_m9, build_payload_canonical,
    load_canonical_subset,
)
from run_m1_codegen import build_sqlite_from_tables, extract_sql, score_sql

RESULTS_DIR = ROOT / "experiments" / "results" / "m_acommB_tpch"

DEFAULT_MODELS = [
    "gpt-5.4-nano",
    "gpt-5.4-mini",
    "gpt-5.4",
    "gpt-4o-mini",
]


class SqlAnswer(BaseModel):
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


def run(
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
        print(f"[M-Acomm-B-TPCH] SKIPPING (no API key): {skipped}")
    if not available_models:
        print("[M-Acomm-B-TPCH] ERROR: no models with API keys configured.")
        return

    cfg = CANONICAL_CONFIGS["tpch-sf001"]
    per_seed: dict[int, dict] = {}
    for seed in seeds:
        tables, meta = load_canonical_subset("tpch-sf001", volume, seed)
        gt = compute_gt_m9(tables, cfg)
        conn = build_sqlite_from_tables(tables)
        payload = build_payload_canonical(tables, meta)
        per_seed[seed] = {
            "gt": gt, "conn": conn, "payload": payload,
            "tables": tables, "meta": meta,
            "payload_chars": len(payload),
        }

    combos = []
    for model in available_models:
        for seed in seeds:
            for nl in naturalness:
                questions = get_natural_questions("tpch", nl)
                for q_name, q in questions.items():
                    key = f"macommBT|{model}|tpch|vol{volume}|s{seed}|{nl.value}|{q_name}"
                    if key in completed:
                        continue
                    combos.append({
                        "key": key, "model": model, "seed": seed,
                        "naturalness": nl, "q_name": q_name, "q": q,
                    })

    total = len(seeds) * len(available_models) * len(naturalness) * 7
    levels_str = ",".join(nl.value for nl in naturalness)
    print(f"[M-Acomm-B-TPCH] {len(available_models)}m x 7q x {len(seeds)}s x {len(naturalness)}lvl ({levels_str}) = {total} combos")
    print(f"                 {len(combos)} to run, {len(completed)} cached")

    sample = per_seed[seeds[0]]
    print(f"\n  TPC-H sf001 vol={volume} seed={seeds[0]}:")
    print(f"  GT: {sample['gt']}")
    print(f"  Payload size: {sample['payload_chars']:,} chars (multi-table schema)\n")

    t_start = time.time()

    for i, c in enumerate(combos, 1):
        model = c["model"]
        state = per_seed[c["seed"]]

        cache_prefix = state["payload"]
        prompt = (
            f"Pergunta: {c['q']['text']}\n"
            f"Gere apenas o SQL para responder, sem explicacao."
        )
        cache_key = f"macommBT|{model}|s{c['seed']}"

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
                print(f"\n[M-Acomm-B-TPCH] BUDGET CAP HIT — stopping. ${client.total_cost_usd:.4f}")
                break

        record = {
            "key": c["key"], "phase": "m_acomm_b_tpch", "model": model,
            "dataset": "tpch-sf001", "variant": "linha_b_sql",
            "naturalness_level": c["naturalness"].value,
            "question": c["q_name"], "question_key": c["q"]["key"],
            "question_type": c["q"]["type"],
            "question_text": c["q"]["text"],
            "seed": c["seed"], "volume": volume,
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

    print(f"\n[M-Acomm-B-TPCH] DONE. Total cost: ${client.total_cost_usd:.4f} USD")
    print_summary(manifest_path)


def print_summary(manifest_path: Path) -> None:
    if not manifest_path.exists():
        print("[M-Acomm-B-TPCH] No records.")
        return
    by_key: dict[str, dict] = {}
    for line in manifest_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        by_key[r["key"]] = r
    records = list(by_key.values())
    if not records:
        return

    total = len(records)
    ok = sum(r["ok"] for r in records)
    total_cost = max((r.get("cumulative_cost_usd", 0) for r in records), default=0)

    print(f"\n=== M-Acomm-B-TPCH Summary ({total} records) ===")
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

    questions = ["q_count", "q_sum", "q_avg", "q_distinct",
                 "q_top_product", "q_lookup", "q_lookup_value"]

    print("  Per model:")
    for m in sorted(by_m):
        oks = by_m[m]
        lo, hi = wilson_ci(sum(oks), len(oks))
        pricing = PRICING.get(m, ("?", "?"))
        print(f"    {m:<22} {sum(oks)}/{len(oks)} = {sum(oks)/len(oks)*100:>5.1f}%  "
              f"CI [{lo*100:.1f}%, {hi*100:.1f}%]  (${pricing[0]}/${pricing[1]} per 1M)")

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
        print(f"  {'Question':<22}" + "  ".join(f"{l:<14}" for l in levels))
        for q in questions:
            row = f"  {q:<22}"
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
    parser = argparse.ArgumentParser(description="M-Acomm-B-TPCH — Linha B SQL gen on TPC-H commercials")
    parser.add_argument("--models", nargs="+", default=DEFAULT_MODELS)
    parser.add_argument("--seeds", nargs="+", type=int, default=[42, 123, 7])
    parser.add_argument("--volume", type=int, default=100)
    parser.add_argument("--max-cost-usd", type=float, default=2.0)
    parser.add_argument("--naturalness", default="N0")
    parser.add_argument("--summary", action="store_true")
    args = parser.parse_args()

    if args.summary:
        print_summary(RESULTS_DIR / "manifest.jsonl")
        return

    levels = tuple(iter_levels(args.naturalness))
    run(args.models, args.volume, args.seeds, args.max_cost_usd, naturalness=levels)


if __name__ == "__main__":
    main()

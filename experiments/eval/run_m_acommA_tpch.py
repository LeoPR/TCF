"""M-Acomm-A-TPCH — Linha A (LLM lê TCF completo e calcula) em TPC-H comerciais.

Closes the gap in the 2D paper-ready table:

|                    | Adult (single-table)  | TPC-H (multi-table)   |
|--------------------|-----------------------|-----------------------|
| Locals Linha A     | F-Q29                 | not tested (ceiling)  |
| Locals Linha B     | F-Q30                 | F-Q33                 |
| Commercial Linha A | F-Q31                 | **THIS RUN**          |
| Commercial Linha B | F-Q32                 | F-Q34                 |

Hypothesis: F-Q31 (commercial reasoning breaks ceiling on Adult) should
extend here, but F-Q33/F-Q34 (TPC-H schema ambiguity in N2) suggests the
naturalness × multi-table interaction will reduce ceiling. Linha A might
suffer LESS than Linha B because it bypasses SQL generation entirely —
the model just reads values and computes. But it also has to handle 3
tables in TCF format.

Reuses ``run_m9_canonical`` for ground truth + dataset loading; ``run_m_acomm``
for AnswerCell schema and prompt template.
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
from llm_eval.metrics import score_response, DEFAULT_CONFIG
from llm_eval.question_naturalness import (
    NaturalnessLevel, get_questions as get_natural_questions, iter_levels,
)
from run_m9_canonical import (
    CANONICAL_CONFIGS, compute_gt_m9, load_canonical_subset,
)
from run_m_acomm import LINHA_A_SYSTEM_PROMPT, build_payload_linha_a

RESULTS_DIR = ROOT / "experiments" / "results" / "m_acommA_tpch"

DEFAULT_MODELS = [
    "gpt-5.4-nano",
    "gpt-5.4-mini",
    "gpt-5.4",
    "gpt-4o-mini",
]


class AnswerCell(BaseModel):
    """Same schema as Adult Linha A — flexible string field."""
    value: str


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
    models: list[str], volume: int, seeds: list[int], level: int,
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
        print(f"[M-Acomm-A-TPCH] SKIPPING (no API key): {skipped}")
    if not available_models:
        print("[M-Acomm-A-TPCH] ERROR: no models with API keys configured.")
        return

    cfg = CANONICAL_CONFIGS["tpch-sf001"]
    per_seed: dict[int, dict] = {}
    for seed in seeds:
        tables, meta = load_canonical_subset("tpch-sf001", volume, seed)
        gt = compute_gt_m9(tables, cfg)
        payload = build_payload_linha_a(tables, level=level)
        per_seed[seed] = {
            "gt": gt, "payload": payload, "meta": meta,
            "tables": tables, "payload_chars": len(payload),
        }

    combos = []
    for model in available_models:
        for seed in seeds:
            for nl in naturalness:
                questions = get_natural_questions("tpch", nl)
                for q_name, q in questions.items():
                    key = f"macommAT|{model}|tpch|vol{volume}|L{level}|s{seed}|{nl.value}|{q_name}"
                    if key in completed:
                        continue
                    combos.append({
                        "key": key, "model": model, "seed": seed,
                        "naturalness": nl, "q_name": q_name, "q": q,
                    })

    total = len(seeds) * len(available_models) * len(naturalness) * 7
    levels_str = ",".join(nl.value for nl in naturalness)
    print(f"[M-Acomm-A-TPCH] {len(available_models)}m x 7q x {len(seeds)}s x {len(naturalness)}lvl ({levels_str}) = {total} combos")
    print(f"                 {len(combos)} to run, {len(completed)} cached")

    sample = per_seed[seeds[0]]
    print(f"\n  TPC-H sf001 vol={volume} seed={seeds[0]} TCF L{level}:")
    print(f"  GT: {sample['gt']}")
    print(f"  Payload size: {sample['payload_chars']:,} chars (3-table TCF L{level})\n")

    t_start = time.time()

    for i, c in enumerate(combos, 1):
        model = c["model"]
        state = per_seed[c["seed"]]

        cache_prefix = LINHA_A_SYSTEM_PROMPT.format(payload=state["payload"])
        prompt = f"## Pergunta\n{c['q']['text']}\n\n## Resposta\n"
        cache_key = f"macommAT|{model}|s{c['seed']}|L{level}"

        elapsed = time.time() - t_start
        print(f"  [{i}/{len(combos)} el={elapsed:.0f}s ${client.total_cost_usd:.3f}] {c['key']}",
              end=" ", flush=True)

        response = ""
        text_parsed = None
        ok = False
        reason = "exception"
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
                text_format=AnswerCell,
                cache_key=cache_key,
            )
            response = result["text"]
            text_parsed = result.get("text_parsed")
            total_ms = result["total_duration_ns"] // 1_000_000
            prompt_tokens = result["prompt_tokens"]
            response_tokens = result["response_tokens"]
            cached_tokens = result.get("cached_tokens", 0)
            cost_usd = result["cost_usd"]

            answer = text_parsed.value if text_parsed is not None else response
            expected = state["gt"][c["q"]["key"]]
            ok, reason = score_response(answer, expected, c["q"]["key"], config=DEFAULT_CONFIG)
            cache_tag = f" cache={cached_tokens}" if cached_tokens > 0 else ""
            print(f"{'OK' if ok else 'NO'} ({reason}) ${cost_usd:.4f}{cache_tag}")
        except Exception as e:
            es = str(e)
            print(f"ERROR: {es[:80]}")
            response = f"ERROR:{es}"
            if "Budget cap" in es:
                print(f"\n[M-Acomm-A-TPCH] BUDGET CAP HIT — ${client.total_cost_usd:.4f}")
                break

        record = {
            "key": c["key"], "phase": "m_acomm_a_tpch", "model": model,
            "dataset": "tpch-sf001", "variant": "linha_a_tcf",
            "tcf_level": level,
            "naturalness_level": c["naturalness"].value,
            "question": c["q_name"], "question_key": c["q"]["key"],
            "question_type": c["q"]["type"],
            "question_text": c["q"]["text"],
            "seed": c["seed"], "volume": volume,
            "response": response,
            "response_parsed": text_parsed.value if text_parsed is not None else None,
            "ok": ok, "reason": reason,
            "expected": str(state["gt"][c["q"]["key"]]),
            "prompt_chars": len(prompt), "total_ms": total_ms,
            "prompt_tokens": prompt_tokens, "response_tokens": response_tokens,
            "cached_tokens": cached_tokens,
            "cost_usd": cost_usd, "cumulative_cost_usd": client.total_cost_usd,
        }
        with open(manifest_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")

    print(f"\n[M-Acomm-A-TPCH] DONE. Total cost: ${client.total_cost_usd:.4f} USD")
    print_summary(manifest_path)


def print_summary(manifest_path: Path) -> None:
    if not manifest_path.exists():
        print("[M-Acomm-A-TPCH] No records.")
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

    print(f"\n=== M-Acomm-A-TPCH Summary ({total} records) ===")
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
    parser = argparse.ArgumentParser(description="M-Acomm-A-TPCH — Linha A on TPC-H commercials")
    parser.add_argument("--models", nargs="+", default=DEFAULT_MODELS)
    parser.add_argument("--seeds", nargs="+", type=int, default=[42, 123, 7])
    parser.add_argument("--volume", type=int, default=100)
    parser.add_argument("--level", type=int, default=2, choices=[0, 1, 2, 3])
    parser.add_argument("--max-cost-usd", type=float, default=4.0)
    parser.add_argument("--naturalness", default="N0")
    parser.add_argument("--summary", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.summary:
        print_summary(RESULTS_DIR / "manifest.jsonl")
        return

    if args.dry_run:
        cfg = CANONICAL_CONFIGS["tpch-sf001"]
        tables, meta = load_canonical_subset("tpch-sf001", args.volume, args.seeds[0])
        gt = compute_gt_m9(tables, cfg)
        payload = build_payload_linha_a(tables, level=args.level)
        print(f"=== M-Acomm-A-TPCH dry-run ===")
        print(f"  Tables loaded: {[(k, len(v)) for k,v in tables.items()]}")
        print(f"  GT: {gt}")
        print(f"  Payload size: {len(payload):,} chars")
        print(f"\n  Payload preview (first 500 chars):")
        print(payload[:500])
        return

    levels = tuple(iter_levels(args.naturalness))
    run(args.models, args.volume, args.seeds, args.level, args.max_cost_usd,
        naturalness=levels)


if __name__ == "__main__":
    main()

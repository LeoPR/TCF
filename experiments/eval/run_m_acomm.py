"""M-Acomm — Linha A (LLM lê TCF e calcula) em modelos comerciais.

F-Q12 estabeleceu que aritmética sobre colunas com >100 valores falha em
modelos LOCAIS 7-14B (teto ~60-70%). Mas nunca foi testado em comerciais.

Hipóteses:
  H1: Linha A em comerciais ≥ 90% — F-Q12 é local-bound, não universal
  H2: Linha A em comerciais ainda satura em ~70% — F-Q12 é universal,
      independente de tamanho/qualidade do modelo
  H3: Comerciais top (GPT-4o, Claude Sonnet) > comerciais mini
      (GPT-4o-mini, Claude Haiku) em margem detectável

Design: Adult Census (1 dataset) × 4 comerciais × 7 questions × 3 seeds
= 84 calls. Custo estimado ~$5-12 USD (varia por modelo).

Diferença vs M9-Adult (Linha B):
- M9-Adult: schema-only payload + "gera SQL" → SQLite executa
- M-Acomm: TCF L2 com DADOS COMPLETOS + "responda valor" → LLM calcula

Usa stratify_by='class' por default (consistente com M9-Adult, F-Q26).
Registra cost_usd e cumulative_cost_usd no manifest para auditoria.
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

from llm_eval.commercial_client import CommercialClient, PRICING, estimate_cost
from pydantic import BaseModel


class AnswerCell(BaseModel):
    """Structured output schema for Adult Census Linha A.

    All answers fit a single field; scorer normalises numeric/string downstream.
    Using a permissive ``str`` keeps the schema flexible across the 7 question
    types (count, numeric mean, max, distinct count, top category name).
    """
    value: str
from llm_eval.metrics import score_response, strip_think, extract_number, DEFAULT_CONFIG, ScoringConfig
from llm_eval.question_naturalness import (
    NaturalnessLevel, get_questions as get_natural_questions, iter_levels,
)
from run_m9_adult import compute_gt_adult, build_questions_adult
from data_sources import load_dataset

from tcf import encode_rows, EncodeConfig


RESULTS_DIR = ROOT / "experiments" / "results" / "m_acomm"

# Default commercial models — mix de cheap + capable + frontier (Apr/2026)
# Pricing snapshot in commercial_client.PRICING.
DEFAULT_MODELS = [
    # Anthropic: 3 tiers
    "claude-haiku-4-5",      # cheap   — $1   /$5     (cached $0.10)
    "claude-sonnet-4-6",     # mid     — $3   /$15    (cached $0.30)
    "claude-opus-4-7",       # frontier — $5  /$25    (cached $0.50)
    # OpenAI: 3 tiers (5.4 family — gpt-4o is in deprecation path)
    "gpt-5.4-nano",          # cheap   — $0.20/$1.25  (cached $0.02)
    "gpt-5.4-mini",          # mid     — $0.75/$4.50  (cached $0.075)
    "gpt-5.4",               # frontier — $2.5/$15    (cached $0.25)
]

# Static prefix that is identical across all questions for a given (seed, level, dataset).
# Splitting out helps Anthropic prompt caching: same TCF payload re-used across 7 questions
# means 6 cache reads at 0.1× input price after the first WRITE.
LINHA_A_SYSTEM_PROMPT = """Voce e um analista de dados. Os dados abaixo estao em formato TCF (Textual Columnar Format) nivel 2:
- Cada coluna lista seus valores em sequencia
- "N*val" significa val repetido N vezes consecutivas (RLE)
- STATS no topo de cada tabela tem agregacoes pre-computadas

Responda a pergunta do usuario com APENAS o valor numerico ou nome textual, sem explicacao nem formula.

{payload}"""


# ---------------------------------------------------------------------------
# Linha A prompt — TCF L2 with DATA + ask for direct answer
# ---------------------------------------------------------------------------

LINHA_A_PROMPT = """Voce e um analista de dados. Os dados abaixo estao em formato TCF (Textual Columnar Format) nivel 2:
- Cada coluna lista seus valores em sequencia
- "N*val" significa val repetido N vezes consecutivas (RLE)
- STATS no topo de cada tabela tem agregacoes pre-computadas

Responda a pergunta com APENAS o valor numerico ou nome textual, sem explicacao nem formula.

{payload}

## Pergunta
{question}

## Resposta
"""


def build_payload_linha_a(tables: dict, level: int = 2) -> str:
    """Encode all tables as TCF text and concatenate (Linha A: data + schema)."""
    parts = []
    for tname, rows in tables.items():
        if not rows:
            continue
        cfg = EncodeConfig(level=level, include_stats=True)
        text = encode_rows(tname, rows, config=cfg)
        parts.append(text)
    return "\n\n".join(parts)


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

def run_m_acomm(
    models: list[str], volume: int, seeds: list[int], level: int,
    max_cost_usd: float | None,
    naturalness: tuple[NaturalnessLevel, ...] = (NaturalnessLevel.N0,),
) -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    manifest_path = RESULTS_DIR / "manifest.jsonl"
    client = CommercialClient(max_cost_usd=max_cost_usd)
    completed = _load_completed(manifest_path)

    # Filter models by API key availability
    available_models = [m for m in models if client.is_available(m)]
    skipped = [m for m in models if not client.is_available(m)]
    if skipped:
        print(f"[M-Acomm] SKIPPING (no API key): {skipped}")
    if not available_models:
        print("[M-Acomm] ERROR: no models with API keys configured.")
        print("Set ANTHROPIC_API_KEY and/or OPENAI_API_KEY env vars,")
        print(f"or create config/api_keys.json with {{\"anthropic\": \"...\", \"openai\": \"...\"}}")
        return

    # Pre-load Adult sample per seed (stratified)
    per_seed: dict[int, dict] = {}
    for seed in seeds:
        tables, meta = load_dataset(
            "canonical:adult-census",
            volume=volume, seed=seed, stratify_by="class",
        )
        gt = compute_gt_adult(tables["adult"])
        payload = build_payload_linha_a(tables, level=level)
        per_seed[seed] = {
            "gt": gt, "payload": payload,
            "meta": meta,
            "payload_chars": len(payload),
            "stratification_metrics": meta.get("_stratification_metrics", []),
        }

    # Iteration order optimised for prompt caching:
    # (model, seed) external -> (naturalness, question) internal.
    # Same TCF payload is re-used across 28 calls per (model, seed) — Anthropic
    # cache_prefix or OpenAI automatic cache catches the repetition.
    combos = []
    for model in available_models:
        for seed in seeds:
            for nl in naturalness:
                questions = get_natural_questions("adult-census", nl)
                for q_name, q in questions.items():
                    key = f"macomm|{model}|vol{volume}|L{level}|s{seed}|{nl.value}|{q_name}"
                    if key in completed:
                        continue
                    combos.append({
                        "key": key, "model": model, "seed": seed,
                        "naturalness": nl, "q_name": q_name, "q": q,
                    })

    total = len(seeds) * len(available_models) * len(naturalness) * 7
    levels_str = ",".join(nl.value for nl in naturalness)
    print(f"[M-Acomm] {len(available_models)}models x 7q x {len(seeds)}s x {len(naturalness)}lvl ({levels_str}) = {total} combos")
    print(f"          {len(combos)} to run, {len(completed)} cached")

    # Pre-flight token count + cost projection using count_tokens API.
    # We use seed[0] payload, the first available model per provider, and assume
    # 50 output tokens per call (short answers).
    sample_payload_chars = per_seed[seeds[0]]["payload_chars"]
    sample_system = LINHA_A_SYSTEM_PROMPT.format(payload=per_seed[seeds[0]]["payload"])
    sample_user_q = "Quantas linhas existem na tabela adult?"  # representative
    est_output_tokens = 50

    print(f"\n  Pre-flight token counts (count_tokens API):")
    cost_breakdown = {}
    for m in available_models:
        try:
            tok_system = client.count_tokens(m, sample_system)
            tok_user = client.count_tokens(m, sample_user_q)
            tok_input_total = tok_system + tok_user
        except Exception as e:
            tok_system = sample_payload_chars // 4
            tok_user = 20
            tok_input_total = tok_system + tok_user
            print(f"    {m:<22} count_tokens FAILED ({e}); falling back to chars/4")
        n_calls_per_model = 7 * len(seeds) * len(naturalness)
        # Without caching cost
        nocache = estimate_cost(m, tok_input_total, est_output_tokens) * n_calls_per_model
        # With caching: 1 write per (seed) at full price + (n-1) reads at cached price
        n_seed_groups = len(seeds)  # 1 cache write per seed group
        n_cache_reads = n_calls_per_model - n_seed_groups
        write_cost = estimate_cost(m, tok_system, 0) * n_seed_groups
        read_cost = (
            estimate_cost(m, 0, 0, cached_input_tokens=tok_system)
            * n_cache_reads if PRICING.get(m, (None,))[-1] is not None else
            estimate_cost(m, tok_system, 0) * n_cache_reads
        )
        # Always pay user-question input + output for every call
        per_call_extra = (
            (tok_user / 1_000_000) * PRICING[m][0]
            + (est_output_tokens / 1_000_000) * PRICING[m][1]
        )
        cached_cost = write_cost + read_cost + per_call_extra * n_calls_per_model
        cost_breakdown[m] = (tok_input_total, nocache, cached_cost)
        print(f"    {m:<22} system={tok_system:<5} user~={tok_user:<3} "
              f"calls={n_calls_per_model:<3}  ${nocache:.3f} no-cache  ${cached_cost:.3f} cached")

    total_no_cache = sum(v[1] for v in cost_breakdown.values())
    total_cached = sum(v[2] for v in cost_breakdown.values())
    print(f"\n  TOTAL projected: ${total_no_cache:.3f} no-cache  |  ${total_cached:.3f} with caching")
    if max_cost_usd:
        print(f"  Budget cap: ${max_cost_usd:.2f} USD")
    print()

    # Preview
    seed0 = seeds[0]
    print(f"  Preview seed={seed0}, vol={volume}, TCF L{level}:")
    print(f"  GT: {per_seed[seed0]['gt']}")
    sm = per_seed[seed0]["stratification_metrics"]
    if sm:
        print(f"  stratification: TVD={sm[0]['tvd']}, chi2_p={sm[0]['chi2_pvalue']}")
    print(f"  payload size: {per_seed[seed0]['payload_chars']:,} chars\n")

    t_start = time.time()

    for i, c in enumerate(combos, 1):
        model = c["model"]
        state = per_seed[c["seed"]]
        provider = "anthropic" if model.startswith("claude") else "openai"

        # cache_prefix is the static TCF system payload (re-used across the
        # 28 questions for a given seed). prompt is the user question only.
        # Both Anthropic (cache_control) and OpenAI (prompt_cache_key) cache it.
        cache_prefix = LINHA_A_SYSTEM_PROMPT.format(payload=state["payload"])
        prompt = f"## Pergunta\n{c['q']['text']}\n\n## Resposta\n"

        # cache_key keeps OpenAI cache routes attributed to (model, seed) — OpenAI
        # binds prompt_cache_key to org+model+key for routing.
        cache_key = f"macomm|{model}|s{c['seed']}|L{level}"

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
        cumulative_cost = client.total_cost_usd

        try:
            # Reasoning models eat the output budget for chain-of-thought.
            # 2048 leaves room for 1500-1800 reasoning tokens + the answer cell.
            num_predict = 2048 if provider == "openai" and (
                model.startswith("gpt-5") or model.startswith("o")
            ) else 256
            result = client.generate(
                model, prompt,
                options={"temperature": 0, "num_predict": num_predict},
                timeout=180,
                cache_prefix=cache_prefix,
                text_format=AnswerCell if provider == "openai" else None,
                cache_key=cache_key,
            )
            response = result["text"]
            text_parsed = result.get("text_parsed")
            total_ms = result["total_duration_ns"] // 1_000_000
            prompt_tokens = result["prompt_tokens"]
            response_tokens = result["response_tokens"]
            cached_tokens = result.get("cached_tokens", 0)
            cost_usd = result["cost_usd"]
            cumulative_cost = result["cumulative_cost_usd"]

            # When structured output gave us a parsed cell, score the .value
            # directly; otherwise fall back to raw text.
            answer_for_score = (text_parsed.value if text_parsed is not None
                                else response)
            expected = state["gt"][c["q"]["key"]]
            ok, reason = score_response(
                answer_for_score, expected, c["q"]["key"], config=DEFAULT_CONFIG,
            )
            cache_tag = f" cache={cached_tokens}" if cached_tokens > 0 else ""
            print(f"{'OK' if ok else 'NO'} ({reason}) ${cost_usd:.4f}{cache_tag}")
        except Exception as e:
            es = str(e)
            print(f"ERROR: {es[:80]}")
            response = f"ERROR:{es}"
            if "Budget cap" in es:
                print(f"\n[M-Acomm] BUDGET CAP HIT — stopping. Cumulative: ${client.total_cost_usd:.4f}")
                break

        record = {
            "key": c["key"], "phase": "m_acomm", "model": model,
            "dataset": "adult-census", "variant": "linha_a_tcf",
            "tcf_level": level,
            "naturalness_level": c["naturalness"].value,
            "question": c["q_name"], "question_key": c["q"]["key"],
            "question_type": c["q"]["type"],
            "question_text": c["q"]["text"],
            "seed": c["seed"], "volume": volume,
            "stratify_by": "class",
            "stratification_metrics": (state["stratification_metrics"][0]
                                        if state["stratification_metrics"] else None),
            "response": response,
            "response_parsed": text_parsed.value if text_parsed is not None else None,
            "executed_result": "",
            "ok": ok, "reason": reason,
            "expected": str(state["gt"][c["q"]["key"]]),
            "prompt_chars": len(prompt), "total_ms": total_ms,
            "prompt_tokens": prompt_tokens, "response_tokens": response_tokens,
            "cached_tokens": cached_tokens,
            "cost_usd": cost_usd, "cumulative_cost_usd": cumulative_cost,
        }
        with open(manifest_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")

    print(f"\n[M-Acomm] DONE. Total cost: ${client.total_cost_usd:.4f} USD")
    print_summary(manifest_path)


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

def print_summary(manifest_path: Path) -> None:
    if not manifest_path.exists():
        print("[M-Acomm] No records.")
        return
    by_key: dict[str, dict] = {}
    for line in manifest_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        by_key[r["key"]] = r
    records = list(by_key.values())

    if not records:
        print("[M-Acomm] Empty manifest.")
        return

    total = len(records)
    ok = sum(r["ok"] for r in records)
    total_cost = max((r.get("cumulative_cost_usd", 0) for r in records), default=0)

    print(f"\n=== M-Acomm Summary ({total} records) ===")
    print(f"  Overall: {ok}/{total} = {ok/total*100:.1f}%")
    print(f"  Total cost: ${total_cost:.4f} USD")
    print(f"  Reference baselines:")
    print(f"    Linha A local (F-Q12): ~60-70% ceiling")
    print(f"    Linha B local M9-Adult: 100% (with SQL execution)")
    print(f"    Linha B local M9-TPCH: 95.2% strict / 100% tie-aware\n")

    # Per-model accuracy
    levels = sorted({r.get("naturalness_level", "N0") for r in records})
    multi_level = len(levels) > 1
    from llm_eval.stats import wilson_ci

    by_m = defaultdict(list)
    by_mq = defaultdict(list)
    by_ml = defaultdict(list)
    by_lq = defaultdict(list)
    for r in records:
        nl = r.get("naturalness_level", "N0")
        by_m[r["model"]].append(r["ok"])
        by_mq[(r["model"], r["question"])].append(r["ok"])
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
        print(f"  {'Model':<25}" + "  ".join(f"{l:<14}" for l in levels))
        for m in sorted(by_m):
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

    print(f"\n  Per (model x question)" + (" [N0 only]" if multi_level else "") + ":")
    models = sorted(set(r["model"] for r in records))
    n0_records = [r for r in records if r.get("naturalness_level", "N0") == "N0"] if multi_level else records
    by_mq_show = defaultdict(list)
    for r in n0_records:
        by_mq_show[(r["model"], r["question"])].append(r["ok"])
    print(f"  {'Question':<25}" + "  ".join(f"{m[:18]:<18}" for m in models))
    for q in questions:
        row = f"  {q:<25}"
        for m in models:
            oks = by_mq_show.get((m, q), [])
            if oks:
                row += f"  {sum(oks)}/{len(oks)} ({sum(oks)/len(oks)*100:.0f}%)        "
            else:
                row += f"  {'-':<18}"
        print(row)

    # Cost per model
    print(f"\n  Cost breakdown:")
    cost_by_m = defaultdict(float)
    calls_by_m = defaultdict(int)
    for r in records:
        cost_by_m[r["model"]] += r.get("cost_usd", 0)
        calls_by_m[r["model"]] += 1
    for m in sorted(cost_by_m):
        print(f"    {m:<22} {calls_by_m[m]} calls, ${cost_by_m[m]:.4f} (avg ${cost_by_m[m]/max(calls_by_m[m],1):.5f}/call)")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="M-Acomm — Linha A on commercial models")
    parser.add_argument("--models", nargs="+", default=DEFAULT_MODELS)
    parser.add_argument("--seeds", nargs="+", type=int, default=[42, 123, 7])
    parser.add_argument("--volume", type=int, default=100)
    parser.add_argument("--level", type=int, default=2,
                        choices=[0, 1, 2, 3], help="TCF compression level")
    parser.add_argument("--max-cost-usd", type=float, default=15.0,
                        help="abort if cumulative cost exceeds USD")
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
        client = CommercialClient()
        levels = tuple(iter_levels(args.naturalness))
        n_calls_per_model = 7 * len(args.seeds) * len(levels)
        n_seed_groups = len(args.seeds)

        print("=== M-Acomm dry-run ===")
        print(f"Models requested:    {args.models}")
        print(f"Seeds:               {args.seeds}")
        print(f"Naturalness levels:  {[l.value for l in levels]}")
        print(f"Calls per model:     7q x {len(args.seeds)}s x {len(levels)}lvl = {n_calls_per_model}")
        print()
        for m in args.models:
            avail = "OK" if client.is_available(m) else "MISSING API KEY"
            pricing = PRICING.get(m)
            cached = pricing[2] if pricing else None
            cached_str = f" cached=${cached}/1M" if cached is not None else " no-cache"
            print(f"  {m:<22} [{avail:<15}] in=${pricing[0]}/1M out=${pricing[1]}/1M{cached_str}")
        print()

        seed = args.seeds[0]
        tables, meta = load_dataset(
            "canonical:adult-census",
            volume=args.volume, seed=seed, stratify_by="class",
        )
        gt = compute_gt_adult(tables["adult"])
        payload = build_payload_linha_a(tables, level=args.level)
        system_text = LINHA_A_SYSTEM_PROMPT.format(payload=payload)
        sample_q = "Quantas linhas existem na tabela adult?"

        print(f"  Adult vol={args.volume} seed={seed} TCF L{args.level}:")
        print(f"    payload chars: {len(payload):,}")
        print(f"    GT: {gt}")
        print()

        print(f"  Per-model token counts + projected cost:")
        print(f"  {'Model':<22} {'sys_tok':>8} {'q_tok':>6} {'no-cache':>10} {'cached':>10} {'savings':>9}")
        print(f"  {'-'*22} {'-'*8} {'-'*6} {'-'*10} {'-'*10} {'-'*9}")
        total_no_cache = 0.0
        total_cached = 0.0
        for m in args.models:
            available = client.is_available(m)
            try:
                if available:
                    tok_system = client.count_tokens(m, system_text)
                    tok_user = client.count_tokens(m, sample_q)
                else:
                    # Fallback when no API key: tiktoken (OpenAI) works locally,
                    # Anthropic count_tokens needs key — use chars/4 heuristic.
                    if not m.startswith("claude"):
                        tok_system = client.count_tokens(m, system_text)
                        tok_user = client.count_tokens(m, sample_q)
                    else:
                        tok_system = len(system_text) // 4
                        tok_user = len(sample_q) // 4
            except Exception:
                tok_system = len(system_text) // 4
                tok_user = len(sample_q) // 4

            tok_input = tok_system + tok_user
            est_output = 50

            no_cache_per_call = estimate_cost(m, tok_input, est_output)
            no_cache_total = no_cache_per_call * n_calls_per_model

            # With caching: tok_system cached after 1 write per seed group
            pricing = PRICING.get(m, (0, 0, None))
            if pricing[2] is not None:
                # 1 cache write per seed (full price), n-1 reads at cached price
                writes = estimate_cost(m, tok_system, 0) * n_seed_groups
                reads = (
                    (tok_system / 1_000_000) * pricing[2]
                    * (n_calls_per_model - n_seed_groups)
                )
                per_call_extra = (
                    (tok_user / 1_000_000) * pricing[0]
                    + (est_output / 1_000_000) * pricing[1]
                ) * n_calls_per_model
                cached_total = writes + reads + per_call_extra
            else:
                cached_total = no_cache_total  # no caching tier

            savings = (1 - cached_total / no_cache_total) * 100 if no_cache_total > 0 else 0
            total_no_cache += no_cache_total
            total_cached += cached_total

            print(f"  {m:<22} {tok_system:>8} {tok_user:>6} ${no_cache_total:>9.3f} ${cached_total:>9.3f} {savings:>7.1f}%")

        print(f"  {'-'*22} {'-'*8} {'-'*6} {'-'*10} {'-'*10} {'-'*9}")
        print(f"  {'TOTAL':<22} {'':>8} {'':>6} ${total_no_cache:>9.3f} ${total_cached:>9.3f}")
        if args.max_cost_usd:
            print(f"\n  Budget cap: ${args.max_cost_usd:.2f}")
            if total_cached > args.max_cost_usd:
                print(f"  WARNING: cached estimate exceeds budget cap!")
        print(f"\n  Payload preview (first 400 chars):")
        print(payload[:400])
        return

    levels = tuple(iter_levels(args.naturalness))
    run_m_acomm(args.models, args.volume, args.seeds, args.level, args.max_cost_usd,
                naturalness=levels)


if __name__ == "__main__":
    main()

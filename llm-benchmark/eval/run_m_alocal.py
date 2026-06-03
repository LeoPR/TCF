"""M-Alocal — Linha A (LLM lê TCF e calcula) em modelos LOCAIS sobre canonical.

Controle direto para M-Acomm: reproduz F-Q12 em canonical Adult com modelos
locais. Sem isso, M-Acomm não tem baseline limpo (F-Q12 antiga foi medida em
synthetic com método antigo).

Compartilha tudo com M-Acomm exceto o cliente:
- Mesmas 7 questions Adult
- Mesmo prompt Linha A (LLM lê TCF L2 + responde valor)
- Mesmo Adult vol=100 stratify_by='class'
- Cliente Ollama em vez de comercial

Hipóteses a confirmar:
- H_F-Q12: locais 7-14B saturam em ~60-70% Linha A (reproduz finding antigo
  em método novo)
- H_local_universal: se locais fazem 100% em Linha A em Adult, F-Q12 era
  artefato do synthetic e Linha B perde parte de sua justificativa

Design: 3 modelos locais × 7 questions × 3 seeds = 63 calls (~15min Ollama).
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

from llm_eval.ollama_client import OllamaClient
from llm_eval.metrics import score_response, _LEGACY_CONFIG
from llm_eval.question_naturalness import (
    NaturalnessLevel, get_questions as get_natural_questions, iter_levels,
)
from run_m9_adult import compute_gt_adult, build_questions_adult
from run_m_acomm import LINHA_A_PROMPT, build_payload_linha_a
from data_sources import load_dataset


RESULTS_DIR = ROOT / "experiments" / "results" / "m_alocal"

DEFAULT_MODELS = ["qwen3:14b", "phi4:latest", "qwen2.5-coder:7b"]

LLM_OPTIONS = {
    "temperature": 0, "seed": 42, "keep_alive": "30m",
    "num_ctx": 8192, "num_predict": 256,
}


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


def run_m_alocal(
    models: list[str], volume: int, seeds: list[int], level: int, endpoint: str,
    naturalness: tuple[NaturalnessLevel, ...] = (NaturalnessLevel.N0,),
) -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    manifest_path = RESULTS_DIR / "manifest.jsonl"
    client = OllamaClient(endpoint)
    completed = _load_completed(manifest_path)

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
            "stratification_metrics": meta.get("_stratification_metrics", []),
        }

    combos = []
    for seed in seeds:
        for model in models:
            for nl in naturalness:
                questions = get_natural_questions("adult-census", nl)
                for q_name, q in questions.items():
                    key = f"malocal|{model}|vol{volume}|L{level}|s{seed}|{nl.value}|{q_name}"
                    if key in completed:
                        continue
                    combos.append({
                        "key": key, "model": model, "seed": seed,
                        "naturalness": nl, "q_name": q_name, "q": q,
                    })

    total = len(seeds) * len(models) * len(naturalness) * 7
    levels_str = ",".join(nl.value for nl in naturalness)
    print(f"[M-Alocal] {len(models)}m x 7q x {len(seeds)}s x {len(naturalness)}lvl ({levels_str}) = {total} combos")
    print(f"           {len(combos)} to run, {len(completed)} cached\n")

    seed0 = seeds[0]
    print(f"  Preview seed={seed0}, vol={volume}, TCF L{level}:")
    print(f"  GT: {per_seed[seed0]['gt']}")
    print(f"  payload chars: {len(per_seed[seed0]['payload']):,}\n")

    t_start = time.time()
    warmed: set[str] = set()

    for i, c in enumerate(combos, 1):
        model = c["model"]
        state = per_seed[c["seed"]]

        if model not in warmed:
            print(f"  warming {model} ...")
            try:
                client.generate(model, "ok",
                                options={**LLM_OPTIONS, "num_predict": 2, "think": False},
                                timeout=300)
            except Exception as e:
                print(f"  warm failed: {e}", file=sys.stderr)
            warmed.add(model)

        prompt = LINHA_A_PROMPT.format(
            payload=state["payload"], question=c["q"]["text"],
        )
        elapsed = time.time() - t_start
        print(f"  [{i}/{len(combos)} el={elapsed:.0f}s] {c['key']}", end=" ", flush=True)

        call_options = {**LLM_OPTIONS, "think": False}
        response, ok, reason, total_ms = "", False, "exception", 0
        prompt_tokens, response_tokens = 0, 0

        for attempt in (1, 2):
            try:
                result = client.generate(model, prompt, options=call_options)
                response = result["text"]
                total_ms = result.get("total_duration_ns", 0) // 1_000_000
                prompt_tokens = result.get("prompt_tokens", 0)
                response_tokens = result.get("response_tokens", 0)
                expected = state["gt"][c["q"]["key"]]
                ok, reason = score_response(response, expected, c["q"]["key"], config=_LEGACY_CONFIG)
                print(f"{'OK' if ok else 'NO'} ({reason})")
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
            "key": c["key"], "phase": "m_alocal", "model": model,
            "dataset": "adult-census", "variant": "linha_a_tcf_local",
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
            "ok": ok, "reason": reason,
            "expected": str(state["gt"][c["q"]["key"]]),
            "prompt_chars": len(prompt), "total_ms": total_ms,
            "prompt_tokens": prompt_tokens, "response_tokens": response_tokens,
        }
        with open(manifest_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")

    print_summary(manifest_path)


def print_summary(manifest_path: Path) -> None:
    if not manifest_path.exists():
        print("[M-Alocal] No records.")
        return
    by_key: dict[str, dict] = {}
    for line in manifest_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        by_key[r["key"]] = r
    records = list(by_key.values())

    total = len(records)
    ok = sum(r["ok"] for r in records)

    print(f"\n=== M-Alocal Summary ({total} records) ===")
    print(f"  Overall: {ok}/{total} = {ok/total*100:.1f}%")
    print(f"  Reference baselines:")
    print(f"    F-Q12 (synthetic, antigo): ~60-70% ceiling esperado")
    print(f"    M9-Adult Linha B (mesmo dataset): 100% (com SQL execution)\n")

    questions = ["q_count", "q_avg_age", "q_max_age", "q_distinct_workclass",
                 "q_top_education", "q_count_high_class", "q_avg_hours_male"]

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

    print("  Per model:")
    for m in sorted(by_m):
        oks = by_m[m]
        lo, hi = wilson_ci(sum(oks), len(oks))
        print(f"    {m:<22} {sum(oks)}/{len(oks)} = {sum(oks)/len(oks)*100:>5.1f}%  CI [{lo*100:.1f}%, {hi*100:.1f}%]")

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


def main() -> None:
    parser = argparse.ArgumentParser(description="M-Alocal - Linha A em locais (controle de M-Acomm)")
    parser.add_argument("--models", nargs="+", default=DEFAULT_MODELS)
    parser.add_argument("--seeds", nargs="+", type=int, default=[42, 123, 7])
    parser.add_argument("--volume", type=int, default=100)
    parser.add_argument("--level", type=int, default=2, choices=[0, 1, 2, 3])
    parser.add_argument("--endpoint", default="http://localhost:11434")
    parser.add_argument(
        "--naturalness", default="N0",
        help="Naturalness level(s): N0|N1|N2|N3|all|comma-separated. Default: N0 (legacy).",
    )
    parser.add_argument("--summary", action="store_true")
    args = parser.parse_args()

    if args.summary:
        print_summary(RESULTS_DIR / "manifest.jsonl")
        return

    levels = tuple(iter_levels(args.naturalness))
    run_m_alocal(args.models, args.volume, args.seeds, args.level,
                 args.endpoint, naturalness=levels)


if __name__ == "__main__":
    main()

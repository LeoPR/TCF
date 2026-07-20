"""E-stats-ablation — TCF accuracy WITH vs WITHOUT STATS hints.

Tests whether models are reading STATS lines instead of computing from data.
Motivated by F81: gemma3:12b scores 88% on TCF L0 in Etapa 2, but 0% on
math_control and 0% on decode_only — it reads STATS, doesn't compute.

Design:
    4 models × 4 format variants × 8 questions = 128 combos
    Format variants: TCF L0+stats, L0-stats, L2+stats, L2-stats

Usage:
    python experiments/eval/run_stats_ablation.py
    python experiments/eval/run_stats_ablation.py --models gemma3:12b qwen3:8b
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

from tcf import encode as tcf_encode, EncodeConfig
from tests.fixtures import _write_fixture
from tests.fixtures.synthetic_v2 import retail_sales

from llm_eval.ollama_client import OllamaClient
from llm_eval.metrics import extract_number, strip_think

RESULTS_DIR = ROOT / "experiments" / "results" / "stats_ablation"
LLM_OPTIONS = {"temperature": 0, "seed": 42}

DEFAULT_MODELS = [
    "gemma3:12b",    # STATS reader (F81)
    "qwen3:8b",      # genuine calculator (F82)
    "phi4:latest",   # good in Etapa 2, unknown mechanism
    "llama3.1:8b",   # medium, unknown mechanism
]

SCALE = 200
SEED = 42

# 4 format variants: stats on/off × L0/L2
FORMAT_VARIANTS = {
    "tcf_L0_stats":   {"level": 0, "stats": True},
    "tcf_L0_nostats": {"level": 0, "stats": False},
    "tcf_L2_stats":   {"level": 2, "stats": True},
    "tcf_L2_nostats": {"level": 2, "stats": False},
}

SYSTEM_PROMPTS = {
    "tcf_L0_stats":   "Voce recebera dados em formato colunar. Cada bloco comeca com nome da coluna. Valores um por linha, mesma ordem entre colunas. Responda com base apenas nos dados.",
    "tcf_L0_nostats": "Voce recebera dados em formato colunar. Cada bloco comeca com nome da coluna. Valores um por linha, mesma ordem entre colunas. Responda com base apenas nos dados.",
    "tcf_L2_stats":   "Voce recebera dados em formato colunar comprimido. N*val = val repetido N vezes. Dados ordenados para agrupar repeticoes. Responda com base apenas nos dados.",
    "tcf_L2_nostats": "Voce recebera dados em formato colunar comprimido. N*val = val repetido N vezes. Dados ordenados para agrupar repeticoes. Responda com base apenas nos dados.",
}

QUESTIONS = {
    "q1_sum": {"template": "Qual e a soma de todos os valores da coluna 'total'? Responda apenas com um numero.", "key": "sum_total", "type": "numeric"},
    "q2_avg": {"template": "Qual e a media dos valores de 'total'? Responda apenas com um numero.", "key": "avg_total", "type": "numeric"},
    "q3_max": {"template": "Qual e o maior valor de 'total'? Responda apenas com um numero.", "key": "max_total", "type": "numeric"},
    "q4_min": {"template": "Qual e o menor valor de 'total'? Responda apenas com um numero.", "key": "min_total", "type": "numeric"},
    "q5_count": {"template": "Quantas linhas existem nos dados? Responda com um numero inteiro.", "key": "count", "type": "count"},
    "q6_top_product": {"template": "Qual produto aparece mais vezes? Responda com o nome do produto.", "key": "top_product", "type": "string"},
    "q7_top_spender": {"template": "Qual pessoa gastou o maior total? Responda com o nome da pessoa.", "key": "top_spender", "type": "string"},
    "q8_distinct": {"template": "Quantos clientes distintos aparecem nos dados? Responda com um numero inteiro.", "key": "distinct_customers", "type": "count"},
}


def _compute_gt(tables):
    clientes = {c["id"]: c["nome"] for c in tables["clientes"]}
    produtos = {p["id"]: p["nome"] for p in tables["produtos"]}
    vendas = tables["vendas"]
    totals = [float(v["total"]) for v in vendas if v["total"]]
    n = len(vendas)
    person_totals = defaultdict(float)
    for v in vendas:
        person_totals[clientes.get(v["id_cliente"], "")] += float(v["total"]) if v["total"] else 0
    prod_counter = Counter(v["id_produto"] for v in vendas)
    top_pid = prod_counter.most_common(1)[0][0]
    return {
        "sum_total": round(sum(totals), 2),
        "avg_total": round(sum(totals) / n, 2) if n else 0,
        "max_total": max(totals), "min_total": min(totals),
        "count": n,
        "top_product": produtos.get(top_pid, top_pid),
        "top_spender": max(person_totals, key=person_totals.get),
        "distinct_customers": len(set(v["id_cliente"] for v in vendas)),
    }


def _score(q, response, gt):
    expected = gt[q["key"]]
    if q["type"] == "string":
        clean = strip_think(response).strip().lower()
        ok = str(expected).lower() in clean
        return ok, "correct" if ok else "wrong_name"
    val = extract_number(response)
    if val is None:
        return False, "parse_failure"
    if q["type"] == "count":
        ok = int(round(val)) == int(expected)
        return ok, "correct" if ok else "wrong_count"
    exp_f = float(expected)
    tol = max(abs(exp_f) * 0.02, 0.5)
    ok = abs(val - exp_f) <= tol
    return ok, "correct" if ok else "arithmetic_error"


def run(models: list[str], endpoint: str) -> None:
    client = OllamaClient(endpoint)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    manifest_path = RESULTS_DIR / "manifest.jsonl"

    completed: set[str] = set()
    if manifest_path.exists():
        for line in manifest_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:
                    completed.add(json.loads(line)["key"])
                except (json.JSONDecodeError, KeyError):
                    pass

    # Generate data
    tables, meta = retail_sales(n_orders=SCALE, seed=SEED)
    gt = _compute_gt(tables)

    # Generate TCF variants
    meta_path, data_dir = _write_fixture(tables, meta)
    data_blocks = {}
    for fmt_name, cfg in FORMAT_VARIANTS.items():
        data_blocks[fmt_name] = tcf_encode(
            str(meta_path), str(data_dir),
            EncodeConfig(level=cfg["level"], include_stats=cfg["stats"]),
        )

    n_vendas = len(tables["vendas"])
    print(f"[STATS Ablation] data: retail_sales({SCALE}) -> {n_vendas} vendas")
    for fmt_name, text in data_blocks.items():
        has_stats = "# STATS" in text
        print(f"  {fmt_name:20s} {len(text):>7} chars  STATS={'YES' if has_stats else 'NO'}")

    formats = list(FORMAT_VARIANTS.keys())
    questions = list(QUESTIONS.keys())
    total = len(models) * len(formats) * len(questions)
    print(f"[STATS Ablation] {total} combos, {len(completed)} cached")

    warmed: set[str] = set()
    i = 0

    for model in models:
        for fmt in formats:
            for q_name in questions:
                i += 1
                key = f"{model}|{fmt}|{q_name}"
                if key in completed:
                    continue

                if model not in warmed:
                    print(f"  [warmup] {model} ... ", end="", flush=True)
                    try:
                        client.generate(model=model, prompt="2+2=?", options=LLM_OPTIONS)
                        print("ready")
                    except Exception as e:
                        print(f"SKIP ({e})")
                        warmed.add(model)
                        break
                    warmed.add(model)

                q = QUESTIONS[q_name]
                prompt = (
                    f"<s>SYSTEM> {SYSTEM_PROMPTS[fmt]}</s>\n"
                    f"<s>CONTEXT>\n{data_blocks[fmt]}\n</s>\n"
                    f"<s>USER> {q['template']}</s>\n"
                    "<s>ASSISTANT>"
                )

                label = f"{fmt:20s} {q_name:18s}"
                print(f"  [{i}/{total}] {model:25s} {label} ", end="", flush=True)

                try:
                    t0 = time.perf_counter()
                    gen = client.generate(model=model, prompt=prompt, options=LLM_OPTIONS)
                    latency = time.perf_counter() - t0
                    response = gen["text"].strip()
                    correct, error_type = _score(q, response, gt)
                    result = {
                        "key": key, "model": model, "format": fmt,
                        "question": q_name, "has_stats": FORMAT_VARIANTS[fmt]["stats"],
                        "level": FORMAT_VARIANTS[fmt]["level"],
                        "correct": correct, "error_type": error_type,
                        "response": response[:200], "latency_s": round(latency, 1),
                        "prompt_chars": len(prompt),
                        "prompt_tokens": gen.get("prompt_tokens", 0),
                        "response_tokens": gen.get("response_tokens", 0),
                    }
                except KeyboardInterrupt:
                    print("\n[interrupted]")
                    sys.exit(0)
                except Exception as exc:
                    result = {
                        "key": key, "model": model, "format": fmt,
                        "question": q_name, "has_stats": FORMAT_VARIANTS[fmt]["stats"],
                        "level": FORMAT_VARIANTS[fmt]["level"],
                        "correct": False, "error_type": "exception",
                        "response": "", "latency_s": 0, "prompt_chars": 0,
                        "error": str(exc)[:200],
                    }

                with manifest_path.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(result, ensure_ascii=False) + "\n")
                completed.add(key)
                print("OK" if result["correct"] else "FAIL", f"{result['latency_s']}s")

    # ── Analysis ──
    entries = [json.loads(l) for l in manifest_path.read_text(encoding="utf-8").splitlines() if l.strip()]

    print(f"\n{'='*70}")
    print(f"STATS ABLATION ({len(entries)} entries)")
    print(f"{'='*70}")

    # Main comparison: stats vs nostats
    print(f"\n{'Model':>25} {'L0+stats':>10} {'L0-stats':>10} {'delta':>7} {'L2+stats':>10} {'L2-stats':>10} {'delta':>7}")
    print("-" * 85)

    for model in models:
        row = f"{model:>25}"
        for level in [0, 2]:
            for has_stats in [True, False]:
                vals = [e["correct"] for e in entries
                        if e["model"] == model and e["level"] == level and e["has_stats"] == has_stats]
                acc = sum(vals) / len(vals) if vals else 0
                row += f" {acc:>9.0%}"
            # delta
            with_s = [e["correct"] for e in entries
                      if e["model"] == model and e["level"] == level and e["has_stats"]]
            without_s = [e["correct"] for e in entries
                         if e["model"] == model and e["level"] == level and not e["has_stats"]]
            if with_s and without_s:
                delta = (sum(with_s)/len(with_s)) - (sum(without_s)/len(without_s))
                row += f" {delta:>+6.0%}"
            else:
                row += "      ?"
        print(row)

    # Per question breakdown
    print(f"\n{'Model':>25} {'Question':>18} {'L0+S':>6} {'L0-S':>6} {'L2+S':>6} {'L2-S':>6}")
    print("-" * 70)
    for model in models:
        for q_name in questions:
            row = f"{model:>25} {q_name:>18}"
            for level in [0, 2]:
                for has_stats in [True, False]:
                    vals = [e["correct"] for e in entries
                            if e["model"] == model and e["level"] == level
                            and e["has_stats"] == has_stats and e["question"] == q_name]
                    if vals:
                        row += f" {'OK' if vals[0] else 'FAIL':>6}"
                    else:
                        row += "      ?"
            print(row)

    # Save summary
    summary = {}
    for model in models:
        summary[model] = {}
        for fmt in formats:
            cfg = FORMAT_VARIANTS[fmt]
            vals = [e["correct"] for e in entries if e["model"] == model and e["format"] == fmt]
            summary[model][fmt] = round(sum(vals) / len(vals), 3) if vals else None
    (RESULTS_DIR / "summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )


def main():
    parser = argparse.ArgumentParser(description="STATS Ablation: with vs without STATS hints")
    parser.add_argument("--models", nargs="+", default=DEFAULT_MODELS)
    parser.add_argument("--endpoint", default="http://localhost:11434")
    args = parser.parse_args()
    run(args.models, args.endpoint)


if __name__ == "__main__":
    main()

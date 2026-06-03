"""G30 — Hyperparameter ablation: thinking on/off, temperature.

Tests with qwen3:8b (has thinking toggle) on retail_200 data.
Compares: thinking ON (default) vs OFF (/no_think suffix).

Usage:
    python experiments/eval/run_g30_hyperparams.py
"""

from __future__ import annotations
import json
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from tcf import encode as tcf_encode, EncodeConfig
from tests.fixtures import _write_fixture
from tests.fixtures.synthetic_v2 import retail_sales

from llm_eval.ollama_client import OllamaClient
from llm_eval.metrics import score_response, extract_number, strip_think

RESULTS_DIR = ROOT / "experiments" / "results" / "g30_hyperparams"

SYSTEM_PROMPTS = {
    "tcf_L0": "Voce recebera dados em formato colunar. Cada bloco comeca com nome da coluna. Valores um por linha, mesma ordem entre colunas. Responda com base apenas nos dados.",
    "tcf_L2": "Voce recebera dados em formato colunar comprimido. N*val = val repetido N vezes. Dados ordenados para agrupar repeticoes. Responda com base apenas nos dados.",
}

QUESTIONS = {
    "q1_sum": {"template": "Qual e a soma de todos os valores da coluna 'total'? Responda apenas com um numero.", "key": "sum_total", "type": "numeric"},
    "q2_avg": {"template": "Qual e a media dos valores de 'total'? Responda apenas com um numero.", "key": "avg_total", "type": "numeric"},
    "q3_max": {"template": "Qual e o maior valor de 'total'? Responda apenas com um numero.", "key": "max_total", "type": "numeric"},
    "q5_count": {"template": "Quantas linhas existem nos dados? Responda com um numero inteiro.", "key": "count", "type": "count"},
    "q6_top_product": {"template": "Qual produto aparece mais vezes? Responda com o nome do produto.", "key": "top_product", "type": "string"},
    "q7_top_spender": {"template": "Qual pessoa gastou o maior total? Responda com o nome da pessoa.", "key": "top_spender", "type": "string"},
}


def _compute_gt(tables):
    from collections import Counter
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
        "sum_total": round(sum(totals), 2), "avg_total": round(sum(totals) / n, 2) if n else 0,
        "max_total": max(totals), "count": n,
        "top_product": produtos.get(top_pid, top_pid),
        "top_spender": max(person_totals, key=person_totals.get),
    }


def _score(q, response, gt):
    expected = gt[q["key"]]
    if q["type"] == "string":
        clean = strip_think(response).strip().lower()
        return str(expected).lower() in clean, "correct" if str(expected).lower() in clean else "wrong"
    val = extract_number(response)
    if val is None:
        return False, "parse_failure"
    if q["type"] == "count":
        return int(round(val)) == int(expected), "correct" if int(round(val)) == int(expected) else "wrong"
    tol = max(abs(float(expected)) * 0.02, 0.5)
    ok = abs(val - float(expected)) <= tol
    return ok, "correct" if ok else "arithmetic_error"


def main():
    client = OllamaClient()

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

    tables, meta = retail_sales(n_orders=200, seed=42)
    gt = _compute_gt(tables)
    meta_path, data_dir = _write_fixture(tables, meta)

    data_blocks = {
        "tcf_L0": tcf_encode(str(meta_path), str(data_dir), EncodeConfig(level=0, include_stats=True)),
        "tcf_L2": tcf_encode(str(meta_path), str(data_dir), EncodeConfig(level=2, include_stats=True)),
    }

    # Configs to test
    configs = [
        {"name": "think_on_t0", "think": True, "temperature": 0},
        {"name": "think_off_t0", "think": False, "temperature": 0},
        {"name": "think_on_t06", "think": True, "temperature": 0.6},
        {"name": "think_off_t06", "think": False, "temperature": 0.6},
    ]

    model = "qwen3:8b"
    formats = list(data_blocks.keys())
    questions = list(QUESTIONS.keys())

    total = len(configs) * len(formats) * len(questions)
    print(f"[G30] {total} combinations, {len(completed)} cached")

    # Warmup
    print(f"  [warmup] {model} ... ", end="", flush=True)
    client.generate(model=model, prompt="2+2=?", options={"temperature": 0})
    print("ready")

    for cfg in configs:
        cfg_name = cfg["name"]
        think_suffix = "" if cfg["think"] else " /no_think"
        options = {"temperature": cfg["temperature"], "seed": 42}

        for fmt in formats:
            for q_name in questions:
                key = f"{model}|{cfg_name}|{fmt}|{q_name}"
                if key in completed:
                    continue

                q = QUESTIONS[q_name]
                prompt = (
                    f"<s>SYSTEM> {SYSTEM_PROMPTS[fmt]}</s>\n"
                    f"<s>CONTEXT>\n{data_blocks[fmt]}\n</s>\n"
                    f"<s>USER> {q['template']}{think_suffix}</s>\n"
                    "<s>ASSISTANT>"
                )

                print(f"  {cfg_name:18s} {fmt:8s} {q_name:20s} ", end="", flush=True)

                try:
                    t0 = time.perf_counter()
                    gen = client.generate(model=model, prompt=prompt, options=options)
                    latency = time.perf_counter() - t0
                    response = gen["text"].strip()
                    correct, error_type = _score(q, response, gt)

                    result = {
                        "key": key, "model": model, "config": cfg_name,
                        "think": cfg["think"], "temperature": cfg["temperature"],
                        "format": fmt, "question": q_name,
                        "correct": correct, "error_type": error_type,
                        "response": response[:200], "latency_s": round(latency, 2),
                        "response_tokens": gen.get("eval_count", 0),
                    }
                except KeyboardInterrupt:
                    print("\n[interrupted]")
                    sys.exit(0)
                except Exception as exc:
                    result = {
                        "key": key, "model": model, "config": cfg_name,
                        "think": cfg["think"], "temperature": cfg["temperature"],
                        "format": fmt, "question": q_name,
                        "correct": False, "error_type": "exception",
                        "response": "", "latency_s": 0, "response_tokens": 0,
                        "error": str(exc)[:200],
                    }

                with manifest_path.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(result, ensure_ascii=False) + "\n")
                completed.add(key)
                print(f"{'OK' if result['correct'] else 'FAIL'} {result['latency_s']:.0f}s")

    # Analysis
    entries = [json.loads(l) for l in manifest_path.read_text(encoding="utf-8").splitlines() if l.strip()]

    print(f"\n{'='*70}")
    print(f"G30 RESULTS ({len(entries)} entries)")
    print(f"{'='*70}")

    print(f"\n{'Config':>20} {'Accuracy':>9} {'Avg latency':>12} {'Avg tokens':>11}")
    print("-" * 55)
    for cfg in configs:
        vals = [e for e in entries if e["config"] == cfg["name"]]
        acc = sum(e["correct"] for e in vals) / len(vals) if vals else 0
        avg_lat = sum(e["latency_s"] for e in vals) / len(vals) if vals else 0
        avg_tok = sum(e["response_tokens"] for e in vals) / len(vals) if vals else 0
        print(f"{cfg['name']:>20} {acc:>8.0%} {avg_lat:>11.1f}s {avg_tok:>10.0f}")

    # By config x format
    print(f"\n{'Config':>20}", end="")
    for fmt in formats:
        print(f" {fmt:>8}", end="")
    print()
    print("-" * (20 + 9 * len(formats)))
    for cfg in configs:
        print(f"{cfg['name']:>20}", end="")
        for fmt in formats:
            vals = [e["correct"] for e in entries if e["config"] == cfg["name"] and e["format"] == fmt]
            acc = sum(vals) / len(vals) if vals else 0
            print(f" {acc:>7.0%}", end="")
        print()

    (RESULTS_DIR / "summary.json").write_text(json.dumps({
        c["name"]: sum(e["correct"] for e in entries if e["config"] == c["name"]) /
        max(1, sum(1 for e in entries if e["config"] == c["name"]))
        for c in configs
    }, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()

"""Etapa 2 — Multiple models x fixed data (retail_200) x best formats.

Tests: CSV vs TCF L0 vs TCF L2 (best from Etapa 1)
Data: retail_sales(200) — fixed, realistic
Models: all available text models, sorted by size (fastest first)

Usage:
    python experiments/eval/run_etapa2.py
    python experiments/eval/run_etapa2.py --models qwen3:8b mistral:latest
"""

from __future__ import annotations
import argparse
import csv as csv_mod
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
from llm_eval.models import fetch_local_models

RESULTS_DIR = ROOT / "experiments" / "results" / "etapa2"
LLM_OPTIONS = {"temperature": 0, "seed": 42}
VISION_FAMILIES = {"mllama", "qwen3vl", "llava", "moondream"}

# Fixed dataset
SCALE = 200
SEED = 42

# Formats to test (best from Etapa 1 + CSV baseline)
FORMATS = ["csv", "tcf_L0", "tcf_L2"]

SYSTEM_PROMPTS = {
    "csv": "Voce recebera dados CSV. Primeira linha = colunas, demais = registros. Responda com base apenas nos dados.",
    "tcf_L0": "Voce recebera dados em formato colunar. Cada bloco comeca com nome da coluna. Valores um por linha, mesma ordem entre colunas. Responda com base apenas nos dados.",
    "tcf_L2": "Voce recebera dados em formato colunar comprimido. N*val = val repetido N vezes. Dados ordenados para agrupar repeticoes. Responda com base apenas nos dados.",
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

    # Prepare data (fixed)
    tables, meta = retail_sales(n_orders=SCALE, seed=SEED)
    gt = _compute_gt(tables)

    clientes = {c["id"]: c["nome"] for c in tables["clientes"]}
    produtos = {p["id"]: p["nome"] for p in tables["produtos"]}

    csv_lines = ["pessoa,produto,dt,qtd,preco_unit,total"]
    for v in tables["vendas"]:
        csv_lines.append(f"{clientes.get(v['id_cliente'],'')},"
                         f"{produtos.get(v['id_produto'],'')},"
                         f"{v['dt']},{v['qtd']},{v['preco_unit']},{v['total']}")

    meta_path, data_dir = _write_fixture(tables, meta)
    data_blocks = {
        "csv": "\n".join(csv_lines),
        "tcf_L0": tcf_encode(str(meta_path), str(data_dir), EncodeConfig(level=0, include_stats=True)),
        "tcf_L2": tcf_encode(str(meta_path), str(data_dir), EncodeConfig(level=2, include_stats=True)),
    }

    n_vendas = len(tables["vendas"])
    print(f"[Etapa 2] data: retail_sales({SCALE}) -> {n_vendas} vendas")
    for fmt in FORMATS:
        print(f"  {fmt:10s} {len(data_blocks[fmt]):>7} chars")

    questions = list(QUESTIONS.keys())
    total = len(models) * len(FORMATS) * len(questions)
    print(f"[Etapa 2] {total} combinations, {len(completed)} cached")

    warmed: set[str] = set()
    i = 0

    for model in models:
        for fmt in FORMATS:
            for q_name in questions:
                i += 1
                key = f"{model}|{SCALE}|{fmt}|{q_name}"
                if key in completed:
                    continue

                if model not in warmed:
                    print(f"  [warmup] {model} ... ", end="", flush=True)
                    try:
                        client.generate(model=model, prompt="2+2=?", options=LLM_OPTIONS)
                        print("ready")
                    except Exception as e:
                        print(f"failed: {e}")
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

                print(f"  [{i}/{total}] {model:25s} {fmt:8s} {q_name:20s} ", end="", flush=True)

                try:
                    t0 = time.perf_counter()
                    gen = client.generate(model=model, prompt=prompt, options=LLM_OPTIONS)
                    latency = time.perf_counter() - t0
                    response = gen["text"].strip()
                    correct, error_type = _score(q, response, gt)
                    result = {
                        "key": key, "model": model, "scale": SCALE,
                        "format": fmt, "question": q_name,
                        "correct": correct, "error_type": error_type,
                        "response": response[:200], "latency_s": round(latency, 2),
                        "prompt_chars": len(prompt),
                        "prompt_tokens": gen.get("prompt_tokens", 0),
                        "response_tokens": gen.get("response_tokens", 0),
                    }
                except KeyboardInterrupt:
                    print("\n[interrupted]")
                    sys.exit(0)
                except Exception as exc:
                    result = {
                        "key": key, "model": model, "scale": SCALE,
                        "format": fmt, "question": q_name,
                        "correct": False, "error_type": "exception",
                        "response": "", "latency_s": 0, "prompt_chars": 0,
                        "error": str(exc)[:200],
                    }

                with manifest_path.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(result, ensure_ascii=False) + "\n")
                completed.add(key)
                print("OK" if result["correct"] else "FAIL")

    # Analysis
    entries = [json.loads(l) for l in manifest_path.read_text(encoding="utf-8").splitlines() if l.strip()]

    print(f"\n{'='*70}")
    print(f"ETAPA 2 RESULTS ({len(entries)} entries)")
    print(f"{'='*70}")

    print(f"\n{'Model':>25}", end="")
    for fmt in FORMATS:
        print(f" {fmt:>8}", end="")
    print(f" {'avg':>6}")
    print("-" * (25 + 9 * len(FORMATS) + 7))

    for model in models:
        print(f"{model:>25}", end="")
        accs = []
        for fmt in FORMATS:
            vals = [e["correct"] for e in entries if e["model"] == model and e["format"] == fmt]
            acc = sum(vals) / len(vals) if vals else 0
            accs.append(acc)
            print(f" {acc:>7.0%}", end="")
        print(f" {sum(accs)/len(accs):>5.0%}")

    (RESULTS_DIR / "summary.json").write_text(json.dumps({
        m: {f: sum(e["correct"] for e in entries if e["model"] == m and e["format"] == f) /
            max(1, sum(1 for e in entries if e["model"] == m and e["format"] == f))
            for f in FORMATS} for m in models
    }, indent=2), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Etapa 2: multiple models x fixed data")
    parser.add_argument("--models", nargs="+", default=["auto"])
    parser.add_argument("--endpoint", default="http://localhost:11434")
    args = parser.parse_args()

    if args.models == ["auto"]:
        all_m = fetch_local_models(args.endpoint)
        text_m = [m for m in all_m if m.get("family") not in VISION_FAMILIES]
        # Sort by param size ascending (fastest first)
        text_m.sort(key=lambda m: float(m.get("parameter_size", "0").replace("B", "").replace("M", "")))
        models = [m["name"] for m in text_m]
        print(f"[Etapa 2] auto-selected {len(models)} models: {models}")
    else:
        models = args.models

    run(models, args.endpoint)


if __name__ == "__main__":
    main()

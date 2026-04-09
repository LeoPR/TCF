"""Etapa 1 — Compression levels x Data scale x Single strong model (qwen3).

Tests TCF v0.2 levels (L0, L2, L3) vs CSV vs JSONL
using retail_sales v2 synthetic data at multiple scales.
Single model (qwen3:8b) to isolate data/format effects from model effects.

Usage:
    python experiments/eval/run_etapa1.py
    python experiments/eval/run_etapa1.py --scales 50 200
    python experiments/eval/run_etapa1.py --model qwen2.5:latest
"""

from __future__ import annotations
import argparse
import csv as csv_mod
import io
import json
import sys
import time
from collections import defaultdict, Counter
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

RESULTS_DIR = ROOT / "experiments" / "results" / "etapa1"
LLM_OPTIONS = {"temperature": 0, "seed": 42}

# System prompts per format
SYSTEM_PROMPTS = {
    "csv": "Voce recebera dados CSV. Primeira linha = colunas, demais = registros. Responda com base apenas nos dados.",
    "jsonl": "Voce recebera dados JSON Lines. Cada linha e um objeto independente. Responda com base apenas nos dados.",
    "tcf_L0": "Voce recebera dados em formato colunar. Cada bloco comeca com nome da coluna. Valores um por linha, na mesma ordem entre colunas. Responda com base apenas nos dados.",
    "tcf_L2": "Voce recebera dados em formato colunar comprimido. N*val = val repetido N vezes. Dados ordenados para agrupar repeticoes. Responda com base apenas nos dados.",
    "tcf_L3": "Voce recebera dados em formato colunar com dicionario. '# dict col: v1,v2' define valores. Nos dados, numeros sao indices (0=primeiro). N*val = val repetido N vezes. Responda com base apenas nos dados.",
}


# ---------------------------------------------------------------------------
# Ground truth computation (dynamic, from generated data)
# ---------------------------------------------------------------------------

def _compute_ground_truth(tables: dict, metadata: dict) -> dict[str, Any]:
    """Compute ground truth from retail_sales tables."""
    clientes = {c["id"]: c["nome"] for c in tables["clientes"]}
    produtos = {p["id"]: p["nome"] for p in tables["produtos"]}
    vendas = tables["vendas"]

    totals = [float(v["total"]) for v in vendas if v["total"]]
    n = len(vendas)

    # Per-person aggregation
    person_totals: dict[str, float] = defaultdict(float)
    person_counts: dict[str, int] = defaultdict(int)
    for v in vendas:
        nome = clientes.get(v["id_cliente"], v["id_cliente"])
        person_totals[nome] += float(v["total"]) if v["total"] else 0
        person_counts[nome] += 1

    # Top customer (most orders)
    top_customer = max(person_counts, key=person_counts.get) if person_counts else ""

    # Product frequency
    prod_counter = Counter(v["id_produto"] for v in vendas)
    top_prod_id = prod_counter.most_common(1)[0][0] if prod_counter else ""
    top_product = produtos.get(top_prod_id, top_prod_id)

    # Top spender
    top_spender = max(person_totals, key=person_totals.get) if person_totals else ""

    return {
        "sum_total": round(sum(totals), 2),
        "avg_total": round(sum(totals) / n, 2) if n else 0,
        "max_total": max(totals) if totals else 0,
        "min_total": min(totals) if totals else 0,
        "count": n,
        "top_product": top_product,
        "top_customer": top_customer,
        "top_spender": top_spender,
        "distinct_customers": len(set(v["id_cliente"] for v in vendas)),
    }


# Questions adapted for retail_sales
QUESTIONS = {
    "q1_sum": {
        "template": "Qual e a soma de todos os valores da coluna 'total'? Responda apenas com um numero.",
        "key": "sum_total",
        "type": "numeric",
    },
    "q2_avg": {
        "template": "Qual e a media dos valores de 'total'? Responda apenas com um numero.",
        "key": "avg_total",
        "type": "numeric",
    },
    "q3_max": {
        "template": "Qual e o maior valor de 'total'? Responda apenas com um numero.",
        "key": "max_total",
        "type": "numeric",
    },
    "q4_min": {
        "template": "Qual e o menor valor de 'total'? Responda apenas com um numero.",
        "key": "min_total",
        "type": "numeric",
    },
    "q5_count": {
        "template": "Quantas linhas existem nos dados? Responda com um numero inteiro.",
        "key": "count",
        "type": "count",
    },
    "q6_top_product": {
        "template": "Qual produto aparece mais vezes? Responda com o nome do produto.",
        "key": "top_product",
        "type": "string",
    },
    "q7_top_spender": {
        "template": "Qual pessoa gastou o maior total? Responda com o nome da pessoa.",
        "key": "top_spender",
        "type": "string",
    },
    "q8_distinct": {
        "template": "Quantos clientes distintos aparecem nos dados? Responda com um numero inteiro.",
        "key": "distinct_customers",
        "type": "count",
    },
}


# ---------------------------------------------------------------------------
# Data preparation
# ---------------------------------------------------------------------------

def _prepare_data(tables: dict, metadata: dict) -> dict[str, str]:
    """Prepare all format variants from tables."""
    clientes = {c["id"]: c["nome"] for c in tables["clientes"]}
    produtos = {p["id"]: p["nome"] for p in tables["produtos"]}

    # CSV (flat, resolved names)
    lines = ["pessoa,produto,dt,qtd,preco_unit,total"]
    for v in tables["vendas"]:
        lines.append(f"{clientes.get(v['id_cliente'], v['id_cliente'])},"
                     f"{produtos.get(v['id_produto'], v['id_produto'])},"
                     f"{v['dt']},{v['qtd']},{v['preco_unit']},{v['total']}")
    csv_text = "\n".join(lines)

    # JSONL (flat, resolved)
    jsonl_lines = []
    for v in tables["vendas"]:
        jsonl_lines.append(json.dumps({
            "pessoa": clientes.get(v["id_cliente"], v["id_cliente"]),
            "produto": produtos.get(v["id_produto"], v["id_produto"]),
            "dt": v["dt"], "qtd": int(v["qtd"]) if v["qtd"] else 0,
            "preco_unit": float(v["preco_unit"]) if v["preco_unit"] else 0,
            "total": float(v["total"]) if v["total"] else 0,
        }, ensure_ascii=False))
    jsonl_text = "\n".join(jsonl_lines)

    # TCF levels
    meta_path, data_dir = _write_fixture(tables, metadata)
    tcf_texts = {}
    for level in [0, 2, 3]:
        tcf_texts[f"tcf_L{level}"] = tcf_encode(
            str(meta_path), str(data_dir),
            EncodeConfig(level=level, include_stats=True))

    return {"csv": csv_text, "jsonl": jsonl_text, **tcf_texts}


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def _score(question: dict, response: str, gt: dict) -> tuple[bool, str]:
    expected = gt[question["key"]]
    qtype = question["type"]

    if qtype == "string":
        clean = strip_think(response).strip().lower()
        ok = str(expected).lower() in clean
        return ok, "correct" if ok else "wrong_name"

    val = extract_number(response)
    if val is None:
        return False, "parse_failure"

    if qtype == "count":
        ok = int(round(val)) == int(expected)
        return ok, "correct" if ok else "wrong_count"

    # numeric
    exp_f = float(expected)
    tol = max(abs(exp_f) * 0.02, 0.5)  # 2% or 0.5 absolute
    ok = abs(val - exp_f) <= tol
    return ok, "correct" if ok else "arithmetic_error"


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run(model: str, scales: list[int], endpoint: str) -> None:
    client = OllamaClient(endpoint)
    if not client.is_available():
        print(f"[ERROR] Ollama not available at {endpoint}", file=sys.stderr)
        sys.exit(1)

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

    formats = ["csv", "jsonl", "tcf_L0", "tcf_L2", "tcf_L3"]
    questions = list(QUESTIONS.keys())

    # Warmup
    print(f"[warmup] {model} ... ", end="", flush=True)
    try:
        client.generate(model=model, prompt="2+2=?", options=LLM_OPTIONS)
        print("ready")
    except Exception as e:
        print(f"failed: {e}")

    all_results = []

    for scale in scales:
        print(f"\n[scale={scale}]")
        tables, meta = retail_sales(n_orders=scale, seed=42)
        gt = _compute_ground_truth(tables, meta)
        data_blocks = _prepare_data(tables, meta)
        n_vendas = len(tables["vendas"])

        # Show sizes
        for fmt in formats:
            print(f"  {fmt:10s} {len(data_blocks[fmt]):>7} chars")

        for fmt in formats:
            for q_name in questions:
                key = f"{model}|{scale}|{fmt}|{q_name}"
                if key in completed:
                    continue

                q = QUESTIONS[q_name]
                sys_prompt = SYSTEM_PROMPTS[fmt]
                prompt = (
                    f"<s>SYSTEM> {sys_prompt}</s>\n"
                    f"<s>CONTEXT>\n{data_blocks[fmt]}\n</s>\n"
                    f"<s>USER> {q['template']}</s>\n"
                    "<s>ASSISTANT>"
                )

                print(f"  {fmt:10s} {q_name:20s} ... ", end="", flush=True)

                try:
                    t0 = time.perf_counter()
                    gen = client.generate(model=model, prompt=prompt, options=LLM_OPTIONS)
                    latency = time.perf_counter() - t0
                    response = gen["text"].strip()
                    correct, error_type = _score(q, response, gt)

                    result = {
                        "key": key, "model": model, "scale": scale,
                        "n_vendas": n_vendas, "format": fmt, "question": q_name,
                        "correct": correct, "error_type": error_type,
                        "response": response[:200], "latency_s": round(latency, 2),
                        "prompt_chars": len(prompt),
                    }
                except KeyboardInterrupt:
                    print("\n[interrupted]")
                    sys.exit(0)
                except Exception as exc:
                    result = {
                        "key": key, "model": model, "scale": scale,
                        "n_vendas": n_vendas, "format": fmt, "question": q_name,
                        "correct": False, "error_type": "exception",
                        "response": "", "latency_s": 0, "prompt_chars": 0,
                        "error": str(exc)[:200],
                    }

                with manifest_path.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(result, ensure_ascii=False) + "\n")
                completed.add(key)
                all_results.append(result)

                print("OK" if result["correct"] else "FAIL")

    # Analysis
    _analyze(manifest_path, model, scales, formats, questions)


def _analyze(manifest_path: Path, model: str, scales: list[int],
             formats: list[str], questions: list[str]) -> None:
    entries = [json.loads(l) for l in manifest_path.read_text(encoding="utf-8").splitlines() if l.strip()]

    print(f"\n{'='*80}")
    print(f"ETAPA 1 RESULTS — {model} ({len(entries)} entries)")
    print(f"{'='*80}")

    # By scale x format
    print(f"\n{'Scale':>6}", end="")
    for fmt in formats:
        print(f" {fmt:>8}", end="")
    print()
    print("-" * (6 + 9 * len(formats)))

    for scale in scales:
        print(f"{scale:>6}", end="")
        for fmt in formats:
            vals = [e["correct"] for e in entries if e["scale"] == scale and e["format"] == fmt]
            acc = sum(vals) / len(vals) if vals else 0
            print(f" {acc:>7.0%}", end="")
        print()

    # By question (aggregated across scales)
    print(f"\n{'Question':>25}", end="")
    for fmt in formats:
        print(f" {fmt:>8}", end="")
    print()
    print("-" * (25 + 9 * len(formats)))

    for q in questions:
        print(f"{q:>25}", end="")
        for fmt in formats:
            vals = [e["correct"] for e in entries if e["question"] == q and e["format"] == fmt]
            acc = sum(vals) / len(vals) if vals else 0
            print(f" {acc:>7.0%}", end="")
        print()

    # Summary
    summary = {}
    for fmt in formats:
        vals = [e["correct"] for e in entries if e["format"] == fmt]
        summary[fmt] = sum(vals) / len(vals) if vals else 0
    print(f"\n{'OVERALL':>25}", end="")
    for fmt in formats:
        print(f" {summary[fmt]:>7.0%}", end="")
    print()

    (manifest_path.parent / "summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Etapa 1: compression x scale x single model")
    parser.add_argument("--model", default="qwen3:8b")
    parser.add_argument("--scales", nargs="+", type=int, default=[50, 200])
    parser.add_argument("--endpoint", default="http://localhost:11434")
    args = parser.parse_args()
    run(args.model, args.scales, args.endpoint)


if __name__ == "__main__":
    main()

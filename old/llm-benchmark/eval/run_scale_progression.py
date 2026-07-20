"""E-scale-progression — accuracy vs number of rows for CSV, TCF L0, TCF L2.

Tests a single strong model (gemma3:12b) at multiple data scales to find
the crossover point where TCF outperforms CSV.

Scales: 20, 50, 100, 200, 500, 1000
Formats: CSV, TCF L0, TCF L2
Questions: q1_sum, q3_max, q5_count, q6_top_product (4 representative)

Total: 6 scales × 3 formats × 4 questions = 72 combos

Usage:
    python experiments/eval/run_scale_progression.py
    python experiments/eval/run_scale_progression.py --model qwen3:8b
    python experiments/eval/run_scale_progression.py --scales 20 50 100
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

RESULTS_DIR = ROOT / "experiments" / "results" / "scale_progression"
LLM_OPTIONS = {"temperature": 0, "seed": 42}

DEFAULT_MODEL = "gemma3:12b"
DEFAULT_SCALES = [20, 50, 100, 200, 500, 1000]
FORMATS = ["csv", "tcf_L0", "tcf_L2"]
SEED = 42

SYSTEM_PROMPTS = {
    "csv": "Voce recebera dados CSV. Primeira linha = colunas, demais = registros. Responda com base apenas nos dados.",
    "tcf_L0": "Voce recebera dados em formato colunar. Cada bloco comeca com nome da coluna. Valores um por linha, mesma ordem entre colunas. Responda com base apenas nos dados.",
    "tcf_L2": "Voce recebera dados em formato colunar comprimido. N*val = val repetido N vezes. Dados ordenados para agrupar repeticoes. Responda com base apenas nos dados.",
}

QUESTIONS = {
    "q1_sum": {"template": "Qual e a soma de todos os valores da coluna 'total'? Responda apenas com um numero.", "key": "sum_total", "type": "numeric"},
    "q3_max": {"template": "Qual e o maior valor de 'total'? Responda apenas com um numero.", "key": "max_total", "type": "numeric"},
    "q5_count": {"template": "Quantas linhas existem nos dados? Responda com um numero inteiro.", "key": "count", "type": "count"},
    "q6_top_product": {"template": "Qual produto aparece mais vezes? Responda com o nome do produto.", "key": "top_product", "type": "string"},
}


def _generate_data(scale: int):
    """Generate retail_sales at given scale, return (tables, meta, gt, data_blocks)."""
    tables, meta = retail_sales(n_orders=scale, seed=SEED)
    clientes = {c["id"]: c["nome"] for c in tables["clientes"]}
    produtos = {p["id"]: p["nome"] for p in tables["produtos"]}
    vendas = tables["vendas"]

    totals = [float(v["total"]) for v in vendas if v["total"]]
    prod_counter = Counter(v["id_produto"] for v in vendas)
    top_pid = prod_counter.most_common(1)[0][0] if prod_counter else ""

    gt = {
        "sum_total": round(sum(totals), 2),
        "max_total": max(totals) if totals else 0,
        "count": len(vendas),
        "top_product": produtos.get(top_pid, top_pid),
    }

    # CSV
    csv_lines = ["pessoa,produto,dt,qtd,preco_unit,total"]
    for v in vendas:
        csv_lines.append(f"{clientes.get(v['id_cliente'],'')},"
                         f"{produtos.get(v['id_produto'],'')},"
                         f"{v['dt']},{v['qtd']},{v['preco_unit']},{v['total']}")
    csv_text = "\n".join(csv_lines)

    # TCF
    meta_path, data_dir = _write_fixture(tables, meta)
    tcf_l0 = tcf_encode(str(meta_path), str(data_dir), EncodeConfig(level=0, include_stats=True))
    tcf_l2 = tcf_encode(str(meta_path), str(data_dir), EncodeConfig(level=2, include_stats=True))

    data_blocks = {"csv": csv_text, "tcf_L0": tcf_l0, "tcf_L2": tcf_l2}
    return gt, data_blocks


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


def _build_prompt(fmt: str, data: str, question: str) -> str:
    return (
        f"<s>SYSTEM> {SYSTEM_PROMPTS[fmt]}</s>\n"
        f"<s>CONTEXT>\n{data}\n</s>\n"
        f"<s>USER> {question}</s>\n"
        "<s>ASSISTANT>"
    )


def run(model: str, scales: list[int], endpoint: str) -> None:
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

    # Pre-generate all data
    scale_data = {}
    for scale in scales:
        gt, data_blocks = _generate_data(scale)
        scale_data[scale] = (gt, data_blocks)
        sizes = {fmt: len(data_blocks[fmt]) for fmt in FORMATS}
        print(f"  scale={scale:>5}: {gt['count']} rows  csv={sizes['csv']}  L0={sizes['tcf_L0']}  L2={sizes['tcf_L2']}")

    questions = list(QUESTIONS.keys())
    total = len(scales) * len(FORMATS) * len(questions)
    print(f"\n[Scale Progression] {model} | {total} combos, {len(completed)} cached")

    # Warmup
    print(f"  [warmup] {model} ... ", end="", flush=True)
    try:
        client.generate(model=model, prompt="2+2=?", options=LLM_OPTIONS)
        print("ready")
    except Exception as e:
        print(f"FAILED: {e}")
        return

    i = 0
    for scale in scales:
        gt, data_blocks = scale_data[scale]
        for fmt in FORMATS:
            for q_name in questions:
                i += 1
                key = f"{model}|{scale}|{fmt}|{q_name}"
                if key in completed:
                    continue

                q = QUESTIONS[q_name]
                prompt = _build_prompt(fmt, data_blocks[fmt], q["template"])

                print(f"  [{i}/{total}] s={scale:>5} {fmt:8s} {q_name:18s} ", end="", flush=True)

                try:
                    t0 = time.perf_counter()
                    gen = client.generate(model=model, prompt=prompt, options=LLM_OPTIONS)
                    latency = time.perf_counter() - t0
                    response = gen["text"].strip()
                    correct, error_type = _score(q, response, gt)

                    result = {
                        "key": key, "model": model, "scale": scale,
                        "format": fmt, "question": q_name,
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
                        "key": key, "model": model, "scale": scale,
                        "format": fmt, "question": q_name,
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
    model_entries = [e for e in entries if e["model"] == model]

    print(f"\n{'='*70}")
    print(f"SCALE PROGRESSION — {model} ({len(model_entries)} entries)")
    print(f"{'='*70}")

    print(f"\n{'Scale':>8}", end="")
    for fmt in FORMATS:
        print(f" {fmt:>8}", end="")
    print(f" {'sizes':>30}")
    print("-" * 60)

    for scale in scales:
        print(f"{scale:>8}", end="")
        for fmt in FORMATS:
            vals = [e["correct"] for e in model_entries if e["scale"] == scale and e["format"] == fmt]
            acc = sum(vals) / len(vals) if vals else 0
            print(f" {acc:>7.0%}", end="")
        gt, data_blocks = scale_data[scale]
        sizes = {fmt: len(data_blocks[fmt]) for fmt in FORMATS}
        print(f"  csv={sizes['csv']:>6} L0={sizes['tcf_L0']:>6} L2={sizes['tcf_L2']:>6}")

    # Save summary
    summary = {}
    for scale in scales:
        summary[scale] = {}
        for fmt in FORMATS:
            vals = [e["correct"] for e in model_entries if e["scale"] == scale and e["format"] == fmt]
            summary[scale][fmt] = round(sum(vals) / len(vals), 3) if vals else None
    (RESULTS_DIR / "summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )


def main():
    parser = argparse.ArgumentParser(description="Scale Progression: accuracy vs rows")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--scales", nargs="+", type=int, default=DEFAULT_SCALES)
    parser.add_argument("--endpoint", default="http://localhost:11434")
    args = parser.parse_args()
    run(args.model, args.scales, args.endpoint)


if __name__ == "__main__":
    main()

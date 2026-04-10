"""3-Layer Diagnostic — isolate arithmetic vs format comprehension vs compute.

Layer 0 (math_control): raw numbers, no format — tests arithmetic ability
Layer 1 (decode_only):  TCF given, "list all values of column X" — tests format reading
Layer 2 (compute):      TCF + aggregation question — full pipeline

Models: top performers from Etapa 2 + a few weaker ones for contrast.
Data: retail_sales(200, seed=42) — same as Etapa 2.
Formats: TCF L0, TCF L2 (for layers 1 and 2).

Usage:
    python experiments/eval/run_diagnostic_3layer.py
    python experiments/eval/run_diagnostic_3layer.py --models gemma3:12b qwen3:8b
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

from tcf import encode as tcf_encode, EncodeConfig
from tests.fixtures import _write_fixture
from tests.fixtures.synthetic_v2 import retail_sales

from llm_eval.ollama_client import OllamaClient
from llm_eval.metrics import extract_number, extract_all_numbers, strip_think

RESULTS_DIR = ROOT / "experiments" / "results" / "diagnostic_3layer"
LLM_OPTIONS = {"temperature": 0, "seed": 42}

# Models to test — top from Etapa 2 + weaker for contrast
DEFAULT_MODELS = [
    "gemma3:12b",    # best overall (88% TCF L0)
    "qwen3:8b",      # good with thinking
    "phi4:latest",   # strong
    "mistral:latest", # medium
    "llama3.1:8b",   # medium
    "gemma2:9b",     # 0% TCF in Etapa 2 — interesting diagnostic
]

SCALE = 200
SEED = 42
FORMATS = ["tcf_L0", "tcf_L2"]

# System prompts
SYS_MATH = "Voce e um assistente de calculo. Responda SOMENTE com o resultado numerico, sem explicacao."
SYS_DECODE = {
    "tcf_L0": "Voce recebera dados em formato colunar. Cada bloco comeca com nome da coluna seguido de ':'. Valores um por linha, mesma ordem entre colunas.",
    "tcf_L2": "Voce recebera dados em formato colunar comprimido. N*val = val repetido N vezes. Dados ordenados para agrupar repeticoes.",
}
SYS_COMPUTE = {
    "tcf_L0": "Voce recebera dados em formato colunar. Cada bloco comeca com nome da coluna. Valores um por linha, mesma ordem entre colunas. Responda com base apenas nos dados.",
    "tcf_L2": "Voce recebera dados em formato colunar comprimido. N*val = val repetido N vezes. Dados ordenados para agrupar repeticoes. Responda com base apenas nos dados.",
}


def _build_prompt(system: str, context: str, question: str) -> str:
    if context:
        return (
            f"<s>SYSTEM> {system}</s>\n"
            f"<s>CONTEXT>\n{context}\n</s>\n"
            f"<s>USER> {question}</s>\n"
            "<s>ASSISTANT>"
        )
    return (
        f"<s>SYSTEM> {system}</s>\n"
        f"<s>USER> {question}</s>\n"
        "<s>ASSISTANT>"
    )


def run(models: list[str], endpoint: str) -> None:
    client = OllamaClient(endpoint)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    manifest_path = RESULTS_DIR / "manifest.jsonl"

    # Load cache
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
    clientes = {c["id"]: c["nome"] for c in tables["clientes"]}
    produtos = {p["id"]: p["nome"] for p in tables["produtos"]}
    vendas = tables["vendas"]

    # Ground truth
    totals = [float(v["total"]) for v in vendas if v["total"]]
    gt_sum = round(sum(totals), 2)
    gt_count = len(vendas)

    # Math control: plain number list
    total_str = " ".join(str(t) for t in totals)

    # TCF data blocks
    meta_path, data_dir = _write_fixture(tables, meta)
    data_blocks = {
        "tcf_L0": tcf_encode(str(meta_path), str(data_dir), EncodeConfig(level=0, include_stats=True)),
        "tcf_L2": tcf_encode(str(meta_path), str(data_dir), EncodeConfig(level=2, include_stats=True)),
    }

    # Build all combos: (key, layer, model, format, prompt, scoring_fn)
    combos = []

    for model in models:
        # Layer 0: math_control — same for all formats
        combos.append({
            "key": f"{model}|math_control|sum",
            "layer": "L0_math", "model": model, "format": "none",
            "prompt": _build_prompt(SYS_MATH, "", f"Some estes valores: {total_str}"),
            "expected": gt_sum, "score_type": "numeric",
        })
        combos.append({
            "key": f"{model}|math_control|count",
            "layer": "L0_math", "model": model, "format": "none",
            "prompt": _build_prompt(SYS_MATH, "", f"Quantos numeros ha nesta lista: {total_str}?"),
            "expected": gt_count, "score_type": "count",
        })

        # Layer 1 & 2 per format
        for fmt in FORMATS:
            data = data_blocks[fmt]

            # Layer 1: decode_only — list values
            combos.append({
                "key": f"{model}|decode_only|{fmt}|list_total",
                "layer": "L1_decode", "model": model, "format": fmt,
                "prompt": _build_prompt(
                    SYS_DECODE[fmt], data,
                    "Liste TODOS os valores da coluna 'total', separados por espaco. Apenas os numeros, sem explicacao."
                ),
                "expected_values": totals, "score_type": "decode",
            })

            # Layer 2: compute — sum and count
            combos.append({
                "key": f"{model}|compute|{fmt}|sum",
                "layer": "L2_compute", "model": model, "format": fmt,
                "prompt": _build_prompt(
                    SYS_COMPUTE[fmt], data,
                    "Qual e a soma de todos os valores da coluna 'total'? Responda apenas com um numero."
                ),
                "expected": gt_sum, "score_type": "numeric",
            })
            combos.append({
                "key": f"{model}|compute|{fmt}|count",
                "layer": "L2_compute", "model": model, "format": fmt,
                "prompt": _build_prompt(
                    SYS_COMPUTE[fmt], data,
                    "Quantas linhas existem nos dados? Responda com um numero inteiro."
                ),
                "expected": gt_count, "score_type": "count",
            })

    # Filter cached
    to_run = [c for c in combos if c["key"] not in completed]
    total_combos = len(combos)
    cached = total_combos - len(to_run)
    print(f"[3-Layer Diagnostic] {total_combos} combos, {cached} cached, {len(to_run)} to run")
    print(f"  Data: retail_sales({SCALE}) -> {gt_count} vendas, sum={gt_sum}")

    warmed: set[str] = set()

    for i, combo in enumerate(to_run, 1):
        model = combo["model"]

        if model not in warmed:
            print(f"  [warmup] {model} ... ", end="", flush=True)
            try:
                client.generate(model=model, prompt="2+2=?", options=LLM_OPTIONS)
                print("ready")
            except Exception as e:
                print(f"SKIP ({e})")
                warmed.add(model)
                continue
            warmed.add(model)

        label = f"{combo['layer']:12s} {combo['format']:8s} {combo['key'].split('|')[-1]:15s}"
        print(f"  [{i}/{len(to_run)}] {model:25s} {label} ", end="", flush=True)

        try:
            t0 = time.perf_counter()
            gen = client.generate(model=model, prompt=combo["prompt"], options=LLM_OPTIONS)
            latency = time.perf_counter() - t0
            response = gen["text"].strip()

            # Score
            if combo["score_type"] == "decode":
                nums = extract_all_numbers(response)
                exp = combo["expected_values"]
                found = len(nums)
                total_exp = len(exp)
                exp_sum = sum(exp)
                got_sum = sum(nums) if nums else 0
                sum_ok = abs(got_sum - exp_sum) <= max(abs(exp_sum) * 0.02, 1.0)
                correct = found == total_exp and sum_ok
                error_type = "correct" if correct else (
                    f"found_{found}_of_{total_exp}" if found != total_exp else "sum_mismatch"
                )
            elif combo["score_type"] == "count":
                val = extract_number(response)
                correct = val is not None and int(round(val)) == int(combo["expected"])
                error_type = "correct" if correct else ("parse_failure" if val is None else "wrong_count")
            else:  # numeric
                val = extract_number(response)
                if val is None:
                    correct, error_type = False, "parse_failure"
                else:
                    exp_f = float(combo["expected"])
                    tol = max(abs(exp_f) * 0.02, 0.5)
                    correct = abs(val - exp_f) <= tol
                    error_type = "correct" if correct else "arithmetic_error"

            result = {
                "key": combo["key"], "layer": combo["layer"],
                "model": model, "format": combo["format"],
                "question": combo["key"].split("|")[-1],
                "correct": correct, "error_type": error_type,
                "response": response[:300], "latency_s": round(latency, 1),
                "prompt_chars": len(combo["prompt"]),
                "prompt_tokens": gen.get("prompt_tokens", 0),
                "response_tokens": gen.get("response_tokens", 0),
            }
        except KeyboardInterrupt:
            print("\n[interrupted]")
            sys.exit(0)
        except Exception as exc:
            result = {
                "key": combo["key"], "layer": combo["layer"],
                "model": model, "format": combo["format"],
                "question": combo["key"].split("|")[-1],
                "correct": False, "error_type": "exception",
                "response": "", "latency_s": 0, "prompt_chars": 0,
                "error": str(exc)[:200],
            }

        with manifest_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(result, ensure_ascii=False) + "\n")
        completed.add(combo["key"])

        status = "OK" if result["correct"] else f"FAIL"
        print(f"{status} {result['latency_s']}s")

    # ── Analysis ──
    entries = [json.loads(l) for l in manifest_path.read_text(encoding="utf-8").splitlines() if l.strip()]

    print(f"\n{'='*70}")
    print(f"3-LAYER DIAGNOSTIC ({len(entries)} entries)")
    print(f"{'='*70}")

    # Per model × layer accuracy
    print(f"\n{'Model':>25} {'L0_math':>8} {'L1_dec':>8} {'L2_comp':>8}")
    print("-" * 55)

    for model in models:
        accs = {}
        for layer in ["L0_math", "L1_decode", "L2_compute"]:
            vals = [e["correct"] for e in entries if e["model"] == model and e["layer"] == layer]
            accs[layer] = f"{sum(vals)/len(vals):.0%}" if vals else "—"
        print(f"{model:>25} {accs['L0_math']:>8} {accs['L1_decode']:>8} {accs['L2_compute']:>8}")

    # Per model × layer × format
    print(f"\n{'Model':>25} {'Layer':>12} {'tcf_L0':>8} {'tcf_L2':>8}")
    print("-" * 60)
    for model in models:
        for layer in ["L1_decode", "L2_compute"]:
            row = f"{model:>25} {layer:>12}"
            for fmt in FORMATS:
                vals = [e["correct"] for e in entries
                        if e["model"] == model and e["layer"] == layer and e["format"] == fmt]
                row += f" {sum(vals)/len(vals):>7.0%}" if vals else "       —"
            print(row)

    # Save summary
    summary = {}
    for model in models:
        summary[model] = {}
        for layer in ["L0_math", "L1_decode", "L2_compute"]:
            vals = [e["correct"] for e in entries if e["model"] == model and e["layer"] == layer]
            summary[model][layer] = round(sum(vals) / len(vals), 3) if vals else None
    (RESULTS_DIR / "summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )


def main():
    parser = argparse.ArgumentParser(description="3-Layer Diagnostic: math vs decode vs compute")
    parser.add_argument("--models", nargs="+", default=DEFAULT_MODELS)
    parser.add_argument("--endpoint", default="http://localhost:11434")
    args = parser.parse_args()
    run(args.models, args.endpoint)


if __name__ == "__main__":
    main()

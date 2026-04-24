"""G21 — LLM comprehension test for TCF v0.2 compression levels.

Compares: CSV vs JSONL vs TCF L0 vs TCF L2 vs TCF L3
Models: survivors from previous phases (auto-select fastest)
Questions: compute layer (10 questions)

Usage:
    python experiments/eval/run_g21_v02.py
    python experiments/eval/run_g21_v02.py --models qwen3:8b qwen2.5:latest
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
sys.path.insert(0, str(Path(__file__).resolve().parent))

from tcf import encode as tcf_encode, EncodeConfig
from llm_eval.ollama_client import OllamaClient
from llm_eval.ground_truth import compute as compute_gt, vl_plain_list
from llm_eval.metrics import score_response, extract_number, strip_think
from llm_eval.prompts import QUESTION_DEFS, list_questions_by_layer
from llm_eval.models import fetch_local_models, auto_select_models

DATA_DIR = ROOT / "data"
META = DATA_DIR / "metadata.json"
RESULTS_DIR = ROOT / "experiments" / "results" / "g21_v02"

GROUND_TRUTH = compute_gt(DATA_DIR)

# Vision model families to exclude
VISION_FAMILIES = {"mllama", "qwen3vl", "llava", "moondream"}

# LLM options for reproducibility
LLM_OPTIONS = {"temperature": 0, "seed": 42}


# ---------------------------------------------------------------------------
# System prompts for each format
# ---------------------------------------------------------------------------

SYSTEM_PROMPTS = {
    "csv": (
        "Voce recebera dados no formato CSV."
        " A primeira linha traz o nome das colunas e as demais linhas sao registros."
        " Responda com base apenas nos dados fornecidos."
    ),
    "jsonl": (
        "Voce recebera dados no formato JSON Lines."
        " Cada linha e um objeto JSON independente."
        " Responda com base apenas nos dados fornecidos."
    ),
    "tcf_L0": (
        "Voce recebera dados em formato colunar."
        " Cada bloco comeca com o nome da coluna seguido de dois-pontos."
        " Os valores aparecem um por linha, na mesma ordem entre colunas."
        " Responda com base apenas nos dados fornecidos."
    ),
    "tcf_L2": (
        "Voce recebera dados em formato colunar comprimido."
        " Cada bloco comeca com o nome da coluna seguido de dois-pontos."
        " A notacao N*val significa que val se repete N vezes consecutivas."
        " Os dados estao ordenados por uma coluna para agrupar valores repetidos."
        " Responda com base apenas nos dados fornecidos."
    ),
    "tcf_L3": (
        "Voce recebera dados em formato colunar comprimido com dicionario."
        " Linhas '# dict col: val1,val2,...' definem valores possiveis."
        " Nos dados, numeros sao indices no dicionario (0=primeiro, 1=segundo, etc)."
        " A notacao N*val significa que val se repete N vezes consecutivas."
        " Responda com base apenas nos dados fornecidos."
    ),
}


# ---------------------------------------------------------------------------
# Data preparation
# ---------------------------------------------------------------------------

def _prepare_csv() -> str:
    """Build CSV string with resolved names (flat, denormalized)."""
    pessoas = {r["id"]: r["nome"] for r in csv_mod.DictReader(
        open(DATA_DIR / "pessoas.csv", encoding="utf-8"))}
    produtos = {r["id"]: r["nome"] for r in csv_mod.DictReader(
        open(DATA_DIR / "produtos.csv", encoding="utf-8"))}
    vendas = list(csv_mod.DictReader(
        open(DATA_DIR / "vendas.csv", encoding="utf-8")))
    lines = ["pessoa,produto,vl"]
    for v in vendas:
        lines.append(f"{pessoas[v['id_pessoa']]},{produtos[v['id_produto']]},{v['vl']}")
    return "\n".join(lines)


def _prepare_jsonl() -> str:
    """Build JSONL string with resolved names."""
    pessoas = {r["id"]: r["nome"] for r in csv_mod.DictReader(
        open(DATA_DIR / "pessoas.csv", encoding="utf-8"))}
    produtos = {r["id"]: r["nome"] for r in csv_mod.DictReader(
        open(DATA_DIR / "produtos.csv", encoding="utf-8"))}
    vendas = list(csv_mod.DictReader(
        open(DATA_DIR / "vendas.csv", encoding="utf-8")))
    lines = []
    for v in vendas:
        lines.append(json.dumps({
            "pessoa": pessoas[v["id_pessoa"]],
            "produto": produtos[v["id_produto"]],
            "vl": float(v["vl"]),
        }, ensure_ascii=False))
    return "\n".join(lines)


def _prepare_tcf(level: int) -> str:
    """Build TCF v0.2 string at given level."""
    return tcf_encode(str(META), str(DATA_DIR),
                      EncodeConfig(level=level, include_stats=True))


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def _score(question_key: str, response: str) -> tuple[bool, str]:
    """Score a response against ground truth."""
    gt_key = QUESTION_DEFS[question_key]["key"]
    expected = GROUND_TRUTH.get(gt_key)
    if expected is None:
        return False, "no_ground_truth"
    try:
        return score_response(response, expected, gt_key)
    except (KeyError, ValueError, TypeError):
        return False, "scoring_error"


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------

def run(models: list[str], endpoint: str = "http://localhost:11434") -> None:
    client = OllamaClient(endpoint)
    if not client.is_available():
        print(f"[ERROR] Ollama not available at {endpoint}", file=sys.stderr)
        sys.exit(1)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    manifest_path = RESULTS_DIR / "manifest.jsonl"

    # Load completed keys
    completed: set[str] = set()
    if manifest_path.exists():
        for line in manifest_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:
                    completed.add(json.loads(line)["key"])
                except (json.JSONDecodeError, KeyError):
                    pass

    # Prepare data blocks (cached)
    data_blocks = {
        "csv": _prepare_csv(),
        "jsonl": _prepare_jsonl(),
        "tcf_L0": _prepare_tcf(0),
        "tcf_L2": _prepare_tcf(2),
        "tcf_L3": _prepare_tcf(3),
    }

    # Show sizes
    print("[G21] Data block sizes:")
    for fmt, block in data_blocks.items():
        print(f"  {fmt:10s} {len(block):>6} chars")

    compute_qs = list(list_questions_by_layer("compute").keys())
    formats = ["csv", "jsonl", "tcf_L0", "tcf_L2", "tcf_L3"]

    # Build combos (grouped by model to minimize GPU swaps)
    combos = []
    for model in models:
        for fmt in formats:
            for q in compute_qs:
                combos.append({"model": model, "format": fmt, "question": q})

    total = len(combos)
    print(f"[G21] {total} combinations, {len(completed)} already done")

    # Warmup + run
    warmed: set[str] = set()
    new_count = 0

    for i, combo in enumerate(combos, 1):
        key = f"{combo['model']}|{combo['format']}|{combo['question']}"
        if key in completed:
            continue

        model = combo["model"]
        if model not in warmed:
            print(f"  [warmup] {model} ... ", end="", flush=True)
            try:
                client.generate(model=model, prompt="2+2=?", options=LLM_OPTIONS)
                print("ready")
            except Exception as e:
                print(f"failed: {e}")
            warmed.add(model)

        fmt = combo["format"]
        q = combo["question"]
        print(f"  [{i}/{total}] {model} {fmt} {q} ... ", end="", flush=True)

        try:
            # Build prompt
            sys_prompt = SYSTEM_PROMPTS[fmt]
            q_template = QUESTION_DEFS[q]["template"]
            data_block = data_blocks[fmt]

            prompt = (
                f"<s>SYSTEM> {sys_prompt}</s>\n"
                f"<s>CONTEXT>\n{data_block}\n</s>\n"
                f"<s>USER> {q_template}</s>\n"
                "<s>ASSISTANT>"
            )

            t0 = time.perf_counter()
            gen = client.generate(model=model, prompt=prompt, options=LLM_OPTIONS)
            latency = time.perf_counter() - t0
            response = gen["text"].strip()
            correct, error_type = _score(q, response)

            result = {
                "key": key,
                "model": model,
                "format": fmt,
                "question": q,
                "correct": correct,
                "error_type": error_type,
                "response": response[:200],
                "latency_s": round(latency, 2),
                "prompt_chars": len(prompt),
                "prompt_tokens": gen.get("prompt_tokens", 0),
                "eval_s": round(gen.get("eval_ns", 0) / 1e9, 2),
            }

        except KeyboardInterrupt:
            print("\n[interrupted] progress saved")
            sys.exit(0)
        except Exception as exc:
            result = {
                "key": key, "model": model, "format": fmt, "question": q,
                "correct": False, "error_type": "exception",
                "response": "", "latency_s": 0, "prompt_chars": 0,
                "prompt_tokens": 0, "eval_s": 0, "error": str(exc)[:200],
            }

        # Persist immediately
        with manifest_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(result, ensure_ascii=False) + "\n")
        completed.add(key)
        new_count += 1

        status = "OK" if result["correct"] else "FAIL"
        print(status)

    print(f"[G21] done: {new_count} new, {total - new_count - (total - len(combos))} cached")

    # Analysis
    _analyze(manifest_path, models, formats, compute_qs)


def _analyze(manifest_path: Path, models: list[str], formats: list[str], questions: list[str]) -> None:
    entries = [json.loads(l) for l in manifest_path.read_text(encoding="utf-8").splitlines() if l.strip()]

    print(f"\n{'='*70}")
    print(f"G21 RESULTS ({len(entries)} entries)")
    print(f"{'='*70}")

    # By format
    fmt_acc: dict[str, list[bool]] = defaultdict(list)
    for e in entries:
        fmt_acc[e["format"]].append(e["correct"])

    print(f"\n{'Format':>12} {'Accuracy':>9} {'N':>5}")
    print("-" * 30)
    for fmt in formats:
        vals = fmt_acc.get(fmt, [])
        acc = sum(vals) / len(vals) if vals else 0
        print(f"{fmt:>12} {acc:>8.0%} {len(vals):>5}")

    # By model x format
    print(f"\n{'Model':>25}", end="")
    for fmt in formats:
        print(f" {fmt:>8}", end="")
    print()
    print("-" * (25 + 9 * len(formats)))

    for model in models:
        print(f"{model:>25}", end="")
        for fmt in formats:
            vals = [e["correct"] for e in entries if e["model"] == model and e["format"] == fmt]
            acc = sum(vals) / len(vals) if vals else 0
            print(f" {acc:>7.0%}", end="")
        print()

    # By question
    print(f"\n{'Question':>30}", end="")
    for fmt in formats:
        print(f" {fmt:>8}", end="")
    print()
    print("-" * (30 + 9 * len(formats)))

    for q in questions:
        print(f"{q:>30}", end="")
        for fmt in formats:
            vals = [e["correct"] for e in entries if e["question"] == q and e["format"] == fmt]
            acc = sum(vals) / len(vals) if vals else 0
            print(f" {acc:>7.0%}", end="")
        print()

    # Save summary
    summary = {
        "by_format": {f: sum(v) / len(v) for f, v in fmt_acc.items() if v},
        "total_entries": len(entries),
    }
    (manifest_path.parent / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"\n[G21] summary saved to {manifest_path.parent}/summary.json")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="G21: TCF v0.2 LLM comprehension test")
    parser.add_argument("--models", nargs="+", default=["auto"],
                        help="Models to test (default: auto-discover)")
    parser.add_argument("--endpoint", default="http://localhost:11434")
    args = parser.parse_args()

    if args.models == ["auto"]:
        all_models = fetch_local_models(args.endpoint)
        text_models = [m for m in all_models if m.get("family") not in VISION_FAMILIES]
        names, picks = auto_select_models(text_models, desired=3)
        # Sort by param size (fastest first)
        param_order = sorted(zip(names, picks), key=lambda x: x[1].get("param_float", 0))
        models = [n for n, _ in param_order]
        print(f"[G21] auto-selected: {models}")
    else:
        models = args.models

    run(models, args.endpoint)


if __name__ == "__main__":
    main()

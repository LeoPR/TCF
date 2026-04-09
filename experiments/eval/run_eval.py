"""Harness de avaliação científica: TCF vs CSV vs JSONL no Ollama.

Método:
    Cada modelo é testado com 3 tipos de teste isolados para diagnosticar
    onde está o gargalo — no formato ou na capacidade do modelo.

    math_control  → números em lista plana, sem formato
                    Falha aqui = modelo não sabe fazer aritmética.
    decode_only   → formato dado, pede só listar valores (sem conta)
                    Falha aqui = modelo não entende o formato.
    compute       → formato dado + pergunta de agregação
                    O experimento real.

Uso:
    python experiments/eval/run_eval.py --model gemma3:12b
    python experiments/eval/run_eval.py --model gemma3:12b --no-pull
    python experiments/eval/run_eval.py --model qwen2.5:7b --endpoint http://localhost:11434
"""

from __future__ import annotations
import argparse
import csv as csv_mod
import json
import sys
import time
from pathlib import Path

# Allow import of src/tcf without install
ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).parent))

from tcf import encode as tcf_encode

from llm_eval.ollama_client import OllamaClient
from llm_eval.formats import format_csv, format_jsonl, format_tcf
from llm_eval.ground_truth import compute as compute_gt, vl_plain_list
from llm_eval.metrics import score_response, score_decode

DATA_DIR = ROOT / "data"
META     = DATA_DIR / "metadata.json"

# Computed once at import — always in sync with source CSVs
GROUND_TRUTH = compute_gt(DATA_DIR)


# ---------------------------------------------------------------------------
# Data preparation
# ---------------------------------------------------------------------------

def _load_vendas_expanded() -> list[dict]:
    """Load vendas joined with pessoa and produto names."""
    pessoas  = {r["id"]: r["nome"] for r in csv_mod.DictReader((DATA_DIR / "pessoas.csv").open(encoding="utf-8"))}
    produtos = {r["id"]: r["nome"] for r in csv_mod.DictReader((DATA_DIR / "produtos.csv").open(encoding="utf-8"))}
    rows = []
    for r in csv_mod.DictReader((DATA_DIR / "vendas.csv").open(encoding="utf-8")):
        rows.append({
            "pessoa":  pessoas.get(r["id_pessoa"], r["id_pessoa"]),
            "produto": produtos.get(r["id_produto"], r["id_produto"]),
            "vl":      float(r["vl"]),
        })
    return rows


# ---------------------------------------------------------------------------
# Prompt builders
# ---------------------------------------------------------------------------

def _prompt_math_control(vl_list: str, question: str) -> str:
    return (
        "Você é um assistente de cálculo. Dados os números abaixo, responda apenas com o resultado numérico, sem texto.\n\n"
        f"Valores: {vl_list}\n\n"
        f"{question}"
    )


def _prompt_compute(fmt_name: str, data_block: str, question: str) -> str:
    system_hints = {
        "csv":  "Formato CSV: primeira linha = colunas, demais = registros.",
        "jsonl": "Formato JSONL: cada linha é um objeto JSON independente.",
        "tcf":  (
            "Formato TCF (Textual Columnar Format): cada linha = uma coluna inteira. "
            "N:val = val repetido N vezes. Sem prefixo = ocorrência única. "
            "[sorted] = coluna ordenada, não correlacionar posição entre colunas."
        ),
    }
    hint = system_hints.get(fmt_name, "")
    return (
        f"Você receberá dados no formato {fmt_name.upper()}. {hint}\n"
        "Use APENAS os dados fornecidos. Responda SOMENTE com o valor numérico, sem texto.\n\n"
        f"{data_block}\n\n"
        f"{question}"
    )


def _prompt_decode_only(fmt_name: str, data_block: str) -> str:
    system_hints = {
        "csv":  "Formato CSV.",
        "jsonl": "Formato JSONL.",
        "tcf":  "Formato TCF: cada linha é uma coluna inteira. N:val = N repetições.",
    }
    hint = system_hints.get(fmt_name, "")
    return (
        f"{hint}\n"
        "Liste TODOS os valores da coluna 'vl', separados por espaço. "
        "Apenas os números, sem nenhuma explicação.\n\n"
        f"{data_block}"
    )


# ---------------------------------------------------------------------------
# Question definitions
# ---------------------------------------------------------------------------

QUESTIONS = {
    "sum_vl":  ("Some todos os valores de 'vl'.",                   "sum_vl"),
    "mean_vl": ("Calcule a média dos valores de 'vl'.",              "mean_vl"),
    "count":   ("Quantas linhas existem? Responda com inteiro.",     "count"),
    "max_vl":  ("Qual é o maior valor de 'vl'?",                    "max_vl"),
}


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def _score(question_key: str, response: str) -> bool:
    ok, _ = score_response(response, GROUND_TRUTH[question_key], question_key)
    return ok


def _score_decode(response: str) -> bool:
    result = score_decode(response, GROUND_TRUTH["vl_values"])
    return result["correct"]


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------

def run(model: str, endpoint: str, pull: bool, out_dir: Path) -> None:
    client = OllamaClient(endpoint)

    # 1. Server check
    if not client.is_available():
        print(f"[ERROR] Ollama não disponível em {endpoint}", file=sys.stderr)
        sys.exit(1)
    print(f"[ok] Ollama disponível em {endpoint}")

    # 2. Ensure model
    if pull:
        client.ensure(model)
    else:
        if not client.is_installed(model):
            print(f"[WARN] Modelo {model!r} não instalado e --no-pull foi passado.", file=sys.stderr)

    # 3. Prepare data representations
    rows_expanded = _load_vendas_expanded()
    vl_list       = vl_plain_list(DATA_DIR)
    csv_block     = format_csv(rows_expanded)
    jsonl_block   = format_jsonl(rows_expanded)
    tcf_raw       = tcf_encode(META, DATA_DIR)
    tcf_block     = format_tcf(tcf_raw)

    formats = {
        "csv":  csv_block,
        "jsonl": jsonl_block,
        "tcf":  tcf_block,
    }

    results = []

    # 4a. math_control — same for all formats, run once
    print("\n── math_control ──────────────────────────────")
    for qkey, (question_text, _) in QUESTIONS.items():
        prompt = _prompt_math_control(vl_list, question_text)
        print(f"  Q: {qkey} ... ", end="", flush=True)
        t0 = time.perf_counter()
        result = client.generate(model=model, prompt=prompt)
        latency = time.perf_counter() - t0
        ok = _score(qkey, result["text"])
        print(f"{'✓' if ok else '✗'}  ({result['text'].strip()[:60]})")
        results.append({
            "model": model, "test_type": "math_control", "format": "none",
            "question": qkey, "expected": GROUND_TRUTH[qkey],
            "response": result["text"].strip(), "correct": ok,
            "latency_s": round(latency, 3), "prompt_chars": len(prompt),
            "prompt_tokens": result["prompt_tokens"],
            "response_tokens": result["response_tokens"],
        })

    # 4b. decode_only — per format
    print("\n── decode_only ───────────────────────────────")
    for fmt_name, data_block in formats.items():
        prompt = _prompt_decode_only(fmt_name, data_block)
        print(f"  [{fmt_name}] decode vl ... ", end="", flush=True)
        t0 = time.perf_counter()
        result = client.generate(model=model, prompt=prompt)
        latency = time.perf_counter() - t0
        ok = _score_decode(result["text"])
        print(f"{'✓' if ok else '✗'}  ({result['text'].strip()[:60]})")
        results.append({
            "model": model, "test_type": "decode_only", "format": fmt_name,
            "question": "list_vl", "expected": "41 values summing 217.55",
            "response": result["text"].strip(), "correct": ok,
            "latency_s": round(latency, 3), "prompt_chars": len(prompt),
            "prompt_tokens": result["prompt_tokens"],
            "response_tokens": result["response_tokens"],
        })

    # 4c. compute — per format × question
    print("\n── compute ───────────────────────────────────")
    for fmt_name, data_block in formats.items():
        for qkey, (question_text, _) in QUESTIONS.items():
            prompt = _prompt_compute(fmt_name, data_block, question_text)
            print(f"  [{fmt_name}] {qkey} ... ", end="", flush=True)
            t0 = time.perf_counter()
            result = client.generate(model=model, prompt=prompt)
            latency = time.perf_counter() - t0
            ok = _score(qkey, result["text"])
            print(f"{'✓' if ok else '✗'}  ({result['text'].strip()[:60]})")
            results.append({
                "model": model, "test_type": "compute", "format": fmt_name,
                "question": qkey, "expected": GROUND_TRUTH[qkey],
                "response": result["text"].strip(), "correct": ok,
                "latency_s": round(latency, 3), "prompt_chars": len(prompt),
                "prompt_tokens": result["prompt_tokens"],
                "response_tokens": result["response_tokens"],
            })

    # 5. Save + summary
    out_dir.mkdir(parents=True, exist_ok=True)
    slug = model.replace(":", "_").replace("/", "_")
    out_file = out_dir / f"{slug}.jsonl"
    with out_file.open("w", encoding="utf-8") as fh:
        for r in results:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"\n[saved] {out_file}")
    _print_summary(results)


def _print_summary(results: list[dict]) -> None:
    print("\n╔══ RESUMO ════════════════════════════════════╗")
    # Group by test_type + format
    from collections import defaultdict
    buckets: dict[tuple, list] = defaultdict(list)
    for r in results:
        key = (r["test_type"], r["format"])
        buckets[key].append(r["correct"])

    for (ttype, fmt), vals in sorted(buckets.items()):
        total   = len(vals)
        correct = sum(vals)
        bar     = "█" * correct + "░" * (total - correct)
        print(f"  {ttype:14} [{fmt:5}]  {correct}/{total}  {bar}")

    total   = len(results)
    correct = sum(r["correct"] for r in results)
    print(f"╚══ TOTAL: {correct}/{total} corretos ═══════════════════╝")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="TCF eval harness")
    parser.add_argument("--model",    required=True, help="Modelo Ollama (ex: gemma3:12b)")
    parser.add_argument("--endpoint", default="http://localhost:11434")
    parser.add_argument("--no-pull",  dest="pull", action="store_false",
                        help="Não tenta baixar o modelo se não estiver instalado")
    parser.add_argument("--out-dir",  default="experiments/results/eval_tcf",
                        help="Diretório para salvar resultados")
    args = parser.parse_args()
    run(
        model    = args.model,
        endpoint = args.endpoint,
        pull     = args.pull,
        out_dir  = ROOT / args.out_dir,
    )


if __name__ == "__main__":
    main()

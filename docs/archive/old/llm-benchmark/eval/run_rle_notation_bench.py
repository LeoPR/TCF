"""RLE notation micro-benchmark — cognitive cost per notation.

Empirical token counting (tiktoken, 2026-04-18) confirmed that notations
tie at 3-4 tokens each. But LLMs may comprehend them differently due to
training data priors: `*` = multiplication, `x` = "times" in English,
space-prefix = natural word boundary.

This benchmark tests 4 notations x 3 models x 6 factual questions on a
small dataset with heavy RLE. If accuracy varies by notation, the choice
matters cognitively (not just for tokens).

Models:
    gemma3:4b           -- small, possibly notation-sensitive
    qwen2.5:7b          -- general-purpose mid-size
    qwen2.5-coder:7b    -- code-trained, same family/size as qwen2.5

Notations:
    N*val   -- current TCF default (3*Ana)
    N val   -- space-separator (3 Ana) -- tokenizer-optimal for strings
    N xval  -- x-separator (3xAna) -- "3 times Ana"
    val xN  -- postfix (Ana x3) -- natural English ("Ana, 3 times")

Usage:
    python experiments/eval/run_rle_notation_bench.py
    python experiments/eval/run_rle_notation_bench.py --models gemma3:4b
    python experiments/eval/run_rle_notation_bench.py --dry-run
"""

from __future__ import annotations
import argparse
import json
import re
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


RESULTS_DIR = ROOT / "experiments" / "results" / "rle_notation"
LLM_OPTIONS = {"temperature": 0, "seed": 42}

DEFAULT_MODELS = [
    "gemma3:4b",
    "qwen2.5:latest",      # 7B general
    "qwen2.5-coder:7b",    # 7B code-specialized
]

# Smoke subset: 1 model, all 4 notations, 2 questions (RLE-sensitive)
SMOKE_MODEL = "gemma3:4b"
SMOKE_QUESTIONS = ("q3_count", "q4_top_product")

SCALE = 200
SEED = 42

# Notations: (name, function(count, val) -> str, prompt_hint)
NOTATIONS = {
    "N_star_val": {
        "rewrite": lambda n, v: f"{n}*{v}",
        "hint": "N*val = val repetido N vezes",
    },
    "N_space_val": {
        "rewrite": lambda n, v: f"{n} {v}",
        "hint": "N val = val repetido N vezes (ex: '3 Ana' = Ana 3 vezes)",
    },
    "N_x_val": {
        "rewrite": lambda n, v: f"{n}x{v}",
        "hint": "Nxval = val repetido N vezes (ex: '3xAna' = Ana 3 vezes)",
    },
    "val_x_N": {
        "rewrite": lambda n, v: f"{v} x{n}",
        "hint": "val xN = val repetido N vezes (ex: 'Ana x3' = Ana 3 vezes)",
    },
}

QUESTIONS = {
    "q1_sum": {
        "template": "Qual e a soma de todos os valores da coluna 'total'? Responda apenas com um numero.",
        "key": "sum_total", "type": "numeric",
    },
    "q2_avg": {
        "template": "Qual e a media dos valores de 'total'? Responda apenas com um numero.",
        "key": "avg_total", "type": "numeric",
    },
    "q3_count": {
        "template": "Quantas linhas existem nos dados? Responda apenas com um numero inteiro.",
        "key": "count", "type": "count",
    },
    "q4_top_product": {
        "template": "Qual produto aparece mais vezes? Responda apenas com o nome do produto.",
        "key": "top_product", "type": "string",
    },
    "q5_top_spender": {
        "template": "Qual pessoa gastou o maior total? Responda apenas com o nome da pessoa.",
        "key": "top_spender", "type": "string",
    },
    "q6_distinct": {
        "template": "Quantos clientes distintos aparecem nos dados? Responda apenas com um numero inteiro.",
        "key": "distinct_customers", "type": "count",
    },
}


# ---------------------------------------------------------------------------
# Notation rewriting
# ---------------------------------------------------------------------------

_RLE_RE = re.compile(r"^(\d+)\*(.+)$")


def rewrite_notation(tcf_text: str, rewrite_fn) -> str:
    """Rewrite all RLE lines (N*val) in a TCF text using rewrite_fn."""
    out = []
    for line in tcf_text.splitlines():
        m = _RLE_RE.match(line)
        if m:
            n = int(m.group(1))
            v = m.group(2)
            out.append(rewrite_fn(n, v))
        else:
            out.append(line)
    return "\n".join(out)


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


def _count_rle_lines(text: str) -> int:
    return sum(1 for line in text.splitlines() if _RLE_RE.match(line))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run(
    models: list[str],
    endpoint: str,
    dry_run: bool = False,
    cpu_only: bool = False,
    num_thread: int | None = None,
    questions_subset: tuple[str, ...] | None = None,
) -> None:
    client = OllamaClient(endpoint)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    manifest_path = RESULTS_DIR / "manifest.jsonl"

    # Build LLM options (cpu_only forces num_gpu=0 -> model runs in system RAM)
    llm_options = dict(LLM_OPTIONS)
    if cpu_only:
        llm_options["num_gpu"] = 0
        print("[RLE Notation] CPU-ONLY mode: num_gpu=0 (VRAM will stay at 0)")
    if num_thread is not None:
        llm_options["num_thread"] = num_thread
        print(f"[RLE Notation] num_thread={num_thread} (leaves other cores for other processes)")

    active_questions = dict(QUESTIONS)
    if questions_subset:
        active_questions = {k: v for k, v in QUESTIONS.items() if k in questions_subset}
        print(f"[RLE Notation] question subset: {list(active_questions)}")

    completed: set[str] = set()
    if manifest_path.exists():
        for line in manifest_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:
                    completed.add(json.loads(line)["key"])
                except (json.JSONDecodeError, KeyError):
                    pass

    # Generate data (same seed, same dataset — only notation changes)
    tables, meta = retail_sales(n_orders=SCALE, seed=SEED)
    gt = _compute_gt(tables)
    meta_path, data_dir = _write_fixture(tables, meta)

    # Base TCF L2 (sorted+RLE) with stats OFF
    # (stats off so models must compute from data; isolates notation effect)
    base_text = tcf_encode(
        str(meta_path), str(data_dir),
        EncodeConfig(level=2, include_stats=False),
    )
    base_rle_lines = _count_rle_lines(base_text)

    # Generate variants
    data_blocks = {}
    for notation, cfg in NOTATIONS.items():
        data_blocks[notation] = rewrite_notation(base_text, cfg["rewrite"])

    print(f"[RLE Notation] dataset: retail_sales(n_orders={SCALE}) seed={SEED}")
    print(f"[RLE Notation] {len(tables['vendas'])} vendas, {base_rle_lines} RLE runs in base")
    for notation, text in data_blocks.items():
        sample = [line for line in text.splitlines() if _RLE_RE.match(line) or notation != "N_star_val"][:3]
        print(f"  {notation:15s} {len(text):>6} chars  sample={sample[:3] if sample else '(no RLE)'}")

    n_combos = len(models) * len(NOTATIONS) * len(active_questions)
    print(f"[RLE Notation] {n_combos} combos ({len(completed)} cached)")

    if dry_run:
        print("[RLE Notation] --dry-run: skipping model calls")
        sample_key = f"{models[0]}|{list(NOTATIONS)[0]}|{list(QUESTIONS)[0]}"
        print(f"  example key: {sample_key}")
        print(f"  example prompt preview:")
        notation = list(NOTATIONS)[0]
        q = list(QUESTIONS.values())[0]
        hint = NOTATIONS[notation]["hint"]
        sys_prompt = f"Voce recebera dados em formato colunar comprimido. {hint}. Dados ordenados para agrupar repeticoes. Responda com base apenas nos dados."
        print("  --- system ---")
        print(f"  {sys_prompt}")
        print("  --- user (first 400 chars) ---")
        print(f"  {q['template']}\n\n  {data_blocks[notation][:400]}...")
        return

    warmed: set[str] = set()
    i = 0
    t_start = time.time()

    for model in models:
        for notation in NOTATIONS:
            hint = NOTATIONS[notation]["hint"]
            sys_prompt = (
                f"Voce recebera dados em formato colunar comprimido. "
                f"{hint}. Dados ordenados para agrupar repeticoes. "
                f"Responda com base apenas nos dados."
            )

            for q_name, q in active_questions.items():
                key = f"{model}|{notation}|{q_name}"
                if key in completed:
                    continue
                i += 1
                prompt = f"{sys_prompt}\n\n{q['template']}\n\n{data_blocks[notation]}"

                # Warm cache once per model
                if model not in warmed:
                    print(f"  warming {model}...")
                    try:
                        warm_opts = {"num_predict": 2}
                        if cpu_only:
                            warm_opts["num_gpu"] = 0
                        if num_thread is not None:
                            warm_opts["num_thread"] = num_thread
                        client.generate(model, "ok", options=warm_opts)
                        warmed.add(model)
                    except Exception as e:
                        print(f"  warm failed: {e}", file=sys.stderr)

                elapsed = time.time() - t_start
                print(f"  [{i}/{n_combos} elapsed={elapsed:.0f}s] {model} {notation} {q_name}", end=" ", flush=True)

                try:
                    result = client.generate(model, prompt, options=llm_options)
                    response = result["text"]
                    ok, reason = _score(q, response, gt)
                    print(f"{'OK' if ok else 'NO'} ({reason})")
                except Exception as e:
                    print(f"ERROR: {e}")
                    response, ok, reason = f"ERROR:{e}", False, "exception"
                    result = {"prompt_tokens": 0, "response_tokens": 0, "total_duration_ns": 0}

                record = {
                    "key": key, "model": model, "notation": notation, "question": q_name,
                    "response": response, "ok": ok, "reason": reason,
                    "prompt_tokens": result.get("prompt_tokens", 0),
                    "response_tokens": result.get("response_tokens", 0),
                    "total_ms": result.get("total_duration_ns", 0) // 1_000_000,
                    "expected": gt[q["key"]],
                }
                with open(manifest_path, "a", encoding="utf-8") as fh:
                    fh.write(json.dumps(record, ensure_ascii=False) + "\n")

    # Summary
    print()
    print("=" * 70)
    print(f"{'model':<22} {'notation':<14} acc   (correct/total)")
    print("-" * 70)
    by_cell: dict[tuple[str, str], list[bool]] = defaultdict(list)
    for line in manifest_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        by_cell[(r["model"], r["notation"])].append(r["ok"])
    for (model, notation), oks in sorted(by_cell.items()):
        n = len(oks)
        c = sum(oks)
        print(f"{model:<22} {notation:<14} {c/n*100:>4.0f}%  ({c}/{n})")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--models", nargs="+", default=DEFAULT_MODELS)
    parser.add_argument("--endpoint", default="http://localhost:11434")
    parser.add_argument("--dry-run", action="store_true",
                        help="print notation samples without calling models")
    parser.add_argument("--cpu-only", action="store_true",
                        help="force num_gpu=0 (model stays in system RAM, VRAM=0)")
    parser.add_argument("--num-thread", type=int, default=None,
                        help="cap threads Ollama uses (default: Ollama chooses). "
                             "On this machine 36 logical cores; use 12 to leave ~2/3 free")
    parser.add_argument("--smoke", action="store_true",
                        help="run smoke subset: gemma3:4b x 4 notations x 2 questions = 8 combos")
    args = parser.parse_args()

    models = args.models
    questions_subset: tuple[str, ...] | None = None
    if args.smoke:
        models = [SMOKE_MODEL]
        questions_subset = SMOKE_QUESTIONS

    run(models, args.endpoint, dry_run=args.dry_run,
        cpu_only=args.cpu_only, num_thread=args.num_thread,
        questions_subset=questions_subset)


if __name__ == "__main__":
    main()

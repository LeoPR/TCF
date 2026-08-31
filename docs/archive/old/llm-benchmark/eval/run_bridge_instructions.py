"""Bridge instructions — how much does the system prompt affect RLE comprehension?

Keeps N val (space-separated, token-cheap) notation FIXED.
Varies only the explanatory system prompt.

    V0  minimal          - no RLE hint at all
    V1  current          - one short example
    V2  pedagogical      - multiple examples + explicit sum instruction
    V3  pseudocode       - code-style hint (works better for coder models?)

Goal: if V2/V3 recover the accuracy that N*val had, we get 25% token savings
"for free" (same acc, cheaper tokens).

Usage:
    python experiments/eval/run_bridge_instructions.py --cpu-only --num-thread 24
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


RESULTS_DIR = ROOT / "experiments" / "results" / "bridge_instructions"
LLM_OPTIONS = {"temperature": 0, "seed": 42}
DEFAULT_MODELS = ["gemma3:4b"]
SCALE_DEFAULT = 50
SEED = 42

# Notation FIXED on N val (space) — the token-cheap but cognitively-risky one
_RLE_STAR_RE = re.compile(r"^(\d+)\*(.+)$")


def rewrite_to_space(text: str) -> str:
    out = []
    for line in text.splitlines():
        m = _RLE_STAR_RE.match(line)
        if m:
            out.append(f"{m.group(1)} {m.group(2)}")
        else:
            out.append(line)
    return "\n".join(out)


# ---------------------------------------------------------------------------
# Bridge prompt variants (all in PT — language held constant)
# ---------------------------------------------------------------------------

BRIDGES = {
    "V0_minimal": (
        "Voce recebera dados em formato colunar. "
        "Responda com base apenas nos dados."
    ),
    "V1_current": (
        "Voce recebera dados em formato colunar comprimido. "
        "N val = val repetido N vezes (ex: '3 Ana' = Ana 3 vezes). "
        "Responda com base apenas nos dados."
    ),
    "V2_pedagogical": (
        "Voce recebera dados em formato colunar comprimido por RLE. "
        "Antes de cada valor, um numero indica quantas vezes o valor aparece consecutivamente. "
        "Exemplos: '3 Ana' significa Ana, Ana, Ana (3 ocorrencias). "
        "'5 Rodrigo' significa 5 ocorrencias de Rodrigo. "
        "Uma linha sem numero no inicio = 1 unica ocorrencia do valor. "
        "Para total de linhas, some TODAS as contagens N (linhas sem N contam como 1). "
        "Responda com base apenas nos dados."
    ),
    "V3_pseudocode": (
        "Data format: compressed columnar with RLE. "
        "A line 'N val' expands to [val] * N (val repeated N times). "
        "A line without numeric prefix = 1 occurrence. "
        "To count total rows: sum(N for each N-val line) + count(plain-value lines). "
        "Responda em portugues, com base apenas nos dados."
    ),
}

QUESTIONS = {
    "q_count":   {"text": "Quantas linhas existem nos dados? Responda apenas com um numero inteiro.",
                   "key": "count", "type": "count"},
    "q_sum":     {"text": "Qual e a soma de todos os valores da coluna 'total'? Responda apenas com um numero.",
                   "key": "sum_total", "type": "numeric"},
    "q_top":     {"text": "Qual produto aparece mais vezes? Responda apenas com o nome do produto.",
                   "key": "top_product", "type": "string"},
    "q_distinct":{"text": "Quantos clientes distintos aparecem nos dados? Responda apenas com um numero inteiro.",
                   "key": "distinct_customers", "type": "count"},
}


def _compute_gt(tables):
    clientes = {c["id"]: c["nome"] for c in tables["clientes"]}
    produtos = {p["id"]: p["nome"] for p in tables["produtos"]}
    vendas = tables["vendas"]
    totals = [float(v["total"]) for v in vendas if v["total"]]
    n = len(vendas)
    prod_counter = Counter(v["id_produto"] for v in vendas)
    top_pid = prod_counter.most_common(1)[0][0]
    return {
        "count": n,
        "sum_total": round(sum(totals), 2),
        "top_product": produtos.get(top_pid, top_pid),
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


def run(models, endpoint, dry_run=False, cpu_only=False, num_thread=None, scale=SCALE_DEFAULT):
    client = OllamaClient(endpoint)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    manifest_path = RESULTS_DIR / "manifest.jsonl"

    llm_options = dict(LLM_OPTIONS)
    if cpu_only:
        llm_options["num_gpu"] = 0
    if num_thread is not None:
        llm_options["num_thread"] = num_thread

    completed = set()
    if manifest_path.exists():
        for line in manifest_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try: completed.add(json.loads(line)["key"])
                except: pass

    print(f"[Bridge] scale={scale}")
    tables, meta = retail_sales(n_orders=scale, seed=SEED)
    gt = _compute_gt(tables)
    mp, dd = _write_fixture(tables, meta)
    base = tcf_encode(str(mp), str(dd), EncodeConfig(level=2, include_stats=False))
    data_text = rewrite_to_space(base)

    print(f"[Bridge] data (N val notation): {len(data_text)} chars")
    print(f"[Bridge] GT: {gt}")
    n_combos = len(models) * len(BRIDGES) * len(QUESTIONS)
    print(f"[Bridge] {n_combos} combos ({len(completed)} cached)")

    if dry_run:
        for name, p in BRIDGES.items():
            print(f"\n--- {name} ---\n{p}")
        return

    warmed = set()
    t_start = time.time()
    i = 0
    for model in models:
        for bridge_name, sys_prompt in BRIDGES.items():
            for q_name, q in QUESTIONS.items():
                key = f"{model}|{bridge_name}|{q_name}"
                if key in completed:
                    continue
                i += 1
                prompt = f"{sys_prompt}\n\n{q['text']}\n\n{data_text}"

                if model not in warmed:
                    print(f"  warming {model}...")
                    wopts = {"num_predict": 2}
                    if cpu_only: wopts["num_gpu"] = 0
                    if num_thread: wopts["num_thread"] = num_thread
                    try:
                        client.generate(model, "ok", options=wopts)
                        warmed.add(model)
                    except Exception as e:
                        print(f"  warm failed: {e}", file=sys.stderr)

                el = time.time() - t_start
                print(f"  [{i}/{n_combos} el={el:.0f}s] {model} {bridge_name} {q_name}", end=" ", flush=True)
                try:
                    result = client.generate(model, prompt, options=llm_options)
                    response = result["text"]
                    ok, reason = _score(q, response, gt)
                    print(f"{'OK' if ok else 'NO'} ({reason}) ans={response[:40]!r}")
                except Exception as e:
                    print(f"ERROR: {e}")
                    response, ok, reason = f"ERROR:{e}", False, "exception"
                    result = {"prompt_tokens": 0, "response_tokens": 0, "total_duration_ns": 0}

                record = {
                    "key": key, "model": model, "bridge": bridge_name, "question": q_name,
                    "response": response, "ok": ok, "reason": reason,
                    "expected": gt[q["key"]],
                    "prompt_tokens": result.get("prompt_tokens", 0),
                    "response_tokens": result.get("response_tokens", 0),
                    "total_ms": result.get("total_duration_ns", 0) // 1_000_000,
                }
                with open(manifest_path, "a", encoding="utf-8") as fh:
                    fh.write(json.dumps(record, ensure_ascii=False) + "\n")

    # Summary
    print()
    print("=" * 60)
    print(f"{'model':<22} {'bridge':<18} acc")
    by = defaultdict(list)
    for line in manifest_path.read_text(encoding="utf-8").splitlines():
        if not line.strip(): continue
        r = json.loads(line)
        by[(r["model"], r["bridge"])].append(r["ok"])
    for (m, b), oks in sorted(by.items()):
        n, c_ok = len(oks), sum(oks)
        print(f"{m:<22} {b:<18} {c_ok/n*100:>4.0f}%  ({c_ok}/{n})")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--models", nargs="+", default=DEFAULT_MODELS)
    p.add_argument("--endpoint", default="http://localhost:11434")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--cpu-only", action="store_true")
    p.add_argument("--num-thread", type=int, default=None)
    p.add_argument("--scale", type=int, default=SCALE_DEFAULT,
                   help=f"retail_sales n_orders (default {SCALE_DEFAULT})")
    a = p.parse_args()
    run(a.models, a.endpoint, dry_run=a.dry_run,
        cpu_only=a.cpu_only, num_thread=a.num_thread, scale=a.scale)


if __name__ == "__main__":
    main()

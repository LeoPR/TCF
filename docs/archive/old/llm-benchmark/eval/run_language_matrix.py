"""Language matrix — data language x question language.

Tests if LLM accuracy on tabular reasoning depends on whether:
    data is in PT vs EN
    question is in PT vs EN
    (or mismatched)

4 language cells x 3 questions = 12 combos per model.
Same retail_sales(200) seed=42 base; translation dict maps names/products.

Usage:
    python experiments/eval/run_language_matrix.py --cpu-only --num-thread 24
    python experiments/eval/run_language_matrix.py --dry-run
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


RESULTS_DIR = ROOT / "experiments" / "results" / "language_matrix"
LLM_OPTIONS = {"temperature": 0, "seed": 42}
DEFAULT_MODELS = ["gemma3:4b"]
SCALE_DEFAULT = 50   # small enough for gemma3:4b to reason about
SEED = 42


# ---------------------------------------------------------------------------
# Translation dicts (PT -> EN)
# ---------------------------------------------------------------------------

NAMES_PT_TO_EN = {
    "Ana": "Anna", "Vitoria": "Victoria", "Rodrigo": "Roderick",
    "Tatiana": "Tanya", "Vanessa": "Vanessa", "Henrique": "Henry",
    "Vinicius": "Vincent", "Sandra": "Sandra", "Roberto": "Robert",
    "Jorge": "George", "Fernanda": "Frances", "Rafael": "Ralph",
    "Isabela": "Isabel", "Andre": "Andrew", "Cesar": "Caesar",
    "Elisa": "Elise", "Fernando": "Ferdinand", "Angela": "Angela",
    "Pedro": "Peter", "Paulo": "Paul", "Maria": "Mary",
    "Joao": "John", "Carlos": "Charles", "Lucas": "Luke",
    "Marcos": "Mark", "Daniel": "Daniel", "Bruno": "Bruno",
    "Gabriel": "Gabriel", "Leonardo": "Leonard", "Julia": "Julia",
}

PRODUCTS_PT_TO_EN = {
    "Regua": "Ruler", "Lapis": "Pencil", "Caneta": "Pen",
    "Borracha": "Eraser", "Caderno": "Notebook", "Mochila": "Backpack",
    "Estojo": "Case", "Tesoura": "Scissors", "Apontador": "Sharpener",
    "Cola": "Glue", "Papel": "Paper", "Livro": "Book",
    "Marcador": "Marker", "Pasta": "Folder", "Clips": "Clips",
    "Grampeador": "Stapler", "Fita": "Tape", "Compasso": "Compass",
    "Cartolina": "Cardboard", "Canetinha": "FeltTip",
}


def translate_tables(tables_pt: dict) -> dict:
    """Return a copy of tables with PT names/products translated to EN."""
    tables_en = {}
    for tname, rows in tables_pt.items():
        new_rows = []
        for r in rows:
            new_r = dict(r)
            for col, val in r.items():
                if val in NAMES_PT_TO_EN:
                    new_r[col] = NAMES_PT_TO_EN[val]
                elif val in PRODUCTS_PT_TO_EN:
                    new_r[col] = PRODUCTS_PT_TO_EN[val]
            new_rows.append(new_r)
        tables_en[tname] = new_rows
    return tables_en


# ---------------------------------------------------------------------------
# Questions (PT and EN parallel)
# ---------------------------------------------------------------------------

QUESTIONS_PT = {
    "q_count": "Quantas linhas existem nos dados? Responda apenas com um numero inteiro.",
    "q_sum":   "Qual e a soma de todos os valores da coluna 'total'? Responda apenas com um numero.",
    "q_top":   "Qual produto aparece mais vezes? Responda apenas com o nome do produto.",
}
QUESTIONS_EN = {
    "q_count": "How many rows exist in the data? Answer with just an integer number.",
    "q_sum":   "What is the sum of all values in the 'total' column? Answer with just a number.",
    "q_top":   "Which product appears most often? Answer with just the product name.",
}
QUESTION_TYPES = {"q_count": "count", "q_sum": "numeric", "q_top": "string"}

SYS_PROMPT_PT = (
    "Voce recebera dados em formato colunar comprimido. "
    "N*val = val repetido N vezes. Dados ordenados para agrupar repeticoes. "
    "Responda com base apenas nos dados."
)
SYS_PROMPT_EN = (
    "You will receive tabular data in compressed columnar format. "
    "N*val means val is repeated N times. Data is sorted to group repetitions. "
    "Answer based only on the data."
)

CELLS = [
    ("pt_pt", SYS_PROMPT_PT, QUESTIONS_PT),
    ("pt_en", SYS_PROMPT_EN, QUESTIONS_EN),  # data PT, questions EN
    ("en_pt", SYS_PROMPT_PT, QUESTIONS_PT),  # data EN, questions PT
    ("en_en", SYS_PROMPT_EN, QUESTIONS_EN),
]


# ---------------------------------------------------------------------------
# Ground truth
# ---------------------------------------------------------------------------

def _compute_gt(tables, translated: bool) -> dict:
    clientes = {c["id"]: c["nome"] for c in tables["clientes"]}
    produtos = {p["id"]: p["nome"] for p in tables["produtos"]}
    vendas = tables["vendas"]
    totals = [float(v["total"]) for v in vendas if v["total"]]
    n = len(vendas)
    prod_counter = Counter(v["id_produto"] for v in vendas)
    top_pid = prod_counter.most_common(1)[0][0]
    top_product = produtos.get(top_pid, top_pid)
    return {
        "q_count": n,
        "q_sum": round(sum(totals), 2),
        "q_top": top_product,
    }


def _score(q_name, response, gt):
    expected = gt[q_name]
    qt = QUESTION_TYPES[q_name]
    if qt == "string":
        clean = strip_think(response).strip().lower()
        ok = str(expected).lower() in clean
        return ok, "correct" if ok else "wrong_name"
    val = extract_number(response)
    if val is None:
        return False, "parse_failure"
    if qt == "count":
        ok = int(round(val)) == int(expected)
        return ok, "correct" if ok else "wrong_count"
    exp_f = float(expected)
    tol = max(abs(exp_f) * 0.02, 0.5)
    ok = abs(val - exp_f) <= tol
    return ok, "correct" if ok else "arithmetic_error"


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

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

    print(f"[LangMatrix] scale={scale}")

    # Data PT
    tables_pt, meta = retail_sales(n_orders=scale, seed=SEED)
    mp_pt, dd_pt = _write_fixture(tables_pt, meta)
    tcf_pt = tcf_encode(str(mp_pt), str(dd_pt),
                         EncodeConfig(level=2, include_stats=False))
    gt_pt = _compute_gt(tables_pt, translated=False)

    # Data EN (translated from PT)
    tables_en = translate_tables(tables_pt)
    mp_en, dd_en = _write_fixture(tables_en, meta)
    tcf_en = tcf_encode(str(mp_en), str(dd_en),
                         EncodeConfig(level=2, include_stats=False))
    gt_en = _compute_gt(tables_en, translated=True)

    data_by_lang = {"pt": tcf_pt, "en": tcf_en}
    gt_by_lang = {"pt": gt_pt, "en": gt_en}

    print(f"[LangMatrix] data PT: {len(tcf_pt):>6} chars")
    print(f"[LangMatrix] data EN: {len(tcf_en):>6} chars")
    print(f"[LangMatrix] GT PT: {gt_pt}")
    print(f"[LangMatrix] GT EN: {gt_en}")
    n_combos = len(models) * len(CELLS) * len(QUESTIONS_PT)
    print(f"[LangMatrix] {n_combos} combos ({len(completed)} cached)")

    if dry_run:
        print("[LangMatrix] --dry-run: exiting")
        return

    warmed = set()
    t_start = time.time()
    i = 0

    for model in models:
        for cell_name, sys_prompt, questions in CELLS:
            data_lang = cell_name.split("_")[0]
            data_text = data_by_lang[data_lang]
            gt = gt_by_lang[data_lang]

            for q_name, q_text in questions.items():
                key = f"{model}|{cell_name}|{q_name}"
                if key in completed:
                    continue
                i += 1
                prompt = f"{sys_prompt}\n\n{q_text}\n\n{data_text}"

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
                print(f"  [{i}/{n_combos} el={el:.0f}s] {model} {cell_name} {q_name}", end=" ", flush=True)
                try:
                    result = client.generate(model, prompt, options=llm_options)
                    response = result["text"]
                    ok, reason = _score(q_name, response, gt)
                    print(f"{'OK' if ok else 'NO'} ({reason}) ans={response[:40]!r}")
                except Exception as e:
                    print(f"ERROR: {e}")
                    response, ok, reason = f"ERROR:{e}", False, "exception"
                    result = {"prompt_tokens": 0, "response_tokens": 0, "total_duration_ns": 0}

                record = {
                    "key": key, "model": model, "cell": cell_name, "question": q_name,
                    "response": response, "ok": ok, "reason": reason,
                    "expected": gt[q_name],
                    "prompt_tokens": result.get("prompt_tokens", 0),
                    "response_tokens": result.get("response_tokens", 0),
                    "total_ms": result.get("total_duration_ns", 0) // 1_000_000,
                }
                with open(manifest_path, "a", encoding="utf-8") as fh:
                    fh.write(json.dumps(record, ensure_ascii=False) + "\n")

    # Summary
    print()
    print("=" * 60)
    print(f"{'model':<22} {'cell':<8} acc")
    by_cell = defaultdict(list)
    for line in manifest_path.read_text(encoding="utf-8").splitlines():
        if not line.strip(): continue
        r = json.loads(line)
        by_cell[(r["model"], r["cell"])].append(r["ok"])
    for (m, c), oks in sorted(by_cell.items()):
        n, c_ok = len(oks), sum(oks)
        print(f"{m:<22} {c:<8} {c_ok/n*100:>4.0f}%  ({c_ok}/{n})")


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

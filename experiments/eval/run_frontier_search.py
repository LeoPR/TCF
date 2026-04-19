"""Sequential frontier search — model capacity × data size × notation × task complexity.

Instead of full factorial (M × N × Q × T = hundreds of combos), this script runs
5 sequential phases, each building on the previous finding:

  Phase 0 — Pilot        : sanity check all models, tiny data (n=20)
  Phase 1 — Model sweep  : rank models at n=50, L3 integer, 4 questions
  Phase 2 — Data sweep   : best model, find n-boundary (where model fails)
  Phase 3 — Notation     : best model, 5 RLE notations (incl N:val), n=50 L2
  Phase 4 — Task sweep   : best model, all 6 questions, n=n_optimal

Total: ~90 combos vs ~400 naive factorial. Each phase appends to the same manifest
so --summary shows the full picture at any point.

Notation inventory (from tokenization empirics 2026-04-18):
  N_star_val  (N*val)   4 tokens — current TCF default
  N_space_val (N val)   3 tokens — cheapest for strings (BPE merge)
  N_x_val     (Nxval)   4 tokens — "N times val"
  val_x_N     (val xN)  4 tokens — postfix, natural English
  N_colon_val (N:val)   4 tokens — YAML/dict-like, NOT YET TESTED

N:val is interesting because `:` is how TCF itself marks column headers
(e.g. `produto:`). This could either help (familiar key-value pattern)
or confuse (conflict with column header syntax).

Usage:
    python experiments/eval/run_frontier_search.py --phase 0 --cpu-only --num-thread 24
    python experiments/eval/run_frontier_search.py --phase 1 --cpu-only --num-thread 24
    python experiments/eval/run_frontier_search.py --phase 2 --cpu-only --num-thread 24
    python experiments/eval/run_frontier_search.py --phase 3 --cpu-only --num-thread 24
    python experiments/eval/run_frontier_search.py --phase 4 --cpu-only --num-thread 24
    python experiments/eval/run_frontier_search.py --summary
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


RESULTS_DIR = ROOT / "experiments" / "results" / "frontier_search"
LLM_OPTIONS = {"temperature": 0, "seed": 42}

DEFAULT_MODELS = [
    "gemma3:4b",
    "qwen2.5:7b",
    "qwen2.5-coder:7b",
]

# ---------------------------------------------------------------------------
# RLE notation variants
# ---------------------------------------------------------------------------

_RLE_STAR_RE = re.compile(r"^(\d+)\*(.+)$")

NOTATIONS: dict[str, dict] = {
    "N_star_val": {
        "rewrite": lambda n, v: f"{n}*{v}",
        "hint": "N*val = val repetido N vezes (ex: 3*Ana = Ana 3 vezes)",
    },
    "N_space_val": {
        "rewrite": lambda n, v: f"{n} {v}",
        "hint": "N val = val repetido N vezes (ex: 3 Ana = Ana 3 vezes)",
    },
    "N_x_val": {
        "rewrite": lambda n, v: f"{n}x{v}",
        "hint": "Nxval = val repetido N vezes (ex: 3xAna = Ana 3 vezes)",
    },
    "val_x_N": {
        "rewrite": lambda n, v: f"{v} x{n}",
        "hint": "val xN = val repetido N vezes (ex: Ana x3 = Ana 3 vezes)",
    },
    "N_colon_val": {
        "rewrite": lambda n, v: f"{n}:{v}",
        "hint": "N:val = val repetido N vezes (ex: 3:Ana = Ana 3 vezes)",
    },
}


def rewrite_notation(tcf_text: str, rewrite_fn) -> str:
    out = []
    for line in tcf_text.splitlines():
        m = _RLE_STAR_RE.match(line)
        if m:
            out.append(rewrite_fn(int(m.group(1)), m.group(2)))
        else:
            out.append(line)
    return "\n".join(out)


# ---------------------------------------------------------------------------
# Ground truth
# ---------------------------------------------------------------------------

def _compute_gt(tables: dict) -> dict:
    clientes = {c["id"]: c["nome"] for c in tables["clientes"]}
    produtos = {p["id"]: p["nome"] for p in tables["produtos"]}
    vendas = tables["vendas"]
    totals = [float(v["total"]) for v in vendas if v["total"]]
    n = len(vendas)
    prod_counter = Counter(v["id_produto"] for v in vendas)
    cli_counter = Counter(v["id_cliente"] for v in vendas)
    top_pid = prod_counter.most_common(1)[0][0]
    top_cid = cli_counter.most_common(1)[0][0]
    max_venda = max(vendas, key=lambda v: float(v["total"]) if v["total"] else 0)
    return {
        "count": n,
        "sum_total": round(sum(totals), 2),
        "avg_total": round(sum(totals) / n, 2) if n else 0,
        "top_product": produtos.get(top_pid, top_pid),
        "top_customer": clientes.get(top_cid, top_cid),
        "distinct_customers": len(set(v["id_cliente"] for v in vendas)),
        "max_buyer": clientes.get(max_venda["id_cliente"], max_venda["id_cliente"]),
    }


# ---------------------------------------------------------------------------
# Questions
# ---------------------------------------------------------------------------

QUESTIONS: dict[str, dict] = {
    # Canary: answerable from header `n=N` — detects header-reading
    "q_count": {
        "text": "Quantas linhas existem nos dados? Responda apenas com um numero inteiro.",
        "key": "count", "type": "count",
    },
    # Requires reading data + ranking
    "q_top_product": {
        "text": "Qual produto aparece mais vezes? Responda apenas com o nome do produto.",
        "key": "top_product", "type": "string",
    },
    # Requires counting distinct values
    "q_distinct": {
        "text": "Quantos clientes distintos aparecem nos dados? Responda apenas com um numero inteiro.",
        "key": "distinct_customers", "type": "count",
    },
    # Requires summing a numeric column (arithmetic)
    "q_sum": {
        "text": "Qual e a soma de todos os valores da coluna total? Responda apenas com um numero.",
        "key": "sum_total", "type": "numeric",
    },
    # Cross-table lookup: max(total) -> id_cliente -> nome
    # Cannot be answered from STATS or header; requires data comprehension
    "q_lookup": {
        "text": "Qual cliente realizou a maior venda individual? Responda apenas com o nome do cliente.",
        "key": "max_buyer", "type": "string",
    },
    # Averaging
    "q_avg": {
        "text": "Qual e a media dos valores de total? Responda apenas com um numero.",
        "key": "avg_total", "type": "numeric",
    },
}

PHASE_QUESTIONS: dict[int, list[str]] = {
    0: ["q_count", "q_top_product"],
    1: ["q_count", "q_top_product", "q_distinct", "q_lookup"],
    2: ["q_top_product", "q_lookup"],
    3: ["q_count", "q_top_product"],
    4: list(QUESTIONS.keys()),
}

SYS_L3 = (
    "Voce recebera dados em formato colunar comprimido (L3). "
    "Colunas com '# dict X: val0,val1,val2' tem valores substituidos pelo indice (0,1,2...). "
    "N*val = val repetido N vezes. "
    "Para responder sobre um valor especifico, busque o indice no dict e conte ocorrencias. "
    "Responda com base apenas nos dados."
)

SYS_L2_TEMPLATE = (
    "Voce recebera dados em formato colunar comprimido. "
    "{hint}. "
    "Linha sem prefixo numerico = 1 ocorrencia. "
    "Dados ordenados para agrupar repeticoes. "
    "Responda com base apenas nos dados."
)


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def _score(q: dict, response: str, gt: dict) -> tuple[bool, str]:
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


# ---------------------------------------------------------------------------
# Manifest helpers
# ---------------------------------------------------------------------------

def load_completed(manifest_path: Path) -> set[str]:
    if not manifest_path.exists():
        return set()
    completed: set[str] = set()
    for line in manifest_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                completed.add(json.loads(line)["key"])
            except Exception:
                pass
    return completed


def append_record(manifest_path: Path, record: dict) -> None:
    with open(manifest_path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")


def read_manifest(manifest_path: Path) -> list[dict]:
    if not manifest_path.exists():
        return []
    result = []
    for line in manifest_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                result.append(json.loads(line))
            except Exception:
                pass
    return result


def phase_acc(records: list[dict], group_key: str) -> dict[str, tuple[int, int]]:
    by: dict[str, list] = defaultdict(list)
    for r in records:
        by[r[group_key]].append(r["ok"])
    return {k: (sum(v), len(v)) for k, v in by.items()}


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def _warm(client: OllamaClient, model: str, llm_options: dict) -> None:
    opts = {**llm_options, "num_predict": 2}
    try:
        client.generate(model, "ok", options=opts)
    except Exception as e:
        print(f"  warm failed: {e}", file=sys.stderr)


def run_combos(
    client: OllamaClient,
    combos: list[dict],
    manifest_path: Path,
    completed: set[str],
    llm_options: dict,
) -> list[dict]:
    new_records = []
    warmed: set[str] = set()
    t_start = time.time()
    pending = [c for c in combos if c["key"] not in completed]
    n_cached = len(combos) - len(pending)
    print(f"  {len(pending)} to run, {n_cached} cached")

    for i, combo in enumerate(pending, 1):
        model = combo["model"]
        if model not in warmed:
            print(f"  warming {model}...")
            _warm(client, model, llm_options)
            warmed.add(model)

        elapsed = time.time() - t_start
        print(f"  [{i}/{len(pending)} el={elapsed:.0f}s] {combo['key']}", end=" ", flush=True)

        try:
            result = client.generate(model, combo["prompt"], options=llm_options)
            response = result["text"]
            ok, reason = _score(combo["q"], response, combo["gt"])
            print(f"{'OK' if ok else 'NO'} ({reason}) ans={response[:40]!r}")
        except Exception as e:
            print(f"ERROR: {e}")
            response, ok, reason = f"ERROR:{e}", False, "exception"
            result = {"prompt_tokens": 0, "response_tokens": 0, "total_duration_ns": 0}

        record = {
            "key": combo["key"],
            "phase": combo["phase"],
            "model": model,
            "question": combo["q"]["key"],
            "response": response,
            "ok": ok,
            "reason": reason,
            "expected": str(combo["gt"][combo["q"]["key"]]),
            "prompt_tokens": result.get("prompt_tokens", 0),
            "response_tokens": result.get("response_tokens", 0),
            "total_ms": result.get("total_duration_ns", 0) // 1_000_000,
            **combo["meta"],
        }
        append_record(manifest_path, record)
        new_records.append(record)

    return new_records


# ---------------------------------------------------------------------------
# Phase builders
# ---------------------------------------------------------------------------

def _l3_data(n_orders: int) -> tuple[str, dict, int]:
    """Returns (tcf_text, ground_truth, actual_n_rows)."""
    tables, meta = retail_sales(n_orders=n_orders, seed=42)
    gt = _compute_gt(tables)
    mp, dd = _write_fixture(tables, meta)
    data_text = tcf_encode(str(mp), str(dd), EncodeConfig(level=3, include_stats=False))
    return data_text, gt, len(tables["vendas"])


def _l2_data(n_orders: int) -> tuple[str, dict, int]:
    tables, meta = retail_sales(n_orders=n_orders, seed=42)
    gt = _compute_gt(tables)
    mp, dd = _write_fixture(tables, meta)
    data_text = tcf_encode(str(mp), str(dd), EncodeConfig(level=2, include_stats=False))
    return data_text, gt, len(tables["vendas"])


def _make_meta(n_orders: int, n_rows: int, level: int, notation: str) -> dict:
    return {"n_orders": n_orders, "n_rows": n_rows, "level": level, "notation": notation}


def build_phase0(models: list[str]) -> list[dict]:
    n_orders = 20
    data_text, gt, n_rows = _l3_data(n_orders)
    combos = []
    for model in models:
        for q_name in PHASE_QUESTIONS[0]:
            q = QUESTIONS[q_name]
            key = f"p0|{model}|{q_name}"
            prompt = f"{SYS_L3}\n\n{q['text']}\n\n{data_text}"
            combos.append({"key": key, "phase": 0, "model": model, "prompt": prompt,
                           "q": q, "gt": gt, "meta": _make_meta(n_orders, n_rows, 3, "N_star_val")})
    print(f"[P0 Pilot] n_orders={n_orders} ({n_rows} vendas), L3 int, "
          f"{len(models)} models × {len(PHASE_QUESTIONS[0])} q = {len(combos)} combos")
    return combos


def build_phase1(models: list[str]) -> list[dict]:
    n_orders = 50
    data_text, gt, n_rows = _l3_data(n_orders)
    combos = []
    for model in models:
        for q_name in PHASE_QUESTIONS[1]:
            q = QUESTIONS[q_name]
            key = f"p1|{model}|{q_name}"
            prompt = f"{SYS_L3}\n\n{q['text']}\n\n{data_text}"
            combos.append({"key": key, "phase": 1, "model": model, "prompt": prompt,
                           "q": q, "gt": gt, "meta": _make_meta(n_orders, n_rows, 3, "N_star_val")})
    print(f"[P1 Model sweep] n_orders={n_orders} ({n_rows} vendas), L3 int, "
          f"{len(models)} models × {len(PHASE_QUESTIONS[1])} q = {len(combos)} combos")
    return combos


def build_phase2(pilot: str) -> list[dict]:
    # n_orders -> actual vendas: 5->11, 10->23, 20->42, 50->115, 100->255, 200->509
    # Capped at 200 to keep CPU time reasonable (509 vendas already ~5k token prompt)
    ns = [5, 10, 20, 50, 100, 200]
    combos = []
    for n_orders in ns:
        data_text, gt, n_rows = _l3_data(n_orders)
        for q_name in PHASE_QUESTIONS[2]:
            q = QUESTIONS[q_name]
            key = f"p2|{pilot}|n{n_orders}|{q_name}"
            prompt = f"{SYS_L3}\n\n{q['text']}\n\n{data_text}"
            combos.append({"key": key, "phase": 2, "model": pilot, "prompt": prompt,
                           "q": q, "gt": gt, "meta": _make_meta(n_orders, n_rows, 3, "N_star_val")})
    print(f"[P2 Data sweep] pilot={pilot}, {len(ns)} scales × {len(PHASE_QUESTIONS[2])} q = {len(combos)} combos")
    return combos


def build_phase3(pilot: str) -> list[dict]:
    n_orders = 50
    base_text, gt, n_rows = _l2_data(n_orders)
    combos = []
    for notation_name, notation_cfg in NOTATIONS.items():
        data_text = rewrite_notation(base_text, notation_cfg["rewrite"])
        sys_prompt = SYS_L2_TEMPLATE.format(hint=notation_cfg["hint"])
        for q_name in PHASE_QUESTIONS[3]:
            q = QUESTIONS[q_name]
            key = f"p3|{pilot}|{notation_name}|{q_name}"
            prompt = f"{sys_prompt}\n\n{q['text']}\n\n{data_text}"
            combos.append({"key": key, "phase": 3, "model": pilot, "prompt": prompt,
                           "q": q, "gt": gt, "meta": _make_meta(n_orders, n_rows, 2, notation_name)})
    print(f"[P3 Notation] pilot={pilot}, n_orders={n_orders} ({n_rows} vendas), "
          f"{len(NOTATIONS)} notations × {len(PHASE_QUESTIONS[3])} q = {len(combos)} combos")
    return combos


def build_phase4(pilot: str, n_orders: int) -> list[dict]:
    data_text, gt, n_rows = _l3_data(n_orders)
    combos = []
    for q_name in PHASE_QUESTIONS[4]:
        q = QUESTIONS[q_name]
        key = f"p4|{pilot}|n{n_orders}|{q_name}"
        prompt = f"{SYS_L3}\n\n{q['text']}\n\n{data_text}"
        combos.append({"key": key, "phase": 4, "model": pilot, "prompt": prompt,
                       "q": q, "gt": gt, "meta": _make_meta(n_orders, n_rows, 3, "N_star_val")})
    print(f"[P4 Task sweep] pilot={pilot}, n_orders={n_orders} ({n_rows} vendas), {len(combos)} questions")
    return combos


# ---------------------------------------------------------------------------
# Auto-pick helpers
# ---------------------------------------------------------------------------

def pick_pilot(records: list[dict]) -> str:
    by_model: dict[str, list] = defaultdict(list)
    for r in records:
        by_model[r["model"]].append(r["ok"])
    ranked = sorted(by_model.items(), key=lambda kv: (sum(kv[1]) / len(kv[1]), len(kv[1])), reverse=True)
    print("  Model ranking:")
    for model, oks in ranked:
        print(f"    {model:<26} {sum(oks)}/{len(oks)} = {sum(oks)/len(oks)*100:.0f}%")
    best = ranked[0][0]
    print(f"  -> pilot: {best}")
    return best


def pick_n_optimal(records: list[dict]) -> int:
    """Return largest n_orders where model got q_top_product correct.

    Uses q_top_product (not q_lookup) as the boundary indicator because
    q_lookup requires tracking row position through RLE runs, which TCF's
    column-independent sort makes unreliable even for capable models.
    """
    by_n: dict[int, dict] = defaultdict(lambda: {"top": None, "lookup": None})
    for r in records:
        n = r.get("n_orders", r.get("n"))  # backward compat
        if r["question"] == "top_product":
            by_n[n]["top"] = r["ok"]
        elif r["question"] == "max_buyer":
            by_n[n]["lookup"] = r["ok"]
    if not by_n:
        print("  No phase-2 data — using n_orders=50")
        return 50

    print("  n_orders | q_top_product | q_lookup")
    for n in sorted(by_n):
        d = by_n[n]
        top_s = "OK" if d["top"] else ("NO" if d["top"] is False else "-")
        lk_s = "OK" if d["lookup"] else ("NO" if d["lookup"] is False else "-")
        print(f"    n={n:<4}  {top_s:<12}  {lk_s}")

    good_ns = [n for n, d in by_n.items() if d["top"] is True]
    if not good_ns:
        print("  Model never got top_product right — using smallest tested n")
        return min(by_n)
    n_opt = max(good_ns)
    print(f"  n_optimal = {n_opt} (largest n_orders with q_top_product correct)")
    return n_opt


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

def print_summary(manifest_path: Path) -> None:
    records = read_manifest(manifest_path)
    if not records:
        print("[Summary] No records yet.")
        return

    by_phase: dict[int, list] = defaultdict(list)
    for r in records:
        by_phase[r["phase"]].append(r)

    for ph in sorted(by_phase):
        recs = by_phase[ph]
        labels = {0: "Pilot", 1: "Model sweep", 2: "Data sweep", 3: "Notation", 4: "Task sweep"}
        print(f"\n{'='*62}")
        print(f"Phase {ph} — {labels.get(ph, '?')}  ({len(recs)} records)")
        print("-"*62)

        if ph in (0, 1):
            for model, (c, t) in sorted(phase_acc(recs, "model").items()):
                bar = "#" * c + "." * (t - c)
                print(f"  {model:<28} [{bar}] {c/t*100:>4.0f}%  ({c}/{t})")
        elif ph == 2:
            by_n: dict[int, list] = defaultdict(list)
            n_rows_of: dict[int, int] = {}
            for r in recs:
                n = r.get("n_orders", r.get("n"))
                by_n[n].append(r["ok"])
                if "n_rows" in r:
                    n_rows_of[n] = r["n_rows"]
            for n in sorted(by_n):
                oks = by_n[n]
                bar = "#" * sum(oks) + "." * (len(oks) - sum(oks))
                nr = f" ({n_rows_of[n]} vendas)" if n in n_rows_of else ""
                print(f"  n_orders={n:<4}{nr:<16} [{bar}] {sum(oks)/len(oks)*100:>4.0f}%  ({sum(oks)}/{len(oks)})")
        elif ph == 3:
            for notation, (c, t) in sorted(phase_acc(recs, "notation").items()):
                bar = "#" * c + "." * (t - c)
                print(f"  {notation:<20} [{bar}] {c/t*100:>4.0f}%  ({c}/{t})")
        elif ph == 4:
            for q, (c, t) in sorted(phase_acc(recs, "question").items()):
                status = "OK" if c == t else "NO"
                print(f"  {q:<22} [{status}] ({c}/{t})")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Sequential frontier search ablation")
    parser.add_argument("--phase", type=int, choices=[0, 1, 2, 3, 4], help="Run a specific phase")
    parser.add_argument("--summary", action="store_true", help="Print all results and exit")
    parser.add_argument("--models", nargs="+", default=DEFAULT_MODELS)
    parser.add_argument("--endpoint", default="http://localhost:11434")
    parser.add_argument("--cpu-only", action="store_true")
    parser.add_argument("--num-thread", type=int, default=None)
    parser.add_argument("--pilot-model", default=None,
                        help="Override auto-selected pilot for phases 2,3,4")
    parser.add_argument("--n-override", type=int, default=None,
                        help="Override n_optimal (n_orders) for phase 4")
    parser.add_argument("--dry-run", action="store_true",
                        help="Build combos and print size estimates without calling models")
    args = parser.parse_args()

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    manifest_path = RESULTS_DIR / "manifest.jsonl"

    if args.summary:
        print_summary(manifest_path)
        return

    if args.phase is None:
        parser.print_help()
        return

    client = OllamaClient(args.endpoint)
    llm_options = dict(LLM_OPTIONS)
    if args.cpu_only:
        llm_options["num_gpu"] = 0
    if args.num_thread is not None:
        llm_options["num_thread"] = args.num_thread

    completed = load_completed(manifest_path)

    def _pilot() -> str:
        if args.pilot_model:
            return args.pilot_model
        for ph in (1, 0):
            recs = [r for r in read_manifest(manifest_path) if r["phase"] == ph]
            if recs:
                print(f"[Auto-pilot] Reading from phase {ph}...")
                return pick_pilot(recs)
        print("[Auto-pilot] No prior phase data — using default model")
        return DEFAULT_MODELS[0]

    def _dry(combos: list[dict]) -> None:
        print(f"\n[Dry-run] {len(combos)} combos, "
              f"{len([c for c in combos if c['key'] not in completed])} would run")
        # Print prompt size stats
        sizes = [len(c["prompt"]) for c in combos]
        print(f"  Prompt chars: min={min(sizes)} avg={sum(sizes)//len(sizes)} max={max(sizes)}")
        print(f"  Sample key: {combos[0]['key']}")
        print(f"  Sample prompt head:")
        for line in combos[0]["prompt"].splitlines()[:15]:
            print(f"    {line}")
        print("    ...")

    if args.phase == 0:
        combos = build_phase0(args.models)
        if args.dry_run: _dry(combos); return
        run_combos(client, combos, manifest_path, completed, llm_options)
        print("\n[P0 Results]")
        print_summary(manifest_path)

    elif args.phase == 1:
        combos = build_phase1(args.models)
        if args.dry_run: _dry(combos); return
        run_combos(client, combos, manifest_path, completed, llm_options)
        print("\n[P1 Results — pick pilot for phase 2]")
        recs = [r for r in read_manifest(manifest_path) if r["phase"] == 1]
        pick_pilot(recs)

    elif args.phase == 2:
        pilot = _pilot()
        combos = build_phase2(pilot)
        if args.dry_run: _dry(combos); return
        run_combos(client, combos, manifest_path, completed, llm_options)
        print("\n[P2 Results — n-boundary]")
        recs = [r for r in read_manifest(manifest_path) if r["phase"] == 2]
        n_opt = pick_n_optimal(recs)
        print(f"\nNext: --phase 4 --n-override {n_opt}  (or run phase 3 first)")

    elif args.phase == 3:
        pilot = _pilot()
        combos = build_phase3(pilot)
        if args.dry_run: _dry(combos); return
        run_combos(client, combos, manifest_path, completed, llm_options)
        print("\n[P3 Results — notation ranking]")
        recs = [r for r in read_manifest(manifest_path) if r["phase"] == 3]
        for notation, (c, t) in sorted(phase_acc(recs, "notation").items()):
            print(f"  {notation:<22} {c/t*100:>4.0f}%  ({c}/{t})")

    elif args.phase == 4:
        pilot = _pilot()
        if args.n_override:
            n_opt = args.n_override
        else:
            recs_p2 = [r for r in read_manifest(manifest_path) if r["phase"] == 2]
            n_opt = pick_n_optimal(recs_p2) if recs_p2 else 50
        combos = build_phase4(pilot, n_opt)
        if args.dry_run: _dry(combos); return
        run_combos(client, combos, manifest_path, completed, llm_options)
        print("\n[P4 Results — full task profile]")
        print_summary(manifest_path)


if __name__ == "__main__":
    main()

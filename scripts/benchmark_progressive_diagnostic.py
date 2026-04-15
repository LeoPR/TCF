"""Progressive diagnostic — scale from 1+1 to 500 rows.

Tests WHERE each model breaks by escalating complexity:
  N0: pure arithmetic (3 numbers)
  N1: pure arithmetic (7 numbers)
  N2: CSV minimal (5 rows, 3 cols)
  N3: TCF L0 minimal (5 rows)
  N4: TOON minimal (5 rows)
  N5: representative sample (20 rows via shaper stratified)
  N6: same in TCF L0
  N7: scale (100 rows, CSV + TCF L0 + TCF L2)
  N8: scale (500 rows, CSV + TCF L0 + TCF L2)

Each level only makes sense if the previous passes.
Results show the "breakpoint" per model.

Persists to Z:/tcf-data/benchmarks/progressive-diagnostic.jsonl

Usage:
    python scripts/benchmark_progressive_diagnostic.py
    python scripts/benchmark_progressive_diagnostic.py --models gemma3:4b
"""

from __future__ import annotations

import argparse
import csv as csv_mod
import io
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _paths import PROJECT_ROOT, data_root  # noqa: E402
from dataset_reader import DatasetReader  # noqa: E402
from writers.toon_writer import encode_toon  # noqa: E402

sys.path.insert(0, str(PROJECT_ROOT / "src"))
from tcf import encode_columns, EncodeConfig  # noqa: E402

sys.path.insert(0, str(PROJECT_ROOT / "experiments" / "eval"))
from llm_eval.ollama_client import OllamaClient  # noqa: E402
from llm_eval.metrics import extract_number, strip_think  # noqa: E402


RESULTS_PATH = data_root() / "benchmarks" / "progressive-diagnostic.jsonl"
LLM_OPTIONS = {"temperature": 0, "seed": 42}

DEFAULT_MODELS = [
    "gemma3:4b",
    "qwen3:8b",
    "gemma3:12b",
    "phi4:latest",
    "gpt-oss:latest",
]

EXCLUDE_COLUMNS = {"c_comment", "l_comment", "s_comment", "ps_comment",
                   "o_comment", "p_comment", "r_comment", "n_comment"}


# ---------------------------------------------------------------------------
# Level definitions
# ---------------------------------------------------------------------------

def _build_levels(reader: DatasetReader) -> list[dict]:
    """Build all diagnostic levels with prompts and ground truth."""

    # Get Adult data at various scales
    all_rows = reader.rows("adult")
    cols = [c for c in reader.column_names("adult") if c not in EXCLUDE_COLUMNS]

    # Compute ground truths at each scale
    def _gt_avg_age(rows):
        ages = [r["age"] for r in rows if r["age"] is not None]
        return round(sum(ages) / len(ages), 2)

    def _gt_count(rows):
        return len(rows)

    def _gt_max_hours(rows):
        return max(r["hours-per-week"] for r in rows if r["hours-per-week"] is not None)

    # Samples at various sizes
    rows_5 = all_rows[:5]
    rows_20 = all_rows[:20]
    rows_100 = all_rows[:100]
    rows_500 = all_rows[:500]

    # Extract just ages for arithmetic tests
    ages_3 = [all_rows[i]["age"] for i in [0, 1, 2]]
    ages_7 = [all_rows[i]["age"] for i in range(7)]

    def _to_csv(rows):
        buf = io.StringIO()
        w = csv_mod.DictWriter(buf, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({c: ("" if r.get(c) is None else r[c]) for c in cols})
        return buf.getvalue()

    def _to_tcf(rows, level=0, stats=True):
        columns = {c: [str(r[c]) if r[c] is not None else "" for r in rows] for c in cols}
        return encode_columns("adult", columns, config=EncodeConfig(level=level, include_stats=stats))

    def _to_toon(rows):
        safe = [{c: r.get(c) for c in cols} for r in rows]
        return encode_toon("adult", cols, safe)

    levels = [
        # N0: Pure arithmetic — 3 numbers
        {
            "id": "N0_arith_3",
            "name": "Pure arithmetic (3 numbers)",
            "system": "You are a calculator. Answer with just the number.",
            "data": "",
            "question": f"What is the average of these numbers: {', '.join(str(a) for a in ages_3)}?",
            "ground_truth": round(sum(ages_3) / len(ages_3), 2),
            "answer_type": "numeric",
            "scale": 3,
            "format": "none",
        },
        # N1: Pure arithmetic — 7 numbers
        {
            "id": "N1_arith_7",
            "name": "Pure arithmetic (7 numbers)",
            "system": "You are a calculator. Answer with just the number.",
            "data": "",
            "question": f"What is the average of these numbers: {', '.join(str(a) for a in ages_7)}?",
            "ground_truth": round(sum(ages_7) / len(ages_7), 2),
            "answer_type": "numeric",
            "scale": 7,
            "format": "none",
        },
        # N2: CSV minimal — 5 rows
        {
            "id": "N2_csv_5",
            "name": "CSV minimal (5 rows)",
            "system": "You will receive tabular data in CSV format. Answer based only on the data.",
            "data": _to_csv(rows_5),
            "question": "What is the average age? Answer with just a number.",
            "ground_truth": _gt_avg_age(rows_5),
            "answer_type": "numeric",
            "scale": 5,
            "format": "csv",
        },
        # N3: TCF L0 minimal — 5 rows
        {
            "id": "N3_tcf_5",
            "name": "TCF L0 minimal (5 rows)",
            "system": "You will receive data in columnar format. Each block starts with column name followed by ':'. Values one per line. Answer based only on the data.",
            "data": _to_tcf(rows_5, level=0),
            "question": "What is the average age? Answer with just a number.",
            "ground_truth": _gt_avg_age(rows_5),
            "answer_type": "numeric",
            "scale": 5,
            "format": "tcf_L0",
        },
        # N4: TOON minimal — 5 rows
        {
            "id": "N4_toon_5",
            "name": "TOON minimal (5 rows)",
            "system": "You will receive data in TOON format. Header declares fields, each indented line is a record. Answer based only on the data.",
            "data": _to_toon(rows_5),
            "question": "What is the average age? Answer with just a number.",
            "ground_truth": _gt_avg_age(rows_5),
            "answer_type": "numeric",
            "scale": 5,
            "format": "toon",
        },
        # N5: CSV 20 rows (representative)
        {
            "id": "N5_csv_20",
            "name": "CSV representative (20 rows)",
            "system": "You will receive tabular data in CSV format. Answer based only on the data.",
            "data": _to_csv(rows_20),
            "question": "What is the average age? Answer with just a number.",
            "ground_truth": _gt_avg_age(rows_20),
            "answer_type": "numeric",
            "scale": 20,
            "format": "csv",
        },
        # N6: TCF L0 20 rows
        {
            "id": "N6_tcf_20",
            "name": "TCF L0 representative (20 rows)",
            "system": "You will receive data in columnar format. Each block starts with column name followed by ':'. Values one per line. Answer based only on the data.",
            "data": _to_tcf(rows_20, level=0),
            "question": "What is the average age? Answer with just a number.",
            "ground_truth": _gt_avg_age(rows_20),
            "answer_type": "numeric",
            "scale": 20,
            "format": "tcf_L0",
        },
        # N7: 100 rows — CSV, TCF L0, TCF L2
        {
            "id": "N7a_csv_100",
            "name": "CSV scale (100 rows)",
            "system": "You will receive tabular data in CSV format. Answer based only on the data.",
            "data": _to_csv(rows_100),
            "question": "What is the average age? Answer with just a number.",
            "ground_truth": _gt_avg_age(rows_100),
            "answer_type": "numeric",
            "scale": 100,
            "format": "csv",
        },
        {
            "id": "N7b_tcf_100",
            "name": "TCF L0 scale (100 rows)",
            "system": "You will receive data in columnar format. Each block starts with column name followed by ':'. Values one per line. Answer based only on the data.",
            "data": _to_tcf(rows_100, level=0),
            "question": "What is the average age? Answer with just a number.",
            "ground_truth": _gt_avg_age(rows_100),
            "answer_type": "numeric",
            "scale": 100,
            "format": "tcf_L0",
        },
        {
            "id": "N7c_tcf_L2_100",
            "name": "TCF L2 scale (100 rows)",
            "system": "You will receive data in compressed columnar format. N*val means val repeated N times. Answer based only on the data.",
            "data": _to_tcf(rows_100, level=2),
            "question": "What is the average age? Answer with just a number.",
            "ground_truth": _gt_avg_age(rows_100),
            "answer_type": "numeric",
            "scale": 100,
            "format": "tcf_L2",
        },
        # N8: 500 rows
        {
            "id": "N8a_csv_500",
            "name": "CSV stress (500 rows)",
            "system": "You will receive tabular data in CSV format. Answer based only on the data.",
            "data": _to_csv(rows_500),
            "question": "What is the average age? Answer with just a number.",
            "ground_truth": _gt_avg_age(rows_500),
            "answer_type": "numeric",
            "scale": 500,
            "format": "csv",
        },
        {
            "id": "N8b_tcf_500",
            "name": "TCF L0 stress (500 rows)",
            "system": "You will receive data in columnar format. Each block starts with column name followed by ':'. Values one per line. Answer based only on the data.",
            "data": _to_tcf(rows_500, level=0),
            "question": "What is the average age? Answer with just a number.",
            "ground_truth": _gt_avg_age(rows_500),
            "answer_type": "numeric",
            "scale": 500,
            "format": "tcf_L0",
        },
    ]

    return levels


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run_diagnostic(models: list[str], endpoint: str) -> None:
    client = OllamaClient(endpoint)
    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Load cache
    completed: set[str] = set()
    if RESULTS_PATH.exists():
        for line in RESULTS_PATH.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:
                    completed.add(json.loads(line)["key"])
                except (json.JSONDecodeError, KeyError):
                    pass

    reader = DatasetReader("adult-census")
    levels = _build_levels(reader)
    reader.close()

    total = len(models) * len(levels)
    cached = len(completed)
    print(f"[diagnostic] {total} combos, {cached} cached, {total - cached} to run")

    warmed: set[str] = set()
    i = 0

    for model in models:
        for level in levels:
            i += 1
            key = f"{model}|{level['id']}"
            if key in completed:
                continue

            if model not in warmed:
                print(f"  [warmup] {model} ...", end="", flush=True)
                try:
                    client.generate(model=model, prompt="2+2=?", options=LLM_OPTIONS)
                    print(" ready")
                except Exception as e:
                    print(f" SKIP ({e})")
                    warmed.add(model)
                    break
                warmed.add(model)

            # Build prompt
            if level["data"]:
                prompt = (
                    f"<s>SYSTEM> {level['system']}</s>\n"
                    f"<s>CONTEXT>\n{level['data']}\n</s>\n"
                    f"<s>USER> {level['question']}</s>\n"
                    "<s>ASSISTANT>"
                )
            else:
                prompt = (
                    f"<s>SYSTEM> {level['system']}</s>\n"
                    f"<s>USER> {level['question']}</s>\n"
                    "<s>ASSISTANT>"
                )

            print(f"  [{i}/{total}] {model:20s} {level['id']:20s} ", end="", flush=True)

            try:
                t0 = time.perf_counter()
                gen = client.generate(model=model, prompt=prompt, options=LLM_OPTIONS)
                latency = time.perf_counter() - t0
                response = gen["text"].strip()

                # Score with multi-level tolerance
                val = extract_number(response)
                expected = float(level["ground_truth"])
                if val is None:
                    correct = False
                    tier = "unparseable"
                    rel_error = None
                elif expected == 0:
                    correct = abs(val) < 1
                    tier = "T1" if correct else "T5"
                    rel_error = abs(val)
                else:
                    rel_error = abs(val - expected) / abs(expected)
                    if rel_error <= 0.01:
                        tier = "T1"
                    elif rel_error <= 0.05:
                        tier = "T2"
                    elif rel_error <= 0.15:
                        tier = "T3"
                    elif rel_error <= 0.50:
                        tier = "T4"
                    else:
                        tier = "T5"
                    correct = tier in ("T1", "T2")

                result = {
                    "key": key,
                    "model": model,
                    "level_id": level["id"],
                    "level_name": level["name"],
                    "scale": level["scale"],
                    "format": level["format"],
                    "correct": correct,
                    "tier": tier,
                    "rel_error": round(rel_error, 4) if rel_error is not None else None,
                    "predicted": val,
                    "expected": expected,
                    "response": response[:200],
                    "latency_s": round(latency, 2),
                    "prompt_chars": len(prompt),
                    "prompt_tokens": gen.get("prompt_tokens", 0),
                }
            except KeyboardInterrupt:
                print("\n[interrupted]")
                sys.exit(0)
            except Exception as exc:
                result = {
                    "key": key, "model": model,
                    "level_id": level["id"], "level_name": level["name"],
                    "scale": level["scale"], "format": level["format"],
                    "correct": False, "tier": "error",
                    "rel_error": None, "predicted": None, "expected": float(level["ground_truth"]),
                    "response": "", "latency_s": 0,
                    "prompt_chars": 0, "prompt_tokens": 0,
                    "error": str(exc)[:200],
                }

            with RESULTS_PATH.open("a", encoding="utf-8") as f:
                f.write(json.dumps(result, ensure_ascii=False) + "\n")
            completed.add(key)

            status = f"{tier} err={result['rel_error']}" if result["rel_error"] is not None else tier
            print(f"{status} {result['latency_s']}s")

    # Summary
    entries = [json.loads(l) for l in RESULTS_PATH.read_text(encoding="utf-8").splitlines() if l.strip()]
    print(f"\n{'='*75}")
    print(f"PROGRESSIVE DIAGNOSTIC ({len(entries)} entries)")
    print(f"{'='*75}")

    level_ids = [l["id"] for l in levels]
    print(f"\n{'Model':>20}", end="")
    for lid in level_ids:
        short = lid.split("_")[0]
        print(f" {short:>5}", end="")
    print()
    print("-" * (22 + 6 * len(level_ids)))

    for model in models:
        print(f"{model:>20}", end="")
        for lid in level_ids:
            match = [e for e in entries if e["model"] == model and e["level_id"] == lid]
            if match:
                e = match[0]
                if e["tier"] in ("T1", "T2"):
                    symbol = "OK"
                elif e["tier"] in ("T3", "T4"):
                    symbol = "~"
                elif e["tier"] == "error":
                    symbol = "ERR"
                else:
                    symbol = "FAIL"
                print(f" {symbol:>5}", end="")
            else:
                print(f" {'?':>5}", end="")
        print()

    print(f"\nLegend: OK=T1/T2 (<=5%), ~=T3/T4 (<=50%), FAIL=T5 (>50%), ERR=exception")


def main():
    parser = argparse.ArgumentParser(description="Progressive diagnostic")
    parser.add_argument("--models", nargs="+", default=DEFAULT_MODELS)
    parser.add_argument("--endpoint", default="http://localhost:11434")
    args = parser.parse_args()
    run_diagnostic(args.models, args.endpoint)


if __name__ == "__main__":
    main()

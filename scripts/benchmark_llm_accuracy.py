"""LLM accuracy benchmark — test how well models answer questions on formatted data.

Compares CSV, JSONL, TOON, TCF L0 (with/without STATS), and TCF L2
across multiple models, datasets, and scales.

Uses:
  - DatasetReader + Shaper (scripts/) to get controlled data subsets
  - encode_columns (src/tcf/) for TCF
  - toon_writer (scripts/) for TOON
  - OllamaClient (experiments/) for LLM inference
  - Timings (src/tcf/) for phase measurement

Results persisted as JSONL in Z:/tcf-data/benchmarks/llm-accuracy-canonical.jsonl

Usage:
    python scripts/benchmark_llm_accuracy.py
    python scripts/benchmark_llm_accuracy.py --models gemma3:4b qwen3:8b
    python scripts/benchmark_llm_accuracy.py --dataset adult-census --scale 100
"""

from __future__ import annotations

import argparse
import csv as csv_mod
import io
import json
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _paths import PROJECT_ROOT, data_root  # noqa: E402
from dataset_reader import DatasetReader  # noqa: E402
from writers.toon_writer import encode_toon  # noqa: E402

sys.path.insert(0, str(PROJECT_ROOT / "src"))
from tcf import encode_columns, EncodeConfig  # noqa: E402
from tcf.timing import Timings  # noqa: E402

sys.path.insert(0, str(PROJECT_ROOT / "experiments" / "eval"))
from llm_eval.ollama_client import OllamaClient  # noqa: E402
from llm_eval.metrics import extract_number, strip_think  # noqa: E402


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

RESULTS_PATH = data_root() / "benchmarks" / "llm-accuracy-canonical.jsonl"

DEFAULT_MODELS = [
    "gemma3:4b",
    "qwen3:8b",
    "gemma3:12b",
    "phi4:latest",
    "gpt-oss:latest",
]

LLM_OPTIONS = {"temperature": 0, "seed": 42}

# Exclude freeform text columns (ticket 29 — decoder bug)
EXCLUDE_COLUMNS = {"c_comment", "l_comment", "s_comment", "ps_comment",
                   "o_comment", "p_comment", "r_comment", "n_comment"}

# System prompts per format
SYSTEM_PROMPTS = {
    "csv": "You will receive tabular data in CSV format. First line is column names, remaining lines are records. Answer based only on the data provided.",
    "jsonl": "You will receive data in JSON Lines format. Each line is an independent JSON object. Answer based only on the data provided.",
    "toon": "You will receive data in TOON (Token-Oriented Object Notation) format. The header declares field names, each indented line is a record with values in the same order. Answer based only on the data provided.",
    "tcf_L0": "You will receive data in columnar format. Each block starts with a column name followed by ':'. Values are listed one per line, in the same order across columns. Answer based only on the data provided.",
    "tcf_L2": "You will receive data in compressed columnar format. N*val means val repeated N times consecutively. Data is sorted to group repetitions. Answer based only on the data provided.",
    "tcf_L0_nostats": "You will receive data in columnar format. Each block starts with a column name followed by ':'. Values are listed one per line, in the same order across columns. Answer based only on the data provided.",
}


# ---------------------------------------------------------------------------
# Format converters
# ---------------------------------------------------------------------------

def _rows_to_csv_text(rows: list[dict], col_names: list[str]) -> str:
    buf = io.StringIO()
    w = csv_mod.DictWriter(buf, fieldnames=col_names, extrasaction="ignore")
    w.writeheader()
    for row in rows:
        w.writerow({c: ("" if row.get(c) is None else row[c]) for c in col_names})
    return buf.getvalue()


def _rows_to_jsonl_text(rows: list[dict], col_names: list[str]) -> str:
    lines = []
    for row in rows:
        obj = {c: row.get(c) for c in col_names}
        lines.append(json.dumps(obj, ensure_ascii=False))
    return "\n".join(lines) + "\n"


def _rows_to_tcf_text(rows: list[dict], col_names: list[str],
                       table_name: str, level: int, stats: bool) -> str:
    columns = {
        c: [str(row[c]) if row[c] is not None else "" for row in rows]
        for c in col_names
    }
    config = EncodeConfig(level=level, include_stats=stats)
    return encode_columns(table_name, columns, config=config)


def _rows_to_toon_text(rows: list[dict], col_names: list[str],
                        table_name: str) -> str:
    safe_rows = [{c: row.get(c) for c in col_names} for row in rows]
    return encode_toon(table_name, col_names, safe_rows)


def format_data(rows: list[dict], col_names: list[str],
                table_name: str, fmt: str) -> str:
    """Convert rows to the specified format string."""
    if fmt == "csv":
        return _rows_to_csv_text(rows, col_names)
    elif fmt == "jsonl":
        return _rows_to_jsonl_text(rows, col_names)
    elif fmt == "toon":
        return _rows_to_toon_text(rows, col_names, table_name)
    elif fmt == "tcf_L0":
        return _rows_to_tcf_text(rows, col_names, table_name, 0, True)
    elif fmt == "tcf_L2":
        return _rows_to_tcf_text(rows, col_names, table_name, 2, True)
    elif fmt == "tcf_L0_nostats":
        return _rows_to_tcf_text(rows, col_names, table_name, 0, False)
    else:
        raise ValueError(f"Unknown format: {fmt}")


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def score_response(response: str, ground_truth: Any, answer_type: str) -> tuple[bool, str]:
    """Score a response against ground truth. Returns (correct, error_type)."""
    clean = strip_think(response).strip()

    if answer_type == "string":
        expected = str(ground_truth).lower()
        ok = expected in clean.lower()
        return ok, "correct" if ok else "wrong_name"

    if answer_type == "pairs":
        # For group-by results, check if all key-value pairs are mentioned
        if isinstance(ground_truth, list):
            found = 0
            for pair in ground_truth:
                key = str(pair[0]).lower()
                if key in clean.lower():
                    found += 1
            ok = found >= len(ground_truth) * 0.5  # at least half mentioned
            return ok, "correct" if ok else "partial_match"
        return False, "parse_failure"

    # Numeric or count
    val = extract_number(response)
    if val is None:
        return False, "parse_failure"

    expected = float(ground_truth)
    if answer_type == "count":
        ok = int(round(val)) == int(expected)
        return ok, "correct" if ok else "wrong_count"

    # Numeric: 2% tolerance or 0.5 absolute
    tol = max(abs(expected) * 0.02, 0.5)
    ok = abs(val - expected) <= tol
    return ok, "correct" if ok else "arithmetic_error"


# ---------------------------------------------------------------------------
# Main benchmark
# ---------------------------------------------------------------------------

def select_questions(dataset: str, n: int = 5) -> list[dict]:
    """Select representative questions from the question bank."""
    qpath = PROJECT_ROOT / "datasets" / "questions" / f"{dataset}.json"
    data = json.loads(qpath.read_text(encoding="utf-8"))
    questions = data["questions"]

    # Prefer diversity: 1 per category, fill rest by difficulty
    categories_seen = set()
    selected = []
    for q in questions:
        cat = q.get("category", "")
        if cat not in categories_seen and len(selected) < n:
            selected.append(q)
            categories_seen.add(cat)
    # Fill remaining
    for q in questions:
        if q not in selected and len(selected) < n:
            selected.append(q)

    return selected[:n]


def run_benchmark(
    models: list[str],
    datasets: list[tuple[str, str, list[int]]],  # [(dataset, table, [scales])]
    formats: list[str],
    n_questions: int,
    endpoint: str,
) -> None:
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

    total_combos = 0
    for ds_name, table, scales in datasets:
        total_combos += len(scales) * len(formats) * len(models) * n_questions
    cached = len(completed)
    print(f"[llm] Total combos: {total_combos}, cached: {cached}, to run: {total_combos - cached}")

    warmed: set[str] = set()
    combo_i = 0

    for ds_name, table, scales in datasets:
        reader = DatasetReader(ds_name)
        questions = select_questions(ds_name, n_questions)
        all_rows = reader.rows(table)
        col_names = [c for c in reader.column_names(table) if c not in EXCLUDE_COLUMNS]

        for scale in scales:
            rows = all_rows[:scale]
            n = len(rows)

            # Pre-generate all formats for this scale
            data_blocks: dict[str, str] = {}
            for fmt in formats:
                data_blocks[fmt] = format_data(rows, col_names, table, fmt)

            for model in models:
                for q in questions:
                    for fmt in formats:
                        combo_i += 1
                        key = f"{model}|{ds_name}|{table}|{n}|{fmt}|{q['id']}"
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
                        sys_prompt = SYSTEM_PROMPTS.get(fmt, SYSTEM_PROMPTS["csv"])
                        question_text = q.get("text_en", q.get("text_pt", ""))
                        prompt = (
                            f"<s>SYSTEM> {sys_prompt}</s>\n"
                            f"<s>CONTEXT>\n{data_blocks[fmt]}\n</s>\n"
                            f"<s>USER> {question_text} Answer with just the value, no explanation.</s>\n"
                            "<s>ASSISTANT>"
                        )

                        label = f"{model:20s} {ds_name}:{table}:{n} {fmt:15s} {q['id']:30s}"
                        print(f"  [{combo_i}/{total_combos}] {label}", end=" ", flush=True)

                        try:
                            t0 = time.perf_counter()
                            gen = client.generate(model=model, prompt=prompt, options=LLM_OPTIONS)
                            latency = time.perf_counter() - t0
                            response = gen["text"].strip()
                            correct, error_type = score_response(
                                response, q["ground_truth"], q["answer_type"]
                            )

                            result = {
                                "key": key,
                                "model": model,
                                "dataset": ds_name,
                                "table": table,
                                "scale": n,
                                "format": fmt,
                                "question_id": q["id"],
                                "question_category": q.get("category", ""),
                                "answer_type": q.get("answer_type", ""),
                                "correct": correct,
                                "error_type": error_type,
                                "response": response[:300],
                                "ground_truth": q["ground_truth"],
                                "latency_s": round(latency, 2),
                                "prompt_chars": len(prompt),
                                "prompt_tokens": gen.get("prompt_tokens", 0),
                                "response_tokens": gen.get("response_tokens", 0),
                            }
                        except KeyboardInterrupt:
                            print("\n[interrupted]")
                            sys.exit(0)
                        except Exception as exc:
                            result = {
                                "key": key,
                                "model": model, "dataset": ds_name, "table": table,
                                "scale": n, "format": fmt,
                                "question_id": q["id"],
                                "correct": False, "error_type": "exception",
                                "response": "", "ground_truth": q["ground_truth"],
                                "latency_s": 0, "prompt_chars": 0,
                                "prompt_tokens": 0, "response_tokens": 0,
                                "error": str(exc)[:200],
                            }

                        with RESULTS_PATH.open("a", encoding="utf-8") as f:
                            f.write(json.dumps(result, ensure_ascii=False) + "\n")
                        completed.add(key)

                        status = "OK" if result["correct"] else "FAIL"
                        tokens = result.get("prompt_tokens", 0)
                        print(f"{status} {result['latency_s']}s tok={tokens}")

        reader.close()

    # Summary
    if RESULTS_PATH.exists():
        entries = [json.loads(l) for l in RESULTS_PATH.read_text(encoding="utf-8").splitlines() if l.strip()]
        print(f"\n{'='*70}")
        print(f"LLM ACCURACY BENCHMARK ({len(entries)} entries)")
        print(f"{'='*70}")

        for ds_name, _, _ in datasets:
            ds_entries = [e for e in entries if e.get("dataset") == ds_name]
            if not ds_entries:
                continue
            print(f"\n--- {ds_name} ---")
            print(f"{'Model':>20} ", end="")
            fmts = sorted(set(e["format"] for e in ds_entries))
            for fmt in fmts:
                print(f" {fmt:>12}", end="")
            print(f" {'avg':>6}")
            print("-" * (25 + 13 * len(fmts) + 7))

            for model in models:
                print(f"{model:>20} ", end="")
                accs = []
                for fmt in fmts:
                    vals = [e["correct"] for e in ds_entries
                            if e["model"] == model and e["format"] == fmt]
                    acc = sum(vals) / len(vals) if vals else 0
                    accs.append(acc)
                    print(f" {acc:>11.0%}", end="")
                avg = sum(accs) / len(accs) if accs else 0
                print(f" {avg:>5.0%}")


def main():
    parser = argparse.ArgumentParser(description="LLM accuracy benchmark on canonical data")
    parser.add_argument("--models", nargs="+", default=DEFAULT_MODELS)
    parser.add_argument("--dataset", default=None, help="single dataset (default: both)")
    parser.add_argument("--scale", type=int, default=None, help="single scale (default: 100+500)")
    parser.add_argument("--endpoint", default="http://localhost:11434")
    parser.add_argument("--questions", type=int, default=5)
    args = parser.parse_args()

    formats = ["csv", "jsonl", "toon", "tcf_L0", "tcf_L2", "tcf_L0_nostats"]
    scales = [args.scale] if args.scale else [100, 500]

    if args.dataset:
        # Need to pick the right table
        table_map = {"tpch-sf001": "orders", "adult-census": "adult"}
        table = table_map.get(args.dataset, "adult")
        datasets = [(args.dataset, table, scales)]
    else:
        datasets = [
            ("adult-census", "adult", scales),
            ("tpch-sf001", "orders", scales),
        ]

    run_benchmark(args.models, datasets, formats, args.questions, args.endpoint)


if __name__ == "__main__":
    main()

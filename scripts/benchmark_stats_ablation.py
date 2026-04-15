"""Stats ablation on canonical data — measure STATS impact per question type.

Tests the same questions WITH and WITHOUT STATS lines in TCF,
at multiple scales, to separate "model reads STATS" from "model reasons".

Uses enriched question bank with stats_answerable field.

Design:
  Questions: 5 selected (mix of stats-answerable + reasoning + heuristic)
  Stats:     2 variants (with STATS, without STATS)
  Scales:    3 (10, 100, 500 rows)
  Formats:   3 (CSV baseline, TCF L0 +stats, TCF L0 -stats)
  Models:    3 (gemma3:4b, gemma3:12b, gpt-oss:latest)
  Total:     5 × 3 × 3 × 3 = 135 combos

Persists to Z:/tcf-data/benchmarks/stats-ablation-canonical.jsonl

Usage:
    python scripts/benchmark_stats_ablation.py
    python scripts/benchmark_stats_ablation.py --models gemma3:12b
"""

from __future__ import annotations

import argparse
import csv as csv_mod
import io
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _paths import PROJECT_ROOT, data_root  # noqa: E402
from dataset_reader import DatasetReader  # noqa: E402

sys.path.insert(0, str(PROJECT_ROOT / "src"))
from tcf import encode_columns, EncodeConfig  # noqa: E402

sys.path.insert(0, str(PROJECT_ROOT / "experiments" / "eval"))
from llm_eval.ollama_client import OllamaClient  # noqa: E402
from llm_eval.metrics import extract_number, strip_think  # noqa: E402


RESULTS_PATH = data_root() / "benchmarks" / "stats-ablation-canonical.jsonl"
LLM_OPTIONS = {"temperature": 0, "seed": 42}

DEFAULT_MODELS = ["gemma3:4b", "gemma3:12b", "gpt-oss:latest"]
SCALES = [10, 100, 500]
EXCLUDE_COLUMNS = {"c_comment", "l_comment", "s_comment", "ps_comment",
                   "o_comment", "p_comment", "r_comment", "n_comment"}

# Selected questions — mix of stats-answerable, reasoning, heuristic
SELECTED_QUESTIONS = [
    "q1_avg_age",          # stats_answerable=true, descriptive
    "r1_count_age_above_50",  # stats_answerable=false, filter+count
    "r2_avg_age_bachelors",   # stats_answerable=false, filter+avg
    "r5_males_more_hours",    # stats_answerable=false, comparison Yes/No
    "h2_income_imbalanced",   # stats_answerable=false, heuristic Yes/No
]

FORMATS = {
    "csv":           {"type": "csv"},
    "tcf_L0_stats":  {"type": "tcf", "level": 0, "stats": True},
    "tcf_L0_nostats": {"type": "tcf", "level": 0, "stats": False},
}

SYSTEM_PROMPTS = {
    "csv": "You will receive tabular data in CSV format. First line is column names. Answer based only on the data provided.",
    "tcf_L0_stats": "You will receive data in columnar format. Each block starts with column name followed by ':'. Values one per line. Lines starting with '# STATS' contain pre-computed statistics. Answer based only on the data.",
    "tcf_L0_nostats": "You will receive data in columnar format. Each block starts with column name followed by ':'. Values one per line. Answer based only on the data.",
}


def _format_data(rows, cols, table, fmt_key):
    if FORMATS[fmt_key]["type"] == "csv":
        buf = io.StringIO()
        w = csv_mod.DictWriter(buf, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({c: ("" if r.get(c) is None else r[c]) for c in cols})
        return buf.getvalue()
    else:
        columns = {c: [str(r[c]) if r[c] is not None else "" for r in rows] for c in cols}
        cfg = FORMATS[fmt_key]
        return encode_columns(table, columns,
                              config=EncodeConfig(level=cfg["level"], include_stats=cfg["stats"]))


def _score(response, gt, answer_type):
    clean = strip_think(response).strip()

    if answer_type == "string":
        expected = str(gt).lower()
        ok = expected in clean.lower()
        if ok:
            return True, "T1", 0.0
        return False, "T5", 1.0

    val = extract_number(response)
    if val is None:
        return False, "unparseable", None

    try:
        expected = float(gt)
    except (TypeError, ValueError):
        return False, "unparseable", None

    if expected == 0:
        rel = abs(val)
        return abs(val) < 1, ("T1" if abs(val) < 1 else "T5"), rel

    rel = abs(val - expected) / abs(expected)
    if rel <= 0.01:
        tier = "T1"
    elif rel <= 0.05:
        tier = "T2"
    elif rel <= 0.15:
        tier = "T3"
    elif rel <= 0.50:
        tier = "T4"
    else:
        tier = "T5"

    return tier in ("T1", "T2"), tier, round(rel, 4)


def run(models, endpoint):
    client = OllamaClient(endpoint)
    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)

    completed = set()
    if RESULTS_PATH.exists():
        for line in RESULTS_PATH.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:
                    completed.add(json.loads(line)["key"])
                except (json.JSONDecodeError, KeyError):
                    pass

    reader = DatasetReader("adult-census")
    qdata = json.loads(
        (PROJECT_ROOT / "datasets" / "questions" / "adult-census.json")
        .read_text(encoding="utf-8")
    )
    all_questions = {q["id"]: q for q in qdata["questions"]}
    questions = [all_questions[qid] for qid in SELECTED_QUESTIONS if qid in all_questions]

    all_rows = reader.rows("adult")
    cols = [c for c in reader.column_names("adult") if c not in EXCLUDE_COLUMNS]

    total = len(models) * len(SCALES) * len(FORMATS) * len(questions)
    print(f"[ablation] {total} combos, {len(completed)} cached, {total - len(completed)} to run")

    warmed = set()
    i = 0

    for model in models:
        for scale in SCALES:
            rows = all_rows[:scale]
            n = len(rows)

            data_blocks = {}
            for fmt_key in FORMATS:
                data_blocks[fmt_key] = _format_data(rows, cols, "adult", fmt_key)

            for q in questions:
                for fmt_key in FORMATS:
                    i += 1
                    key = f"{model}|{n}|{fmt_key}|{q['id']}"
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

                    prompt = (
                        f"<s>SYSTEM> {SYSTEM_PROMPTS[fmt_key]}</s>\n"
                        f"<s>CONTEXT>\n{data_blocks[fmt_key]}\n</s>\n"
                        f"<s>USER> {q['text_en']} Answer concisely.</s>\n"
                        "<s>ASSISTANT>"
                    )

                    label = f"{model:15s} n={n:>3} {fmt_key:15s} {q['id']:25s}"
                    print(f"  [{i}/{total}] {label}", end=" ", flush=True)

                    try:
                        t0 = time.perf_counter()
                        gen = client.generate(model=model, prompt=prompt, options=LLM_OPTIONS)
                        latency = time.perf_counter() - t0
                        response = gen["text"].strip()
                        correct, tier, rel_error = _score(response, q["ground_truth"], q["answer_type"])

                        result = {
                            "key": key, "model": model, "scale": n,
                            "format": fmt_key, "question_id": q["id"],
                            "stats_answerable": q.get("stats_answerable", False),
                            "analytics_level": q.get("analytics_level", ""),
                            "answer_type": q.get("answer_type", ""),
                            "correct": correct, "tier": tier,
                            "rel_error": rel_error,
                            "response": response[:200],
                            "ground_truth": q["ground_truth"],
                            "latency_s": round(latency, 2),
                            "prompt_chars": len(prompt),
                            "prompt_tokens": gen.get("prompt_tokens", 0),
                        }
                    except KeyboardInterrupt:
                        print("\n[interrupted]")
                        sys.exit(0)
                    except Exception as exc:
                        result = {
                            "key": key, "model": model, "scale": n,
                            "format": fmt_key, "question_id": q["id"],
                            "stats_answerable": q.get("stats_answerable", False),
                            "correct": False, "tier": "error",
                            "rel_error": None, "response": "",
                            "ground_truth": q["ground_truth"],
                            "latency_s": 0, "prompt_chars": 0, "prompt_tokens": 0,
                            "error": str(exc)[:200],
                        }

                    with RESULTS_PATH.open("a", encoding="utf-8") as f:
                        f.write(json.dumps(result, ensure_ascii=False) + "\n")
                    completed.add(key)
                    print(f"{result['tier']} err={result.get('rel_error')} {result['latency_s']}s")

    reader.close()

    # Analysis
    entries = [json.loads(l) for l in RESULTS_PATH.read_text(encoding="utf-8").splitlines() if l.strip()]
    print(f"\n{'='*75}")
    print(f"STATS ABLATION — CANONICAL DATA ({len(entries)} entries)")
    print(f"{'='*75}")

    # Main comparison: stats vs nostats per question type
    print(f"\n{'Question':>25} {'Stats?':>8} {'csv':>8} {'tcf+S':>8} {'tcf-S':>8} {'Gap':>8}")
    print("-" * 65)

    for q in questions:
        sa = "YES" if q.get("stats_answerable") else "no"
        row_parts = [f"{q['id']:>25} {sa:>8}"]
        accs = {}
        for fmt_key in ["csv", "tcf_L0_stats", "tcf_L0_nostats"]:
            vals = [e for e in entries if e["question_id"] == q["id"] and e["format"] == fmt_key]
            responded = [e for e in vals if e["tier"] not in ("error", "unparseable")]
            acc = sum(1 for e in responded if e["tier"] in ("T1", "T2")) / max(1, len(responded))
            accs[fmt_key] = acc
            row_parts.append(f"{acc:>7.0%}")

        gap = accs.get("tcf_L0_stats", 0) - accs.get("tcf_L0_nostats", 0)
        row_parts.append(f"{gap:>+7.0%}")
        print(" ".join(row_parts))

    # Summary by stats_answerable
    print(f"\n--- Stats dependency summary ---")
    for sa_val, sa_label in [(True, "Stats-answerable"), (False, "Reasoning-required")]:
        sa_entries = [e for e in entries if e.get("stats_answerable") == sa_val]
        for fmt_key in ["tcf_L0_stats", "tcf_L0_nostats"]:
            vals = [e for e in sa_entries if e["format"] == fmt_key]
            responded = [e for e in vals if e["tier"] not in ("error", "unparseable")]
            acc = sum(1 for e in responded if e["tier"] in ("T1", "T2")) / max(1, len(responded))
            print(f"  {sa_label:>25} {fmt_key:>15}: Acc@T2 = {acc:.0%} (n={len(responded)})")


def main():
    parser = argparse.ArgumentParser(description="Stats ablation on canonical data")
    parser.add_argument("--models", nargs="+", default=DEFAULT_MODELS)
    parser.add_argument("--endpoint", default="http://localhost:11434")
    args = parser.parse_args()
    run(args.models, args.endpoint)


if __name__ == "__main__":
    main()

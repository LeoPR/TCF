"""Multi-level analysis of LLM accuracy benchmark results.

Reads the JSONL manifest from Z:/tcf-data/benchmarks/llm-accuracy-canonical.jsonl
and produces:
  1. Execution status breakdown (RESPONDED vs TIMEOUT vs ERROR)
  2. Accuracy tiers (T1 exact .. T5 wrong) per model × format
  3. MAE/MAPE per model × format (only over RESPONDED numerics)
  4. Token efficiency (Acc@T2 / avg_tokens)
  5. Truncation analysis (combos where prompt_tokens > context limit)
  6. Summary report in markdown + JSON

Based on framework defined in:
  docs/research-notes/2026-04-14-evaluation-metrics.md

Usage:
    python scripts/analyze_llm_results.py
    python scripts/analyze_llm_results.py --json    # output JSON instead of markdown
    python scripts/analyze_llm_results.py --context-limit 32768
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _paths import data_root  # noqa: E402


RESULTS_PATH = data_root() / "benchmarks" / "llm-accuracy-canonical.jsonl"
ANALYSIS_PATH = data_root() / "benchmarks" / "llm-analysis-multilevel.json"


# ---------------------------------------------------------------------------
# Execution status classification
# ---------------------------------------------------------------------------

def classify_execution(entry: dict) -> str:
    """Classify whether the model actually responded or had a technical failure."""
    if entry.get("error_type") == "exception":
        if entry.get("prompt_tokens", 0) == 0 and entry.get("latency_s", 0) == 0:
            return "TIMEOUT"
        return "ERROR"
    if not entry.get("response", "").strip():
        return "EMPTY"
    # Check if we can extract any number for numeric questions
    atype = entry.get("answer_type", "")
    if atype in ("numeric", "count"):
        resp = re.sub(r"<think>.*?</think>", "", entry.get("response", ""), flags=re.DOTALL)
        nums = re.findall(r"-?\d+(?:\.\d+)?", resp)
        if not nums:
            return "UNPARSEABLE"
    return "RESPONDED"


# ---------------------------------------------------------------------------
# Accuracy tier classification (only for RESPONDED)
# ---------------------------------------------------------------------------

def classify_accuracy_tier(entry: dict) -> str:
    """Classify accuracy tier T1-T5 based on relative error."""
    atype = entry.get("answer_type", "")
    gt = entry.get("ground_truth")
    resp = entry.get("response", "")

    if atype == "string":
        expected = str(gt).lower()
        clean = re.sub(r"<think>.*?</think>", "", resp, flags=re.DOTALL).strip().lower()
        return "T1_exact" if expected in clean else "T5_wrong"

    if atype == "pairs":
        if not isinstance(gt, list):
            return "T5_wrong"
        clean = re.sub(r"<think>.*?</think>", "", resp, flags=re.DOTALL).strip().lower()
        found = sum(1 for pair in gt if str(pair[0]).lower() in clean)
        ratio = found / len(gt) if gt else 0
        if ratio >= 0.8:
            return "T1_exact"
        if ratio >= 0.5:
            return "T3_approximate"
        return "T5_wrong"

    # Numeric or count
    clean = re.sub(r"<think>.*?</think>", "", resp, flags=re.DOTALL).strip()
    nums = re.findall(r"-?\d+(?:\.\d+)?", clean)
    if not nums:
        return "T5_wrong"

    try:
        predicted = float(nums[-1])
        expected = float(gt)
    except (TypeError, ValueError):
        return "T5_wrong"

    if expected == 0:
        return "T1_exact" if abs(predicted) < 1 else "T5_wrong"

    rel_error = abs(predicted - expected) / abs(expected)

    if rel_error <= 0.01:
        return "T1_exact"
    elif rel_error <= 0.05:
        return "T2_precise"
    elif rel_error <= 0.15:
        return "T3_approximate"
    elif rel_error <= 0.50:
        return "T4_directional"
    else:
        return "T5_wrong"


def compute_relative_error(entry: dict) -> float | None:
    """Compute relative error for numeric entries. Returns None if not applicable."""
    atype = entry.get("answer_type", "")
    if atype not in ("numeric", "count"):
        return None

    resp = entry.get("response", "")
    clean = re.sub(r"<think>.*?</think>", "", resp, flags=re.DOTALL).strip()
    nums = re.findall(r"-?\d+(?:\.\d+)?", clean)
    if not nums:
        return None

    try:
        predicted = float(nums[-1])
        expected = float(entry.get("ground_truth", 0))
    except (TypeError, ValueError):
        return None

    if expected == 0:
        return abs(predicted)
    return abs(predicted - expected) / abs(expected)


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------

def analyze(entries: list[dict], context_limit: int = 32768) -> dict:
    """Run full multi-level analysis on benchmark entries."""

    # Enrich entries
    for e in entries:
        e["_exec_status"] = classify_execution(e)
        if e["_exec_status"] == "RESPONDED":
            e["_tier"] = classify_accuracy_tier(e)
            e["_rel_error"] = compute_relative_error(e)
        else:
            e["_tier"] = None
            e["_rel_error"] = None
        e["_truncated"] = (e.get("prompt_tokens", 0) > context_limit)

    models = sorted(set(e["model"] for e in entries))
    formats = sorted(set(e["format"] for e in entries))
    scales = sorted(set(e["scale"] for e in entries))
    datasets = sorted(set(e["dataset"] for e in entries))

    result = {
        "total_entries": len(entries),
        "models": models,
        "formats": formats,
        "scales": scales,
        "datasets": datasets,
        "context_limit": context_limit,
    }

    # --- 1. Execution status ---
    exec_counts = Counter(e["_exec_status"] for e in entries)
    result["execution_status"] = {
        "counts": dict(exec_counts),
        "response_rate": round(exec_counts.get("RESPONDED", 0) / len(entries), 4),
    }

    # By model
    result["execution_by_model"] = {}
    for model in models:
        me = [e for e in entries if e["model"] == model]
        counts = Counter(e["_exec_status"] for e in me)
        result["execution_by_model"][model] = {
            "total": len(me),
            "responded": counts.get("RESPONDED", 0),
            "response_rate": round(counts.get("RESPONDED", 0) / max(1, len(me)), 4),
            "timeout": counts.get("TIMEOUT", 0),
            "error": counts.get("ERROR", 0),
        }

    # --- 2. Accuracy tiers (only RESPONDED) ---
    responded = [e for e in entries if e["_exec_status"] == "RESPONDED"]

    result["accuracy_tiers_overall"] = dict(Counter(e["_tier"] for e in responded))

    # By model × format
    result["accuracy_by_model_format"] = {}
    for model in models:
        result["accuracy_by_model_format"][model] = {}
        for fmt in formats:
            subset = [e for e in responded if e["model"] == model and e["format"] == fmt]
            if not subset:
                continue
            tiers = Counter(e["_tier"] for e in subset)
            n = len(subset)
            result["accuracy_by_model_format"][model][fmt] = {
                "n": n,
                "T1_exact": round(tiers.get("T1_exact", 0) / n, 4),
                "T2_precise": round((tiers.get("T1_exact", 0) + tiers.get("T2_precise", 0)) / n, 4),
                "T3_approximate": round(sum(tiers.get(t, 0) for t in ["T1_exact", "T2_precise", "T3_approximate"]) / n, 4),
            }

    # --- 3. Error metrics (MAE, MAPE) ---
    result["error_metrics_by_model_format"] = {}
    for model in models:
        result["error_metrics_by_model_format"][model] = {}
        for fmt in formats:
            errors = [e["_rel_error"] for e in responded
                      if e["model"] == model and e["format"] == fmt
                      and e["_rel_error"] is not None]
            if not errors:
                continue
            result["error_metrics_by_model_format"][model][fmt] = {
                "n": len(errors),
                "mean_relative_error": round(sum(errors) / len(errors), 4),
                "median_relative_error": round(sorted(errors)[len(errors) // 2], 4),
                "min_error": round(min(errors), 4),
                "max_error": round(max(errors), 4),
            }

    # --- 4. Token usage ---
    result["tokens_by_format_scale"] = {}
    for fmt in formats:
        result["tokens_by_format_scale"][fmt] = {}
        for scale in scales:
            toks = [e["prompt_tokens"] for e in entries
                    if e["format"] == fmt and e["scale"] == scale
                    and e.get("prompt_tokens", 0) > 0]
            if toks:
                result["tokens_by_format_scale"][fmt][str(scale)] = {
                    "avg": round(sum(toks) / len(toks)),
                    "min": min(toks),
                    "max": max(toks),
                    "n": len(toks),
                }

    # --- 5. Truncation analysis ---
    truncated = [e for e in entries if e["_truncated"]]
    result["truncation"] = {
        "total_truncated": len(truncated),
        "by_format": dict(Counter(e["format"] for e in truncated)),
        "by_scale": dict(Counter(str(e["scale"]) for e in truncated)),
    }

    # --- 6. Token efficiency (Acc@T2 per token) ---
    result["token_efficiency"] = {}
    for fmt in formats:
        fmt_responded = [e for e in responded if e["format"] == fmt]
        if not fmt_responded:
            continue
        tiers = Counter(e["_tier"] for e in fmt_responded)
        n = len(fmt_responded)
        acc_t2 = (tiers.get("T1_exact", 0) + tiers.get("T2_precise", 0)) / n

        avg_tokens = sum(e.get("prompt_tokens", 0) for e in fmt_responded
                        if e.get("prompt_tokens", 0) > 0)
        n_with_tokens = sum(1 for e in fmt_responded if e.get("prompt_tokens", 0) > 0)
        avg_tok = avg_tokens / max(1, n_with_tokens)

        result["token_efficiency"][fmt] = {
            "acc_t2": round(acc_t2, 4),
            "avg_tokens": round(avg_tok),
            "efficiency": round(acc_t2 / max(1, avg_tok) * 10000, 4),  # acc per 10K tokens
        }

    return result


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

def print_markdown_report(analysis: dict) -> str:
    lines = []
    lines.append("# LLM Accuracy Analysis — Multi-Level Metrics")
    lines.append(f"\nTotal entries: {analysis['total_entries']}")
    lines.append(f"Models: {', '.join(analysis['models'])}")
    lines.append(f"Formats: {', '.join(analysis['formats'])}")
    lines.append(f"Scales: {analysis['scales']}")
    lines.append(f"Context limit: {analysis['context_limit']:,} tokens")

    # Execution status
    lines.append("\n## 1. Execution Status")
    es = analysis["execution_status"]
    lines.append(f"\nOverall response rate: **{es['response_rate']:.0%}**")
    for status, count in sorted(es["counts"].items()):
        pct = 100 * count / analysis["total_entries"]
        lines.append(f"- {status}: {count} ({pct:.0f}%)")

    lines.append("\n### By model")
    lines.append(f"| {'Model':>20} | {'Responded':>10} | {'Rate':>6} | {'Timeout':>8} | {'Error':>6} |")
    lines.append(f"|{'---':>21}|{'---':>11}|{'---':>7}|{'---':>9}|{'---':>7}|")
    for model, data in analysis["execution_by_model"].items():
        lines.append(f"| {model:>20} | {data['responded']:>10} | {data['response_rate']:>5.0%} | {data['timeout']:>8} | {data['error']:>6} |")

    # Accuracy tiers
    lines.append("\n## 2. Accuracy Tiers (RESPONDED only)")
    lines.append(f"\n| {'Model':>20} | {'Format':>15} | {'Acc@T1':>7} | {'Acc@T2':>7} | {'Acc@T3':>7} | {'N':>4} |")
    lines.append(f"|{'---':>21}|{'---':>16}|{'---':>8}|{'---':>8}|{'---':>8}|{'---':>5}|")
    for model in analysis["models"]:
        fmt_data = analysis["accuracy_by_model_format"].get(model, {})
        for fmt in analysis["formats"]:
            if fmt not in fmt_data:
                continue
            d = fmt_data[fmt]
            lines.append(f"| {model:>20} | {fmt:>15} | {d['T1_exact']:>6.0%} | {d['T2_precise']:>6.0%} | {d['T3_approximate']:>6.0%} | {d['n']:>4} |")

    # Token usage
    lines.append("\n## 3. Token Usage by Format × Scale")
    header = f"\n| {'Format':>15} |"
    for scale in analysis["scales"]:
        header += f" {scale:>8} |"
    lines.append(header)
    lines.append(f"|{'---':>16}|" + "|".join(f"{'---':>9}" for _ in analysis["scales"]) + "|")
    for fmt in analysis["formats"]:
        line = f"| {fmt:>15} |"
        fmt_data = analysis["tokens_by_format_scale"].get(fmt, {})
        for scale in analysis["scales"]:
            sd = fmt_data.get(str(scale), {})
            avg = sd.get("avg", 0)
            marker = " *" if avg > analysis["context_limit"] else "  "
            line += f" {avg:>6,}{marker}|"
        lines.append(line)
    lines.append("(* = exceeds context limit, likely truncated)")

    # Truncation
    trunc = analysis["truncation"]
    lines.append(f"\n## 4. Truncation")
    lines.append(f"\nTotal truncated combos: **{trunc['total_truncated']}**")
    if trunc["by_format"]:
        lines.append("By format: " + ", ".join(f"{k}={v}" for k, v in trunc["by_format"].items()))

    # Token efficiency
    lines.append("\n## 5. Token Efficiency (Acc@T2 per 10K tokens)")
    lines.append(f"\n| {'Format':>15} | {'Acc@T2':>7} | {'Avg tokens':>11} | {'Efficiency':>11} |")
    lines.append(f"|{'---':>16}|{'---':>8}|{'---':>12}|{'---':>12}|")
    for fmt in sorted(analysis["token_efficiency"].keys(),
                      key=lambda f: analysis["token_efficiency"][f]["efficiency"],
                      reverse=True):
        d = analysis["token_efficiency"][fmt]
        lines.append(f"| {fmt:>15} | {d['acc_t2']:>6.0%} | {d['avg_tokens']:>11,} | {d['efficiency']:>11.2f} |")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Multi-level LLM results analysis")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--context-limit", type=int, default=32768)
    args = parser.parse_args()

    if not RESULTS_PATH.exists():
        sys.exit(f"Results file not found: {RESULTS_PATH}")

    entries = [json.loads(l) for l in RESULTS_PATH.read_text(encoding="utf-8").splitlines() if l.strip()]
    print(f"[analyze] loaded {len(entries)} entries from {RESULTS_PATH}", file=sys.stderr)

    analysis = analyze(entries, context_limit=args.context_limit)

    # Always save JSON
    ANALYSIS_PATH.parent.mkdir(parents=True, exist_ok=True)
    ANALYSIS_PATH.write_text(json.dumps(analysis, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"[analyze] saved analysis to {ANALYSIS_PATH}", file=sys.stderr)

    if args.json:
        print(json.dumps(analysis, indent=2, ensure_ascii=False))
    else:
        report = print_markdown_report(analysis)
        print(report)


if __name__ == "__main__":
    main()

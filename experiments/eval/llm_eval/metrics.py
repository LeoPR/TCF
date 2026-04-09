"""Scoring, response parsing, and error classification for TCF eval."""

from __future__ import annotations
import json
import re
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Response parsing
# ---------------------------------------------------------------------------

def strip_think(text: str) -> str:
    """Remove <think>...</think> blocks emitted by reasoning models (deepseek-r1, qwen3)."""
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()


def extract_number(text: str) -> float | None:
    """Extract the last numeric value from a model response.

    Handles:
    - Think-block stripping
    - Comma as decimal separator (pt-BR)
    - Trailing units (e.g. "217.55 reais")
    - Responses like "The answer is 42."
    """
    text = strip_think(text)
    # Normalise comma decimals but be careful: "1,234.56" (thousands) vs "1,23" (decimal)
    # Strategy: replace comma only when it separates exactly 2 decimal digits at end
    text = re.sub(r"(\d),(\d{2})(?!\d)", r"\1.\2", text)
    matches = re.findall(r"-?\d+(?:\.\d+)?", text)
    if not matches:
        return None
    return float(matches[-1])


def extract_all_numbers(text: str) -> list[float]:
    """Return all numbers found in the response (after think-block stripping)."""
    text = strip_think(text)
    text = re.sub(r"(\d),(\d{2})(?!\d)", r"\1.\2", text)
    return [float(m) for m in re.findall(r"-?\d+(?:\.\d+)?", text)]


# ---------------------------------------------------------------------------
# Error classification
# ---------------------------------------------------------------------------

ERROR_TYPES = (
    "correct",
    "list_instead_of_agg",  # listed values instead of aggregating
    "wrong_count",          # plausible integer but wrong
    "hallucinated",         # number outside plausible range
    "arithmetic_error",     # parsed ok, wrong result
    "refusal",              # no number, short text
    "parse_failure",        # no number, long text
)


def classify_error(
    response: str,
    expected: float | int,
    question_key: str,
) -> str:
    """Classify why a response is wrong (or confirm it is correct).

    Args:
        response:     Raw model response string.
        expected:     Ground truth value.
        question_key: One of "count", "sum_vl", "avg_vl", "max_vl", "min_vl", etc.
    """
    nums = extract_all_numbers(response)

    if not nums:
        return "refusal" if len(strip_think(response).strip()) < 40 else "parse_failure"

    # Check correctness first
    val = nums[-1]
    exp_f = float(expected)
    tol = max(abs(exp_f) * 0.01, 0.1)
    if abs(val - exp_f) <= tol:
        return "correct"

    # More than 5 numbers in an aggregation question → listed instead of computing
    agg_questions = {"sum_vl", "avg_vl", "max_vl", "min_vl", "sum_field", "avg_field"}
    if len(nums) > 5 and question_key in agg_questions:
        return "list_instead_of_agg"

    # Count question: plausible integer but wrong
    if question_key in ("count", "count_rows"):
        return "wrong_count"

    # Value outside plausible range (10× the expected)
    if exp_f != 0 and (val < 0 or abs(val) > abs(exp_f) * 10):
        return "hallucinated"

    return "arithmetic_error"


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def score_response(
    response: str,
    expected: float | int | str,
    question_key: str,
) -> tuple[bool, str]:
    """Score a single response against ground truth.

    Returns:
        (correct: bool, error_type: str)
    """
    if isinstance(expected, str):
        # Name-match questions (e.g. top_product)
        clean = strip_think(response).strip().lower()
        ok = expected.lower() in clean
        return ok, ("correct" if ok else "parse_failure")

    val = extract_number(response)
    if val is None:
        return False, "parse_failure" if len(strip_think(response).strip()) >= 40 else "refusal"

    exp_f = float(expected)

    if question_key in ("count", "count_rows", "count_distinct_pessoa"):
        ok = int(round(val)) == int(exp_f)
    else:
        tol = max(abs(exp_f) * 0.01, 0.1)
        ok = abs(val - exp_f) <= tol

    if ok:
        return True, "correct"
    return False, classify_error(response, expected, question_key)


# ---------------------------------------------------------------------------
# Decode accuracy (Layer 1 — list_vl)
# ---------------------------------------------------------------------------

def score_decode(response: str, expected_values: list[float], tol_rel: float = 0.01) -> dict[str, Any]:
    """Score a decode_only response: did the model list all values correctly?

    Returns a dict with:
        correct (bool), found (int), total (int), sum_ok (bool), order_ok (bool)
    """
    nums = extract_all_numbers(response)
    total = len(expected_values)
    found = len(nums)

    # Sum check: if the model listed the right numbers (possibly reordered), sum matches
    exp_sum = sum(expected_values)
    got_sum = sum(nums) if nums else 0.0
    sum_tol = max(abs(exp_sum) * tol_rel, 0.1)
    sum_ok = abs(got_sum - exp_sum) <= sum_tol

    # Order check: values match position by position
    order_ok = (found == total) and all(
        abs(a - b) <= max(abs(b) * tol_rel, 0.01)
        for a, b in zip(nums, expected_values)
    )

    correct = found == total and sum_ok

    return {
        "correct": correct,
        "found": found,
        "total": total,
        "sum_ok": sum_ok,
        "order_ok": order_ok,
    }


# ---------------------------------------------------------------------------
# Batch scoring (legacy, kept for compatibility)
# ---------------------------------------------------------------------------

def score_results(
    results_path: str,
    ground_truth: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Score a JSONL results file against a ground truth dict.

    results_path: JSONL with fields {chunk_id, question, response, rows, latency_s}
    ground_truth: {chunk_id: {question_key: expected_value}}
    """
    total = 0
    correct = 0
    latencies: list[float] = []
    prompt_chars: list[int] = []
    detailed: list[dict[str, Any]] = []

    with open(results_path, encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            chunk_id = row["chunk_id"]
            q        = row["question"]
            resp     = row["response"]
            expected = ground_truth.get(chunk_id, {}).get(q)
            ok = False
            error_type = "no_ground_truth"

            if expected is not None:
                ok, error_type = score_response(resp, expected, q)

            latencies.append(row.get("latency_s", 0.0))
            prompt_chars.append(row.get("prompt_chars", 0))
            detailed.append({
                "chunk_id": chunk_id,
                "question": q,
                "response": resp,
                "expected": expected,
                "ok": ok,
                "error_type": error_type,
            })
            total += 1
            correct += int(ok)

    avg_latency    = sum(latencies) / len(latencies) if latencies else 0.0
    avg_prompt_chars = sum(prompt_chars) / len(prompt_chars) if prompt_chars else 0.0
    accuracy = correct / total if total else 0.0

    return {
        "total":            total,
        "correct":          correct,
        "accuracy":         accuracy,
        "avg_latency_s":    avg_latency,
        "avg_prompt_chars": avg_prompt_chars,
        "composite_score":  accuracy - 0.001 * avg_latency - 0.00005 * avg_prompt_chars,
        "details":          detailed,
    }


def save_report(report: dict[str, Any], out_path: str | Path) -> None:
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

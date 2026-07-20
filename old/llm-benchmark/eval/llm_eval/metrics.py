"""Scoring, response parsing, and error classification for TCF eval."""

from __future__ import annotations
import json
import re
from dataclasses import dataclass, field
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
    tol_rel: float = 0.01,
    tol_abs: float = 0.1,
) -> str:
    """Classify why a response is wrong (or confirm it is correct)."""
    nums = extract_all_numbers(response)

    if not nums:
        return "refusal" if len(strip_think(response).strip()) < 40 else "parse_failure"

    val = nums[-1]
    exp_f = float(expected)
    tol = max(abs(exp_f) * tol_rel, tol_abs)
    if abs(val - exp_f) <= tol:
        return "correct"

    agg_questions = {"sum_vl", "avg_vl", "max_vl", "min_vl", "sum_field", "avg_field"}
    if len(nums) > 5 and question_key in agg_questions:
        return "list_instead_of_agg"

    if question_key in ("count", "count_rows"):
        return "wrong_count"

    if exp_f != 0 and (val < 0 or abs(val) > abs(exp_f) * 10):
        return "hallucinated"

    return "arithmetic_error"


# ---------------------------------------------------------------------------
# Scoring config
# ---------------------------------------------------------------------------

def _normalize_string(s: str) -> str:
    """Normalize for lenient string matching.

    Lowercases, replaces hyphens/underscores/slashes with spaces,
    removes remaining punctuation, collapses whitespace.

    Examples:
        "Some-college"  -> "some college"
        "HS-grad"       -> "hs grad"
        ">50K"          -> "50k"
    """
    s = s.lower()
    s = re.sub(r"[-_/]", " ", s)
    s = re.sub(r"[^\w\s]", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


@dataclass
class ScoringConfig:
    """Parameters that control how model responses are scored.

    Attributes
    ----------
    string_match
        Strategy for matching string-type answers:
        - ``"strict"``: expected.lower() must appear as substring in response
          (legacy behavior, safest for unambiguous categorical values).
        - ``"normalized"``: also try normalized forms (hyphens→spaces, no
          punctuation). Handles "Some College" matching "Some-college".
        - ``"lenient"``: tries strict first, then normalized. Most permissive.
    tol_rel
        Relative tolerance for numeric answers (default 1%).
        ``ok`` if ``|got - expected| <= max(|expected| * tol_rel, tol_abs)``.
    tol_abs
        Absolute tolerance floor for numeric answers (default 0.1).
    count_exact
        If True, integer count answers must match exactly (no tolerance).
        Overrides tol_rel/tol_abs for count-type questions.
    """

    string_match: str = "lenient"
    tol_rel: float = 0.01
    tol_abs: float = 0.1
    count_exact: bool = True

    def as_dict(self) -> dict:
        return {
            "string_match": self.string_match,
            "tol_rel": self.tol_rel,
            "tol_abs": self.tol_abs,
            "count_exact": self.count_exact,
        }


# Backwards-compatible default — matches legacy behaviour
_LEGACY_CONFIG = ScoringConfig(
    string_match="strict",
    tol_rel=0.01,
    tol_abs=0.1,
    count_exact=True,
)

# Default for new experiments (more permissive on strings, same on numbers)
DEFAULT_CONFIG = ScoringConfig()


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def score_response(
    response: str,
    expected: float | int | str,
    question_key: str,
    config: ScoringConfig | None = None,
) -> tuple[bool, str]:
    """Score a single response against ground truth.

    Args:
        response:     Raw model response string.
        expected:     Ground truth value (str, int, or float).
        question_key: GT key used to select scoring mode for integers.
        config:       :class:`ScoringConfig` instance. Defaults to
                      ``DEFAULT_CONFIG`` (lenient string, 1% numeric tol).

    Returns:
        ``(correct: bool, reason: str)`` where reason is one of
        :data:`ERROR_TYPES`.
    """
    if config is None:
        config = DEFAULT_CONFIG

    if isinstance(expected, str):
        clean = strip_think(response).strip()
        clean_lower = clean.lower()
        exp_lower = expected.lower()

        if config.string_match == "strict":
            ok = exp_lower in clean_lower
        elif config.string_match == "normalized":
            norm_exp = _normalize_string(expected)
            norm_clean = _normalize_string(clean)
            ok = norm_exp in norm_clean
        else:  # "lenient" — try strict first, then normalized
            ok = exp_lower in clean_lower
            if not ok:
                norm_exp = _normalize_string(expected)
                norm_clean = _normalize_string(clean)
                ok = norm_exp in norm_clean

        return ok, ("correct" if ok else "parse_failure")

    val = extract_number(response)
    if val is None:
        reason = "parse_failure" if len(strip_think(response).strip()) >= 40 else "refusal"
        return False, reason

    exp_f = float(expected)

    count_keys = ("count", "count_rows", "count_distinct_pessoa",
                  "distinct_workclass", "count_high_class",
                  "max_age", "count_rows")
    if config.count_exact and question_key in count_keys:
        ok = int(round(val)) == int(exp_f)
    else:
        tol = max(abs(exp_f) * config.tol_rel, config.tol_abs)
        ok = abs(val - exp_f) <= tol

    if ok:
        return True, "correct"
    return False, classify_error(response, expected, question_key,
                                 tol_rel=config.tol_rel, tol_abs=config.tol_abs)


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

    exp_sum = sum(expected_values)
    got_sum = sum(nums) if nums else 0.0
    sum_tol = max(abs(exp_sum) * tol_rel, 0.1)
    sum_ok = abs(got_sum - exp_sum) <= sum_tol

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
    config: ScoringConfig | None = None,
) -> dict[str, Any]:
    """Score a JSONL results file against a ground truth dict."""
    if config is None:
        config = DEFAULT_CONFIG

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
                ok, error_type = score_response(resp, expected, q, config=config)

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

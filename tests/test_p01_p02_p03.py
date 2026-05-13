"""Tests for P01 (token count), P02 (response parser), P03 (ground truth)."""

import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "experiments" / "eval"))

import pytest
from llm_eval.metrics import (
    strip_think,
    extract_number,
    extract_all_numbers,
    classify_error,
    score_response,
    score_decode,
)
from llm_eval.ground_truth import compute, vl_plain_list

DATA_DIR = ROOT / "data"


# ---------------------------------------------------------------------------
# P02 — strip_think
# ---------------------------------------------------------------------------

def test_strip_think_removes_block():
    text = "<think>\nSome calculation here\n</think>\n217.55"
    assert strip_think(text) == "217.55"

def test_strip_think_no_block():
    assert strip_think("42.0") == "42.0"

def test_strip_think_multiple_blocks():
    text = "<think>a</think> interim <think>b</think> 5.0"
    assert strip_think(text) == "interim  5.0"


# ---------------------------------------------------------------------------
# P02 — extract_number
# ---------------------------------------------------------------------------

def test_extract_number_plain():
    assert extract_number("217.55") == pytest.approx(217.55)

def test_extract_number_after_think():
    assert extract_number("<think>sum is 217.55</think>\n217.55") == pytest.approx(217.55)

def test_extract_number_embedded():
    assert extract_number("The answer is 42.") == pytest.approx(42.0)

def test_extract_number_comma_decimal():
    assert extract_number("217,55") == pytest.approx(217.55)

def test_extract_number_none():
    assert extract_number("I cannot answer this.") is None

def test_extract_number_takes_last():
    # "Sum of 3 values is 6" → takes 6, not 3
    assert extract_number("Sum of 3 values is 6") == pytest.approx(6.0)


# ---------------------------------------------------------------------------
# P02 — classify_error
# ---------------------------------------------------------------------------

def test_classify_correct():
    assert classify_error("217.55", 217.55, "sum_vl") == "correct"

def test_classify_list_instead_of_agg():
    many = " ".join(["2.5"] * 10)
    assert classify_error(many, 217.55, "sum_vl") == "list_instead_of_agg"

def test_classify_wrong_count():
    assert classify_error("30", 41, "count") == "wrong_count"

def test_classify_hallucinated():
    assert classify_error("999999", 217.55, "sum_vl") == "hallucinated"

def test_classify_arithmetic_error():
    assert classify_error("200.0", 217.55, "sum_vl") == "arithmetic_error"


# ---------------------------------------------------------------------------
# P02 — score_response
# ---------------------------------------------------------------------------

def test_score_response_correct_float():
    ok, err = score_response("217.55", 217.55, "sum_vl")
    assert ok is True
    assert err == "correct"

def test_score_response_within_tolerance():
    ok, _ = score_response("217.6", 217.55, "sum_vl")  # within 1%
    assert ok is True

def test_score_response_wrong():
    ok, err = score_response("100.0", 217.55, "sum_vl")
    assert ok is False
    assert err != "correct"

def test_score_response_count():
    ok, _ = score_response("41", 41, "count")
    assert ok is True

def test_score_response_count_wrong():
    ok, err = score_response("30", 41, "count")
    assert ok is False
    assert err == "wrong_count"

def test_score_response_think_block():
    resp = "<think>I need to sum all values...</think>\n217.55"
    ok, _ = score_response(resp, 217.55, "sum_vl")
    assert ok is True

def test_score_response_string_match():
    ok, _ = score_response("O produto mais vendido é Caneta com 5 vendas.", "Caneta", "top_product")
    assert ok is True

def test_score_response_string_no_match():
    ok, _ = score_response("Lápis", "Caneta", "top_product")
    assert ok is False


# ---------------------------------------------------------------------------
# P02 — score_decode
# ---------------------------------------------------------------------------

def test_score_decode_correct():
    gt = compute(DATA_DIR)
    vl = gt["vl_values"]
    response = " ".join(str(v) for v in vl)
    result = score_decode(response, vl)
    assert result["correct"] is True
    assert result["found"] == 41
    assert result["sum_ok"] is True

def test_score_decode_wrong_count():
    gt = compute(DATA_DIR)
    vl = gt["vl_values"]
    response = "1.0 2.0 3.0"  # only 3 values
    result = score_decode(response, vl)
    assert result["correct"] is False
    assert result["found"] == 3

def test_score_decode_sum_check():
    vl = [1.0, 2.0, 3.0]
    response = "3.0 2.0 1.0"  # reordered — sum still ok
    result = score_decode(response, vl)
    assert result["sum_ok"] is True
    assert result["order_ok"] is False  # different order


# ---------------------------------------------------------------------------
# P03 — ground_truth.compute
# ---------------------------------------------------------------------------

def test_gt_sum_vl():
    gt = compute(DATA_DIR)
    assert gt["sum_vl"] == pytest.approx(217.55, rel=1e-3)

def test_gt_avg_vl():
    gt = compute(DATA_DIR)
    assert gt["avg_vl"] == pytest.approx(217.55 / 41, rel=1e-3)

def test_gt_max_min():
    gt = compute(DATA_DIR)
    assert gt["max_vl"] == pytest.approx(12.4)
    assert gt["min_vl"] == pytest.approx(1.0)

def test_gt_count():
    gt = compute(DATA_DIR)
    assert gt["count"] == 41

def test_gt_count_by_pessoa_ana():
    gt = compute(DATA_DIR)
    assert gt["count_by_pessoa"]["Ana"] == 3

def test_gt_sum_by_pessoa_ana():
    gt = compute(DATA_DIR)
    assert gt["sum_by_pessoa"]["Ana"] == pytest.approx(8.70, rel=1e-3)

def test_gt_top_product():
    gt = compute(DATA_DIR)
    assert gt["top_product_name"] == "Caneta"
    assert gt["top_product_count"] == 5

def test_gt_distinct_pessoa():
    gt = compute(DATA_DIR)
    assert gt["count_distinct_pessoa"] == 27

def test_gt_vl_values_length():
    gt = compute(DATA_DIR)
    assert len(gt["vl_values"]) == 41

def test_vl_plain_list():
    s = vl_plain_list(DATA_DIR)
    parts = s.split()
    assert len(parts) == 41
    assert abs(sum(float(p) for p in parts) - 217.55) < 0.01


# ---------------------------------------------------------------------------
# P01 — GenerateResult structure (without hitting Ollama)
# ---------------------------------------------------------------------------

def test_generate_result_keys():
    from llm_eval.ollama_client import GenerateResult
    r = GenerateResult(text="hello", prompt_tokens=10, response_tokens=5, total_duration_ns=1000)
    assert r["text"] == "hello"
    assert r["prompt_tokens"] == 10
    assert r["response_tokens"] == 5

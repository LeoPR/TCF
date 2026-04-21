"""Model Qualification Suite — TCF-agnostic sanity check for local Ollama models.

Runs literature-inspired canonical questions (arithmetic, factual recall,
instruction following, counting, structured output) on each installed model
across 3 seeds to establish which models respond correctly on this hardware
BEFORE consuming them in TCF experiments.

Outputs:
    results/capability_audit.json  — environment snapshot
    results/qualification.jsonl    — one line per (model, question, seed)
    results/qualified_models.json  — final list, consumed by TCF experiments

Usage:
    python qualify.py                    # full flow
    python qualify.py --audit-only       # just environment snapshot
    python qualify.py --model qwen3:8b   # single model
    python qualify.py --report           # regenerate qualified list from manifest
"""

from __future__ import annotations
import argparse
import json
import re
import sys
import time
import urllib.request
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experiments" / "eval"))

from llm_eval.ollama_client import OllamaClient
from llm_eval.ollama_registry import OllamaRegistry


HERE = Path(__file__).resolve().parent
RESULTS_DIR = HERE / "results"
QA_FILE = HERE / "canonical_qa.json"
THINKING_CATALOG = HERE / "model_thinking_catalog.json"
MANIFEST_PATH = RESULTS_DIR / "qualification.jsonl"
AUDIT_PATH = RESULTS_DIR / "capability_audit.json"
QUALIFIED_PATH = RESULTS_DIR / "qualified_models.json"

OLLAMA_ENDPOINT = "http://localhost:11434"
OPTIONS_BASE = {"temperature": 0, "keep_alive": "10m", "num_thread": 12}


def load_thinking_policy(model: str) -> tuple[bool | None, str]:
    """Return (think_flag, category) for a model, based on catalog.

    If model not in catalog: return (None, 'unknown') — use model's own default.
    """
    if not THINKING_CATALOG.exists():
        return (None, "unknown")
    catalog = json.loads(THINKING_CATALOG.read_text(encoding="utf-8"))
    entry = catalog.get("models", {}).get(model)
    if not entry:
        return (None, "unknown")
    return (entry.get("default_think"), entry.get("category", "unknown"))


# ---------------------------------------------------------------------------
# Capability audit
# ---------------------------------------------------------------------------

def audit() -> dict[str, Any]:
    """Snapshot Ollama + hardware state, independent of models tested."""
    reg = OllamaRegistry(OLLAMA_ENDPOINT)
    installed = reg.get_installed_details()

    # Query /api/ps for currently loaded models
    try:
        ps_raw = urllib.request.urlopen(f"{OLLAMA_ENDPOINT}/api/ps", timeout=5).read()
        ps = json.loads(ps_raw)
    except Exception as e:
        ps = {"error": str(e)}

    # Query /api/version
    try:
        ver_raw = urllib.request.urlopen(f"{OLLAMA_ENDPOINT}/api/version", timeout=5).read()
        version = json.loads(ver_raw)
    except Exception as e:
        version = {"error": str(e)}

    return {
        "timestamp": time.time(),
        "ollama_version": version,
        "installed_models": installed,
        "currently_loaded": ps.get("models", []),
        "endpoint": OLLAMA_ENDPOINT,
    }


# ---------------------------------------------------------------------------
# Scoring canonical answers
# ---------------------------------------------------------------------------

_THINK_TAGS = re.compile(r"<think>.*?</think>", re.DOTALL)


def _strip_think(text: str) -> str:
    return _THINK_TAGS.sub("", text).strip()


def _extract_number(text: str) -> float | None:
    text = _strip_think(text)
    m = re.findall(r"-?\d+(?:\.\d+)?", text)
    return float(m[-1]) if m else None


def _extract_first_number(text: str) -> float | None:
    text = _strip_think(text)
    m = re.findall(r"-?\d+(?:\.\d+)?", text)
    return float(m[0]) if m else None


def score_answer(question: dict, language: str, response: str) -> tuple[bool, str]:
    """Return (correct, reason)."""
    scoring = question["scoring"]
    clean = _strip_think(response).strip().lower()

    if scoring == "substring_ci":
        subs = question.get("expected_substrings", [])
        ok = any(s.lower() in clean for s in subs)
        return ok, "correct" if ok else "missing_substring"

    if scoring == "substring_ci_short":
        subs_key = f"expected_substrings_{language}"
        subs = question.get(subs_key, question.get("expected_substrings", []))
        max_tokens = question.get("max_length_tokens", 10)
        # Approximate: 1 token ≈ 1 short word; count words
        word_count = len(clean.split())
        if word_count > max_tokens * 3:  # very lax: 3x buffer
            return False, "too_long"
        ok = any(s.lower() in clean for s in subs)
        return ok, "correct" if ok else "missing_substring"

    if scoring == "extract_number_exact":
        expected = float(question["expected_number"])
        val = _extract_number(response)
        if val is None:
            return False, "no_number"
        return abs(val - expected) < 0.5, "correct" if abs(val - expected) < 0.5 else f"wrong_number({val})"

    if scoring == "extract_number_with_variants":
        # Primary expected + acceptable_variants both count as correct; mark which was answered
        expected = float(question["expected_number"])
        variants = {float(v) for v in question.get("acceptable_variants", [])}
        val = _extract_number(response)
        if val is None:
            return False, "no_number"
        if abs(val - expected) < 0.5:
            return True, "correct"
        for v in variants:
            if abs(val - v) < 0.5:
                return True, f"correct_variant({int(v)})"
        return False, f"wrong_number({val})"

    if scoring == "comma_separated_count":
        sep = question.get("expected_count_separator", ",")
        expected = question["expected_count"]
        # Count non-empty items
        items = [x.strip() for x in clean.split(sep) if x.strip()]
        return len(items) == expected, "correct" if len(items) == expected else f"wrong_count({len(items)})"

    return False, f"unknown_scoring({scoring})"


# ---------------------------------------------------------------------------
# Manifest helpers
# ---------------------------------------------------------------------------

def load_completed() -> set[str]:
    if not MANIFEST_PATH.exists():
        return set()
    completed: set[str] = set()
    for line in MANIFEST_PATH.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            r = json.loads(line)
            if r.get("reason") == "exception":
                continue
            completed.add(r["key"])
        except Exception:
            pass
    return completed


def append_record(record: dict) -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(MANIFEST_PATH, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")


def read_manifest() -> list[dict]:
    if not MANIFEST_PATH.exists():
        return []
    out = []
    for line in MANIFEST_PATH.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            out.append(json.loads(line))
        except Exception:
            pass
    return out


# ---------------------------------------------------------------------------
# Running the tests
# ---------------------------------------------------------------------------

def run_model_tests(
    client: OllamaClient,
    model: str,
    questions: list[dict],
    seeds: list[int],
    language: str = "pt",
    completed: set[str] | None = None,
) -> list[dict]:
    """Run all canonical questions × seeds on one model. Returns new records."""
    completed = completed or set()
    new_records = []
    prompt_key = f"prompt_{language}"

    # Consult thinking catalog for per-model policy
    think_flag, think_category = load_thinking_policy(model)
    print(f"\n[{model}] testing {len(questions)}q × {len(seeds)} seeds = {len(questions)*len(seeds)} calls"
          f"  [thinking: {think_category} default={think_flag}]")
    warmed = False

    for question in questions:
        for seed in seeds:
            key = f"{model}|{question['id']}|{language}|seed{seed}"
            if key in completed:
                continue

            if not warmed:
                print(f"  warming {model}...")
                try:
                    warm_opts = {**OPTIONS_BASE, "num_predict": 2}
                    if think_flag is not None:
                        warm_opts["think"] = think_flag
                    client.generate(model, "ok", options=warm_opts, timeout=300)
                    warmed = True
                except Exception as e:
                    print(f"  warm failed: {e}")
                    warmed = True  # proceed anyway

            opts = {**OPTIONS_BASE, "seed": seed}
            if think_flag is not None:
                opts["think"] = think_flag
            prompt = question[prompt_key]
            max_latency = question.get("max_latency_s", 120)
            t0 = time.time()
            try:
                result = client.generate(model, prompt, options=opts, timeout=max_latency + 30)
                resp = result["text"]
                latency_s = (time.time() - t0)
                ok, reason = score_answer(question, language, resp)
                print(f"  [{question['id']:<18} seed={seed:<3}] {'OK' if ok else 'NO':<2} ({reason:<20}) {latency_s:>5.1f}s ans={resp[:50]!r}")
            except Exception as e:
                latency_s = (time.time() - t0)
                resp = f"ERROR:{e}"
                ok, reason = False, "exception"
                print(f"  [{question['id']:<18} seed={seed:<3}] ERR ({type(e).__name__}) {latency_s:>5.1f}s")

            record = {
                "key": key,
                "model": model,
                "question_id": question["id"],
                "category": question["category"],
                "language": language,
                "seed": seed,
                "response": resp,
                "response_length": len(resp) if isinstance(resp, str) else 0,
                "ok": ok,
                "reason": reason,
                "latency_s": round(latency_s, 2),
                "think_flag": think_flag,
                "think_category": think_category,
                "timestamp": time.time(),
            }
            append_record(record)
            new_records.append(record)

    return new_records


# ---------------------------------------------------------------------------
# Qualification decision
# ---------------------------------------------------------------------------

def decide_qualified(records: list[dict], qa_data: dict) -> dict[str, dict]:
    """Apply qualification criteria to grouped records."""
    criteria = qa_data["qualification_criteria"]
    questions_by_cat: dict[str, list[str]] = {}
    for q in qa_data["questions"]:
        questions_by_cat.setdefault(q["category"], []).append(q["id"])

    per_model: dict[str, dict] = {}
    for r in records:
        m = r["model"]
        per_model.setdefault(m, {"records": []})
        per_model[m]["records"].append(r)

    qualified: dict[str, dict] = {}
    for model, data in per_model.items():
        recs = data["records"]
        # Per-category pass: must get ≥min_correct_per_category across seeds
        cat_pass: dict[str, bool] = {}
        cat_stats: dict[str, dict] = {}
        for cat, qids in questions_by_cat.items():
            cat_recs = [r for r in recs if r["category"] == cat]
            cat_correct = sum(1 for r in cat_recs if r["ok"])
            cat_total = len(cat_recs)
            cat_stats[cat] = {"correct": cat_correct, "total": cat_total}
            cat_pass[cat] = cat_correct >= criteria["min_correct_per_category"]

        categories_passed = sum(1 for v in cat_pass.values() if v)
        hang_detected = any(r["latency_s"] > criteria["max_hang_time_s"] for r in recs)
        exceptions = sum(1 for r in recs if r["reason"] == "exception")

        is_qualified = (
            categories_passed >= criteria["min_categories_passed"]
            and not hang_detected
            and exceptions == 0
        )

        avg_latency = sum(r["latency_s"] for r in recs) / max(len(recs), 1)
        qualified[model] = {
            "qualified": is_qualified,
            "categories_passed": categories_passed,
            "categories_total": len(questions_by_cat),
            "hang_detected": hang_detected,
            "exception_count": exceptions,
            "avg_latency_s": round(avg_latency, 2),
            "category_stats": cat_stats,
            "total_records": len(recs),
        }

    return qualified


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

def generate_report(qa_data: dict) -> None:
    records = read_manifest()
    if not records:
        print("[report] no records in manifest yet")
        return

    decisions = decide_qualified(records, qa_data)

    print(f"\n{'='*72}")
    print(f"Qualification report ({len(decisions)} models)")
    print(f"{'='*72}")
    print(f"{'Model':<26} {'Qual':<6} {'Cats':<6} {'Hang':<6} {'Exc':<5} {'Lat(s)':<8}")
    print("-"*72)
    for model in sorted(decisions):
        d = decisions[model]
        q = "YES" if d["qualified"] else "no"
        cats = f"{d['categories_passed']}/{d['categories_total']}"
        hang = "HANG" if d["hang_detected"] else "-"
        exc = d["exception_count"]
        lat = d["avg_latency_s"]
        print(f"  {model:<24} {q:<6} {cats:<6} {hang:<6} {exc:<5} {lat:<8.2f}")

    # Save qualified_models.json for TCF consumption
    qualified_only = {m: d for m, d in decisions.items() if d["qualified"]}
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    QUALIFIED_PATH.write_text(
        json.dumps(qualified_only, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    print(f"\nQualified models saved to: {QUALIFIED_PATH.relative_to(ROOT)}")
    print(f"  {len(qualified_only)} qualified / {len(decisions)} tested")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Model Qualification Suite")
    parser.add_argument("--audit-only", action="store_true", help="Only snapshot environment, don't test models")
    parser.add_argument("--report", action="store_true", help="Generate report from existing manifest")
    parser.add_argument("--model", help="Test a specific model only")
    parser.add_argument("--language", choices=["pt", "en"], default="pt", help="Question language (default pt)")
    parser.add_argument("--endpoint", default=OLLAMA_ENDPOINT)
    args = parser.parse_args()

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    # Always run audit first
    print("[audit] snapshotting Ollama environment...")
    audit_data = audit()
    AUDIT_PATH.write_text(json.dumps(audit_data, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(f"[audit] saved: {AUDIT_PATH.relative_to(ROOT)}")
    print(f"[audit] {len(audit_data['installed_models'])} models installed")

    if args.audit_only:
        return

    if args.report:
        qa_data = json.loads(QA_FILE.read_text(encoding="utf-8"))
        generate_report(qa_data)
        return

    qa_data = json.loads(QA_FILE.read_text(encoding="utf-8"))
    questions = qa_data["questions"]
    seeds = qa_data["seeds"]

    # Determine model list
    if args.model:
        models = [args.model]
    else:
        models = [m["name"] for m in audit_data["installed_models"]]

    print(f"\n[qualify] {len(models)} model(s) × {len(questions)} questions × {len(seeds)} seeds = {len(models)*len(questions)*len(seeds)} calls")

    client = OllamaClient(args.endpoint)
    completed = load_completed()

    for model in models:
        try:
            run_model_tests(client, model, questions, seeds, language=args.language, completed=completed)
        except KeyboardInterrupt:
            print(f"\n[interrupted] stopping at model {model}")
            break
        except Exception as e:
            print(f"[{model}] unexpected error: {e}")

    # Final report
    generate_report(qa_data)


if __name__ == "__main__":
    main()

"""Investigate EN→PT bias in top-performing qualified models.

Hypothesis: LLMs are primarily trained in English. Portuguese prompts produce:
  (a) More verbose responses (less training data → model over-explains)
  (b) Higher latency (more complex tokenization)
  (c) Possibly lower accuracy (harder task)

Test: 5 top performers × 7 canonical questions × 2 languages (PT+EN) = 70 calls.
Same seed (42) per question. Only language varies.

Measures:
  - accuracy (binary correct/wrong)
  - response_length (characters — proxy for verbosity)
  - latency_s
  - aggregates per-language

Output: probe_en_pt_bias.json + printed report.
"""
from __future__ import annotations
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent.parent
RESULTS = HERE.parent / "results" / "probe_en_pt_bias.json"
ENDPOINT = "http://localhost:11434"
QA_FILE = HERE.parent / "canonical_qa.json"
CATALOG = HERE.parent / "model_thinking_catalog.json"

MODELS = [
    "phi4:latest",
    "deepseek-r1:14b",
    "gpt-oss:latest",
    "qwen3:14b",
    "gemma3:4b",
]

SEED = 42


def strip_think(t: str) -> str:
    return re.sub(r"<think>.*?</think>", "", t, flags=re.DOTALL).strip()


def extract_number(text: str) -> float | None:
    text = strip_think(text)
    m = re.findall(r"-?\d+(?:\.\d+)?", text)
    return float(m[-1]) if m else None


def score(question: dict, lang: str, response: str) -> tuple[bool, str]:
    scoring = question["scoring"]
    clean = strip_think(response).strip().lower()

    if scoring == "substring_ci":
        subs = question.get("expected_substrings", [])
        return any(s.lower() in clean for s in subs), "factual"

    if scoring == "substring_ci_short":
        key = f"expected_substrings_{lang}"
        subs = question.get(key, question.get("expected_substrings", []))
        word_count = len(clean.split())
        if word_count > question.get("max_length_tokens", 10) * 3:
            return False, "too_long"
        return any(s.lower() in clean for s in subs), "instr"

    if scoring in ("extract_number_exact", "extract_number_with_variants"):
        expected = float(question["expected_number"])
        variants = {float(v) for v in question.get("acceptable_variants", [])}
        val = extract_number(response)
        if val is None: return False, "no_number"
        if abs(val - expected) < 0.5: return True, "num_exact"
        for v in variants:
            if abs(val - v) < 0.5: return True, f"num_variant({int(v)})"
        return False, "num_wrong"

    if scoring == "comma_separated_count":
        items = [x.strip() for x in clean.split(",") if x.strip()]
        return len(items) == question["expected_count"], "list"

    return False, "unknown"


def load_thinking_flag(model: str) -> bool | None:
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    entry = catalog.get("models", {}).get(model, {})
    return entry.get("default_think")


def generate(model: str, prompt: str, think: bool | None) -> dict:
    url = f"{ENDPOINT}/api/generate"
    opts = {"temperature": 0, "seed": SEED, "keep_alive": "10m", "num_thread": 12}
    payload = {"model": model, "prompt": prompt, "stream": False, "options": opts,
               "keep_alive": "10m"}
    if think is not None: payload["think"] = think

    t0 = time.time()
    try:
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"),
                                      headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=120) as r:
            data = json.loads(r.read())
        return {
            "response": data.get("response", ""),
            "latency_s": round(time.time() - t0, 2),
            "error": None,
        }
    except Exception as e:
        return {"response": None, "latency_s": round(time.time() - t0, 2), "error": str(e)}


def main():
    qa = json.loads(QA_FILE.read_text(encoding="utf-8"))
    questions = qa["questions"]

    print(f"\n{'='*78}")
    print(f"EN/PT bias probe  —  {len(MODELS)} models × {len(questions)} Qs × 2 langs = {len(MODELS)*len(questions)*2} calls")
    print(f"{'='*78}")

    all_records = []

    for model in MODELS:
        think_flag = load_thinking_flag(model)
        print(f"\n[{model}] think={think_flag}")
        for q in questions:
            for lang in ["pt", "en"]:
                prompt = q.get(f"prompt_{lang}")
                if not prompt:
                    continue
                r = generate(model, prompt, think=think_flag)
                resp = r["response"] or ""
                ok, reason = (False, "error") if r.get("error") else score(q, lang, resp)
                rec = {
                    "model": model,
                    "question_id": q["id"],
                    "category": q["category"],
                    "language": lang,
                    "ok": ok,
                    "reason": reason,
                    "response": resp,
                    "response_length": len(resp),
                    "latency_s": r["latency_s"],
                    "error": r.get("error"),
                }
                all_records.append(rec)
                print(f"  {q['id']:<18} {lang} {'OK' if ok else 'NO'} ({reason:<14}) "
                      f"len={len(resp):>4} lat={r['latency_s']:>5.1f}s")

    RESULTS.parent.mkdir(parents=True, exist_ok=True)
    RESULTS.write_text(json.dumps({"records": all_records, "timestamp": time.time()},
                                   ensure_ascii=False, indent=2), encoding="utf-8")

    # Report
    print(f"\n{'='*78}")
    print("Per-model PT vs EN aggregates:")
    print(f"{'='*78}")
    print(f"{'model':<24} {'lang':<4} {'acc':<10} {'avg_len':<10} {'avg_lat':<10}")
    by = {}
    for r in all_records:
        k = (r["model"], r["language"])
        by.setdefault(k, []).append(r)
    for (m, l), recs in sorted(by.items()):
        acc = sum(1 for r in recs if r["ok"]) / len(recs) * 100
        avg_len = sum(r["response_length"] for r in recs) / len(recs)
        avg_lat = sum(r["latency_s"] for r in recs) / len(recs)
        print(f"  {m:<22} {l:<4} {acc:>4.0f}%     {avg_len:>6.0f}    {avg_lat:>5.1f}s")

    # Delta analysis
    print(f"\nPT vs EN deltas (negative = PT worse):")
    print(f"{'model':<24} {'Δacc':<8} {'Δlen':<8} {'Δlat':<8}")
    for model in MODELS:
        pt = by.get((model, "pt"), [])
        en = by.get((model, "en"), [])
        if not pt or not en: continue
        pt_acc = sum(1 for r in pt if r["ok"])/len(pt)*100
        en_acc = sum(1 for r in en if r["ok"])/len(en)*100
        pt_len = sum(r["response_length"] for r in pt)/len(pt)
        en_len = sum(r["response_length"] for r in en)/len(en)
        pt_lat = sum(r["latency_s"] for r in pt)/len(pt)
        en_lat = sum(r["latency_s"] for r in en)/len(en)
        d_acc = pt_acc - en_acc
        d_len = pt_len - en_len
        d_lat = pt_lat - en_lat
        print(f"  {model:<22} {d_acc:+5.0f}pp  {d_len:+5.0f}    {d_lat:+5.1f}s")

    print(f"\nSaved: {RESULTS.relative_to(ROOT)}")


if __name__ == "__main__":
    main()

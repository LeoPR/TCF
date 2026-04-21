"""Diagnostic probe for deepseek-r1:7b factual-recall bug.

V1 observation: returned the PROMPT itself as the response for factual_br and factual_fr
(e.g., "Qual a capital do Brasil? Responda apenas com o no..."), while arithmetic,
instruction, and list tests worked correctly.

Hypothesis to test:
  H1: Persistent bug — same prompt always echoes (replication with 5 seeds)
  H2: `think=False` interferes with deepseek-r1's intrinsic reasoning
  H3: Prompt-specific — rephrasing factual_br fixes the echo
  H4: /api/chat endpoint behaves differently from /api/generate
  H5: Language-specific — English factual works even if Portuguese echoes

Output: probe_deepseek_r1_7b.json with full details per experiment.

Usage:
    python probe_deepseek_r1_7b.py
"""
from __future__ import annotations
import json
import sys
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
RESULTS = HERE.parent / "results" / "probe_deepseek_r1_7b.json"
ENDPOINT = "http://localhost:11434"
MODEL = "deepseek-r1:7b"


def generate(prompt: str, options: dict | None = None, think: bool | None = None,
             use_chat: bool = False, timeout: int = 120) -> dict:
    """Call /api/generate or /api/chat with all the knobs we want to test."""
    if use_chat:
        url = f"{ENDPOINT}/api/chat"
        payload = {
            "model": MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "keep_alive": "10m",
        }
    else:
        url = f"{ENDPOINT}/api/generate"
        payload = {
            "model": MODEL,
            "prompt": prompt,
            "stream": False,
            "keep_alive": "10m",
        }

    if options:
        payload["options"] = options
    if think is not None:
        payload["think"] = think

    t0 = time.time()
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"),
                                  headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read())
    elapsed = time.time() - t0

    if use_chat:
        text = data.get("message", {}).get("content", "")
    else:
        text = data.get("response", "")
    thinking_text = data.get("thinking", "")

    return {
        "response": text,
        "thinking": thinking_text,
        "elapsed_s": round(elapsed, 2),
        "done_reason": data.get("done_reason", ""),
        "eval_count": data.get("eval_count", 0),
        "raw": data,
    }


def h1_replication(n_seeds: int = 5) -> list[dict]:
    """H1: Same prompt, 5 different seeds. Is the echo bug persistent?"""
    prompt = "Qual a capital do Brasil? Responda apenas com o nome da cidade."
    results = []
    for seed in [42, 7, 123, 999, 1]:
        r = generate(prompt, options={"temperature": 0, "seed": seed, "think": False})
        r.pop("raw", None)
        r["seed"] = seed
        results.append(r)
        print(f"  seed={seed:<4} elapsed={r['elapsed_s']:>5.1f}s resp={r['response'][:80]!r}")
    return results


def h2_think_variations() -> list[dict]:
    """H2: think=False, None (default), True — which behavior?"""
    prompt = "Qual a capital do Brasil? Responda apenas com o nome da cidade."
    results = []
    for label, think in [("think=False", False), ("think=None", None), ("think=True", True)]:
        r = generate(prompt, options={"temperature": 0, "seed": 42}, think=think)
        r.pop("raw", None)
        r["variant"] = label
        results.append(r)
        think_len = len(r.get("thinking", ""))
        print(f"  {label:<14} elapsed={r['elapsed_s']:>5.1f}s think_chars={think_len:>4} resp={r['response'][:80]!r}")
    return results


def h3_prompt_variations() -> list[dict]:
    """H3: Reword the factual question — does that fix the echo?"""
    prompts = [
        ("orig", "Qual a capital do Brasil? Responda apenas com o nome da cidade."),
        ("direct", "A capital do Brasil \u00e9:"),
        ("noprefix", "Capital do Brasil?"),
        ("en", "What is the capital of Brazil? Answer with just the city name."),
        ("en_direct", "The capital of Brazil is:"),
        ("instruction", "Me diga o nome da capital do Brasil. Responda apenas o nome."),
    ]
    results = []
    for label, p in prompts:
        r = generate(p, options={"temperature": 0, "seed": 42, "think": False})
        r.pop("raw", None)
        r["variant"] = label
        r["prompt"] = p
        results.append(r)
        print(f"  {label:<12} elapsed={r['elapsed_s']:>5.1f}s resp={r['response'][:80]!r}")
    return results


def h4_chat_vs_generate() -> list[dict]:
    """H4: /api/chat vs /api/generate — different behavior?"""
    prompt = "Qual a capital do Brasil? Responda apenas com o nome da cidade."
    results = []
    for label, use_chat in [("generate", False), ("chat", True)]:
        r = generate(prompt, options={"temperature": 0, "seed": 42, "think": False}, use_chat=use_chat)
        r.pop("raw", None)
        r["variant"] = label
        results.append(r)
        print(f"  {label:<10} elapsed={r['elapsed_s']:>5.1f}s resp={r['response'][:80]!r}")
    return results


def h5_language_pt_en() -> list[dict]:
    """H5: Does English work when Portuguese echoes?"""
    pairs = [
        ("pt_br", "Qual a capital do Brasil? Responda apenas com o nome da cidade."),
        ("en_br", "What is the capital of Brazil? Answer with just the city name."),
        ("pt_fr", "Qual a capital da Fran\u00e7a? Responda apenas com o nome da cidade."),
        ("en_fr", "What is the capital of France? Answer with just the city name."),
    ]
    results = []
    for label, p in pairs:
        r = generate(p, options={"temperature": 0, "seed": 42, "think": False})
        r.pop("raw", None)
        r["variant"] = label
        r["prompt"] = p
        results.append(r)
        print(f"  {label:<6} elapsed={r['elapsed_s']:>5.1f}s resp={r['response'][:80]!r}")
    return results


def main():
    print(f"=== Probing {MODEL} factual-recall bug ===\n")

    all_results = {"model": MODEL, "timestamp": time.time()}

    print("H1: Persistent across 5 seeds?")
    all_results["h1_replication"] = h1_replication(n_seeds=5)
    print()

    print("H2: think=False/None/True — which matters?")
    all_results["h2_think"] = h2_think_variations()
    print()

    print("H3: Prompt rephrasing fixes echo?")
    all_results["h3_prompt_variations"] = h3_prompt_variations()
    print()

    print("H4: /api/chat vs /api/generate?")
    all_results["h4_endpoint"] = h4_chat_vs_generate()
    print()

    print("H5: Portuguese vs English?")
    all_results["h5_language"] = h5_language_pt_en()

    RESULTS.parent.mkdir(parents=True, exist_ok=True)
    RESULTS.write_text(json.dumps(all_results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nSaved: {RESULTS}")


if __name__ == "__main__":
    main()

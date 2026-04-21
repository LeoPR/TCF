"""Combined investigations:

  Phase A — deepseek-r1:7b think=False causality (10 calls)
    H2.1: think=False × 5 seeds — bug persistent?
    H2.2: think=True × 5 seeds — control (should all succeed)

  Phase B — qwen3-vl:8b list_colors hang isolation (6 calls)
    B.1: V2 original (control, expect hang)
    B.2: V2 sem parênteses/exemplos (is it the examples?)
    B.3: V2 com triple-quote delimiter (OpenAI convention)
    B.4: V2 curto "Liste 3 cores"
    B.5: V1 original (control, expect success)
    B.6: V2 com EXEMPLOS EM INGLÊS ("like red, blue, green")
"""
from __future__ import annotations
import json
import sys
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
RESULTS = HERE.parent / "results" / "probe_investigations.json"
ENDPOINT = "http://localhost:11434"


def generate(model: str, prompt: str, options: dict | None = None,
             think: bool | None = None, timeout: int = 60) -> dict:
    url = f"{ENDPOINT}/api/generate"
    payload = {"model": model, "prompt": prompt, "stream": False, "keep_alive": "10m"}
    if options:
        payload["options"] = options
    if think is not None:
        payload["think"] = think

    t0 = time.time()
    try:
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"),
                                      headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read())
        elapsed = time.time() - t0
        return {
            "response": data.get("response", ""),
            "thinking_chars": len(data.get("thinking", "")),
            "elapsed_s": round(elapsed, 2),
            "done_reason": data.get("done_reason", ""),
            "eval_count": data.get("eval_count", 0),
            "error": None,
        }
    except Exception as e:
        return {
            "response": None,
            "elapsed_s": round(time.time() - t0, 2),
            "error": f"{type(e).__name__}: {e}",
        }


def phase_a_deepseek_causality() -> dict:
    """deepseek-r1:7b: think=False × 5 seeds vs think=True × 5 seeds."""
    print("\n=== PHASE A: deepseek-r1:7b think=False causality ===")
    prompt = "Qual a capital do Brasil? Responda apenas com o nome da cidade."
    model = "deepseek-r1:7b"
    seeds = [42, 7, 123, 999, 1]

    results = {"model": model, "prompt": prompt, "runs": []}

    print("\nH2.1: think=False × 5 seeds")
    for seed in seeds:
        r = generate(model, prompt, options={"temperature": 0, "seed": seed}, think=False)
        r.update({"think": False, "seed": seed})
        results["runs"].append(r)
        resp_preview = (r["response"] or r.get("error",""))[:80]
        print(f"  seed={seed:<4} elapsed={r['elapsed_s']:>5.1f}s resp={resp_preview!r}")

    print("\nH2.2: think=True × 5 seeds")
    for seed in seeds:
        r = generate(model, prompt, options={"temperature": 0, "seed": seed}, think=True, timeout=60)
        r.update({"think": True, "seed": seed})
        results["runs"].append(r)
        resp_preview = (r["response"] or r.get("error",""))[:80]
        print(f"  seed={seed:<4} elapsed={r['elapsed_s']:>5.1f}s think_chars={r.get('thinking_chars',0)} resp={resp_preview!r}")

    # Aggregate
    false_correct = sum(1 for r in results["runs"] if r["think"] is False
                        and r["response"] and "bras" in r["response"].lower())
    true_correct = sum(1 for r in results["runs"] if r["think"] is True
                       and r["response"] and "bras" in r["response"].lower())
    print(f"\n  Aggregate: think=False correct {false_correct}/5   think=True correct {true_correct}/5")
    results["aggregate"] = {"think_false_correct": false_correct, "think_true_correct": true_correct}
    return results


def phase_b_qwenvl_isolation() -> dict:
    """qwen3-vl:8b: isolate which part of V2 list_colors prompt triggers hang."""
    print("\n\n=== PHASE B: qwen3-vl:8b list_colors hang isolation ===")
    model = "qwen3-vl:8b"

    variants = [
        ("b1_v2_original",
         "Liste 3 nomes de cores (como vermelho, azul, amarelo), separados por vírgula. Responda apenas com os 3 nomes de cores."),
        ("b2_v2_sem_exemplos",
         "Liste 3 nomes de cores, separados por vírgula. Responda apenas com os 3 nomes de cores."),
        ("b3_triple_quote",
         '"""\nListe 3 nomes de cores (como vermelho, azul, amarelo), separados por vírgula.\n"""\nResponda apenas com os 3 nomes de cores.'),
        ("b4_curto",
         "Liste 3 cores separadas por vírgula."),
        ("b5_v1_original",
         "Liste 3 cores separadas por vírgula. Responda apenas com a lista."),
        ("b6_exemplos_en",
         "Liste 3 nomes de cores (like red, blue, green), separados por vírgula. Responda apenas com os 3 nomes de cores."),
    ]

    results = {"model": model, "variants": []}
    for label, prompt in variants:
        r = generate(model, prompt,
                     options={"temperature": 0, "seed": 42},
                     think=False,
                     timeout=45)  # 45s max — shorter than 150s, will timeout faster
        r.update({"variant": label, "prompt": prompt})
        results["variants"].append(r)
        resp_preview = (r["response"] or r.get("error", ""))[:80]
        timeout_flag = " [TIMEOUT]" if r.get("error") and "timed out" in r["error"].lower() else ""
        print(f"  {label:<22} elapsed={r['elapsed_s']:>5.1f}s{timeout_flag} resp={resp_preview!r}")

    return results


def main():
    all_results = {"timestamp": time.time()}

    all_results["phase_a_deepseek"] = phase_a_deepseek_causality()
    all_results["phase_b_qwenvl"] = phase_b_qwenvl_isolation()

    RESULTS.parent.mkdir(parents=True, exist_ok=True)
    RESULTS.write_text(json.dumps(all_results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n\nSaved: {RESULTS}")


if __name__ == "__main__":
    main()

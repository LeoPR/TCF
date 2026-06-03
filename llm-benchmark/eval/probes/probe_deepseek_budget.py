"""Probe deepseek-r1:7b: find config that avoids thinking-truncation.

Context: Phase 1 L3 TCF showed 3/5 combos truncated due to thinking chain
exceeding num_predict=4096 (chains of 4647-14176 chars). This probe tests:

  A (budget):  raise num_predict to 8192, 16384, 32768
  C (prompt):  add "seja conciso no raciocinio" prefix
  AC:          both combined
  effort:      try reasoning_effort=low (may or may not be supported)

Questions: q_count and q_lookup (both truncated in Phase 1).

Records per-combo: thinking_length, done_reason, truncated, latency,
correctness. Saved to probe_deepseek_budget.json.
"""
from __future__ import annotations
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent.parent.parent  # TCF/ (probe now at llm-benchmark/eval/probes/)
RESULTS = ROOT / "experiments" / "results" / "probes" / "probe_deepseek_budget.json"
RESULTS.parent.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "llm-benchmark" / "eval"))

from tcf import encode as tcf_encode, EncodeConfig
from tests.fixtures import _write_fixture
from tests.fixtures.synthetic_v2 import retail_sales
from llm_eval.metrics import extract_number, strip_think

ENDPOINT = "http://localhost:11434"
MODEL = "deepseek-r1:7b"
N_ORDERS = 50
SEED = 42

# Build the same L3 prompts as Phase 1
tables, meta = retail_sales(n_orders=N_ORDERS, seed=SEED)
mp, dd = _write_fixture(tables, meta)
DATA_TEXT = tcf_encode(str(mp), str(dd), EncodeConfig(level=3, include_stats=False))

SYS_L3 = (
    "Voce recebera dados em formato colunar comprimido (L3). "
    "Colunas com '# dict X: val0,val1,val2' tem valores substituidos pelo indice (0,1,2...). "
    "N*val = val repetido N vezes. "
    "Para responder sobre um valor especifico, busque o indice no dict e conte ocorrencias. "
    "Responda com base apenas nos dados."
)

CONCISE_ADDENDUM = " Seja conciso no raciocinio: pense de forma breve e direta, sem elaborar demais."

QUESTIONS = {
    "q_count": {
        "text": "Quantas linhas existem nos dados? Responda apenas com um numero inteiro.",
        "type": "count",
        "expected": len(tables["vendas"]),
    },
    "q_lookup": {
        "text": "Qual cliente realizou a maior venda individual? Responda apenas com o nome do cliente.",
        "type": "string",
        "expected": None,  # computed below
    },
}

# Compute expected for q_lookup
from collections import Counter
clientes = {c["id"]: c["nome"] for c in tables["clientes"]}
vendas = tables["vendas"]
max_v = max(vendas, key=lambda v: float(v["total"]) if v["total"] else 0)
QUESTIONS["q_lookup"]["expected"] = clientes.get(max_v["id_cliente"])

CONFIGS = [
    {"label": "baseline",          "num_predict": 4096,  "concise": False, "effort": None},
    {"label": "A_budget_8k",       "num_predict": 8192,  "concise": False, "effort": None},
    {"label": "A_budget_16k",      "num_predict": 16384, "concise": False, "effort": None},
    {"label": "A_budget_32k",      "num_predict": 32768, "concise": False, "effort": None},
    {"label": "C_concise",         "num_predict": 4096,  "concise": True,  "effort": None},
    {"label": "AC_combo_16k",      "num_predict": 16384, "concise": True,  "effort": None},
    {"label": "effort_low",        "num_predict": 4096,  "concise": False, "effort": "low"},
    {"label": "AC_effort_16k_low", "num_predict": 16384, "concise": True,  "effort": "low"},
]


def call(prompt: str, num_predict: int, effort: str | None, think: bool | None = True) -> dict:
    """Call Ollama /api/generate; return full instrumentation."""
    url = f"{ENDPOINT}/api/generate"
    options = {
        "temperature": 0, "seed": SEED, "num_ctx": 16384,
        "num_predict": num_predict, "keep_alive": "20m", "num_thread": 12,
    }
    if effort:
        options["reasoning_effort"] = effort  # gpt-oss-style; may be ignored
    payload = {"model": MODEL, "prompt": prompt, "stream": False,
               "options": options, "keep_alive": "20m"}
    if think is not None:
        payload["think"] = think

    t0 = time.time()
    try:
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"),
                                      headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=3600) as r:
            data = json.loads(r.read())
        thinking = data.get("thinking", "") or ""
        resp = data.get("response", "") or ""
        return {
            "response": resp,
            "response_length": len(resp),
            "thinking_length": len(thinking),
            "done_reason": data.get("done_reason", ""),
            "truncated": data.get("done_reason") == "length",
            "eval_count": data.get("eval_count", 0),
            "latency_s": round(time.time() - t0, 2),
            "error": None,
        }
    except Exception as e:
        return {"error": str(e), "latency_s": round(time.time() - t0, 2)}


def score(q: dict, resp: str) -> bool:
    if not resp:
        return False
    if q["type"] == "count":
        val = extract_number(resp)
        if val is None: return False
        return int(round(val)) == int(q["expected"])
    else:
        clean = strip_think(resp).strip().lower()
        return str(q["expected"]).lower() in clean


def main():
    results = []
    print(f"=== probe_deepseek_budget: {MODEL} × {len(QUESTIONS)} Qs × {len(CONFIGS)} configs = {len(QUESTIONS)*len(CONFIGS)} calls ===")
    print(f"  L3 prompt n_orders={N_ORDERS} ({len(tables['vendas'])} vendas, {len(DATA_TEXT)} chars)")
    print()

    for cfg in CONFIGS:
        print(f"\n--- {cfg['label']}: num_predict={cfg['num_predict']} concise={cfg['concise']} effort={cfg['effort']} ---")
        for q_name, q in QUESTIONS.items():
            base_sys = SYS_L3 + (CONCISE_ADDENDUM if cfg["concise"] else "")
            prompt = f"{base_sys}\n\n{q['text']}\n\n{DATA_TEXT}"
            r = call(prompt, cfg["num_predict"], cfg["effort"])
            if r.get("error"):
                print(f"  {q_name:<10} ERROR ({r.get('latency_s'):>5.0f}s): {r['error'][:100]}")
                ok = False
            else:
                ok = score(q, r["response"])
                trunc = "TRUNC" if r["truncated"] else "stop"
                print(f"  {q_name:<10} {'OK' if ok else 'NO':<3} "
                      f"think={r['thinking_length']:>5}c resp={r['response_length']:>4}c "
                      f"done={trunc:<5} lat={r['latency_s']:>5.0f}s  "
                      f"ans={(r['response'] or '')[:50]!r}")
            results.append({
                "config": cfg["label"], "num_predict": cfg["num_predict"],
                "concise": cfg["concise"], "effort": cfg["effort"],
                "question": q_name, "ok": ok,
                **{k: v for k, v in r.items() if k != "error"},
                "error": r.get("error"),
            })

    RESULTS.parent.mkdir(parents=True, exist_ok=True)
    RESULTS.write_text(json.dumps({"model": MODEL, "n_orders": N_ORDERS, "results": results,
                                    "timestamp": time.time()},
                                   ensure_ascii=False, indent=2), encoding="utf-8")

    # Summary
    print(f"\n{'='*78}")
    print(f"{'Config':<20} {'q_count':<16} {'q_lookup':<16}")
    print('-'*78)
    from collections import defaultdict
    by = defaultdict(dict)
    for r in results:
        by[r["config"]][r["question"]] = r
    for cfg_label in [c["label"] for c in CONFIGS]:
        row = by.get(cfg_label, {})
        cells = []
        for q in ["q_count", "q_lookup"]:
            rr = row.get(q, {})
            if not rr:
                cells.append("—")
            else:
                status = "OK" if rr.get("ok") else ("TRUNC" if rr.get("truncated") else "NO")
                think = rr.get("thinking_length", 0)
                cells.append(f"{status}({think})")
        print(f"  {cfg_label:<18} {cells[0]:<16} {cells[1]:<16}")

    print(f"\nSaved: {RESULTS.relative_to(ROOT)}")


if __name__ == "__main__":
    main()

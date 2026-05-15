# 05 — Recommended models

Ranked by accuracy × cost based on actual M-Acomm results
(2256 records over Adult + TPC-H × 4 paradigms × 7 commercial models +
13 local models). Full data:
[../findings/04-naturalness-Q29-Q36.md](../findings/04-naturalness-Q29-Q36.md).

## Linha A (LLM reads TCF and computes directly)

### Best cost/perf — gpt-5.4-nano

```python
client.responses.parse(
    model="gpt-5.4-nano",
    instructions=tcf_payload,    # cached
    input=question,
    reasoning={"effort": "low"}, # required for filter+agg
    text={"verbosity": "low"},
    max_output_tokens=2048,
    text_format=AnswerCell,
    prompt_cache_key=f"tcf_{model}_{seed}",
)
```

- 86.9% Adult-A, 76.2% TPC-H-A (best in TPC-H Linha A among commercials!)
- $0.0007/call cached → $0.06 for 84 calls
- Pareto-optimal cost × accuracy point

### Frontier — gpt-5.4

- 95.2% Adult-A — only model >90% in Linha A
- $0.0061/call cached
- Use when accuracy matters more than cost

### Anthropic alternative — claude-haiku-4-5

- 79.8% Adult-A (with `thinking={"type":"enabled","budget_tokens":2048}`
  required — without thinking falls to 58%)
- $0.0036/call cached
- Best Anthropic option for Linha A in single-table

### Avoid for Linha A

- **gpt-4o-mini** — non-reasoning, falls to local-tier accuracy (52%)
- **All local models** — capped at ~57% by arithmetic-over-100-values
  ceiling (F-Q12 / F-Q28). Schema ambiguity in TPC-H drops them
  further.

## Linha B (LLM generates SQL → SQLite executes)

### Universally good — gpt-5.4 or gpt-5.4-mini

- **100%** Adult-B both, 85.7% TPC-H-B
- gpt-5.4-mini at $0.0006/call cached is the cost sweet spot

### Best for multi-table — claude-sonnet-4-6

- **88.1%** TPC-H-B (the only model that beats gpt-5.4 here)
- 96.4% Adult-B
- $0.0024/call cached

### Local recommendation — qwen3:14b

- **100%** Adult-B in all naturalness levels
- 95% N0 / 62% N2 in TPC-H-B (schema ambiguity hits)
- $0 (Ollama local)
- Use when budget = 0 and dataset is small / schema is clean

### Small but capable — qwen2.5-coder:7b

- 86% N0 in Adult-B
- 95% N0 in TPC-H-B (with reasoning — qwen3:14b still preferred)
- $0 — fits in 12 GB VRAM

## What NOT to use

- **gpt-oss:latest (20B)** — local frontier in size but only 28.6%
  Linha A. MXFP4 quantization seems to hurt. Use qwen3:14b instead.
- **qwen3:0.6b** — capacity floor at 7%. Don't use under 1.5B params
  for any tabular task.
- **gpt-4o-mini for Linha A in TPC-H** — 59.5% with `hours-per-week`
  consistently failing (no double-quoting). For Linha A use gpt-5.x;
  for Linha B even gpt-4o-mini works (85.7%).

## Decision tree

```
Need accuracy > 90%?
  Yes → gpt-5.4 (Linha A) or gpt-5.4-mini (Linha B)
  No  → continue

Multi-table with schema ambiguity?
  Yes → Linha B + claude-sonnet-4-6 (best schema-mapping)
  No  → continue

Budget constrained ($0.05/100 calls)?
  Yes → gpt-5.4-nano (commercial) or qwen3:14b (local)
  No  → gpt-5.4-mini

Workload is JOIN-heavy?
  Yes → Linha B mandatory (Linha A dies at 17% q_top_product)
  No  → either
```

## Pricing snapshot (2026-04, USD per 1M tokens)

| Model | Input | Output | Cached input |
|-------|-------|--------|---------------|
| gpt-5.4-nano | $0.20 | $1.25 | $0.02 |
| gpt-5.4-mini | $0.75 | $4.50 | $0.075 |
| gpt-5.4 | $2.50 | $15.00 | $0.25 |
| gpt-4o-mini | $0.15 | $0.60 | $0.075 |
| claude-haiku-4-5 | $1.00 | $5.00 | $0.10 |
| claude-sonnet-4-6 | $3.00 | $15.00 | $0.30 |
| claude-opus-4-7 | $5.00 | $25.00 | $0.50 |

Verify current prices in
[`scripts/../experiments/eval/llm_eval/commercial_client.py`](../../experiments/eval/llm_eval/commercial_client.py).

---
title: TCF + LLMs — Integration Guide for Users
date: 2026-04-21
status: ACTIVE
type: user-guide
audience: users of TCF who will feed data to local or commercial LLMs
---

# Integrating TCF with LLMs — What You Need to Know

TCF is a **data compression format**. Its value depends on the LLM that
reads it. This guide documents pitfalls we hit during TCF research, so
you don't have to rediscover them.

If you're implementing a client that feeds TCF data to models, read this
before writing any code.

## 1. Not all LLMs are equivalent for structured parsing

### What we observed (2026-04-20 through 2026-04-21)

Testing on 14 local models, 12 answer simple canonical questions (capital
cities, basic math) correctly, but **only ~3 parse TCF L3 reliably**:

- ✅ **Always worked** (100% on TCF L3): `phi4:latest` (14.7B),
  `deepseek-r1:14b`, `gpt-oss:latest` (20.9B)
- ⚠️ **Partial** (40-60%): `qwen3:14b`, `gemma3:4b`, `llama3.2:3b`
- ❌ **Degenerate** (0-25%): smaller models and some families

**Capacity threshold for TCF L3 appears to be ~14B parameters with
reasoning-oriented training.** Below that, expect inconsistent results.

### Recommendation

If you will deploy TCF with a specific LLM:
1. **First** run it through a qualification suite
   (see `infra/model-qualification/` in this repo) to confirm it even
   answers simple questions on your hardware.
2. **Then** benchmark TCF-specific prompts — accuracy can drop dramatically
   vs simple questions even on "qualified" models.

## 2. "Thinking" / "reasoning" models have special rules

Many modern models (DeepSeek-R1, Qwen3, GPT-OSS, Phi-4-Reasoning) generate
an internal "thinking" chain before emitting the user-visible response.
This creates several pitfalls.

### Pitfall 2.1: Never force `think=false` on intrinsic-reasoning models

**DeepSeek-R1** REQUIRES thinking — it's part of the model's operational
pipeline, not an optional feature. Setting `think=false`:
- On `deepseek-r1:7b`: 100% of responses become **verbatim echoes of the
  input prompt** (confirmed N=5 seeds)
- On `deepseek-r1:14b`: mostly survives but may produce lower quality

| Model category | Safe value for `think` flag |
|----------------|------------------------------|
| `none` (phi4, gemma3, llama3.2) | Flag ignored — can omit |
| `toggle` (qwen3 family) | Either `true` or `false` OK |
| `intrinsic` (deepseek-r1) | **NEVER** `false`. Use `true` or omit |
| `graded` (gpt-oss) | Use `reasoning_effort: low/medium/high` |

### Pitfall 2.2: Thinking consumes the same budget as the response

When a model has thinking enabled, the generation budget is **shared**:

```
[prompt tokens] + [thinking tokens] + [response tokens] ≤ num_ctx
                         total ≤ num_predict
```

**If thinking is long, the response can be truncated or emit empty.**

Symptoms we observed:
- `response = ""` (empty string) after a 14-minute call
- `response = "The answer is \\boxe"` (cut off mid-word — LaTeX macro truncated)
- Long latency (5-95 minutes) followed by incomplete output

**Cause**: On complex prompts (e.g., L3 TCF), a 7B reasoning model can
generate 5000+ tokens of thinking, hitting `num_predict` before writing
the final answer.

### Fix: configure `num_predict` and `num_ctx` appropriately

```python
options = {
    "temperature": 0,
    "seed": 42,
    "num_ctx": 8192,       # give space for thinking + response
    "num_predict": 4096,   # same — don't let default (usually 128) cap thinking
}
```

### Pitfall 2.3: `num_ctx` can be silently clamped

Even if you request `num_ctx=32768`:
- If your **model's `n_ctx_train` is 8192**, Ollama clamps to 8192 (with warning)
- If **GPU VRAM is low**, new Ollama engine clamps to as low as **4096** silently
- **Your prompt may exceed the effective context** without you knowing

**Detection**: check server logs for `"requested context size too large"` warnings.
Check `/api/ps` to see current `context` field per loaded model.

## 3. Pitfall: first call after model load is slower and can hang

Every time Ollama swaps to a different model, the first call:
- Is 20-60× slower than subsequent calls (we've seen 14 min on a 7B model)
- May hit `done_reason="length"` that subsequent calls don't hit
- Is especially pathological with complex prompts (TCF L3)

### Mitigation

- **Warm-up pattern**: send one dummy call (`prompt="ok"`, `num_predict=2`)
  to force the model load before the real call
- **Avoid switching models mid-benchmark** — iterate all questions on one
  model before moving to the next
- **Increase `keep_alive`** (e.g., `"30m"`) so models stay in memory between
  benchmark rounds

## 4. Pitfall: Portuguese-specific quirks

We tested with Portuguese data and prompts. No accuracy bias vs English
was detected (both 100% on canonical), but:

- **First call in PT is 20-60s slower** than EN (cold-start KV cache for
  less-common tokens) — warm up with a trivial PT prompt before measuring
- **Word "cores"** in Portuguese prompts can be mis-interpreted as CPU
  cores by multilingual models — disambiguate with context or examples
- **Linguistic interpretation of "palavra"** varies: "A raposa marrom
  pula" has 4 lexical words OR 3 content words (excluding article "A").
  Both defensible — design prompts to be unambiguous

## 5. Pitfall: model metadata is deceiving

### Model names
- `llama3.2:latest` IS the instruction-tuned version by default — no
  separate "llama3.2-instruct" needed
- GGUF metadata `name="Qwen2.5 7B Instruct"` appearing in Ollama logs is
  JUST the internal GGUF label, not a separate model

### Vision variants
- `llama3.2-vision:11b` preserves text-only capability well
- `qwen3-vl:8b` **DEGRADES** text-only performance (timeouts on simple prompts).
  Don't assume all vision variants are fine for text tasks.

## 6. Recommended client architecture

If building a TCF client that uses local LLMs, structure it like:

```
┌─────────────────────────────────────────────────┐
│ TCF encode/decode (pure functions, no LLM)     │
└────────────────┬────────────────────────────────┘
                 ▼
┌─────────────────────────────────────────────────┐
│ LLM Backend (abstract — Protocol/interface)    │
│   generate(model, prompt, options) → result    │
└────┬────────────┬─────────────┬────────────────┘
     ▼            ▼             ▼
┌──────────┐ ┌──────────┐ ┌──────────────┐
│ Ollama   │ │ OpenAI   │ │ Anthropic    │
│ HTTP     │ │ API      │ │ API          │
└──────────┘ └──────────┘ └──────────────┘
```

### Essential fields to capture per call

```python
{
  "response": str,            # post-</think> content
  "thinking": str,            # pre-</think> content (None for non-thinking)
  "done_reason": str,         # "stop" | "length" | "unload" | "load"
  "prompt_tokens": int,
  "eval_tokens": int,         # total (think + response)
  "latency_s": float,
  "model_version": str,       # pin to specific tag, not "latest"
}
```

### Essential validations per call

- **If `done_reason == "length"`**: log warning — truncation may have
  occurred. Response is unreliable.
- **If `thinking_length > 5000 chars` AND `response == ""`**: thinking
  consumed full budget. Increase `num_predict`.
- **If `response` ends mid-word** (no punctuation, ends in letter mid-sequence):
  truncation likely. Validate `done_reason`.

### Essential logging

- Always log `model`, `model_version`, options used (esp. `think`, `num_ctx`,
  `num_predict`), and `done_reason`.
- **Don't silently accept empty responses** as "model failure" — investigate
  for truncation first.

## 7. What to do if things don't work

Start with these diagnostics in order:

1. **Does the model answer simple canonical questions?** (capital of Brazil,
   2+2, list 3 colors). If not, it has capability issues before TCF is
   even relevant.

2. **Is `think` flag correct for this model?** Check per-model policy.

3. **Is `num_ctx` sufficient?** Your prompt size + ~4000 tokens for thinking
   buffer.

4. **Is `done_reason == "length"`?** Increase `num_predict`.

5. **Is the first call failing?** Warm up with a dummy call first.

6. **Is the model qualified for YOUR hardware?** Partial VRAM offload can
   make fast models unusably slow.

## 8. References

### Internal
- [Model qualification suite](../../infra/model-qualification/README.md)
- [Ollama server behavior reference](../../infra/docs/ollama-server-behavior.md)
- [Research rigor methodology](../methodology/llm-research-rigor.md)
- [Qualification findings F-Q1 to F-Q7](../research-notes/2026-04-20-qualification-findings.md)

### External
- [Ollama API docs](https://github.com/ollama/ollama/blob/main/docs/api.md)
- [Ollama context length](https://docs.ollama.com/context-length)

## Changelog

- **2026-04-21 v1**: created after Phase 1 re-run revealed systemic
  thinking-truncation behavior. Consolidates pitfalls discovered through
  qualification suite and TCF experiments.

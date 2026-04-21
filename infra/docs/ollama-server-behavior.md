---
title: Ollama Server — Behavior Reference
date: 2026-04-21
status: ACTIVE
type: infrastructure-reference
audience: operators, script authors, client implementers
primary_sources:
  - https://github.com/ollama/ollama/blob/main/docs/api.md (sparse but official)
  - https://github.com/ollama/ollama/issues/10974 (num_ctx silent clamping)
  - https://github.com/ollama/ollama/issues/2714 (num_ctx misconceptions)
  - empirical experiments in this project (2026-04-19 to 2026-04-21)
---

# Ollama Server — Behavior Reference

Reference document consolidating how the Ollama server *actually* behaves,
especially for behaviors that are poorly documented officially. Combines
official docs, GitHub issues, and our empirical observations.

**IMPORTANT**: Official Ollama docs (as of 2026-04-21) are sparse or silent
on many of the behaviors below. Our project had to discover these empirically.
Treat this doc as authoritative for behaviors marked "empirically confirmed".

## 1. Context window (`num_ctx`) — layered control

### The layers (in order of precedence)

```
Request option: num_ctx=X      ← client can request explicitly (per call)
    ↓ clamped by
Env var: OLLAMA_CONTEXT_LENGTH=Y  ← server default ceiling (per docker start)
    ↓ clamped by
Model card: n_ctx_train=Z      ← baked into GGUF; architectural limit
    ↓ clamped by
VRAM availability heuristic    ← new engine reduces if VRAM insufficient
```

### Behaviors observed

1. **Ollama does NOT truncate silently at the end** — when a prompt
   exceeds `num_ctx`, Ollama truncates from **the START** of the prompt.
   This means the initial instructions (often the most important)
   get dropped, not the trailing user question.
   - Source: Ollama docs context-length section.

2. **`OLLAMA_CONTEXT_LENGTH=32768` was set in our docker-compose** but
   during VRAM pressure we observed logs with `default_num_ctx=4096`.
   The "new engine" (OLLAMA_NEW_ENGINE=1) auto-reduces context to fit VRAM.
   - Source: [Issue #10974](https://github.com/ollama/ollama/issues/10974) confirms
     community observation of silent clamping.
   - Our log evidence: 2026-04-19, runner restart showed
     `"vram-based default context" total_vram="12.0 GiB" default_num_ctx=4096`.

3. **Warning `"requested context size too large for model"`** appears when
   `num_ctx > n_ctx_train`. Ollama clamps to `n_ctx_train` silently.
   Example from our logs:
   ```
   level=WARN source=server.go:169 msg="requested context size too large for model"
       num_ctx=32768 n_ctx_train=8192
   ```

4. **Changing `num_ctx` between requests forces model RELOAD** (~13s per
   switch). Keep `num_ctx` constant across a test run to avoid thrashing.
   - Confirmed empirically and documented in `E-speed-tradeoffs.md`.

## 2. Thinking (`think` parameter)

### What the docs say (minimal)

Official docs (api.md):
> `think`: (for thinking models) should the model think before responding?

No further elaboration. **The following is empirically confirmed.**

### Model categories (our taxonomy)

| Category | Example models | Behavior |
|----------|----------------|----------|
| `none` | phi4, gemma3, llama3.2, mistral | `think` param is ignored |
| `toggle` | qwen3 family | `think=true/false` both work |
| `intrinsic` | deepseek-r1 | Requires thinking; `think=false` **BREAKS** the model |
| `graded` | gpt-oss | Uses `reasoning_effort: low/medium/high` instead |

### Empirical confirmation — `think=false` breaks intrinsic models

**Experiment** (2026-04-20, N=5 seeds each):
- `deepseek-r1:7b` with `think=false`: 5/5 responses **echo the prompt literally**
  (e.g., "Qual a capital do Brasil? Responda...")
- `deepseek-r1:7b` with `think=true`: 5/5 respond correctly ("Brasília")

**Causality confirmed**. Mechanism: DeepSeek-R1 was trained with reasoning
as mandatory pipeline step. Forcing `think=false` skips this step and
degrades output to echo.

**Implication**: NEVER use `think=false` globally. Always consult per-model
policy (see `infra/model-qualification/model_thinking_catalog.json`).

### `think` routing in request body (Ollama 0.21+)

`think` is a **top-level** field in the payload, NOT inside `options`:

```json
POST /api/generate
{
  "model": "deepseek-r1:7b",
  "prompt": "...",
  "stream": false,
  "think": true,            ← TOP LEVEL
  "keep_alive": "10m",      ← also top level
  "options": {
    "temperature": 0,       ← inside options
    "num_ctx": 8192
  }
}
```

Misplacing `think` inside `options` results in it being ignored silently.

## 3. The `thinking` response field

### What the docs say

For `/api/generate`: **silent** about a `thinking` response field.

For `/api/chat` (only): *"'thinking': (for thinking models) the model's
thinking process"* — mentioned once, no elaboration.

### What actually happens (empirically confirmed)

When `think=true` (or an intrinsic model), the Ollama response includes
BOTH fields:

```json
{
  "response": "Brasília",              ← post-</think> content
  "thinking": "The user asks...",      ← pre-</think> content (can be long)
  "done": true,
  "done_reason": "stop",               ← or "length", "unload", "load"
  "eval_count": 456,                   ← TOTAL tokens (thinking + response)
  "prompt_eval_count": 123
}
```

### Critical observation — thinking consumes the generation budget

Because thinking is emitted BEFORE the `</think>` token, it counts against:
- **`num_predict`** (max tokens to generate per call)
- **`num_ctx`** (context window — prompt + generated must fit)

**Failure mode**: if thinking is long and budget is tight, **response gets
truncated or emits empty** (`response: ""`).

#### Evidence
- 2026-04-20 Phase 5 (CPU thinking, n=50 L3): qwen3:0.6b with thinking
  returned `ans=''` on multiple questions after 5000+ seconds of generation.
  Thinking filled the output buffer until stop.
- 2026-04-21 Phase 1: deepseek-r1:7b q_count hung 2 hours then timed out,
  q_top_product returned `"The product...**G"` (truncated mid-word = LaTeX
  `\boxed{Grampeador}` cut off). Consistent with `done_reason="length"`.

### Diagnostic protocol

To tell "model failed" apart from "context/budget truncation":

| Observed | Likely cause |
|----------|--------------|
| `response=""` + long `thinking` + `done_reason="length"` | **Truncation** — increase num_predict |
| `response=""` + empty `thinking` + `done_reason="stop"` | Model genuinely refused/failed |
| `response="partial text..."` cut mid-word + `done_reason="length"` | **Truncation** |
| `response="complete answer"` + `done_reason="stop"` | Normal success |

## 4. Token accounting

### `eval_count` includes thinking tokens (empirically confirmed)

The official docs say:
> `eval_count`: number of tokens in the response

But in practice, `eval_count` = thinking tokens + response tokens combined.
This is **not documented explicitly** but follows from the generation
pipeline (both emitted from same model head).

**Implication**: cannot use `eval_count` alone to gauge response length.
Must check `len(response_text)` OR compute `eval_count - thinking_tokens`
(requires counting thinking tokens separately, which Ollama doesn't expose).

### `eval_duration_ns` and timing

Similar — includes time spent generating thinking tokens. A call that
reports `eval_duration=120s` may have spent most of it on thinking and
only seconds on the actual response.

## 5. Multi-model loading / unloading

### Observed behavior

1. `OLLAMA_MAX_LOADED_MODELS=0` (our config) means auto-decide by memory.
2. When memory fits, multiple models remain loaded — saw 2 models (~11GB
   combined) co-resident in RAM+VRAM with partial GPU offload.
3. `keep_alive` (request-level) overrides `OLLAMA_KEEP_ALIVE` (env-level)
   per call.
4. When a model unloads:
   - Triggered by: explicit `keep_alive=0`, TTL expiry, or memory pressure
   - `done_reason="unload"` appears in the final response of an in-flight request

### Reload triggers

Actions that force model reload (slow — 10-60s depending on model size):
- Change `num_ctx` between requests
- Change `num_gpu` between requests
- Quantization change (impossible in practice — same blob)
- Model switch (obviously)

Actions that do NOT force reload:
- Change `temperature`, `seed`, `top_p`, `top_k`
- Change `num_predict` (upper limit, doesn't affect KV cache shape)
- Change `think` flag
- Change `keep_alive`

## 6. Our client resilience checklist

When implementing a client for Ollama (esp. for reasoning models):

- [ ] Capture `response`, `thinking`, `done_reason`, `eval_count`,
      `prompt_eval_count` separately in records
- [ ] Log `done_reason="length"` as warning — indicates truncation
- [ ] Log `done_reason="load"` — model was freshly loaded (first-call warmup)
- [ ] For `intrinsic` models, NEVER send `think=false`
- [ ] For structured/complex prompts with thinking models, override
      `num_ctx=8192` and `num_predict=4096` explicitly to prevent truncation
- [ ] Use consistent `num_ctx` across a test run to avoid reloads
- [ ] Check `len(thinking) > 10000` as a heuristic for "thinking consumed
      most budget" even if `done_reason=stop`

## 6.1 Non-convergent thinking (specific-domain observation)

**Warning**: narrow-scope observation, see
[full caveats](../../docs/research-notes/2026-04-21-thinking-non-convergence.md).

Small reasoning models (observed in `deepseek-r1:7b`, not yet tested
broadly) may enter **non-convergent thinking loops** when facing prompts
outside their training distribution. Symptoms:

- `thinking_length` grows proportionally with `num_predict` budget,
  without reaching `</think>` termination
- `done_reason == "length"` on every retry at escalating budgets
- Model eventually either (a) truncates with empty response, or
  (b) emits wrong answer after exhausting budget
- Task-specific: **same model+data on OTHER questions** converges
  normally. Not a blanket failure.

**Practical mitigation**:
- Don't assume "just give more budget" — monotonic budget scaling
  doesn't necessarily help
- Consider prompt engineering (add "seja conciso") OR `reasoning_effort`
- If persistent for your use case, **use a larger model** in same family
  (14B in our case)
- ALWAYS instrument `thinking_length` and `done_reason` to detect
  this early

**Do NOT conclude** that the affected model is "broken" or "unsuitable"
generically — it likely works fine on most tasks. This is a niche
failure mode triggered by specific prompt structures.

## 7. When official docs conflict with observations

Prefer observations documented here. Submit bugs/questions to Ollama when
our findings diverge significantly — they're accepting community contributions
to docs (PRs welcome per repo).

## References and further reading

### Primary sources
- [ollama/ollama api.md](https://github.com/ollama/ollama/blob/main/docs/api.md) — `/api/generate` and `/api/chat` reference
- [Context length](https://docs.ollama.com/context-length) — prompt truncation semantics
- [Issue #10974: num_ctx instability](https://github.com/ollama/ollama/issues/10974)
- [Issue #2714: num_ctx misunderstandings](https://github.com/ollama/ollama/issues/2714)

### Our empirical reference docs
- `docs/research-notes/2026-04-20-qualification-findings.md` — F-Q1 through F-Q7
- `docs/research-notes/2026-04-20-tcf-retrospective.md` — which TCF phases were
  affected by these behaviors
- `infra/model-qualification/results/probe_*.json` — raw experiment data

## Changelog

- **2026-04-21 v1**: initial documentation after Phase 1 re-run revealed thinking
  budget truncation affecting deepseek-r1:7b responses. Consolidated with
  qualification suite findings.

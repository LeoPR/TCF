# 07 — Troubleshooting

## Linha A returns wrong answer for filter+agg questions

**Symptom**: `q_avg_hours_male`-style questions (filter + aggregation)
return 0% accuracy in local models, ~50% in non-reasoning commercials.

**Cause**: arithmetic over 100+ values exceeds capacity of small models
(F-Q12, F-Q28). Models without chain-of-thought reasoning can't iterate
and filter mentally.

**Fix**: switch to a reasoning model (gpt-5.x family with
`reasoning={"effort":"low"}` minimum, or claude with
`thinking={"type":"enabled"}`) **OR** switch to Linha B (LLM generates SQL).

## Anthropic models with thinking returns empty output

**Symptom**: `reasoning_tokens > 0` but `output_text == ""`. All output
budget consumed by chain-of-thought.

**Cause**: `max_tokens` too low for the thinking budget + answer.

**Fix**: set `max_tokens >= thinking.budget_tokens + 256`. Default
2048 is enough for most cases.

```python
client.messages.create(
    ...,
    max_tokens=4096,  # leaves 2048 for thinking + 2048 for answer
    thinking={"type": "enabled", "budget_tokens": 2048},
)
```

## Opus 4.7 returns "temperature is deprecated"

**Cause**: opus 4.7 dropped temperature/top_p in favor of
`output_config.effort` and `thinking.type=adaptive`.

**Fix**: don't pass `temperature` for opus 4.7. Use:

```python
client.messages.create(
    model="claude-opus-4-7",
    max_tokens=4096,
    thinking={"type": "adaptive"},
    output_config={"effort": "low"},
    messages=[...],
)
```

The `commercial_client.py` shipped here already detects opus 4.7 and
routes correctly.

## SQL fails with "no such column: hours"

**Symptom**: SQLite errors like `OperationalError: no such column: hours`
when querying columns with hyphens (e.g. `hours-per-week`).

**Cause**: SQLite parses `hours-per-week` as `hours - per - week`
(subtraction) without quoting. Model didn't double-quote the column name.

**Fix**: hint the model in the prompt OR use schema with quoted column
names. `qwen2.5-coder:7b` consistently fails this without explicit hint;
`qwen3:14b`, `gpt-5.x`, and `claude-sonnet-4-6` quote correctly by default.

## Schema ambiguity drops accuracy in TPC-H

**Symptom**: questions like "what's the most expensive item?" return 0%
in N2 wording (full schema), ~80% in minimal schema.

**Cause**: TPC-H has multiple `$` columns (`ps_supplycost`,
`p_retailprice`, `l_extendedprice`, `o_totalprice`). Natural-language
wordings activate alternate-but-wrong interpretations. F-Q34 / F-Q38.

**Fix** (in order of preference):
1. **Schema pruning** — only show the relevant subset of tables in
   the payload (use Shaper's `schema=["partsupp", ...]` parameter)
2. **Schema-aware wording** — say `ps_supplycost` explicitly instead
   of "valor" or "preço"
3. **Few-shot examples** anchoring the right column

## Prompt cache misses despite identical prefix

**Symptom**: `cached_tokens=0` on calls 2+ even though `instructions=`
is identical.

**Cause** (OpenAI): missing `prompt_cache_key`, or prefix below 1024
tokens minimum, or > 5 min idle since last call (cache TTL).

**Fix**:
```python
client.responses.parse(
    ...,
    prompt_cache_key="stable_per_session_id",  # required for routing
    instructions=long_prefix,                  # >= 1024 tokens
)
```

**Cause** (Anthropic): missing `cache_control` in system block, or
prefix too short, or 5-min TTL elapsed.

**Fix**:
```python
client.messages.create(
    system=[{
        "type": "text",
        "text": long_prefix,
        "cache_control": {"type": "ephemeral"},
    }],
    ...
)
```

## Round-trip decode produces different rows

**Symptom**: `decode(encode_rows(t, rows, cfg)) != rows`.

**Causes & fixes**:

| Cause | Fix |
|-------|-----|
| `level=3` was used | L3 is schema-only, lossy by design. Use L0..L2. |
| `sort_by` reordered rows | Set `sort_by=None` or accept reordering. |
| Float precision loss | Compare with tolerance (issue 23, open ticket). |
| Custom types (datetime, Decimal) | Convert to JSON-serializable scalars first. |

## Costs exceed estimates

**Symptom**: real spend > `estimate_cost()` projection.

**Causes**:
1. **Reasoning tokens count as output** in commercial billing — for
   reasoning models, multiply estimate by 2-5×.
2. **Cache write happens at full input price**; only reads are cheaper.
3. **Anthropic 5-min TTL** — cache resets if you idle.

**Fix**: use the `--max-cost-usd` cap on every runner. The runner
breaks early on budget exhaustion and emits `BUDGET CAP HIT`.

## Local model very slow

**Symptom**: qwen3:14b takes 20s/call in M-series runners.

**Causes**: cold model load (first call after `keep_alive` expires) or
context size pushing into CPU offload.

**Fix**:
- Set `options.keep_alive="30m"` to avoid reloads
- Drop to qwen2.5-coder:7b if VRAM-bound
- For huge payloads (TCF L2 with 1000+ rows), consider Linha B
  (schema-only, much smaller)

## Need help

- Open an issue with: model id, runner command, full error, and
  manifest record (mask any API keys)
- Workbench tickets: [../workbench/tickets/](../workbench/tickets/)

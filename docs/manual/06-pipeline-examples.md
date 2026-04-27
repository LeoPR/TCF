# 06 — Pipeline examples

End-to-end recipes for common scenarios.

## Recipe 1 — Linha A (read-and-compute) for small data

When: ≤200 rows, simple aggregations, want to skip SQL plumbing.

```python
from tcf import encode_rows, EncodeConfig
from openai import OpenAI
from pydantic import BaseModel

class Cell(BaseModel):
    value: str

client = OpenAI()

# 1. Encode data
rows = load_my_table()
payload = encode_rows("sales", rows, config=EncodeConfig(level=2,
                       include_stats=True, sort_by="region"))

# 2. Build cached prefix + variable question
system = f"""You are a data analyst. Data below is in TCF L2:
- Each column lists values in sequence
- "N*val" = val repeated N times (RLE)
- STATS at top has pre-computed aggregations

{payload}"""

# 3. Call (note prompt_cache_key for cache reuse across questions)
def ask(q: str) -> str:
    r = client.responses.parse(
        model="gpt-5.4-nano",
        instructions=system,
        input=f"## Question\n{q}\n\n## Answer",
        text_format=Cell,
        max_output_tokens=2048,
        reasoning={"effort": "low"},
        text={"verbosity": "low"},
        prompt_cache_key="my_sales_session",
    )
    return r.output_parsed.value

print(ask("What is the average revenue?"))
print(ask("How many orders are from region North?"))  # cache hit
```

## Recipe 2 — Linha B (LLM → SQL → SQLite)

When: any non-trivial workload, multi-table, JOINs, filter+agg.

```python
from tcf import encode_rows, EncodeConfig
from openai import OpenAI
from pydantic import BaseModel
import sqlite3

class SqlAnswer(BaseModel):
    sql: str

# 1. Build SQLite from data
conn = sqlite3.connect(":memory:")
load_tables_into_sqlite(conn, my_tables)  # CREATE + INSERT

# 2. Encode SCHEMA ONLY (level=3 or schema-only payload)
schema_payload = build_schema_only_payload(my_tables)  # see scripts/

system = f"""You generate SQLite queries. Schema:
{schema_payload}

Output a single SQL query, no explanation."""

client = OpenAI()
def ask_sql(q: str):
    r = client.responses.parse(
        model="gpt-5.4-nano",
        instructions=system,
        input=q,
        text_format=SqlAnswer,
        max_output_tokens=2048,
        reasoning={"effort": "low"},
        text={"verbosity": "low"},
    )
    sql = r.output_parsed.sql
    return conn.execute(sql).fetchall()

print(ask_sql("How many sales above $1000 by region?"))
```

## Recipe 3 — Multi-table TCF for one-shot LLM

When: small dataset, want it all in context.

```python
parts = []
cfg = EncodeConfig(level=2, include_stats=True)
for tname, rows in {"customers": cust, "orders": ords, "items": items}.items():
    parts.append(encode_rows(tname, rows, config=cfg))
payload = "\n\n".join(parts)

# Now use in either Linha A or Linha B prompt
```

## Recipe 4 — Cost-optimized batch with caching

When: many questions about the same data; want minimum spend.

Iterate **(model, seed) external, (question) internal** so the prompt
prefix stays identical and OpenAI's prompt cache hits:

```python
for model in models:
    for seed in seeds:
        # data is constant for this (model, seed)
        cache_key = f"job_{model}_{seed}"
        for question in questions:
            r = client.responses.parse(
                model=model,
                instructions=system_payload,  # same → cache hits after 1st
                input=question,
                prompt_cache_key=cache_key,
                ...
            )
```

Anthropic equivalent:

```python
client.messages.create(
    model="claude-haiku-4-5",
    system=[{
        "type": "text",
        "text": payload,
        "cache_control": {"type": "ephemeral"},  # 5-min TTL
    }],
    thinking={"type": "enabled", "budget_tokens": 2048},
    max_tokens=4096,
    messages=[{"role": "user", "content": question}],
)
```

Expected savings: **75-95%** on input tokens after the first call.

## Recipe 5 — Stratified sampling for fair comparison

When: dataset has class imbalance; you don't want sample bias.

```python
from experiments.eval.data_sources import load_dataset

tables, meta = load_dataset(
    "canonical:adult-census",
    volume=100,
    seed=42,
    stratify_by="class",  # ensures sample preserves <=50K / >50K ratio
)
# meta["_stratification_metrics"] has TVD/JSD/Wilson CI for audit
```

## Recipe 6 — Local-only setup (zero spend)

When: privacy or cost constraints absolute.

```python
import requests

OLLAMA = "http://localhost:11434/api/generate"

def ollama_call(model: str, prompt: str) -> str:
    r = requests.post(OLLAMA, json={
        "model": model,
        "prompt": prompt,
        "options": {"temperature": 0, "num_predict": 256, "think": False},
        "stream": False,
    })
    return r.json()["response"]

# Use qwen3:14b for Linha B (100% Adult, ~62% TPC-H N2)
# Or qwen2.5-coder:7b for resource-constrained
```

## Performance reference

For a 100-row Adult Census dataset:

| Pipeline | Cost (84 calls) | Latency | Accuracy |
|----------|-----------------|---------|----------|
| Linha A gpt-5.4-nano | $0.06 | ~3s/call | 86.9% |
| Linha B gpt-5.4-nano | $0.013 | ~2s/call | 90.5% |
| Linha B qwen3:14b local | $0 | ~3s/call | 100% N0 |

Linha B is consistently cheaper and at least as accurate as Linha A
in M-Acomm experiments — recommend it as default.

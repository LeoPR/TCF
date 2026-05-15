# 01 — Quickstart

## Install

```bash
pip install -e .
```

Requires Python 3.10+. No external runtime deps for core encode/decode.

## Encode a single table

```python
from tcf import encode_rows, EncodeConfig

rows = [
    {"id": 1, "name": "Alice", "age": 30},
    {"id": 2, "name": "Bob",   "age": 30},
    {"id": 3, "name": "Carol", "age": 31},
]

text = encode_rows("people", rows, config=EncodeConfig(level=2, include_stats=True))
print(text)
```

Output (compact L2 with STATS):

```
# TCF v0.2 level=2
# N*val = val repeated N times

## people n=3
# STATS id: n=3 sum=6 min=1 max=3 avg=2.00
# STATS age: n=3 sum=91 min=30 max=31 avg=30.33
id:
1
2
3
name:
Alice
Bob
Carol
age:
2*30
31
```

## Encode multiple tables

```python
from tcf import encode_rows, EncodeConfig

cfg = EncodeConfig(level=2, include_stats=True)
parts = []
for tname, rows in {"people": people, "orders": orders}.items():
    parts.append(encode_rows(tname, rows, config=cfg))
payload = "\n\n".join(parts)
```

## Use with an LLM (1-shot pattern)

```python
import openai

client = openai.OpenAI()
prompt = f"""You are a data analyst. The data below is in TCF format:
- Each column lists its values in sequence
- "N*val" means val repeated N times consecutively (RLE)
- STATS at the top of each table contains pre-computed aggregations

{payload}

## Question
How many people are 30 years old?

## Answer
"""

resp = client.responses.parse(
    model="gpt-5.4-nano",
    input=prompt,
    text_format=...  # see chapter 04
)
```

## Decode back to rows

```python
from tcf import decode

restored = decode(text)
# restored[0] == {"id": 1, "name": "Alice", "age": 30}
```

## Next steps

- [02](02-encode-decode.md) — full API reference
- [03](03-compression-levels.md) — choose level L0..L3
- [04](04-llm-integration.md) — build NL2SQL pipelines

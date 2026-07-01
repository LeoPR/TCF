---
title: Getting Started — TCF
type: tutorial
status: active
tags: [tutorial, beginner, compression]
created: 2026-05-27
updated: 2026-05-27
---
<!-- l10n: doc_id=getting-started · lang=en · canonical -->
**English** · [Português](getting-started.pt-BR.md)

# Getting Started — TCF

In this tutorial you will build a complete hands-on experience with TCF: encode a list of strings, see how the format compacts the data, decode it back, and confirm the transformation is lossless. By the end you will understand how TCF works both single-column and multi-column.

## What you will build

You will encode a simple dataset (a list of strings with repetitive patterns), examine the generated TCF text, measure the byte savings, decode it all back exactly as it was, and then expand the example to multi-column tables. Total: 10 minutes.

## Prerequisites

- Python 3.10 or later
- TCF installed with development dependencies:

```bash
git clone https://github.com/LeoPR/TCF.git && cd TCF
pip install -e ".[dev]"
```

You can validate the installation quickly:

```bash
python -c "from tcf import encode, decode; print('TCF OK')"
```

## Step 1 — Encode a simple list

Let's start with three strings that share common prefixes. Open a Python terminal or create a file `hello_tcf.py`:

```python
from tcf import encode

data = ["abc", "abcd", "abcde"]
text = encode(data)

print("Original data:", data)
print("TCF text:")
print(text)
print("Repr:", repr(text))
```

Run it:

```bash
python hello_tcf.py
```

Expected output:

```
Original data: ['abc', 'abcd', 'abcde']
TCF text:
abc
1d
1,2e

Repr: 'abc\n1d\n1,2e\n'
```

What happened:

- **First string (`abc`)**: written as a literal, since it is the first.
- **Second string (`abcd`)**: represented as `1d`. It means "reuse 3 characters of the prefix of string 1 and append `d` at the end".
- **Third string (`abcde`)**: represented as `1,2e`. It means "reuse 4 characters (covering all of `abcd` from string 2) and append `e` at the end".

TCF uses references to earlier strings, saving characters whenever there is similarity.

## Step 2 — Decode and confirm the lossless round-trip

Now let's decode the TCF text back to the original data and confirm no information was lost:

```python
from tcf import encode, decode

data = ["abc", "abcd", "abcde"]
text = encode(data)

decoded = decode(text)

print("Original:", data)
print("Decoded: ", decoded)
print("Equal?   ", decoded == data)
```

Expected output:

```
Original: ['abc', 'abcd', 'abcde']
Decoded:  ['abc', 'abcd', 'abcde']
Equal?    True
```

The **lossless round-trip** property is guaranteed by TCF: any encoded data can be recovered exactly (see [ADR-0024](../adr/0024-pre-1.0-versioning-git-as-compat.md) — pre-1.0 project).

```python
assert decode(encode(x)) == x  # always true
```

## Step 3 — Measure the compression

Let's quantify the gain. We compare the raw size (newline-delimited) with the TCF size:

```python
from tcf import encode

data = ["abc", "abcd", "abcde"]
text = encode(data)

# Compute raw size (newline-delimited)
raw_bytes = sum(len(s) + 1 for s in data)  # each string + 1 newline
tcf_bytes = len(text.encode('utf-8'))

print(f"Raw (newline-delimited): {raw_bytes} bytes")
print(f"TCF encoded:              {tcf_bytes} bytes")
print(f"Compression ratio:        {tcf_bytes/raw_bytes*100:.1f}%")
print(f"Savings:                  {raw_bytes - tcf_bytes} bytes")
```

Expected output:

```
Raw (newline-delimited): 15 bytes
TCF encoded:              12 bytes
Compression ratio:        80.0%
Savings:                  3 bytes
```

Now let's scale the example with more realistic data (a list of emails with repetitive patterns):

```python
from tcf import encode

emails = [
    "joao@gmail.com",
    "joao@hotmail.com",
    "maria@gmail.com",
    "maria@hotmail.com",
    "pedro@gmail.com",
    "pedro@hotmail.com",
]

encoded = encode(emails)

# Raw size
raw_bytes = sum(len(e) + 1 for e in emails)
tcf_bytes = len(encoded.encode('utf-8'))

print(f"Raw (newline-delimited): {raw_bytes} bytes")
print(f"TCF encoded:              {tcf_bytes} bytes")
print(f"Compression ratio:        {tcf_bytes/raw_bytes*100:.1f}%")
print(f"Savings:                  {raw_bytes - tcf_bytes} bytes ({(1 - tcf_bytes/raw_bytes)*100:.1f}%)")
```

Expected output:

```
Raw (newline-delimited): 100 bytes
TCF encoded:              64 bytes
Compression ratio:        64.0%
Savings:                  36 bytes (36.0%)
```

With data that shares common prefixes and suffixes, TCF shrinks the size. The two layers (OBAT + HCC) detect and exploit these patterns automatically.

## Step 4 — Work with multi-column tables

So far we used single-column (a Python list). TCF also supports multi-column natively via dicts. Each column is compacted independently, but TCF preserves the table structure:

```python
from tcf import encode, decode

table = {
    "id":   ["1", "2", "3"],
    "name": ["Alice", "Bob", "Charlie"],
}

encoded = encode(table)
decoded = decode(encoded)

print("Original table:")
print(table)
print()
print("TCF text:")
print(repr(encoded))
print()
print("Decoded:")
print(decoded)
print()
print("Round-trip OK?", decoded == table)
```

Expected output:

```
Original table:
{'id': ['1', '2', '3'], 'name': ['Alice', 'Bob', 'Charlie']}

TCF text:
'#TCF.7 M\n!8=id,!18=name\n*3+1|\\1\nAlice\nBob\nCharlie\n'

Decoded:
{'id': ['1', '2', '3'], 'name': ['Alice', 'Bob', 'Charlie']}

Round-trip OK? True
```

Notice the structure of the multi-column TCF text:

- **Line 1**: `#TCF.7 M` — the format signature indicating TCF format (`#TCF.7`) Multi-column (`M`).
- **Line 2**: `!8=id,!18=name` — metadata: `!` = raw mode (V2-A); 8/18 = body bytes; `id`/`name` = names. The decoder slices the body by those sizes. Details: [TCF-format.md](../algorithms/TCF-format.md).
- **Following lines**: the column bodies concatenated byte-by-byte (each one compacted by the single-column pipeline).

TCF guarantees that the shape of the table (column names, order) is preserved exactly.

## Next steps

You covered the fundamentals:

1. **encode(data)** turns a list or dict into TCF text.
2. **decode(text)** recovers the original data exactly.
3. TCF compacts by exploiting prefixes, suffixes and compositional patterns.
4. The round-trip is guaranteed lossless.

### Explore more

- **[How-to guides](../how-to/)** — practical recipes: [encode a CSV](../how-to/encode-csv-file.md), [use natures (CPF/CNPJ/IP)](../how-to/use-natures.md), [inspect the compression](../how-to/inspect-compression.md).
- **[TCF format](../algorithms/TCF-format.md)** — format specification, pipeline and reference API.
- **[Algorithms](../algorithms/)** — OBAT (Online Bidirectional Affix Tokenizer) and HCC (Hierarchical Compositional Coding).

### Benchmarks and validation

TCF has been validated on multiple datasets:

- **Synthetic D1-D9**: 1523 bytes (53.2% ratio), round-trip 9/9.
- **Real-world Adult+TPC-H**: 57 columns, -33% weighted vs raw, -31% vs naive single-column.
- **Benchmark vs csv/jsonl + gzip/brotli/zstd**: TCF wins 7/9 datasets.

See [`README.md`](../../README.md) and [`docs/algorithms/`](../algorithms/) for details.

---

**Questions?** Open an issue at [LeoPR/TCF](https://github.com/LeoPR/TCF/issues).

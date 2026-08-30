# TCF · Tabular Compact Format

![Version](https://img.shields.io/badge/version-0.8.3%20(pre--1.0)-orange)
![Format](https://img.shields.io/badge/format-%23TCF.8%20default-blue)
![Python](https://img.shields.io/badge/python-3.10+-blue)
![License](https://img.shields.io/badge/license-MIT-green)

**Send the same table in far fewer bytes, without turning it into a binary blob
nobody can open and read.**

TCF compresses tabular and nested data into **inspectable ASCII text**: what repeats
becomes a reference, what is unique stays as-is (no inflation). Zero runtime dependencies.

```bash
pip install tcf-format        # or: uv pip install tcf-format
```

> Distribution: `tcf-format` · importable package: `tcf`

## One minute

```python
from tcf import encode, decode

# Single-column: list of strings
blob = encode(["ana@acme.com.br", "bruno@acme.com.br", "carla@acme.com.br"])
assert decode(blob) == ["ana@acme.com.br", "bruno@acme.com.br", "carla@acme.com.br"]

# Multi-column: dict of columns
table = {
    "name": ["Ana Souza", "Bruno Lima", "Carla Nunes"],
    "city": ["Sao Paulo", "Sao Paulo", "Rio de Janeiro"],
    "plan": ["Premium",   "Premium",   "Basic"],
}
blob = encode(table)
assert decode(blob) == table         # round-trip is always exact

# Nested (the JSON your API sends): routes to #TCF.8H through the same door
orders = [{"customer": "Ana", "items": [{"sku": "A1", "qty": 2}], "active": True}]
assert decode(encode(orders)) == orders
```

One door: `encode()` routes by the **type of the input**, `decode()` by the format
signature. Round-trip is always lossless: it either preserves or fails loud.

## What the wire looks like

Four records, actual `encode` output:

```
#TCF.8M!2c=name,2a=email,1c=city,14=plan,!cpf
Ana Souza
Bruno Lima
Carla Nunes
Diego Rochaan*a*@acme.com.br
brun*o3
carl2,3
dieg5,3
*3|Sao Paulo
Rio de Janeiro
*2|Premium
Basic
^1
111.111.111-11
222.222.222-22
333.333.333-33
444.444.444-44
```

`*3|Sao Paulo` means *"Sao Paulo, 3×"*. `^1` means *"same as line 1"*. In the e-mail
column the unique prefix stays and the shared domain becomes a reference. That is where
the biggest wins are, and where the text gets densest. **Readable does not mean obvious
at first glance.**

## Numbers

Across the 15 synthetic datasets, **with no compressor at all**, TCF is the most compact
text of the set: **3131 B** vs CSV 4872 · JSON 5409 · JSONL 7001 (~36% smaller than CSV).
On real multi-column data (9 Adult + TPC-H tables, 136k rows): **−33% weighted** vs raw CSV.

Against `gzip`/`brotli`/`zstd` the comparison is a different category. They are
**opaque**: answering any question means inflating everything first. TCF composes with
them, and the gain shows up **with volume**: `tcf+brotli` beats `csv+brotli` on Adult 3k
(**21.8 KB** vs 30.4 KB). On tiny payloads the header dominates and the composition
loses, so measure your own case before assuming it.

## Query without decompressing

```python
from tcf import encode, view

sales = {
    "customer": ["Ana", "Bruno", "Carla", "Diego", "Eva", "Ana"],
    "city":     [ "SP",    "SP",    "SP",    "RJ",  "SP",  "RJ"],
    "amount":   [  120,     100,     170,     200,    80,    80],
}
v = view(encode(sales))                    # connects, decompresses nothing

v.count()                                  # 6, read from the structure
v.distinct("city")                         # ['SP', 'RJ']
v.sum("amount")                            # 750.0
v.where("city", "SP").sum("amount")        # 470.0, touching only city + amount
v.group_sum("city", "amount")              # {'SP': 470.0, 'RJ': 280.0}
```

Values come back in the type they went in as, and the filter compares in that type.

Not every question is equally cheap, and the docs say which is which. `count` reads the row
count from the structure and materializes nothing. On a dictionary column, `where`,
`distinct` and `group_count` answer over the K distinct values instead of the N rows, and
walk the index stream **without expanding it**. The aggregators and `select` do materialize
the column they read, so on a single high-cardinality column `view()` and `decode()` cost
nearly the same. The gain is real where the shape allows it, and stated plainly where it
does not.

## Specs: semantic type, string result

Two separate claims: the **wire** is always text, and the **data comes back in the type it
went in as**. Strings return byte for byte; `True` and `3.14` return a **bool** and a
**float**, not the spelling `"True"` (TCF marks the type in the header: `#TCF.8b`, `#TCF.8n`).

```python
from tcf import encode, decode

assert decode(encode([True, False])) == [True, False]    # bool, not "True"
```

On top of that, *knowing the nature* of a text column unlocks compression far beyond what
structure alone gives. That is what **specs** are for:

```python
from tcf import encode, decode

cpfs = ["111.111.111-11", "222.222.222-22", "333.333.333-33", "444.444.444-44"]
blob = encode(cpfs, schema="cpf")     # 69 B -> 39 B
assert decode(blob) == cpfs           # the header says which spec to invert
```

A spec is **not a type**. The difference matters:

| | input type (`bool`, `int`, `float`) | semantic spec (`cpf`, `cnpj`, `ip`) |
|---|---|---|
| who asserts it | **your language**: the value already is a bool | **TCF**, as a hypothesis: *"has the shape of a CPF"* |
| what comes back | the same value, same type (`True`, not `"True"`) | the **original string**, byte for byte |
| when it does not match | not applicable, the type is a fact | falls back to literal, **no failure, no loss** |
| what you gain | the type preserved, plus bits (1-2 per bool) | bytes on the wire |

A spec exploits **redundancy that the shape guarantees**: a CPF has 11 digits, a fixed
mask and two check digits that are *derivable*, so the mask does not travel, the check
digits do not travel, and the body goes in a dense base. The result is still the string
`"111.111.111-11"`.

It is **opt-in per value and never-worse**: the spec competes with the regular pipeline
and only wins if it shrinks; a value that does not match the shape becomes a literal in
the same column. And it is **self-describing**: when it wins, the header carries the id
(`:cpf`) and `decode` inverts it on its own, receiving nothing.

The registry ships `cpf`, `cnpj` (alphanumeric, IN RFB 2.229/2024), `ip`, `data-iso` and
`int-pad`; `schema` is **incremental**. Without it, every column is a semantic string
and the pipeline decides by itself:

```python
from tcf import encode, decode

clients = {
    "cnpj":       ["11.222.333/0001-81", "12.ABC.345/01DE-35"],
    "created_at": ["2026-01-15", "2026-02-20"],
    "notes":      ["-", "-"],
}
blob = encode(clients, schema={"cnpj": "cnpj", "created_at": "data-iso"})  # by name
assert encode(clients, schema={0: "cnpj"}) == encode(clients, schema={"cnpj": "cnpj"})
assert decode(blob) == clients             # `notes` was never mentioned: stays a string
```

## What it is not

Not a database, not object serialization, not a general-purpose binary compressor. It
does not validate semantics (it does not check whether a CPF *exists*). Lossless
round-trip is the contract; compression is the consequence.

## Status: pre-1.0

Format `#TCF.8`. Pre-1.0 minors are **development iterations** towards a solid 1.0:
**there is no rigid compatibility between them**; old versions are recoverable through
git. The definitive freeze is an act of 1.0.

## Documentation

Everything lives in the repository:

- **[Repository and full README](https://github.com/LeoPR/TCF)**: examples with measured
  bytes, comparisons and a line-by-line read of the wire
- **[CHANGELOG](https://github.com/LeoPR/TCF/blob/main/CHANGELOG.md)**
- **[API reference](https://github.com/LeoPR/TCF/blob/main/docs/reference/api.md)** ·
  [encode knobs](https://github.com/LeoPR/TCF/blob/main/docs/reference/encode-knobs.md) ·
  [lazy view()](https://github.com/LeoPR/TCF/blob/main/docs/reference/lazy-view.md)
- **[How to use specs](https://github.com/LeoPR/TCF/blob/main/docs/how-to/use-natures.md)** ·
  [JSON equivalence](https://github.com/LeoPR/TCF/blob/main/docs/reference/json-equivalence.md)
- **[Format specification](https://github.com/LeoPR/TCF/blob/main/docs/algorithms/TCF-format.en.md)** ·
  [architecture decision records (ADR)](https://github.com/LeoPR/TCF/blob/main/docs/adr/README.md)
- **[Portuguese version](https://github.com/LeoPR/TCF/blob/main/README.pt-BR.md)**

## License

MIT: [LICENSE](https://github.com/LeoPR/TCF/blob/main/LICENSE).
To cite: [CITATION.cff](https://github.com/LeoPR/TCF/blob/main/CITATION.cff).

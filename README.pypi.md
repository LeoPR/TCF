# TCF · Tabular Compact Format

![Version](https://img.shields.io/badge/version-0.8.4%20(pre--1.0)-orange)
![Format](https://img.shields.io/badge/format-%23TCF.8%20default-blue)
![Python](https://img.shields.io/badge/python-3.10+-blue)
![License](https://img.shields.io/badge/license-MIT-green)

TCF is a Python library for lossless encoding of tabular and nested data into
**inspectable text**. Repeated values and shared text fragments can be stored as groups
or references. Use `encode()` to produce the representation, `decode()` to recover the
data, and `view()` to query supported inputs without reconstructing the entire table.

Compression depends on the data. Headers and metadata have a cost, so a TCF value is not
guaranteed to be smaller than its JSON or CSV equivalent.

## Installation

Requires **Python 3.10 or newer**, with **no runtime dependencies**.

```bash
python -m pip install tcf-format
```

The distribution name is `tcf-format`; import it as `tcf`. With uv, use
`uv pip install tcf-format`.

## Encode and decode

`encode()` returns a Python string. The input shape determines the representation:
a list of values is a column, a dictionary of columns is a table, and a list of records
is returned as records when decoded.

```python
from tcf import encode, decode

blob = encode(["ana@acme.com.br", "bruno@acme.com.br", "carla@acme.com.br"])
assert decode(blob) == ["ana@acme.com.br", "bruno@acme.com.br", "carla@acme.com.br"]

table = {
    "name": ["Ana Souza", "Bruno Lima", "Carla Nunes"],
    "city": ["Sao Paulo", "Sao Paulo", "Rio de Janeiro"],
    "plan": ["Premium",   "Premium",   "Basic"],
}
blob = encode(table)
assert decode(blob) == table

rows = [{"name": "Ana", "city": "SP"}, {"name": "Bruno", "city": "SP"}]
assert decode(encode(rows)) == rows

orders = [{"customer": "Ana", "items": [{"sku": "A1", "qty": 2}], "active": True}]
assert decode(encode(orders)) == orders
```

These assertions check the round-trip contract for supported inputs. Nested objects,
lists, numbers, booleans and `None` are handled as data, not as JSON source text: whitespace
and formatting from a JSON document are not preserved. TCF is not a serializer for arbitrary
Python objects. See the
[supported mapping and limits](https://github.com/LeoPR/TCF/blob/main/docs/reference/json-equivalence.md).

The output contains markers such as `*3|Sao Paulo`, meaning three consecutive occurrences
of that value. Shared fragments can become references. Inspectable text is not the same
as a plain table: reading the encoded form requires understanding those markers.

## Query selected columns

`view()` provides read-only query methods over a TCF string. It can answer some questions
from metadata or encoded structure; other operations decode the columns they need.

```python
from tcf import encode, view

sales = {
    "customer": ["Ana", "Bruno", "Carla", "Diego", "Eva", "Ana"],
    "city":     [ "SP",    "SP",    "SP",    "RJ",  "SP",  "RJ"],
    "amount":   [  120,     100,     170,     200,    80,    80],
}
blob = encode(sales)
assert decode(blob) == sales
v = view(blob)

assert v.count() == 6
assert set(v.distinct("city")) == {"SP", "RJ"}
assert v.sum("amount") == 750.0
assert v.where("city", "SP").sum("amount") == 470.0
assert v.group_sum("city", "amount") == {"SP": 470.0, "RJ": 280.0}
```

The filtered sum needs `city` and `amount`, not `customer`. This does not mean every query
avoids decoding: the work depends on the column's encoding and the operation. A column
with many distinct values may require full materialization. See the
[query API and cost model](https://github.com/LeoPR/TCF/blob/main/docs/reference/lazy-view.md).

## Optional filters for structured strings

The `schema` argument selects filters for known text patterns. For example, the `cpf`
filter can reconstruct the fixed punctuation and check digits of a Brazilian taxpayer
identifier, storing only the information needed to recover the original string:

```python
from tcf import encode, decode

cpfs = ["111.111.111-11", "222.222.222-22", "333.333.333-33", "444.444.444-44"]
blob = encode(cpfs, schema="cpf")
assert decode(blob) == cpfs
```

The repeated-digit identifiers above are example placeholders. A filter is not identity
validation and does not check whether a CPF exists. Values that do not satisfy the filter's
rules are preserved literally. The filtered representation competes with the ordinary
encoding and is used only when it is smaller, including its metadata.

Built-in filters include `cpf`, `cnpj`, `ip`, `data-iso` and `int-pad`. The header records
the selected built-in filter so `decode()` can reverse it without a `schema` argument.
Filters do not change a string into another Python type.

For tables, specify filters by column name or index. Unspecified columns keep their
input types and use the ordinary encoding:

```python
from tcf import encode, decode

clients = {
    "cnpj":       ["11.222.333/0001-81", "12.ABC.345/01DE-35"],
    "created_at": ["2026-01-15", "2026-02-20"],
    "notes":      ["-", "-"],
}
blob = encode(clients, schema={"cnpj": "cnpj", "created_at": "data-iso"})
assert encode(clients, schema={0: "cnpj"}) == encode(clients, schema={"cnpj": "cnpj"})
assert decode(blob) == clients
```

## Evaluate before adopting

TCF is not a database or a general-purpose binary compressor. It can be combined with
gzip, brotli or zstd, but the combined result is not guaranteed to be smaller than
compressing JSON or CSV directly. External compression must be reversed before querying
the TCF representation; decompression itself may be streamed.

Encoding searches for patterns and may cost substantially more than decoding. Measure
size, encoding time, query time and memory with your own workload, especially if each
request produces new data. For comparisons and their experimental scope, see the
[repository results](https://github.com/LeoPR/TCF#results).

## Compatibility

Version **0.8.4** uses format `#TCF.8`. The project is **pre-1.0**: compatibility between
minor versions is not guaranteed. Pin the package version when persisting encoded data,
and retain access to the matching reader when upgrading. Published packages and git tags
provide access to older readers; the current decoder is not a universal legacy reader.

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

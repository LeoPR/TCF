**English** · [Português](artigo.pt-BR.md)

# TCF: reducing repetitive data without hiding its structure

> **Publishing note, not part of the article.** This text is for LinkedIn Articles;
> the short introduction is in [post.en.md](post.en.md).
> Technical source: [release document](../2026-09-04-release.en.md).
> Use `0-capa` from [figuras/en/](figuras/en/) as the cover and the other images where
> indicated below. The Python examples run in the documentation test suite.

---

Imagine a customer list: names, email addresses, cities and subscription plans. Many customers
live in the same city, subscribe to the same plan or use email addresses with the same domain.
Those repetitions are easy to spot in a table. The way the data is represented, however,
does not always take advantage of what the records have in common.

When that list needs to leave an application, whether as a file or a message to another
system, it needs a representation. Two common choices are JSON and CSV. In JSON arranged
as a list of objects, each record includes field names such as `city` and `plan`. In CSV
with a header, those names appear once, but the values are still written on every row:
a hundred customers in the same city means a hundred occurrences of its name.

That repetition raises a question: **can we use less space while keeping some of the data's
structure visible in the result?**

TCF, short for *Tabular Compact Format*, explores that possibility. It replaces repetitions
with references and groups while retaining a text representation that can be opened in an
editor. Reading it requires learning a few markers, so it is not as immediately clear as
the original table. Even so, values and patterns remain recognizable without reconstructing
every record.

There is one condition: no information can be lost. For supported inputs, encoding and then
decoding must return the same data. That requirement lets us assess size reductions without
confusing compression with discarding content.

## The same data, in two common formats

For a concrete example, consider four people with a name, email address, city, plan and CPF,
a Brazilian individual taxpayer identifier. Three live in São Paulo, and all their email
addresses end in `@acme.com.br`. The example keeps its Portuguese field names: `nome` means
name, `cidade` means city, and `plano` means plan.

In JSON, every record repeats the name of every field:

```json
[
  {
    "nome": "Ana Souza",
    "email": "ana@acme.com.br",
    "cidade": "Sao Paulo",
    "plano": "Premium",
    "cpf": "111.111.111-11"
  },
  {
    "nome": "Bruno Lima",
    "email": "bruno@acme.com.br",
    ...
```

In CSV, the names appear once, in the header, and each line carries only the values:

```csv
nome,email,cidade,plano,cpf
Ana Souza,ana@acme.com.br,Sao Paulo,Premium,111.111.111-11
Bruno Lima,bruno@acme.com.br,Sao Paulo,Premium,222.222.222-22
Carla Nunes,carla@acme.com.br,Sao Paulo,Basic,333.333.333-33
Diego Rocha,diego@acme.com.br,Rio de Janeiro,Premium,444.444.444-44
```

The whole list takes **451 bytes in compact JSON and 277 in CSV**. The JSON above is indented
for reading; the measurement is of the compact form, without superfluous whitespace.

CSV has already solved the repetition of field names. But it still writes `Sao Paulo` three
times, `@acme.com.br` four times and `Premium` three times.

## The same table, after TCF

![Annotated TCF representation and comparison with the optional CPF filter](figuras/en/2-wire.svg)

It is **242 bytes**, and the point is not only the number: it is still text you open and read.
There is no binary dump, and no tool is needed to inspect it. The markers that appear there
are the subject of the next section.

![Proportional bars comparing JSON, JSONL, CSV and TCF in real bytes](figuras/en/1-formatos.svg)

These are measurements of this example, not a guaranteed ratio for every table. The figure
also includes JSONL, which stores one JSON object per line.

## What replaces the repetition

In the city column, three consecutive occurrences of `Sao Paulo` become a single line:

```text
*3|Sao Paulo
```

The marker means "repeat this value three times." The information is still there; only
the way it is written has changed. The same happens in the plan column with `Premium`, and
the fourth occurrence is written as `^1`, meaning "same as the first row of this column".

The emails offer another pattern: the `@acme.com.br` fragment is written once and referenced
by the other values.

TCF combines two stages to find these opportunities. The first, called OBAT, looks for
shared beginnings and endings, such as the email domain. The second, HCC, collects recurring
fragments into reusable references and groups repetitions. Regular numeric sequences can
also be described by a starting value, a step and a count instead of listing every item.

Not every column offers savings. The encoder therefore compares the available representations
and chooses the smallest for each column, including the option to store values without this
compression. **This does not guarantee a file smaller than any JSON or CSV**: headers and
other metadata also take space.

There are optional filters for known structures, including Brazilian CPF and CNPJ taxpayer
identifiers and IPv4 addresses. For a CPF, fixed punctuation and check digits can be
reconstructed when the value satisfies the filter's rules. Values that do not fit are
preserved literally. This does not establish whether a CPF exists or belongs to anyone;
it only takes advantage of the text's structure. That is the second half of the figure above:
with this filter, the total drops from 242 to 210 bytes while preserving the round-trip.

## And in Python, how it is used

The table goes in as a dictionary of columns. `encode` produces the TCF text, and `decode`
reconstructs the data:

```python
from tcf import decode, encode

table = {
    "nome":   ["Ana Souza", "Bruno Lima", "Carla Nunes", "Diego Rocha"],
    "email":  ["ana@acme.com.br", "bruno@acme.com.br",
               "carla@acme.com.br", "diego@acme.com.br"],
    "cidade": ["Sao Paulo", "Sao Paulo", "Sao Paulo", "Rio de Janeiro"],
    "plano":  ["Premium", "Premium", "Basic", "Premium"],
    "cpf":    ["111.111.111-11", "222.222.222-22",
               "333.333.333-33", "444.444.444-44"],
}

wire = encode(table)

assert decode(wire) == table
```

The last line checks that the reconstructed output equals the input. This is a *round-trip*
check: the data makes the journey in both directions without changing.

## Why visible structure matters

So far, the benefit has been using less space. But a marker such as `*3|Sao Paulo` also
states how many records that group represents. Reading that count does not require
reconstructing three copies of the text. Certain sequences offer similar opportunities
for numeric operations.

The `view()` function uses this property to query a TCF representation without reconstructing
the entire output table. Depending on the query, the answer comes from metadata or markers;
when those are insufficient, the necessary data is decoded.

Consider a table of customers and subscription amounts. We can count records, add amounts
or filter by city. Here, `cliente` means customer and `valor` means amount:

```python
from tcf import encode, view

table = {
    "cliente": ["Ana", "Bruno", "Carla", "Diego", "Eva", "Ana"],
    "cidade": ["SP", "SP", "SP", "RJ", "SP", "RJ"],
    "plano": ["Premium", "Premium", "Basic",
              "Premium", "Basic", "Premium"],
    "valor": [120, 100, 170, 200, 80, 80],
}

blob = encode(table)
v = view(blob)

assert v.count() == 6
assert v.sum("valor") == 750.0
assert v.group_count("plano") == {"Premium": 4, "Basic": 2}
assert v.where("cidade", "SP").sum("valor") == 470.0
```

The last query needs only `cidade` and `valor`: one identifies the selected records, and
the other supplies the amounts to add. There is no need to decode `cliente` or `plano`
to answer that question.

![The columns a query materializes, and the ones never touched](figuras/en/3-view.svg)

## What about traditional compressors?

Reducing repetition is also the job of tools such as gzip, brotli and zstd. The distinction
is that they compress the bytes of a representation, while JSON, CSV and TCF define how
data is represented. The choices can therefore be combined: TCF content can be compressed
with gzip, just as JSON content can.

After that additional compression, the content must be decompressed before it can be
interpreted. This can happen as a stream without keeping everything decompressed in memory.
What gzip alone does not provide is a way to identify columns or count records based on
the table's structure.

TCF's value lies in what is available **without that additional layer**, or after it is
removed: a compact representation with values, references and groups that the application
can inspect and query.

This difference in purpose does not remove the need to measure size. For the four-person
example, with external compressors at their maximum levels, the results are:

![Channel compression table: JSON, JSONL, CSV and TCF](figuras/en/4-tabela.svg)

Under gzip, JSON, JSONL and TCF are nearly tied. With brotli or zstd, TCF is smaller than
JSON and JSONL, but compressed CSV is the smallest of the four in this example. These
results do not support claiming that TCF replaces traditional compressors or always uses
less space.

## What the measurements tell us

Four records help explain the mechanism, but not how it behaves on other data.
[EXP-019](../../../experiments/lab/clean/EXP-019-consistencia-0-8-4/) evaluated eight samples
of 800 rows, including real and generated data. It compared two representations within TCF:
one hierarchical, the other designed for tabular records. The total fell from 390,863 to
290,949 bytes, a **25.6% reduction**, with verified round-trips. This percentage does not
measure an advantage over CSV, JSON or gzip.

Even within that comparison, reductions ranged from 4.1% to 46.6% per sample. The variation
reinforces that savings depend on the patterns in the input. The experiment checks
consistency on these samples, not performance at scale, and its gains should not be treated
as a forecast for every application.

Size is also only part of the decision. Searching for patterns concentrates work in encoding;
reading tends to cost less than producing the representation. Data prepared once and reused
across many reads is therefore a use case worth investigating. If every request requires
encoding different data, that cost needs to be included in the evaluation.

The project is at version 0.8.4, still before 1.0, without a strict compatibility guarantee
between minor versions. The measurements presented here do not establish a comparison with
Parquet or other storage formats either. Adoption requires measuring size, write and read
times, and memory use with the application's own data and queries.

## Trying it out

TCF starts from a simple observation: repetitions can carry useful information even when
written compactly. Its purpose is not just to shrink a file, but to preserve structure
that lets us understand and query parts of the data without reconstructing the whole set.

The library is open source under the MIT license, requires Python 3.10 or newer, and has
no runtime dependencies. To try the example in this article:

```sh
pip install tcf-format
```

The repository contains the code, documentation and measurements for evaluating the format
in your own context:

https://github.com/LeoPR/TCF

#Python #Compression #DataEngineering #OpenSource #DataFormats

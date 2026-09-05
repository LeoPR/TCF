**English** · [Português](artigo.pt-BR.md)

# TCF: compressing tables without turning them into a blob nobody can open

*Technical article, derived from the repository README. Every number here already lives in a
test or in a dated report of the project, and the code blocks on this page run in the suite.*

Source: [`../2026-09-04-release.en.md`](../2026-09-04-release.en.md). The figures are in
[`figuras/en/`](figuras/en/); upload `0-capa` to the header frame and the others where the text
calls them.

---

To a system, a table is text that has to be stored and transmitted. The usual formats for that
carry a cost you do not see at first: JSON repeats every field name on every row, CSV repeats
nothing but also exploits nothing, and gzip solves the size by turning everything into an
opaque block that you can only read after inflating it whole.

TCF (Tabular Compact Format) sits between those two worlds. It compresses much like gzip, with
one difference: the result **stays ASCII text you can open and inspect**, without
decompressing. It does not stay as obvious as the original, because the more TCF factors, the
denser the text gets. But it never becomes an opaque blob.

It is lossless: `decode(encode(x)) == x`, always.

## The same data in three formats

Four people, five fields, every format measured compact.

**JSON**, 451 bytes: repeats every field name on every row.

**CSV**, 277 bytes: drops the names, one line per record.

**TCF**, 242 bytes: what repeats becomes a reference, what is unique stays raw.

![Proportional bars comparing JSON, JSONL, CSV and TCF in real bytes](figuras/en/1-formatos.svg)

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
assert len(wire.encode("utf-8")) == 242
```

And the wire is this, real `encode` output:

```
#TCF.8M!2c=nome,2a=email,1c=cidade,14=plano,!cpf
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

Column names appear once, in the header. `*3|Sao Paulo` says there are three identical rows
there, written once. `^1` says "same as row 1". The domain `@acme.com.br` was written once and
referenced by the other three e-mails.

## How it does that: two layers

**OBAT** (Online Bidirectional Affix Tokenizer) finds what the strings have in common. For each
value it looks for the longest prefix **and** suffix shared with the previous ones: e-mail
domains, URL roots, codes from the same family. It writes the fragment once and references the
rest. It is bidirectional front-coding, and the "bidirectional" is what captures the shared
suffix, not only the prefix.

**HCC** (Hierarchical Compositional Coding) decides what is worth naming and groups repetition.
It takes OBAT's tokens and factors recurring compositions into reusable named references. It
also collapses consecutive repeats, including near-identical sequences such as IDs that only
change at the end. Since a reference points to a reference, the result is an acyclic graph of
fragments, in the spirit of Re-Pair and Sequitur, operating on tokens rather than bytes.

Each column runs its own pipeline, and for each one the encoder generates the candidates and
writes the **smallest**: `min(tcf, raw, dictionary, split)`. The result is never worse by
construction. You do not need to test whether the format inflated your data, because it cannot.

## Nature filters, when the data has a fixed shape

Some values carry a structure a generic compressor cannot exploit. A Brazilian CPF like
`123.456.789-09` has nine useful digits: the punctuation is fixed, and the last two digits are
computed from the others. The opt-in filter stores only the nine, and `decode` recomputes the
check digits and reinserts the punctuation. Exact reconstruction.

Four CPFs in a single column: 69 bytes without the filter, 39 with it, −43%. There are filters
for CPF, CNPJ and IPv4, and all of them are **never-worse**: they compete with the ordinary
pipeline and only win if they shrink it. A value that does not match the shape falls back to a
literal in the same column, without breaking the round-trip.

One detail that matters: a filter is not a type. TCF never validates semantics, and does not
check whether a CPF exists. It is a hypothesis about the **shape** of the text, and the string
comes back byte for byte.

## Querying almost without decompressing

A gzip block on disk makes you allocate memory and inflate everything before you can scan
anything. TCF's structure works as an index: `*N|` is already a ready count, `^1` is already
visible dedup. You can count, group and even sum by reading the markers, materializing only the
part you need.

`view()` is the API over that. It connects without decompressing and only materializes the
column, and the rows, that the aggregator needs.

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
v = view(blob)              # connects, decompresses nothing

v.count()                   # 6, touches no column at all
v.sum("valor")              # 750.0, touches: valor
v.group_count("plano")      # {'Premium': 4, 'Basic': 2}
v.where("cidade", "SP").sum("valor")     # 470.0
```

The filtered sum materializes only `cidade` and `valor`. The other two columns are never
decompressed, and `view.report()` says how much of the blob was read.

![The columns a query materializes, and the ones never touched](figuras/en/3-view.svg)

## The numbers on larger sets

Across the 15 synthetic datasets of EXP-008, with no compressor at all, TCF is the most compact
text format of the set: 3131 bytes against 4872 for CSV, about 36% smaller.

On real multi-column data, 9 Adult and TPC-H tables totalling 136k rows, it is **−33.02%
weighted** against raw CSV. And across the 8 real datasets of EXP-019 the set fell from 390,863
to 290,949 bytes, **−25.6%**, ranging from −4.1% to −46.6% depending on the data.

The format reads nested structure as of 0.8. It consumes the dataset your language builds from
JSON, so nested objects, arrays, `null` and typed booleans round-trip byte for byte. Two
records with a list inside: 184 bytes in compact JSON, 144 in TCF with the CPF filter.

## And against gzip, brotli, zstd?

Not a competitor, a layer underneath. In transmission `Content-Encoding` is negotiated by the
transport and is invisible to your code: by the time your handler reads the body, it has
already been inflated. The honest question is not "TCF or brotli", it is **what my process
holds and parses once the channel has done its invisible work**.

On the four-record set, under channel compression at maximum level:

![Channel compression table: JSON, JSONL, CSV and TCF](figuras/en/4-tabela.svg)

Under `gzip` the three API formats tie within 1 byte. TCF wins raw, under `br` and under
`zstd`. And CSV, which is rarely an API payload and has no `view`, is smaller once compressed
at this tiny size.

## Where this applies today

**It is pre-1.0**, at 0.8.4. The current cycle closed functionality: four wire families welded
and published. The next cycle is algorithm optimization, and it has not started.

**Writing is expensive, reading is cheap.** The work sits in `encode`, in the affix search.
`decode` is a single linear pass, with O(1) lookups and no search. That decides where the
format pays off: cacheable data pays the encode once and distributes many times, while data
personalized per request pays it every time.

**Under `gzip`, TCF does not win.** At tiny sizes, CSV beats it.

**Comparison against Parquet and storage formats has not been done.** They occupy a different
place and deserve their own measurement.

## Practical

Python 3.10 or newer, zero runtime dependencies, MIT.

```
pip install tcf-format
```

The code, the measurements and the documentation of what does not work are open:

https://github.com/LeoPR/TCF

#Python #Compression #DataEngineering #OpenSource #DataFormats

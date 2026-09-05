[Português](pagina.md) · **English**

# TCF: as small as a compressor, as readable as text

Illustrated page to assemble on any channel. The images live in [`figuras/en/`](figuras/en/) and
can be reordered or used on their own. Nothing here is drawn: the bytes are measured with a
validated round-trip, and the wire shown is what `encode` returns. Everything comes from
`python scripts/make_divulgacao_figuras.py`.

To a system, a table is text that has to be stored and transmitted. The usual formats carry a
cost you do not see at first: JSON repeats every field name on every row, CSV repeats nothing
but exploits nothing either, and gzip solves the size by turning everything into an opaque
block.

The figures are linked as **SVG**, which is what the repository versions and what GitHub
renders. To upload to LinkedIn, convert them to PNG: any browser opens the SVG and exports it,
and the script produces the PNG itself when `cairosvg` is installed.

## 1. The same records, three formats

![Proportional bars comparing JSON, JSONL, CSV and TCF in real bytes](figuras/en/1-formatos.svg)

Four people and five fields. JSON spends 451 bytes because it writes `"nome"`, `"email"`,
`"cidade"`, `"plano"` and `"cpf"` again in every record. CSV drops the names and falls to 277.
TCF reaches 242 by factoring what repeats inside the columns, not only across rows.

The difference is not that the format is smarter in general. It is that it looks at the table
**per column**, which is where the repetition actually lives.

## 2. What the compressor leaves in plain sight

![The real encode output, with four highlighted and annotated lines](figuras/en/2-wire.svg)

This is the string you send. It is not a hex dump, and it needs no tool to open.

The header carries the column names once. `*3|Sao Paulo` says there are three identical rows
there, written once. `^1` says "same as row 1". And the domain `@acme.com.br` appears once,
referenced by the other three e-mails.

It is worth being exact about what that means, because the density misleads. **It is not loss:**
the round-trip returns the table identical, `decode(encode(x)) == x`. What disappeared was the
repetition, not the data.

## 3. A query materializes only what it needs

![Four columns, two marked as materialized and two as never decompressed](figuras/en/3-view.svg)

This is where readability stops being comfort and becomes capability.

A compressed block on disk forces you to allocate memory and inflate everything before scanning
anything. Because TCF's structure stays in plain sight, it doubles as an index: you can count,
group and sum by reading the markers.

In the filtered sum shown, `cidade` and `valor` were materialized, `cliente` and `plano` were
never touched, and the total read was 39.9% of the blob. That number comes from `view.report()`,
not from an estimate.

## 4. And against gzip, brotli, zstd?

![The channel compression table, with JSON, JSONL, CSV and TCF](figuras/en/4-tabela.svg)

Not a competitor, a layer underneath, and the comparison is usually misplaced.

In transmission `Content-Encoding` is negotiated by the transport and is invisible to your code:
by the time the handler reads the body, it has already been inflated. What is left is the
question of what your process holds and parses after that.

The numbers say the rest without needing a defence. Under `gzip` the three API formats tie
within 1 byte. TCF wins raw, under `br` and under `zstd`. And CSV, which is rarely an API payload
and has no `view`, is smaller once compressed at this tiny size.

## Where this applies today

It is pre-1.0, at 0.8.4. The current cycle closed functionality, and algorithm optimization is
the next one. Writing is expensive and reading is cheap, so the format pays off on cacheable
data and charges dearly on data personalized per request. And the comparison against Parquet and
storage formats has not been done.

`pip install tcf-format` · Python 3.10 or newer · zero dependencies · MIT.

https://github.com/LeoPR/TCF

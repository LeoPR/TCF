[Português](README.pt-BR.md) · **English**

# `docs/divulgacao/`: material for presenting TCF

Pieces for showing the project publicly. It is supporting material, not the library's
documentation, which lives in the sibling folders. It publishes no new measurement: every number
comes from a dated document in the repository, and each one names where it is reproduced.

## How it is organized

The **root** holds the dated **news source**: one file per announcement, with the state, the
headlines and the limits stated in full. The **subfolders** are the **channels**, and each gives
that source the shape its medium accepts.

The rule that keeps the two aligned: no channel text changes without the dated source changing
first.

| Path | What it is |
|---|---|
| [`2026-09-04-lancamento.md`](2026-09-04-lancamento.md) / [`2026-09-04-release.en.md`](2026-09-04-release.en.md) | the current news source (PT / EN) |
| [`linkedin/post.*`](linkedin/) | the short feed piece, one per language |
| [`linkedin/artigo.*`](linkedin/) | the article, one per language, **ready to paste** |
| [`linkedin/figuras/<language>/`](linkedin/figuras/) | the five figures, one folder per language |

Two texts per language and nothing else. LinkedIn has two areas: the feed post, with a hard
character limit, and the article, which takes long text but in a narrow column. Each file
serves one of them.

It sits under `docs/` because **outreach documents are documents**. A second hierarchy at the
repository root would make the reader choose between two places to look for the same thing.

**The article comes out ready to paste.** The LinkedIn editor does not render tables and its
column is narrow, so the article has no table: where one would go, it calls the `4-tabela` figure,
built from the same numbers so text and image cannot diverge. The code blocks are narrow for the
same reason. Paste the text and upload the figures where it calls them.

The figures live in `linkedin/figuras/<language>/`, one subfolder per language so the channel
directory does not mix text with binaries. `scripts/make_divulgacao_figuras.py` generates them
all, and running it regenerates everything. They obey the same rule as the numbers in the text:
there is a command that reproduces them.

They come out as **SVG**, which is text and can be edited. The PNG that LinkedIn wants is
produced alongside only if `cairosvg` is installed, and the script warns instead of failing when
it is not.

None of them is an illustration. The bars are bytes measured with the round-trip validated
first, the wire shown is what `encode` actually returns, and the materialized columns in figure 3
come from `view.report()`.

There are five per language, numbered in reading order: `0-capa` is the 1.91:1 header frame,
`1-formatos` compares the four formats, `2-wire` annotates the real output, `3-view` shows what a
query materializes, and `4-tabela` is the compression table the editor will not render.

Here Portuguese is the canonical language, unlike the rest of the project, because the audience
these texts address reads Portuguese first. English is the translation.

## Limits of each channel

- **LinkedIn post** (`linkedin/post.*`): about 3,000 characters, and only the first two or three
  lines appear before "see more". Those lines cannot contain jargon: the audience is broad, and a
  first sentence that only speaks to people who already know compression filters instead of
  inviting. Context before jargon, density without a lecturing tone, and an ending that closes
  rather than stops. Hashtags at the end and without accents, because an accented hashtag breaks
  LinkedIn search.
- **LinkedIn article** (`linkedin/artigo.*`): long form, with headings rendering, good for the
  version that carries the numbers. **Tables do not render and the column is narrow**, so no
  tables and no wide lines: what would be a table becomes a figure. Ends with the repository
  link.

## Before publishing

**None of the numbers in these texts has an instrument of its own, and that is deliberate.** Each
one still belongs to whoever already owned it: the canonical sizes to
`tests/test_regression_v1_baseline.py`, which pins them byte for byte and runs the §RT
round-trip; the real-data gains to the dated EXP-019 report; the timings to the pinned baseline
of `scripts/bench_perf`. An outreach script measuring the same thing would create a second truth
to diverge from the first.

What outreach adds is that **the examples run**. The current source and the articles are in
`PAGINAS_DIDATICAS` of `tests/test_docs_snippets.py`, alongside the README and the reference, and
the source carries its own size assertions. A number that goes stale breaks the suite.

**What these texts avoid on purpose:**

- superlatives. The hook is the reader's problem, not the project's advantage;
- saying "smaller" without saying smaller than what, measured how, and on which data;
- development history. These texts say what the library does today. The path here stays in
  `CHANGELOG.md`, the ADRs and the dated labs, which is where someone looks on purpose. The
  reason is the reader's: whoever arrives now never saw the old version.

**Do not soften the limits section.** It is short, it is true, and it is the part that gives the
rest its credibility. Here it includes what does not favour the project: under `gzip` the formats
tie within 1 B, CSV beats TCF once compressed at tiny sizes, algorithm optimization is the next
cycle and has not happened, and the comparison against Parquet has not been done.

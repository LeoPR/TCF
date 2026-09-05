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
| [`linkedin/`](linkedin/) | LinkedIn: `post.*` (short), `artigo.*` (long technical), `page.md` (illustrated) and the figures |

It sits under `docs/` because **outreach documents are documents**. A second hierarchy at the
repository root would make the reader choose between two places to look for the same thing.

**To publish the article**, use `linkedin/artigo-linkedin.en.md`, which is the same article
generated without the two things the LinkedIn editor cannot do: inline code and tables. The table
becomes the `4-tabela` image, extracted from the article itself so the numbers cannot diverge,
and the file carries the paste-by-paste instructions at the top plus `[IMAGEM: ...]` markers at
the exact point each figure goes. Do not edit that file: edit the article and run the script.

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

**The text stays outside the images**, in `linkedin/pagina.md` and `linkedin/page.md`, which is
the page assembled with the figures linked. That way the text stays editable and the images can
be reordered or used on their own, instead of being baked into pixels.

Here Portuguese is the canonical language, unlike the rest of the project, because the audience
these texts address reads Portuguese first. English is the translation.

## Limits of each channel

- **LinkedIn post** (`linkedin/post.*`): about 3,000 characters, and only the first two or three
  lines appear before "see more". Those lines cannot contain jargon: the audience is broad, and a
  first sentence that only speaks to people who already know compression filters instead of
  inviting. Context before jargon, density without a lecturing tone, and an ending that closes
  rather than stops. Hashtags at the end and without accents, because an accented hashtag breaks
  LinkedIn search.
- **LinkedIn article** (`linkedin/artigo.*`): long form, with headings and tables rendering, good
  for the version that carries the numbers. Ends with the repository link.

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

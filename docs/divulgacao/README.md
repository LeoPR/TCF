[Português](README.pt-BR.md) · **English**

# `docs/divulgacao/`: material for presenting TCF

This folder contains text and figures for presenting the project outside the repository.
Usage documentation lives in sibling folders. These pieces adapt existing evidence:
every measurement must retain its source, comparison baseline and scope.

## Audience and purpose

The texts share facts, not one wording or structure. Each should answer the question that
brings its reader to that surface:

| surface | reader's need | editorial priority |
|---|---|---|
| [GitHub README](../../README.md) | understand, evaluate or contribute to the project | purpose, quick start, format, evidence, limits and technical navigation |
| [PyPI page](../../README.pypi.md) | install the library and use it in Python | Python requirement, installation/import names, complete examples, contracts and compatibility; absolute links |
| LinkedIn article | understand an idea without knowing the project | context, example, explanation, application and conclusion; introduce terms before relying on them |
| LinkedIn post | decide whether to open the article | one central idea, a short example, a relevant caveat and an invitation to read |
| outreach source | verify what can be claimed | facts, provenance, testable examples and limits; no promotional hook |

An article can develop an argument; a README should support lookup and evaluation.
A post need not reproduce the feature catalog, and the PyPI page need not repeat the
algorithm's internal design.

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
| [`linkedin/artigo.*`](linkedin/) | the article, one per language, with separate publishing notes |
| [`linkedin/figuras/<language>/`](linkedin/figuras/) | figures, one folder per language |

There are two texts per language: a feed introduction and a long-form article. Notes at the
start of each file are publishing instructions, not part of the reader-facing text.

It sits under `docs/` because **outreach documents are documents**. A second hierarchy at the
repository root would make the reader choose between two places to look for the same thing.

The article uses figures for tabular comparisons and short code blocks for readability in
a narrow column. When publishing, apply headings, links and code blocks in the editor,
insert the indicated images and check the preview. Pasting Markdown does not replace
that check.

The figures live in `linkedin/figuras/<language>/`, one subfolder per language so the channel
directory does not mix text with binaries. `scripts/make_divulgacao_figuras.py` generates them
all, and running it regenerates everything. They obey the same rule as the numbers in the text:
there is a command that reproduces them.

They come out as **SVG and PNG** side by side. The SVG is text, the repository versions it and
GitHub renders it; the PNG is what you upload, because **LinkedIn does not accept SVG**.

The conversion uses the machine's own Chrome or Edge in headless mode, so it installs nothing.
It renders at 2× on purpose: LinkedIn downsamples the image, and thin text at 1× comes out dirty
after that. With no browser available the script reports which figures have no PNG instead of
failing.

Result figures use executable evidence: bars represent sizes measured after round-trip
validation, encoded text comes from `encode`, and the query figure uses `view.report()`.
Captions and conclusions still need editorial review.

There are six SVGs per language: `0-capa` is the 1.91:1 cover; `1-formatos` compares formats;
`2-wire` annotates the output; `3-view` shows queried columns; `4-tabela` compares external
compression; `5-pipeline` presents the encoding stages. Use the figures referenced by
the piece, not necessarily the whole set.

Here Portuguese is the canonical language, unlike the rest of the project, because the audience
these texts address reads Portuguese first. English is the translation.

## Limits of each channel

- **LinkedIn post** (`linkedin/post.*`): body budget of up to 3,000 characters, including
  links and hashtags. Leave room for the final URL. The opening must make sense on its own
  in the preview, whose cutoff varies by interface. Use plain text, context before jargon
  and hashtags at the end; unaccented hashtags are an editorial convention.
- **LinkedIn article** (`linkedin/artigo.*`): long form, developing an argument with
  transitions between sections. Use figures instead of wide tables and explain examples
  before drawing conclusions. Close with limits and a route to trying the project.

## Before publishing

Check every number against its named source. The
[baselines](../../tests/test_regression_v1_baseline.py) protect canonical output;
[EXP-019](../../experiments/lab/clean/EXP-019-consistencia-0-8-4/report.md) compares two
internal TCF representations, not TCF against CSV; the
[performance tools](../../scripts/bench_perf/) cover timing and memory.

The current source and articles participate in the
[example tests](../../tests/test_docs_snippets.py). They execute Python blocks and their
assertions, but do not automatically verify every number in prose, the images or the
LinkedIn presentation. Also check links, captions, post length and replacement of the
placeholder with the published URL.

**What these texts avoid on purpose:**

- superlatives. The hook is the reader's problem, not the project's advantage;
- saying "smaller" without saying smaller than what, measured how, and on which data;
- development history. These texts say what the library does today. The path here stays in
  `CHANGELOG.md`, the ADRs and the dated labs, which is where someone looks on purpose. The
  reason is the reader's: whoever arrives now never saw the old version.

**Keep caveats beside the claims they qualify.** The gzip tie and compressed CSV advantage
belong to the small example, not all data. Encoding cost, pre-1.0 compatibility and the
absence of a storage-format comparison must not disappear when a piece is shortened.
Consult the [current status](../../STATUS.md) when describing work in progress.
